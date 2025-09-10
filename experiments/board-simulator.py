#!/usr/bin/env python3
"""
Pipeline & Peril - Visual Board Simulator
Simulates 4-player game with visual board representation and dice-specific actions.
"""

import random
import argparse
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from PIL import Image, ImageDraw, ImageFont
import math


class ServiceState(Enum):
    """Service states in the distributed system."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    FAILED = "failed"
    CASCADING = "cascading"


class DiceType(Enum):
    """Available dice types with their specific purposes."""
    D4 = (4, "latency")      # Network latency rolls
    D6 = (6, "resource")     # Resource allocation
    D8 = (8, "bug")          # Bug generation
    D10 = (10, "traffic")    # Traffic generation
    D12 = (12, "chaos")      # Chaos engineering
    D20 = (20, "service")    # Service checks


@dataclass
class BoardTile:
    """Represents a hexagonal tile on the board."""
    id: int
    name: str
    service_type: str  # web, api, database, cache, queue, cdn
    state: ServiceState = ServiceState.HEALTHY
    connections: List[int] = field(default_factory=list)
    load: int = 0
    capacity: int = 100
    bugs: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class Player:
    """Represents a player with position and character."""
    id: int
    name: str
    character_type: str
    position: int  # Current tile ID
    resources: int = 50
    reputation: int = 0
    cards: List[str] = field(default_factory=list)
    color: str = "blue"


class BoardSimulator:
    """Simulates the visual board game with 4 players."""
    
    def __init__(self, board_image_path: str = "board-image.webp"):
        self.board_image_path = board_image_path
        self.round = 0
        self.tiles = self._create_board()
        self.players = self._create_players()
        self.game_state = {
            'global_chaos_level': 0,
            'network_stability': 100,
            'total_bugs': 0,
            'active_incidents': []
        }
        self.history = []
        
        # Load and process board image
        self._load_board_image()
    
    def _load_board_image(self):
        """Load and resize the board image."""
        try:
            self.board_image = Image.open(self.board_image_path)
            # Resize to standard size for display
            self.board_image = self.board_image.resize((800, 600), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Warning: Could not load board image: {e}")
            # Create a simple placeholder
            self.board_image = Image.new('RGB', (800, 600), color='darkgray')
            draw = ImageDraw.Draw(self.board_image)
            draw.text((300, 250), "Pipeline & Peril", fill='white')
            draw.text((320, 300), "Board Game", fill='white')
    
    def _create_board(self) -> Dict[int, BoardTile]:
        """Create the hexagonal board layout inspired by the image."""
        tiles = {}
        
        # Based on the board image, create service tiles
        services = [
            (1, "LoadBalancer", "web"),
            (2, "AuthService", "api"),
            (3, "UserDB", "database"),
            (4, "SessionCache", "cache"),
            (5, "MessageQueue", "queue"),
            (6, "CDN", "cdn"),
            (7, "PaymentAPI", "api"),
            (8, "InventoryDB", "database"),
            (9, "LoggingService", "api"),
            (10, "MetricsDB", "database"),
            (11, "NotificationQueue", "queue"),
            (12, "ImageCache", "cache"),
            (13, "SearchAPI", "api"),
            (14, "BackupService", "api"),
            (15, "MonitoringDash", "web"),
            (16, "HealthCheck", "api"),
            (17, "ConfigService", "api"),
            (18, "AuditLog", "database"),
            (19, "EmailQueue", "queue")
        ]
        
        # Create tiles with hex grid positions
        for i, (tile_id, name, service_type) in enumerate(services):
            # Arrange in hexagonal pattern
            row = i // 5
            col = i % 5
            x = col * 60 + (row % 2) * 30
            y = row * 52
            
            tiles[tile_id] = BoardTile(
                id=tile_id,
                name=name,
                service_type=service_type,
                x=x + 100,  # Offset for board margins
                y=y + 100,
                capacity=random.randint(80, 120)
            )
        
        # Define network connections (based on typical microservice architecture)
        connections = {
            1: [2, 3, 6],      # LoadBalancer -> Auth, UserDB, CDN
            2: [3, 4, 7],      # AuthService -> UserDB, SessionCache, PaymentAPI
            3: [4, 8],         # UserDB -> SessionCache, InventoryDB
            4: [5],            # SessionCache -> MessageQueue
            5: [11, 19],       # MessageQueue -> NotificationQueue, EmailQueue
            6: [12, 13],       # CDN -> ImageCache, SearchAPI
            7: [8, 9],         # PaymentAPI -> InventoryDB, LoggingService
            8: [10],           # InventoryDB -> MetricsDB
            9: [10, 18],       # LoggingService -> MetricsDB, AuditLog
            10: [15],          # MetricsDB -> MonitoringDash
            11: [19],          # NotificationQueue -> EmailQueue
            12: [13],          # ImageCache -> SearchAPI
            13: [14],          # SearchAPI -> BackupService
            14: [16, 17],      # BackupService -> HealthCheck, ConfigService
            15: [16],          # MonitoringDash -> HealthCheck
            16: [17],          # HealthCheck -> ConfigService
            17: [18],          # ConfigService -> AuditLog
        }
        
        for tile_id, connected_ids in connections.items():
            if tile_id in tiles:
                tiles[tile_id].connections = connected_ids
        
        return tiles
    
    def _create_players(self) -> List[Player]:
        """Create 4 players with different starting positions and characters."""
        characters = ["developer", "architect", "manager", "devops"]
        colors = ["red", "blue", "green", "yellow"]
        start_positions = [1, 5, 10, 15]  # Corner positions
        
        players = []
        for i in range(4):
            player = Player(
                id=i + 1,
                name=f"Player {i + 1}",
                character_type=characters[i],
                position=start_positions[i],
                color=colors[i]
            )
            players.append(player)
        
        return players
    
    def roll_dice(self, dice_type: DiceType, count: int = 1, modifier: int = 0) -> Tuple[List[int], int]:
        """Roll specified dice type with count and modifier."""
        sides = dice_type.value[0]
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        return rolls, total
    
    def simulate_turn(self, player: Player) -> Dict:
        """Simulate a complete turn for one player."""
        turn_result = {
            'player_id': player.id,
            'player_name': player.name,
            'character': player.character_type,
            'starting_position': player.position,
            'actions': [],
            'ending_position': player.position,
            'resources_gained': 0,
            'reputation_change': 0
        }
        
        current_tile = self.tiles[player.position]
        print(f"\n{player.name} ({player.character_type}) at {current_tile.name}")
        print("-" * 50)
        
        # Action 1: Traffic Generation (2d10)
        traffic_rolls, traffic_total = self.roll_dice(DiceType.D10, 2)
        print(f"🚦 Traffic Generation: {traffic_rolls} = {traffic_total}")
        current_tile.load += traffic_total
        
        turn_result['actions'].append({
            'type': 'traffic_generation',
            'dice': f"2d10",
            'rolls': traffic_rolls,
            'total': traffic_total,
            'tile_affected': current_tile.name
        })
        
        # Action 2: Service Check (d20)
        service_rolls, service_total = self.roll_dice(DiceType.D20, 1)
        character_bonus = self._get_character_bonus(player.character_type, 'service_check')
        final_service = service_total + character_bonus
        
        # Determine service state based on load and roll
        load_penalty = max(0, (current_tile.load - current_tile.capacity) // 10)
        effective_roll = final_service - load_penalty
        
        if effective_roll >= 18:
            result = "CRITICAL SUCCESS"
            current_tile.state = ServiceState.HEALTHY
            current_tile.load = max(0, current_tile.load - 20)
            player.reputation += 3
            turn_result['reputation_change'] += 3
        elif effective_roll >= 12:
            result = "SUCCESS"
            current_tile.state = ServiceState.HEALTHY
            current_tile.load = max(0, current_tile.load - 10)
            player.reputation += 1
            turn_result['reputation_change'] += 1
        elif effective_roll >= 8:
            result = "PARTIAL SUCCESS"
            current_tile.state = ServiceState.DEGRADED
        elif effective_roll >= 4:
            result = "FAILURE"
            current_tile.state = ServiceState.OVERLOADED
            self._spawn_bugs(current_tile, player)
        else:
            result = "CRITICAL FAILURE"
            current_tile.state = ServiceState.FAILED
            self._spawn_bugs(current_tile, player)
            self._check_cascade_failure(current_tile)
        
        print(f"🎲 Service Check: {service_rolls[0]}")
        if character_bonus != 0:
            print(f"   Character Bonus: {character_bonus:+d}")
        if load_penalty > 0:
            print(f"   Load Penalty: -{load_penalty}")
        print(f"   Final: {effective_roll} → {result}")
        
        turn_result['actions'].append({
            'type': 'service_check',
            'dice': 'd20',
            'roll': service_rolls[0],
            'bonus': character_bonus,
            'load_penalty': load_penalty,
            'final_total': effective_roll,
            'result': result,
            'tile_state': current_tile.state.value
        })
        
        # Action 3: Resource Allocation (3d6)
        resource_rolls, resource_total = self.roll_dice(DiceType.D6, 3)
        character_bonus = self._get_character_bonus(player.character_type, 'resource_allocation')
        final_resources = resource_total + character_bonus
        player.resources += final_resources
        turn_result['resources_gained'] = final_resources
        
        print(f"💰 Resource Allocation: {resource_rolls} = {resource_total}")
        if character_bonus != 0:
            print(f"   Character Bonus: {character_bonus:+d}")
        print(f"   Total Gained: {final_resources}")
        
        turn_result['actions'].append({
            'type': 'resource_allocation',
            'dice': '3d6',
            'rolls': resource_rolls,
            'bonus': character_bonus,
            'total': final_resources
        })
        
        # Action 4: Movement (optional, based on resources)
        if player.resources >= 10:
            movement_choice = random.choice([True, False])  # AI decision
            if movement_choice and current_tile.connections:
                new_position = random.choice(current_tile.connections)
                player.resources -= 10
                old_position = player.position
                player.position = new_position
                turn_result['ending_position'] = new_position
                
                print(f"🚶 Movement: {self.tiles[old_position].name} → {self.tiles[new_position].name}")
                print(f"   Cost: 10 resources")
                
                turn_result['actions'].append({
                    'type': 'movement',
                    'from_tile': old_position,
                    'to_tile': new_position,
                    'cost': 10
                })
        
        # Action 5: Special Character Ability
        special_result = self._use_character_ability(player, current_tile)
        if special_result:
            turn_result['actions'].append(special_result)
        
        print(f"💎 Resources: {player.resources} | ⭐ Reputation: {player.reputation}")
        
        return turn_result
    
    def _get_character_bonus(self, character: str, action: str) -> int:
        """Get character-specific bonuses for actions."""
        bonuses = {
            'developer': {
                'service_check': 2,
                'bug_spawn': -1,
                'latency_reduction': 2
            },
            'architect': {
                'cascade_check': 3,
                'resource_allocation': 1,
                'network_design': 2
            },
            'manager': {
                'resource_allocation': 2,
                'traffic_generation': 1,
                'team_coordination': 3
            },
            'devops': {
                'service_check': 1,
                'chaos_event': -2,
                'monitoring': 3
            }
        }
        
        return bonuses.get(character, {}).get(action, 0)
    
    def _spawn_bugs(self, tile: BoardTile, player: Player):
        """Spawn bugs when services fail."""
        bug_rolls, bug_total = self.roll_dice(DiceType.D8, 1)
        character_bonus = self._get_character_bonus(player.character_type, 'bug_spawn')
        bugs_spawned = max(0, (bug_total + character_bonus) // 3)
        
        tile.bugs += bugs_spawned
        self.game_state['total_bugs'] += bugs_spawned
        
        print(f"🐛 Bug Spawn: {bug_rolls[0]} → {bugs_spawned} bugs")
    
    def _check_cascade_failure(self, tile: BoardTile):
        """Check if failure cascades to connected services."""
        cascade_rolls, cascade_total = self.roll_dice(DiceType.D20, 1)
        
        if cascade_total <= 8:  # 40% chance of cascade
            print(f"⚠️  CASCADE FAILURE! {cascade_rolls[0]} ≤ 8")
            
            for connected_id in tile.connections:
                if connected_id in self.tiles:
                    connected_tile = self.tiles[connected_id]
                    if connected_tile.state != ServiceState.FAILED:
                        connected_tile.state = ServiceState.CASCADING
                        connected_tile.load += 30
                        print(f"   → {connected_tile.name} now cascading")
        else:
            print(f"✅ No cascade: {cascade_rolls[0]} > 8")
    
    def _use_character_ability(self, player: Player, tile: BoardTile) -> Optional[Dict]:
        """Use character-specific special abilities."""
        if player.resources < 15:
            return None
        
        abilities = {
            'developer': self._developer_ability,
            'architect': self._architect_ability,
            'manager': self._manager_ability,
            'devops': self._devops_ability
        }
        
        ability_func = abilities.get(player.character_type)
        if ability_func:
            return ability_func(player, tile)
        
        return None
    
    def _developer_ability(self, player: Player, tile: BoardTile) -> Dict:
        """Developer: Debug and fix bugs."""
        if tile.bugs > 0:
            bugs_fixed = min(tile.bugs, 3)
            tile.bugs -= bugs_fixed
            player.resources -= 15
            player.reputation += bugs_fixed
            
            print(f"🔧 Developer Ability: Fixed {bugs_fixed} bugs")
            
            return {
                'type': 'special_ability',
                'ability': 'debug_bugs',
                'bugs_fixed': bugs_fixed,
                'cost': 15,
                'reputation_gained': bugs_fixed
            }
        return None
    
    def _architect_ability(self, player: Player, tile: BoardTile) -> Dict:
        """Architect: Redesign network topology."""
        if tile.state in [ServiceState.DEGRADED, ServiceState.OVERLOADED]:
            tile.capacity += 20
            tile.state = ServiceState.HEALTHY
            player.resources -= 15
            player.reputation += 2
            
            print(f"🏗️  Architect Ability: Increased capacity by 20")
            
            return {
                'type': 'special_ability',
                'ability': 'increase_capacity',
                'capacity_added': 20,
                'cost': 15,
                'reputation_gained': 2
            }
        return None
    
    def _manager_ability(self, player: Player, tile: BoardTile) -> Dict:
        """Manager: Allocate additional resources."""
        bonus_resources = 25
        player.resources += bonus_resources - 15  # Net gain of 10
        
        print(f"💼 Manager Ability: Gained {bonus_resources} resources")
        
        return {
            'type': 'special_ability',
            'ability': 'resource_boost',
            'resources_gained': bonus_resources,
            'cost': 15
        }
    
    def _devops_ability(self, player: Player, tile: BoardTile) -> Dict:
        """DevOps: Monitor and prevent issues."""
        if tile.load > tile.capacity * 0.7:
            load_reduced = min(tile.load, 40)
            tile.load -= load_reduced
            player.resources -= 15
            player.reputation += 1
            
            print(f"📊 DevOps Ability: Reduced load by {load_reduced}")
            
            return {
                'type': 'special_ability',
                'ability': 'load_balancing',
                'load_reduced': load_reduced,
                'cost': 15,
                'reputation_gained': 1
            }
        return None
    
    def simulate_chaos_event(self) -> Dict:
        """Simulate global chaos event affecting all players."""
        chaos_rolls, chaos_total = self.roll_dice(DiceType.D12, 1)
        
        event_types = {
            (1, 3): ("DDoS Attack", "All web services gain +30 load"),
            (4, 6): ("Database Corruption", "All databases spawn 2 bugs each"),
            (7, 9): ("Network Partition", "Break random connections"),
            (10, 12): ("Zero Day Exploit", "All services become vulnerable")
        }
        
        event_name = "Minor Glitch"
        event_description = "Small hiccup in the system"
        
        for (min_roll, max_roll), (name, desc) in event_types.items():
            if min_roll <= chaos_total <= max_roll:
                event_name = name
                event_description = desc
                break
        
        print(f"\n🌪️  CHAOS EVENT: {chaos_rolls[0]} - {event_name}")
        print(f"    {event_description}")
        
        # Apply chaos effects
        if "DDoS" in event_name:
            for tile in self.tiles.values():
                if tile.service_type == "web":
                    tile.load += 30
        elif "Database" in event_name:
            for tile in self.tiles.values():
                if tile.service_type == "database":
                    tile.bugs += 2
                    self.game_state['total_bugs'] += 2
        
        self.game_state['global_chaos_level'] += chaos_total
        
        return {
            'type': 'chaos_event',
            'roll': chaos_rolls[0],
            'event_name': event_name,
            'description': event_description,
            'chaos_level_increase': chaos_total
        }
    
    def create_board_visualization(self, round_num: int) -> str:
        """Create visual representation of current board state."""
        img = self.board_image.copy()
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
            small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 10)
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Draw round info
        draw.text((10, 10), f"Round {round_num}", fill='white', font=font)
        draw.text((10, 30), f"Global Chaos: {self.game_state['global_chaos_level']}", fill='yellow', font=small_font)
        draw.text((10, 45), f"Total Bugs: {self.game_state['total_bugs']}", fill='red', font=small_font)
        
        # Draw tiles with states
        for tile in self.tiles.values():
            x, y = int(tile.x), int(tile.y)
            
            # Color based on state
            state_colors = {
                ServiceState.HEALTHY: 'green',
                ServiceState.DEGRADED: 'yellow',
                ServiceState.OVERLOADED: 'orange',
                ServiceState.FAILED: 'red',
                ServiceState.CASCADING: 'purple'
            }
            
            color = state_colors.get(tile.state, 'gray')
            
            # Draw hexagon (simplified as circle)
            radius = 15
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color, outline='white')
            
            # Draw tile info
            if tile.bugs > 0:
                draw.text((x-5, y-25), f"🐛{tile.bugs}", fill='red', font=small_font)
            
            load_percent = min(100, (tile.load / tile.capacity) * 100)
            if load_percent > 80:
                draw.text((x-8, y+20), f"{load_percent:.0f}%", fill='red', font=small_font)
        
        # Draw players
        player_colors = {'red': 'red', 'blue': 'blue', 'green': 'green', 'yellow': 'gold'}
        for player in self.players:
            tile = self.tiles[player.position]
            x, y = int(tile.x), int(tile.y)
            
            # Offset players so they don't overlap
            offset_x = (player.id - 1) * 8 - 12
            offset_y = (player.id - 1) * 8 - 12
            
            color = player_colors.get(player.color, 'white')
            draw.ellipse([x+offset_x-3, y+offset_y-3, x+offset_x+3, y+offset_y+3], 
                        fill=color, outline='black')
        
        # Draw player stats
        stats_y = 70
        for i, player in enumerate(self.players):
            color = player_colors.get(player.color, 'white')
            stats_text = f"P{player.id}: {player.resources}R {player.reputation}★"
            draw.text((10, stats_y + i*15), stats_text, fill=color, font=small_font)
        
        # Save image
        filename = f"board_round_{round_num:02d}.png"
        img.save(filename)
        return filename
    
    def simulate_round(self) -> Dict:
        """Simulate one complete round with all players."""
        self.round += 1
        
        print(f"\n{'='*60}")
        print(f"ROUND {self.round}")
        print(f"{'='*60}")
        
        round_result = {
            'round': self.round,
            'timestamp': datetime.now().isoformat(),
            'player_turns': [],
            'chaos_event': None,
            'board_state': {},
            'game_state': self.game_state.copy()
        }
        
        # Each player takes a turn
        for player in self.players:
            turn_result = self.simulate_turn(player)
            round_result['player_turns'].append(turn_result)
        
        # Global chaos event
        chaos_result = self.simulate_chaos_event()
        round_result['chaos_event'] = chaos_result
        
        # Save board state
        round_result['board_state'] = {
            tile_id: {
                'name': tile.name,
                'state': tile.state.value,
                'load': tile.load,
                'capacity': tile.capacity,
                'bugs': tile.bugs
            }
            for tile_id, tile in self.tiles.items()
        }
        
        # Create visualization
        board_image_file = self.create_board_visualization(self.round)
        round_result['board_image'] = board_image_file
        
        self.history.append(round_result)
        return round_result
    
    def simulate_game(self, num_rounds: int = 5) -> Dict:
        """Simulate complete game."""
        print(f"\n{'='*60}")
        print(f"PIPELINE & PERIL - VISUAL BOARD SIMULATOR")
        print(f"Players: 4 | Rounds: {num_rounds}")
        print(f"{'='*60}")
        
        print("\nPLAYERS:")
        for player in self.players:
            start_tile = self.tiles[player.position]
            print(f"  • {player.name} ({player.character_type}) at {start_tile.name}")
        
        print("\nBOARD SERVICES:")
        for tile in list(self.tiles.values())[:10]:  # Show first 10
            print(f"  • {tile.name} ({tile.service_type}) - Capacity: {tile.capacity}")
        print(f"  ... and {len(self.tiles) - 10} more services")
        
        for _ in range(num_rounds):
            self.simulate_round()
            time.sleep(0.5)  # Brief pause for effect
        
        return self.get_final_statistics()
    
    def get_final_statistics(self) -> Dict:
        """Calculate final game statistics."""
        stats = {
            'game_summary': {
                'total_rounds': len(self.history),
                'winner': None,
                'final_chaos_level': self.game_state['global_chaos_level'],
                'total_bugs_created': self.game_state['total_bugs']
            },
            'players': {},
            'service_performance': {},
            'network_health': 0
        }
        
        # Calculate player scores (reputation + resources/10)
        player_scores = {}
        for player in self.players:
            score = player.reputation + (player.resources // 10)
            player_scores[player.name] = score
            
            stats['players'][player.name] = {
                'character': player.character_type,
                'final_position': self.tiles[player.position].name,
                'resources': player.resources,
                'reputation': player.reputation,
                'score': score,
                'turns_taken': len(self.history)
            }
        
        # Determine winner
        winner = max(player_scores, key=player_scores.get)
        stats['game_summary']['winner'] = winner
        
        # Service performance
        healthy_services = sum(1 for tile in self.tiles.values() 
                             if tile.state == ServiceState.HEALTHY)
        total_services = len(self.tiles)
        stats['network_health'] = (healthy_services / total_services) * 100
        
        for tile in self.tiles.values():
            stats['service_performance'][tile.name] = {
                'final_state': tile.state.value,
                'load_percentage': (tile.load / tile.capacity) * 100,
                'bugs': tile.bugs
            }
        
        return stats
    
    def print_final_results(self):
        """Print final game results."""
        stats = self.get_final_statistics()
        
        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        
        print(f"\n🏆 WINNER: {stats['game_summary']['winner']}")
        print(f"Network Health: {stats['network_health']:.1f}%")
        print(f"Total Chaos Level: {stats['game_summary']['final_chaos_level']}")
        print(f"Total Bugs Created: {stats['game_summary']['total_bugs_created']}")
        
        print("\nFINAL PLAYER STANDINGS:")
        sorted_players = sorted(stats['players'].items(), 
                              key=lambda x: x[1]['score'], reverse=True)
        
        for i, (name, data) in enumerate(sorted_players, 1):
            print(f"{i}. {name} ({data['character']})")
            print(f"   Score: {data['score']} | Resources: {data['resources']} | Reputation: {data['reputation']}")
            print(f"   Final Position: {data['final_position']}")
        
        print("\nSERVICE HEALTH SUMMARY:")
        failed_services = [name for name, data in stats['service_performance'].items()
                          if data['final_state'] == 'failed']
        if failed_services:
            print(f"Failed Services: {', '.join(failed_services)}")
        
        buggy_services = [(name, data['bugs']) for name, data in stats['service_performance'].items()
                         if data['bugs'] > 0]
        if buggy_services:
            print("Services with Bugs:")
            for name, bugs in buggy_services:
                print(f"  • {name}: {bugs} bugs")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pipeline & Peril Visual Board Simulator - 4 players with dice-specific actions"
    )
    parser.add_argument(
        '--rounds', 
        type=int, 
        default=5,
        help='Number of rounds to simulate (default: 5)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducible results'
    )
    parser.add_argument(
        '--board-image',
        default='board-image.webp',
        help='Path to board image file'
    )
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    # Create and run simulator
    simulator = BoardSimulator(args.board_image)
    simulator.simulate_game(num_rounds=args.rounds)
    simulator.print_final_results()
    
    print(f"\nBoard visualizations saved as board_round_XX.png")


if __name__ == "__main__":
    main()