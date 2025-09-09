#!/usr/bin/env python3
"""
Pipeline & Peril - Dice Simulator
Quick simulator to show dice rolls for multiple players in a game.
"""

import random
import argparse
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class Player:
    """Represents a player in the game."""
    id: int
    name: str
    character_type: str  # developer, architect, manager, devops
    
    def __str__(self):
        return f"{self.name} ({self.character_type})"


class DiceSimulator:
    """Simulates dice rolls for Pipeline & Peril game."""
    
    DICE_TYPES = {
        'd4': 4,
        'd6': 6, 
        'd8': 8,
        'd10': 10,
        'd12': 12,
        'd20': 20
    }
    
    GAME_EVENTS = {
        'traffic_generation': '2d10',
        'service_check': 'd20',
        'resource_allocation': '3d6',
        'chaos_event': 'd12',
        'latency_calculation': '2d12',
        'bug_spawn': 'd8',
        'cascade_check': 'd20'
    }
    
    CHARACTER_BONUSES = {
        'developer': {'service_check': 2, 'bug_spawn': -1},
        'architect': {'cascade_check': 3, 'resource_allocation': 1},
        'manager': {'resource_allocation': 2, 'traffic_generation': 1},
        'devops': {'service_check': 1, 'chaos_event': -2}
    }
    
    def __init__(self, num_players: int = 2, verbose: bool = True):
        self.verbose = verbose
        self.players = self._create_players(num_players)
        self.round = 0
        self.history = []
    
    def _create_players(self, num_players: int) -> List[Player]:
        """Create players with random character types."""
        characters = ['developer', 'architect', 'manager', 'devops']
        players = []
        
        for i in range(num_players):
            char_type = characters[i % len(characters)]
            player = Player(
                id=i+1,
                name=f"Player {i+1}",
                character_type=char_type
            )
            players.append(player)
        
        return players
    
    def roll_dice(self, dice_notation: str) -> Tuple[List[int], int]:
        """
        Roll dice based on notation (e.g., '2d10', 'd20', '3d6').
        Returns tuple of (individual rolls, total).
        """
        rolls = []
        
        if '+' in dice_notation:
            # Handle notation like 'd20+2'
            parts = dice_notation.split('+')
            dice_part = parts[0]
            modifier = int(parts[1])
        else:
            dice_part = dice_notation
            modifier = 0
        
        if 'd' in dice_part:
            if dice_part.startswith('d'):
                # Single die like 'd20'
                num_dice = 1
                die_type = dice_part
            else:
                # Multiple dice like '2d10'
                parts = dice_part.split('d')
                num_dice = int(parts[0])
                die_type = f"d{parts[1]}"
            
            if die_type in self.DICE_TYPES:
                max_value = self.DICE_TYPES[die_type]
                for _ in range(num_dice):
                    roll = random.randint(1, max_value)
                    rolls.append(roll)
        
        total = sum(rolls) + modifier
        return rolls, total
    
    def simulate_round(self) -> Dict:
        """Simulate one round of the game for all players."""
        self.round += 1
        round_results = {
            'round': self.round,
            'timestamp': datetime.now().isoformat(),
            'player_actions': []
        }
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"ROUND {self.round}")
            print(f"{'='*60}")
        
        # Each player performs actions
        for player in self.players:
            player_results = self._player_turn(player)
            round_results['player_actions'].append(player_results)
        
        # Global events that affect all players
        chaos_rolls, chaos_total = self.roll_dice(self.GAME_EVENTS['chaos_event'])
        round_results['chaos_event'] = {
            'rolls': chaos_rolls,
            'total': chaos_total,
            'severity': self._get_chaos_severity(chaos_total)
        }
        
        if self.verbose:
            print(f"\n🌪️  CHAOS EVENT: {chaos_rolls[0]} - {round_results['chaos_event']['severity']}")
        
        self.history.append(round_results)
        return round_results
    
    def _player_turn(self, player: Player) -> Dict:
        """Simulate a single player's turn."""
        results = {
            'player': player.name,
            'character': player.character_type,
            'actions': {}
        }
        
        if self.verbose:
            print(f"\n{player}")
            print("-" * 40)
        
        # Traffic generation (start of turn)
        traffic_rolls, traffic_total = self.roll_dice(self.GAME_EVENTS['traffic_generation'])
        bonus = self.CHARACTER_BONUSES[player.character_type].get('traffic_generation', 0)
        results['actions']['traffic'] = {
            'rolls': traffic_rolls,
            'bonus': bonus,
            'total': traffic_total + bonus
        }
        
        if self.verbose:
            print(f"📊 Traffic: {traffic_rolls} = {traffic_total}")
            if bonus != 0:
                print(f"   Bonus: {bonus:+d} → Total: {traffic_total + bonus}")
        
        # Service check (main action)
        service_rolls, service_total = self.roll_dice(self.GAME_EVENTS['service_check'])
        bonus = self.CHARACTER_BONUSES[player.character_type].get('service_check', 0)
        final_total = service_total + bonus
        success = final_total >= 12  # Base difficulty
        
        results['actions']['service_check'] = {
            'roll': service_rolls[0],
            'bonus': bonus,
            'total': final_total,
            'success': success,
            'critical': service_rolls[0] == 20,
            'fumble': service_rolls[0] == 1
        }
        
        if self.verbose:
            status = "✅ SUCCESS" if success else "❌ FAILURE"
            print(f"🎲 Service Check: {service_rolls[0]}")
            if bonus != 0:
                print(f"   Bonus: {bonus:+d} → Total: {final_total}")
            if service_rolls[0] == 20:
                print(f"   ⭐ CRITICAL SUCCESS! {status}")
            elif service_rolls[0] == 1:
                print(f"   💀 CRITICAL FAILURE!")
            else:
                print(f"   {status}")
        
        # Resource allocation
        resource_rolls, resource_total = self.roll_dice(self.GAME_EVENTS['resource_allocation'])
        bonus = self.CHARACTER_BONUSES[player.character_type].get('resource_allocation', 0)
        results['actions']['resources'] = {
            'rolls': resource_rolls,
            'bonus': bonus,
            'total': resource_total + bonus
        }
        
        if self.verbose:
            print(f"💰 Resources: {resource_rolls} = {resource_total}")
            if bonus != 0:
                print(f"   Bonus: {bonus:+d} → Total: {resource_total + bonus}")
        
        # Bug check (if service failed)
        if not success:
            bug_rolls, bug_total = self.roll_dice(self.GAME_EVENTS['bug_spawn'])
            bonus = self.CHARACTER_BONUSES[player.character_type].get('bug_spawn', 0)
            bugs_spawned = max(0, (bug_total + bonus) // 3)  # Every 3 points = 1 bug
            
            results['actions']['bugs'] = {
                'roll': bug_rolls[0],
                'bonus': bonus,
                'total': bug_total + bonus,
                'spawned': bugs_spawned
            }
            
            if self.verbose:
                print(f"🐛 Bug Check: {bug_rolls[0]}")
                if bonus != 0:
                    print(f"   Bonus: {bonus:+d} → Total: {bug_total + bonus}")
                print(f"   Bugs spawned: {bugs_spawned}")
        
        return results
    
    def _get_chaos_severity(self, roll: int) -> str:
        """Determine chaos event severity based on roll."""
        if roll <= 3:
            return "Minor disruption"
        elif roll <= 6:
            return "Service degradation"
        elif roll <= 9:
            return "Major incident"
        else:
            return "CATASTROPHIC FAILURE"
    
    def simulate_game(self, num_rounds: int = 10) -> Dict:
        """Simulate a complete game."""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"PIPELINE & PERIL - DICE SIMULATOR")
            print(f"Players: {len(self.players)}")
            print(f"Rounds: {num_rounds}")
            print(f"{'='*60}")
            
            print("\nPLAYERS:")
            for player in self.players:
                print(f"  • {player}")
        
        for _ in range(num_rounds):
            self.simulate_round()
        
        return self.get_statistics()
    
    def get_statistics(self) -> Dict:
        """Calculate game statistics."""
        stats = {
            'total_rounds': len(self.history),
            'players': {},
            'overall': {
                'service_checks': {'success': 0, 'failure': 0, 'critical': 0, 'fumble': 0},
                'total_traffic': 0,
                'total_resources': 0,
                'total_bugs': 0,
                'chaos_events': {'minor': 0, 'degradation': 0, 'major': 0, 'catastrophic': 0}
            }
        }
        
        # Initialize player stats
        for player in self.players:
            stats['players'][player.name] = {
                'character': player.character_type,
                'service_success_rate': 0,
                'average_traffic': 0,
                'average_resources': 0,
                'total_bugs': 0,
                'critical_successes': 0,
                'critical_failures': 0
            }
        
        # Process history
        for round_data in self.history:
            # Player actions
            for action in round_data['player_actions']:
                player_name = action['player']
                
                # Service checks
                if 'service_check' in action['actions']:
                    check = action['actions']['service_check']
                    if check['success']:
                        stats['overall']['service_checks']['success'] += 1
                        stats['players'][player_name]['service_success_rate'] += 1
                    else:
                        stats['overall']['service_checks']['failure'] += 1
                    
                    if check['critical']:
                        stats['overall']['service_checks']['critical'] += 1
                        stats['players'][player_name]['critical_successes'] += 1
                    if check['fumble']:
                        stats['overall']['service_checks']['fumble'] += 1
                        stats['players'][player_name]['critical_failures'] += 1
                
                # Traffic
                if 'traffic' in action['actions']:
                    traffic = action['actions']['traffic']['total']
                    stats['overall']['total_traffic'] += traffic
                    stats['players'][player_name]['average_traffic'] += traffic
                
                # Resources
                if 'resources' in action['actions']:
                    resources = action['actions']['resources']['total']
                    stats['overall']['total_resources'] += resources
                    stats['players'][player_name]['average_resources'] += resources
                
                # Bugs
                if 'bugs' in action['actions']:
                    bugs = action['actions']['bugs']['spawned']
                    stats['overall']['total_bugs'] += bugs
                    stats['players'][player_name]['total_bugs'] += bugs
            
            # Chaos events
            chaos = round_data['chaos_event']['severity']
            if 'Minor' in chaos:
                stats['overall']['chaos_events']['minor'] += 1
            elif 'degradation' in chaos:
                stats['overall']['chaos_events']['degradation'] += 1
            elif 'Major' in chaos:
                stats['overall']['chaos_events']['major'] += 1
            elif 'CATASTROPHIC' in chaos:
                stats['overall']['chaos_events']['catastrophic'] += 1
        
        # Calculate averages
        num_rounds = len(self.history)
        if num_rounds > 0:
            for player_name in stats['players']:
                stats['players'][player_name]['service_success_rate'] = (
                    stats['players'][player_name]['service_success_rate'] / num_rounds * 100
                )
                stats['players'][player_name]['average_traffic'] /= num_rounds
                stats['players'][player_name]['average_resources'] /= num_rounds
        
        return stats
    
    def print_statistics(self):
        """Print game statistics summary."""
        stats = self.get_statistics()
        
        print(f"\n{'='*60}")
        print("GAME STATISTICS")
        print(f"{'='*60}")
        
        print(f"\nTotal Rounds: {stats['total_rounds']}")
        
        print("\nOVERALL PERFORMANCE:")
        checks = stats['overall']['service_checks']
        total_checks = checks['success'] + checks['failure']
        if total_checks > 0:
            success_rate = checks['success'] / total_checks * 100
            print(f"  Service Success Rate: {success_rate:.1f}%")
            print(f"  Critical Successes: {checks['critical']}")
            print(f"  Critical Failures: {checks['fumble']}")
        
        print(f"  Total Traffic Generated: {stats['overall']['total_traffic']}")
        print(f"  Total Resources Allocated: {stats['overall']['total_resources']}")
        print(f"  Total Bugs Spawned: {stats['overall']['total_bugs']}")
        
        print("\nCHAOS EVENTS:")
        chaos = stats['overall']['chaos_events']
        for severity, count in chaos.items():
            print(f"  {severity.title()}: {count}")
        
        print("\nPLAYER PERFORMANCE:")
        for player_name, player_stats in stats['players'].items():
            print(f"\n  {player_name} ({player_stats['character']}):")
            print(f"    Service Success Rate: {player_stats['service_success_rate']:.1f}%")
            print(f"    Avg Traffic/Round: {player_stats['average_traffic']:.1f}")
            print(f"    Avg Resources/Round: {player_stats['average_resources']:.1f}")
            print(f"    Total Bugs: {player_stats['total_bugs']}")
            if player_stats['critical_successes'] > 0:
                print(f"    Critical Successes: {player_stats['critical_successes']}")
            if player_stats['critical_failures'] > 0:
                print(f"    Critical Failures: {player_stats['critical_failures']}")
    
    def save_history(self, filename: str = None):
        """Save game history to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dice_simulation_{timestamp}.json"
        
        data = {
            'metadata': {
                'num_players': len(self.players),
                'num_rounds': len(self.history),
                'timestamp': datetime.now().isoformat(),
                'players': [{'name': p.name, 'character': p.character_type} for p in self.players]
            },
            'history': self.history,
            'statistics': self.get_statistics()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nGame history saved to: {filename}")


def main():
    """Main entry point for dice simulator."""
    parser = argparse.ArgumentParser(
        description="Pipeline & Peril Dice Simulator - Simulate dice rolls for multiple players"
    )
    parser.add_argument(
        'players', 
        type=int, 
        nargs='?', 
        default=2,
        help='Number of players (default: 2)'
    )
    parser.add_argument(
        '--rounds', 
        type=int, 
        default=5,
        help='Number of rounds to simulate (default: 5)'
    )
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Suppress detailed output, only show statistics'
    )
    parser.add_argument(
        '--save', 
        metavar='FILE',
        help='Save game history to JSON file'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducible results'
    )
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    # Create and run simulator
    simulator = DiceSimulator(
        num_players=args.players,
        verbose=not args.quiet
    )
    
    # Run simulation
    simulator.simulate_game(num_rounds=args.rounds)
    
    # Always show statistics
    simulator.print_statistics()
    
    # Save if requested
    if args.save:
        simulator.save_history(args.save)


if __name__ == "__main__":
    main()