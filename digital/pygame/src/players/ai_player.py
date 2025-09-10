#!/usr/bin/env python3
"""
Pipeline & Peril - AI Player Implementation
Provides autonomous players with different strategic profiles.
"""

import random
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from engine.game_state import GameState, ServiceType, ServiceState, PlayerStrategy


@dataclass
class StrategyWeights:
    """Weights for different action types based on strategy."""
    deploy_service: float = 0.3
    repair_service: float = 0.2
    scale_service: float = 0.1
    conservative_threshold: float = 0.5  # Resources to keep in reserve
    expansion_rate: float = 0.3  # How aggressively to expand
    service_preferences: Dict[ServiceType, float] = None
    
    def __post_init__(self):
        if self.service_preferences is None:
            # Default equal preferences
            self.service_preferences = {
                service_type: 1.0 for service_type in ServiceType
            }


class AIPlayer:
    """Autonomous AI player that can make strategic decisions."""
    
    def __init__(self, player_id: int, strategy: PlayerStrategy = PlayerStrategy.BALANCED):
        self.player_id = player_id
        self.strategy = strategy
        self.weights = self._get_strategy_weights()
        
        # Learning/adaptation tracking
        self.action_history = []
        self.performance_history = []
        
    def _get_strategy_weights(self) -> StrategyWeights:
        """Get strategy weights based on player strategy."""
        if self.strategy == PlayerStrategy.AGGRESSIVE:
            return StrategyWeights(
                deploy_service=0.5,
                repair_service=0.1,
                scale_service=0.2,
                conservative_threshold=0.2,
                expansion_rate=0.8,
                service_preferences={
                    ServiceType.LOAD_BALANCER: 2.0,
                    ServiceType.API_GATEWAY: 1.8,
                    ServiceType.COMPUTE: 1.5,
                    ServiceType.CACHE: 1.2,
                    ServiceType.QUEUE: 1.0,
                    ServiceType.DATABASE: 0.8
                }
            )
        
        elif self.strategy == PlayerStrategy.DEFENSIVE:
            return StrategyWeights(
                deploy_service=0.2,
                repair_service=0.4,
                scale_service=0.3,
                conservative_threshold=0.7,
                expansion_rate=0.3,
                service_preferences={
                    ServiceType.DATABASE: 2.0,
                    ServiceType.CACHE: 1.8,
                    ServiceType.QUEUE: 1.5,
                    ServiceType.COMPUTE: 1.2,
                    ServiceType.LOAD_BALANCER: 1.0,
                    ServiceType.API_GATEWAY: 0.8
                }
            )
        
        elif self.strategy == PlayerStrategy.BALANCED:
            return StrategyWeights(
                deploy_service=0.35,
                repair_service=0.25,
                scale_service=0.15,
                conservative_threshold=0.4,
                expansion_rate=0.5,
                service_preferences={
                    service_type: 1.0 for service_type in ServiceType
                }
            )
        
        else:  # RANDOM
            return StrategyWeights(
                deploy_service=random.uniform(0.2, 0.6),
                repair_service=random.uniform(0.1, 0.4),
                scale_service=random.uniform(0.1, 0.3),
                conservative_threshold=random.uniform(0.2, 0.8),
                expansion_rate=random.uniform(0.2, 0.8),
                service_preferences={
                    service_type: random.uniform(0.5, 2.0) for service_type in ServiceType
                }
            )
    
    def choose_action(self, game_state: GameState) -> Optional[Dict]:
        """Choose the best action for current game state."""
        legal_actions = game_state.get_legal_actions(self.player_id)
        
        if not legal_actions:
            return None
        
        player = game_state.players[self.player_id]
        
        # Emergency repairs take priority
        urgent_repairs = self._find_urgent_repairs(game_state)
        if urgent_repairs and random.random() < 0.8:
            return random.choice(urgent_repairs)
        
        # Strategy-based action selection
        if self.strategy == PlayerStrategy.RANDOM:
            return random.choice(legal_actions)
        
        # Score all legal actions
        scored_actions = []
        for action in legal_actions:
            score = self._score_action(action, game_state)
            scored_actions.append((score, action))
        
        # Sort by score and pick from top options
        scored_actions.sort(reverse=True)
        
        # Add some randomness - pick from top 3 actions
        top_actions = scored_actions[:min(3, len(scored_actions))]
        weights = [score for score, _ in top_actions]
        
        if weights:
            chosen_action = random.choices(
                [action for _, action in top_actions],
                weights=weights
            )[0]
            
            # Log action for learning
            self.action_history.append({
                "round": game_state.round,
                "action": chosen_action,
                "game_state_hash": hash(str(game_state.to_dict()))
            })
            
            return chosen_action
        
        return None
    
    def _find_urgent_repairs(self, game_state: GameState) -> List[Dict]:
        """Find services that urgently need repair."""
        player = game_state.players[self.player_id]
        urgent_repairs = []
        
        for service_id in player.services_owned:
            service = game_state.services[service_id]
            
            # Prioritize failed or critically overloaded services
            if (service.state in [ServiceState.FAILED, ServiceState.OVERLOADED] or
                service.load > service.capacity * 1.5):
                
                # Check if repair action is available
                repair_action = {
                    "type": "repair",
                    "service_id": service_id
                }
                
                if repair_action in game_state.get_legal_actions(self.player_id):
                    urgent_repairs.append(repair_action)
        
        return urgent_repairs
    
    def _score_action(self, action: Dict, game_state: GameState) -> float:
        """Score an action based on strategy and game state."""
        player = game_state.players[self.player_id]
        base_score = 0.0
        
        if action["type"] == "deploy":
            base_score = self._score_deploy_action(action, game_state)
        elif action["type"] == "repair":
            base_score = self._score_repair_action(action, game_state)
        elif action["type"] == "scale":
            base_score = self._score_scale_action(action, game_state)
        
        # Apply strategy modifiers
        if action["type"] == "deploy":
            base_score *= self.weights.deploy_service
        elif action["type"] == "repair":
            base_score *= self.weights.repair_service
        elif action["type"] == "scale":
            base_score *= self.weights.scale_service
        
        # Add randomness
        base_score += random.uniform(-0.1, 0.1)
        
        return base_score
    
    def _score_deploy_action(self, action: Dict, game_state: GameState) -> float:
        """Score a service deployment action."""
        service_type = ServiceType(action["service_type"])
        position = tuple(action["position"])
        player = game_state.players[self.player_id]
        
        score = 0.0
        
        # Base score from service type preference
        score += self.weights.service_preferences.get(service_type, 1.0)
        
        # Resource efficiency consideration
        props = service_type.value
        total_cost = getattr(props, 'cpu_cost', 1) + getattr(props, 'memory_cost', 1) + getattr(props, 'storage_cost', 1)
        if total_cost > 0:
            efficiency = getattr(props, 'capacity', 1) / total_cost
            score += efficiency * 0.5
        
        # Position scoring
        score += self._score_position(position, service_type, game_state)
        
        # Network effect - bonus for connecting to existing services
        nearby_services = self._count_nearby_services(position, game_state)
        if nearby_services > 0:
            score += nearby_services * 0.3
        
        # Load balancing consideration
        if service_type == ServiceType.LOAD_BALANCER:
            existing_lbs = sum(1 for s in game_state.services.values() 
                             if s.service_type == ServiceType.LOAD_BALANCER and s.owner == self.player_id)
            if existing_lbs == 0:
                score += 2.0  # High priority for first load balancer
            elif existing_lbs < 2:
                score += 1.0  # Medium priority for second
        
        # Conservative resource management
        remaining_resources = player.cpu + player.memory + player.storage - total_cost
        if remaining_resources < self.weights.conservative_threshold * 30:  # 30 = rough max resources
            score *= 0.5  # Penalize if it would use too many resources
        
        return score
    
    def _score_repair_action(self, action: Dict, game_state: GameState) -> float:
        """Score a service repair action."""
        service_id = action["service_id"]
        service = game_state.services[service_id]
        
        score = 1.0  # Base repair score
        
        # Urgency based on service state
        if service.state == ServiceState.FAILED:
            score += 3.0
        elif service.state == ServiceState.OVERLOADED:
            score += 2.0
        elif service.state == ServiceState.DEGRADED:
            score += 1.0
        
        # Critical service types get priority
        if service.service_type in [ServiceType.LOAD_BALANCER, ServiceType.DATABASE]:
            score += 1.5
        
        # Network position importance
        if len(service.connections) > 3:  # Highly connected
            score += 1.0
        
        # Load consideration
        if service.load > service.capacity:
            score += (service.load - service.capacity) * 0.1
        
        return score
    
    def _score_scale_action(self, action: Dict, game_state: GameState) -> float:
        """Score a service scaling action."""
        service_id = action["service_id"]
        service = game_state.services[service_id]
        
        score = 0.5  # Base scale score
        
        # More valuable for high-load services
        load_ratio = service.load / service.capacity if service.capacity > 0 else 0
        if load_ratio > 0.8:
            score += 2.0
        elif load_ratio > 0.6:
            score += 1.0
        
        # Service type considerations
        if service.service_type in [ServiceType.CACHE, ServiceType.QUEUE]:
            score += 0.5  # These benefit more from scaling
        
        return score
    
    def _score_position(self, position: Tuple[int, int], service_type: ServiceType, 
                       game_state: GameState) -> float:
        """Score a board position for placing a service."""
        row, col = position
        score = 0.0
        
        # Central positions are generally better
        center_row = game_state.config.board_rows // 2
        center_col = game_state.config.board_cols // 2
        
        distance_from_center = abs(row - center_row) + abs(col - center_col)
        max_distance = center_row + center_col
        
        centrality_score = 1.0 - (distance_from_center / max_distance)
        score += centrality_score * 0.5
        
        # Strategy-specific position preferences
        if self.strategy == PlayerStrategy.AGGRESSIVE:
            # Prefer expansion toward opponents
            score += self._score_expansion_position(position, game_state)
        elif self.strategy == PlayerStrategy.DEFENSIVE:
            # Prefer positions near own services
            score += self._score_defensive_position(position, game_state)
        
        return score
    
    def _score_expansion_position(self, position: Tuple[int, int], game_state: GameState) -> float:
        """Score position for aggressive expansion strategy."""
        # Prefer positions that extend toward opponent territory
        opponent_services = [s for s in game_state.services.values() if s.owner != self.player_id]
        
        if not opponent_services:
            return 0.0
        
        # Find closest opponent service
        min_distance = float('inf')
        for service in opponent_services:
            distance = abs(position[0] - service.position[0]) + abs(position[1] - service.position[1])
            min_distance = min(min_distance, distance)
        
        # Closer to opponents = higher score
        return 1.0 / (min_distance + 1)
    
    def _score_defensive_position(self, position: Tuple[int, int], game_state: GameState) -> float:
        """Score position for defensive strategy."""
        # Prefer positions near own services
        own_services = [s for s in game_state.services.values() if s.owner == self.player_id]
        
        if not own_services:
            return 0.0
        
        # Find closest own service
        min_distance = float('inf')
        for service in own_services:
            distance = abs(position[0] - service.position[0]) + abs(position[1] - service.position[1])
            min_distance = min(min_distance, distance)
        
        # Closer to own services = higher score
        return 1.0 / (min_distance + 1)
    
    def _count_nearby_services(self, position: Tuple[int, int], game_state: GameState) -> int:
        """Count services within 2 hexes of position."""
        row, col = position
        count = 0
        
        for r in range(max(0, row-2), min(game_state.config.board_rows, row+3)):
            for c in range(max(0, col-2), min(game_state.config.board_cols, col+3)):
                if (r, c) in game_state.board_grid:
                    count += 1
        
        return count
    
    def update_performance(self, game_result: Dict):
        """Update AI based on game performance (for learning)."""
        self.performance_history.append({
            "game_result": game_result,
            "actions_taken": len(self.action_history),
            "final_score": game_result.get("final_score", 0),
            "final_uptime": game_result.get("final_uptime", 0)
        })
        
        # Simple adaptation: if performing poorly, increase randomness
        if len(self.performance_history) >= 3:
            recent_scores = [p["final_score"] for p in self.performance_history[-3:]]
            avg_score = sum(recent_scores) / len(recent_scores)
            
            if avg_score < 10:  # Poor performance threshold
                # Add more randomness to strategy weights
                for key in self.weights.service_preferences:
                    self.weights.service_preferences[key] *= random.uniform(0.9, 1.1)
        
        # Clear old history to prevent memory bloat
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-50:]
        if len(self.performance_history) > 20:
            self.performance_history = self.performance_history[-10:]
    
    def get_statistics(self) -> Dict:
        """Get AI player statistics for analysis."""
        if not self.performance_history:
            return {"games_played": 0}
        
        scores = [p["final_score"] for p in self.performance_history]
        uptimes = [p["final_uptime"] for p in self.performance_history]
        
        return {
            "games_played": len(self.performance_history),
            "avg_score": sum(scores) / len(scores),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "strategy": self.strategy.value,
            "action_types_used": self._get_action_type_distribution(),
            "service_preferences": dict(self.weights.service_preferences)
        }
    
    def _get_action_type_distribution(self) -> Dict[str, int]:
        """Get distribution of action types used."""
        distribution = {}
        for action_record in self.action_history:
            action_type = action_record["action"]["type"]
            distribution[action_type] = distribution.get(action_type, 0) + 1
        return distribution


