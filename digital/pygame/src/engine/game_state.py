#!/usr/bin/env python3
"""
Pipeline & Peril - Core Game State Management
Manages the complete state of a distributed systems board game.
"""

import random
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time
from datetime import datetime


class ServiceType(Enum):
    """Types of services in the distributed system."""
    COMPUTE = "compute"
    DATABASE = "database" 
    CACHE = "cache"
    QUEUE = "queue"
    LOAD_BALANCER = "load_balancer"
    API_GATEWAY = "api_gateway"


class ServiceState(Enum):
    """Current operational state of a service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    FAILED = "failed"
    CASCADING = "cascading"


class PlayerStrategy(Enum):
    """AI player strategy types."""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    RANDOM = "random"


@dataclass
class ServiceProperties:
    """Static properties for each service type."""
    cpu_cost: int
    memory_cost: int
    storage_cost: int
    capacity: int
    base_latency: int
    
    @classmethod
    def get_properties(cls, service_type: ServiceType) -> 'ServiceProperties':
        """Get properties for a service type."""
        properties = {
            ServiceType.COMPUTE: cls(2, 2, 1, 5, 10),
            ServiceType.DATABASE: cls(1, 2, 3, 3, 50),
            ServiceType.CACHE: cls(1, 3, 1, 8, 5),
            ServiceType.QUEUE: cls(1, 1, 2, 6, 15),
            ServiceType.LOAD_BALANCER: cls(2, 1, 1, 10, 8),
            ServiceType.API_GATEWAY: cls(1, 1, 1, 7, 12)
        }
        return properties[service_type]


@dataclass
class Service:
    """Individual service instance on the board."""
    id: int
    service_type: ServiceType
    position: Tuple[int, int]  # (row, col) on hex grid
    state: ServiceState = ServiceState.HEALTHY
    load: int = 0
    bugs: int = 0
    connections: Set[int] = field(default_factory=set)
    owner: Optional[int] = None  # Player ID who owns this service
    
    @property
    def properties(self) -> ServiceProperties:
        return ServiceProperties.get_properties(self.service_type)
    
    @property
    def capacity(self) -> int:
        return self.properties.capacity
    
    @property
    def is_overloaded(self) -> bool:
        return self.load > self.capacity
    
    @property
    def load_percentage(self) -> float:
        return (self.load / self.capacity) * 100 if self.capacity > 0 else 0


@dataclass
class Player:
    """Player state including resources and strategy."""
    id: int
    name: str
    strategy: PlayerStrategy
    cpu: int = 20
    memory: int = 20
    storage: int = 20
    score: int = 0
    services_owned: Set[int] = field(default_factory=set)
    actions_remaining: int = 3
    
    def can_afford(self, service_type: ServiceType) -> bool:
        """Check if player can afford to deploy a service."""
        props = ServiceProperties.get_properties(service_type)
        return (self.cpu >= props.cpu_cost and 
                self.memory >= props.memory_cost and 
                self.storage >= props.storage_cost)
    
    def spend_resources(self, service_type: ServiceType) -> bool:
        """Spend resources to deploy a service."""
        if not self.can_afford(service_type):
            return False
        
        props = ServiceProperties.get_properties(service_type)
        self.cpu -= props.cpu_cost
        self.memory -= props.memory_cost
        self.storage -= props.storage_cost
        return True
    
    def gain_resources(self, cpu: int = 0, memory: int = 0, storage: int = 0):
        """Gain resources (e.g., from successful operations)."""
        self.cpu = min(50, self.cpu + cpu)  # Cap at 50
        self.memory = min(50, self.memory + memory)
        self.storage = min(50, self.storage + storage)


@dataclass
class GameConfig:
    """Configuration for game rules and parameters."""
    board_rows: int = 8
    board_cols: int = 6
    max_rounds: int = 10
    uptime_target: float = 0.8
    max_entropy: int = 10
    chaos_threshold: int = 3
    cooperative_mode: bool = True
    

class GameState:
    """Main game state manager."""
    
    def __init__(self, config: GameConfig = None, num_players: int = 4):
        self.config = config or GameConfig()
        self.round = 0
        self.phase = "traffic"  # traffic, action, resolution, chaos
        self.current_player = 0
        self.entropy = 0
        
        # Initialize players
        self.players = []
        strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, 
                     PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
        for i in range(num_players):
            strategy = strategies[i % len(strategies)]
            self.players.append(Player(
                id=i,
                name=f"Player_{i}",
                strategy=strategy
            ))
        
        # Initialize board
        self.services: Dict[int, Service] = {}
        self.next_service_id = 1
        self.board_grid = {}  # (row, col) -> service_id mapping
        
        # Game metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.uptime_history = []
        
        # Event log for analysis
        self.event_log = []
        self.game_start_time = time.time()
        
        # Dice roll tracking
        self.dice_history = []  # Track all dice rolls
        self.last_dice_roll = None  # Most recent dice roll for display
        
        self._initialize_starting_services()
    
    def _initialize_starting_services(self):
        """Place initial services for each player."""
        starting_positions = [
            (1, 1),  # Player 0 - top left
            (1, 4),  # Player 1 - top right  
            (6, 1),  # Player 2 - bottom left
            (6, 4),  # Player 3 - bottom right
        ]
        
        for i, player in enumerate(self.players):
            if i < len(starting_positions):
                pos = starting_positions[i]
                service = self._place_service(ServiceType.LOAD_BALANCER, pos, player.id)
                if service:
                    self.log_event("initial_placement", {
                        "player_id": player.id,
                        "service_id": service.id,
                        "service_type": service.service_type.value,
                        "position": pos
                    })
    
    def _place_service(self, service_type: ServiceType, position: Tuple[int, int], 
                      owner_id: int) -> Optional[Service]:
        """Place a service on the board."""
        row, col = position
        
        # Check bounds
        if not (0 <= row < self.config.board_rows and 0 <= col < self.config.board_cols):
            return None
        
        # Check if position is occupied
        if position in self.board_grid:
            return None
        
        # Create service
        service = Service(
            id=self.next_service_id,
            service_type=service_type,
            position=position,
            owner=owner_id
        )
        
        self.services[service.id] = service
        self.board_grid[position] = service.id
        self.players[owner_id].services_owned.add(service.id)
        self.next_service_id += 1
        
        # Auto-connect to nearby services
        self._auto_connect_service(service)
        
        return service
    
    def _auto_connect_service(self, service: Service):
        """Automatically connect service to nearby services."""
        row, col = service.position
        
        # Hexagonal neighbors (odd-r offset coordinates)
        if row % 2 == 0:  # Even row
            neighbors = [
                (row-1, col-1), (row-1, col),
                (row, col-1), (row, col+1),
                (row+1, col-1), (row+1, col)
            ]
        else:  # Odd row
            neighbors = [
                (row-1, col), (row-1, col+1),
                (row, col-1), (row, col+1),
                (row+1, col), (row+1, col+1)
            ]
        
        for neighbor_pos in neighbors:
            if neighbor_pos in self.board_grid:
                neighbor_id = self.board_grid[neighbor_pos]
                neighbor = self.services[neighbor_id]
                
                # Connect services (bidirectional)
                service.connections.add(neighbor_id)
                neighbor.connections.add(service.id)
    
    def roll_dice(self, dice_type: str, count: int = 1) -> tuple:
        """Roll dice and record the result."""
        rolls = []
        for _ in range(count):
            if dice_type == "d4":
                rolls.append(random.randint(1, 4))
            elif dice_type == "d6":
                rolls.append(random.randint(1, 6))
            elif dice_type == "d8":
                rolls.append(random.randint(1, 8))
            elif dice_type == "d10":
                rolls.append(random.randint(1, 10))
            elif dice_type == "d12":
                rolls.append(random.randint(1, 12))
            elif dice_type == "d20":
                rolls.append(random.randint(1, 20))
            else:
                rolls.append(random.randint(1, 6))  # Default to d6
        
        total = sum(rolls)
        roll_record = {
            "dice_type": dice_type,
            "count": count,
            "rolls": rolls,
            "total": total,
            "round": self.round,
            "phase": self.phase,
            "timestamp": time.time()
        }
        
        self.dice_history.append(roll_record)
        self.last_dice_roll = roll_record
        
        return rolls, total
    
    def generate_traffic(self) -> int:
        """Generate incoming traffic for this round."""
        # Roll 2d10 for requests
        rolls, requests = self.roll_dice("d10", 2)
        self.total_requests += requests
        
        self.log_event("traffic_generated", {
            "requests": requests,
            "dice_rolls": rolls,
            "round": self.round
        })
        
        return requests
    
    def process_requests(self, requests: int):
        """Process incoming requests through the service network."""
        # Find all load balancers as entry points
        entry_points = [s for s in self.services.values() 
                       if s.service_type == ServiceType.LOAD_BALANCER and 
                       s.state != ServiceState.FAILED]
        
        if not entry_points:
            # No entry points - all requests fail
            self.failed_requests += requests
            self.log_event("all_requests_failed", {"reason": "no_load_balancers"})
            return
        
        # Distribute requests among load balancers
        requests_per_lb = requests // len(entry_points)
        extra_requests = requests % len(entry_points)
        
        for i, lb in enumerate(entry_points):
            lb_requests = requests_per_lb
            if i < extra_requests:
                lb_requests += 1
            
            self._process_service_requests(lb, lb_requests)
    
    def _process_service_requests(self, service: Service, requests: int, depth: int = 0):
        """Process requests through a specific service."""
        # Prevent infinite recursion
        if depth > 10:
            self.failed_requests += requests
            return
            
        if service.state == ServiceState.FAILED:
            self.failed_requests += requests
            return
        
        # Add load to service
        service.load += requests
        
        # Check if service becomes overloaded
        if service.is_overloaded:
            excess = service.load - service.capacity
            if service.state == ServiceState.HEALTHY:
                service.state = ServiceState.DEGRADED
            elif service.state == ServiceState.DEGRADED:
                service.state = ServiceState.OVERLOADED
            
            # Chance of failure based on overload
            if excess > service.capacity:
                failure_chance = min(0.8, excess / service.capacity)
                if random.random() < failure_chance:
                    service.state = ServiceState.FAILED
                    self._trigger_cascade_check(service)
        
        # Route requests to connected services if needed (only for load balancers and gateways)
        if (service.service_type in [ServiceType.LOAD_BALANCER, ServiceType.API_GATEWAY] 
            and service.connections and depth < 3):  # Limit routing depth
            
            # Route to connected services
            downstream_services = [self.services[sid] for sid in service.connections
                                 if self.services[sid].state != ServiceState.FAILED]
            
            if downstream_services:
                requests_per_service = requests // len(downstream_services)
                for downstream in downstream_services:
                    self._process_service_requests(downstream, requests_per_service, depth + 1)
            else:
                # No healthy downstream services
                self.failed_requests += requests
        else:
            # Terminal service - requests complete here
            if service.state != ServiceState.FAILED:
                self.successful_requests += requests
            else:
                self.failed_requests += requests
    
    def _trigger_cascade_check(self, failed_service: Service):
        """Check if service failure triggers cascades."""
        # Roll d20 for cascade check
        rolls, cascade_roll = self.roll_dice("d20", 1)
        
        # Cascade happens on roll of 8 or less (40% chance)
        if cascade_roll <= 8:
            self.log_event("cascade_failure", {
                "origin_service": failed_service.id,
                "cascade_roll": cascade_roll
            })
            
            # Cascade to connected services
            for connected_id in failed_service.connections:
                connected = self.services[connected_id]
                if connected.state != ServiceState.FAILED:
                    connected.state = ServiceState.CASCADING
                    connected.load += 5  # Increased load from cascade
                    
                    # Chance of cascade propagation
                    if random.random() < 0.3:  # 30% chance to propagate
                        self._trigger_cascade_check(connected)
    
    def chaos_event(self):
        """Trigger a chaos event if entropy is high enough."""
        if self.entropy < self.config.chaos_threshold:
            return
        
        # Roll d8 for chaos event
        rolls, chaos_roll = self.roll_dice("d8", 1)
        
        events = {
            1: ("minor_glitch", "Minor network glitch"),
            2: ("memory_leak", "Memory leak in random service"),
            3: ("ddos_attack", "DDoS attack increases all load"),
            4: ("config_error", "Configuration error affects API gateways"),
            5: ("disk_full", "Disk full on database services"), 
            6: ("network_partition", "Network partition breaks connections"),
            7: ("security_breach", "Security breach requires service restarts"),
            8: ("datacenter_outage", "Datacenter outage affects multiple services")
        }
        
        event_type, description = events.get(chaos_roll, ("unknown", "Unknown chaos event"))
        
        self.log_event("chaos_event", {
            "type": event_type,
            "description": description,
            "entropy_level": self.entropy,
            "chaos_roll": chaos_roll
        })
        
        # Apply chaos effects
        self._apply_chaos_effects(event_type)
        
        # Increase entropy
        self.entropy = min(self.config.max_entropy, self.entropy + chaos_roll)
    
    def _apply_chaos_effects(self, event_type: str):
        """Apply the effects of a chaos event."""
        if event_type == "ddos_attack":
            for service in self.services.values():
                if service.service_type in [ServiceType.LOAD_BALANCER, ServiceType.API_GATEWAY]:
                    service.load += 3
        
        elif event_type == "memory_leak":
            # Random service gets degraded
            healthy_services = [s for s in self.services.values() 
                              if s.state == ServiceState.HEALTHY]
            if healthy_services:
                victim = random.choice(healthy_services)
                victim.state = ServiceState.DEGRADED
                victim.load += 2
        
        elif event_type == "disk_full":
            for service in self.services.values():
                if service.service_type == ServiceType.DATABASE:
                    service.state = ServiceState.OVERLOADED
                    service.load += 5
        
        elif event_type == "network_partition":
            # Break some random connections
            all_services = list(self.services.values())
            for _ in range(min(3, len(all_services))):
                service = random.choice(all_services)
                if service.connections:
                    broken_connection = random.choice(list(service.connections))
                    service.connections.discard(broken_connection)
                    self.services[broken_connection].connections.discard(service.id)
        
        elif event_type == "datacenter_outage":
            # Fail random services
            healthy_services = [s for s in self.services.values() 
                              if s.state != ServiceState.FAILED]
            failure_count = min(2, len(healthy_services))
            for service in random.sample(healthy_services, failure_count):
                service.state = ServiceState.FAILED
    
    def calculate_uptime(self) -> float:
        """Calculate current system uptime percentage."""
        if self.total_requests == 0:
            return 1.0
        
        return self.successful_requests / self.total_requests
    
    def advance_round(self):
        """Advance to the next round."""
        self.round += 1
        
        # Record uptime for this round
        uptime = self.calculate_uptime()
        self.uptime_history.append(uptime)
        
        # Reset player actions
        for player in self.players:
            player.actions_remaining = 3
        
        # Decay service load
        for service in self.services.values():
            service.load = max(0, service.load - 1)
            
            # Healing: degraded services might recover
            if service.state == ServiceState.DEGRADED and service.load < service.capacity * 0.5:
                if random.random() < 0.3:  # 30% chance to heal
                    service.state = ServiceState.HEALTHY
        
        # Reduce entropy slightly
        self.entropy = max(0, self.entropy - 1)
        
        self.log_event("round_end", {
            "round": self.round,
            "uptime": uptime,
            "entropy": self.entropy,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests
        })
    
    def is_game_over(self) -> bool:
        """Check if game should end."""
        # Max rounds reached
        if self.round >= self.config.max_rounds:
            return True
        
        # Cooperative mode: check if uptime target met
        if self.config.cooperative_mode:
            if len(self.uptime_history) >= 3:
                recent_uptime = sum(self.uptime_history[-3:]) / 3
                return recent_uptime >= self.config.uptime_target
        
        # Check if all players have failed (no services)
        active_players = sum(1 for p in self.players if p.services_owned)
        if active_players == 0:
            return True
        
        return False
    
    def get_winner(self) -> Optional[int]:
        """Determine the winner (competitive mode) or if team succeeded."""
        if self.config.cooperative_mode:
            avg_uptime = sum(self.uptime_history) / len(self.uptime_history) if self.uptime_history else 0
            return -1 if avg_uptime >= self.config.uptime_target else None
        
        # Competitive: highest score wins
        best_player = max(self.players, key=lambda p: p.score)
        return best_player.id
    
    def log_event(self, event_type: str, data: Dict):
        """Log an event for later analysis."""
        self.event_log.append({
            "timestamp": time.time() - self.game_start_time,
            "round": self.round,
            "phase": self.phase,
            "type": event_type,
            "data": data
        })
    
    def get_legal_actions(self, player_id: int) -> List[Dict]:
        """Get all legal actions for a player."""
        player = self.players[player_id]
        actions = []
        
        if player.actions_remaining <= 0:
            return actions
        
        # Deploy service actions
        for service_type in ServiceType:
            if player.can_afford(service_type):
                for row in range(self.config.board_rows):
                    for col in range(self.config.board_cols):
                        if (row, col) not in self.board_grid:
                            actions.append({
                                "type": "deploy",
                                "service_type": service_type.value,
                                "position": (row, col)
                            })
        
        # Repair service actions
        for service_id in player.services_owned:
            service = self.services[service_id]
            if service.state in [ServiceState.DEGRADED, ServiceState.OVERLOADED]:
                actions.append({
                    "type": "repair",
                    "service_id": service_id
                })
        
        # Scale service actions (if player has resources)
        for service_id in player.services_owned:
            service = self.services[service_id]
            if service.state == ServiceState.HEALTHY and player.cpu >= 1:
                actions.append({
                    "type": "scale",
                    "service_id": service_id
                })
        
        return actions
    
    def execute_action(self, player_id: int, action: Dict) -> bool:
        """Execute a player action."""
        player = self.players[player_id]
        
        if player.actions_remaining <= 0:
            return False
        
        success = False
        
        if action["type"] == "deploy":
            service_type = ServiceType(action["service_type"])
            position = tuple(action["position"])
            
            if player.spend_resources(service_type):
                service = self._place_service(service_type, position, player_id)
                if service:
                    success = True
                    self.log_event("deploy_service", {
                        "player_id": player_id,
                        "service_id": service.id,
                        "service_type": service_type.value,
                        "position": position
                    })
        
        elif action["type"] == "repair":
            service_id = action["service_id"]
            if service_id in player.services_owned and player.cpu >= 2:
                service = self.services[service_id]
                if service.state in [ServiceState.DEGRADED, ServiceState.OVERLOADED]:
                    service.state = ServiceState.HEALTHY
                    service.load = max(0, service.load - 3)
                    player.cpu -= 2
                    success = True
                    self.log_event("repair_service", {
                        "player_id": player_id,
                        "service_id": service_id
                    })
        
        elif action["type"] == "scale":
            service_id = action["service_id"]
            if service_id in player.services_owned and player.cpu >= 1:
                service = self.services[service_id]
                # Temporarily increase capacity
                service.load = max(0, service.load - 2)
                player.cpu -= 1
                success = True
                self.log_event("scale_service", {
                    "player_id": player_id,
                    "service_id": service_id
                })
        
        if success:
            player.actions_remaining -= 1
            # Small score increase for any action
            player.score += 1
        
        return success
    
    def to_dict(self) -> Dict:
        """Export game state as dictionary."""
        return {
            "round": self.round,
            "phase": self.phase,
            "entropy": self.entropy,
            "uptime": self.calculate_uptime(),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "strategy": p.strategy.value,
                    "cpu": p.cpu,
                    "memory": p.memory,
                    "storage": p.storage,
                    "score": p.score,
                    "actions_remaining": p.actions_remaining,
                    "services_owned": list(p.services_owned)
                }
                for p in self.players
            ],
            "services": [
                {
                    "id": s.id,
                    "type": s.service_type.value,
                    "position": s.position,
                    "state": s.state.value,
                    "load": s.load,
                    "capacity": s.capacity,
                    "bugs": s.bugs,
                    "connections": list(s.connections),
                    "owner": s.owner
                }
                for s in self.services.values()
            ],
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "uptime_history": self.uptime_history
        }