class AIPlayerManager:
    """Manages multiple AI players and their interactions."""
    
    def __init__(self, strategies: List[PlayerStrategy] = None):
        if strategies is None:
            strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, 
                         PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
        
        self.ai_players = []
        for i, strategy in enumerate(strategies):
            self.ai_players.append(AIPlayer(i, strategy))
    
    def get_action(self, player_id: int, game_state: GameState) -> Optional[Dict]:
        """Get action from specified AI player."""
        if 0 <= player_id < len(self.ai_players):
            return self.ai_players[player_id].choose_action(game_state)
        return None
    
    def update_all_performance(self, game_results: List[Dict]):
        """Update performance for all AI players."""
        for i, ai_player in enumerate(self.ai_players):
            if i < len(game_results):
                ai_player.update_performance(game_results[i])
    
    def get_all_statistics(self) -> Dict:
        """Get statistics for all AI players."""
        return {
            f"player_{i}": ai_player.get_statistics() 
            for i, ai_player in enumerate(self.ai_players)
        }
    
    def save_strategies(self, filename: str):
        """Save current AI strategies to file."""
        data = {
            "ai_players": [
                {
                    "player_id": ai.player_id,
                    "strategy": ai.strategy.value,
                    "weights": {
                        "deploy_service": ai.weights.deploy_service,
                        "repair_service": ai.weights.repair_service,
                        "scale_service": ai.weights.scale_service,
                        "conservative_threshold": ai.weights.conservative_threshold,
                        "expansion_rate": ai.weights.expansion_rate,
                        "service_preferences": {
                            k.value: v for k, v in ai.weights.service_preferences.items()
                        }
                    },
                    "performance_history": ai.performance_history[-5:]  # Last 5 games
                }
                for ai in self.ai_players
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_strategies(self, filename: str):
        """Load AI strategies from file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            for ai_data in data["ai_players"]:
                player_id = ai_data["player_id"]
                if player_id < len(self.ai_players):
                    ai = self.ai_players[player_id]
                    
                    # Update strategy weights
                    weights_data = ai_data["weights"]
                    ai.weights.deploy_service = weights_data["deploy_service"]
                    ai.weights.repair_service = weights_data["repair_service"]
                    ai.weights.scale_service = weights_data["scale_service"]
                    ai.weights.conservative_threshold = weights_data["conservative_threshold"]
                    ai.weights.expansion_rate = weights_data["expansion_rate"]
                    
                    # Update service preferences
                    for service_name, pref in weights_data["service_preferences"].items():
                        service_type = ServiceType(service_name)
                        ai.weights.service_preferences[service_type] = pref
                    
                    # Restore performance history
                    ai.performance_history = ai_data.get("performance_history", [])
        
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load AI strategies from {filename}: {e}")