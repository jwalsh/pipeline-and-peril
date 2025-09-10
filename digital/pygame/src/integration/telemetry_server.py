#!/usr/bin/env python3
"""
Pipeline & Peril - Telemetry Server
Prometheus metrics export and monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server, REGISTRY
import time
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engine.game_state import GameState, GameConfig, PlayerStrategy
from players.ai_player import AIPlayerManager

# Metrics definitions
games_total = Counter('pipeline_games_total', 'Total games played', ['status', 'mode'])
game_duration = Histogram('pipeline_game_duration_seconds', 'Game duration in seconds')
round_duration = Histogram('pipeline_round_duration_seconds', 'Round duration in seconds')

uptime_gauge = Gauge('pipeline_uptime_current', 'Current system uptime', ['game_id'])
entropy_gauge = Gauge('pipeline_entropy_current', 'Current entropy level', ['game_id'])
services_gauge = Gauge('pipeline_services_active', 'Active services', ['game_id', 'type'])

services_deployed = Counter('pipeline_services_deployed_total', 'Services deployed', ['type', 'player'])
services_failed = Counter('pipeline_services_failed_total', 'Services failed', ['type', 'reason'])
cascade_failures = Counter('pipeline_cascade_failures_total', 'Cascade failures triggered')
chaos_events = Counter('pipeline_chaos_events_total', 'Chaos events', ['severity'])

requests_processed = Counter('pipeline_requests_total', 'Total requests processed', ['result'])
player_wins = Counter('pipeline_player_wins_total', 'Player wins', ['strategy'])
player_score = Histogram('pipeline_player_score', 'Player final scores', ['strategy'])

action_latency = Histogram('pipeline_action_latency_seconds', 'AI action decision time')
action_success = Counter('pipeline_actions_total', 'Actions executed', ['type', 'result'])

# Performance metrics
cpu_usage = Gauge('pipeline_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('pipeline_memory_usage_mb', 'Memory usage in MB')
games_per_second = Gauge('pipeline_games_per_second', 'Games processing rate')

class TelemetryCollector:
    """Collects and exports game telemetry."""
    
    def __init__(self):
        self.active_games = {}
        self.game_history = []
        self.start_time = time.time()
        self.total_games = 0
        
    def start_game(self, game_id: str, config: GameConfig):
        """Record game start."""
        self.active_games[game_id] = {
            'start_time': time.time(),
            'config': config,
            'rounds': 0,
            'services_deployed': {},
            'chaos_count': 0
        }
        
    def end_game(self, game_id: str, game_state: GameState):
        """Record game completion."""
        if game_id not in self.active_games:
            return
            
        game_data = self.active_games[game_id]
        duration = time.time() - game_data['start_time']
        
        # Record metrics
        game_duration.observe(duration)
        games_total.labels(status='completed', mode='competitive').inc()
        
        # Record winner
        winner_id = game_state.get_winner()
        if winner_id >= 0 and winner_id < len(game_state.players):
            winner = game_state.players[winner_id]
            player_wins.labels(strategy=winner.strategy.value).inc()
        
        # Record player scores
        for player in game_state.players:
            player_score.labels(strategy=player.strategy.value).observe(player.score)
        
        # Record final state
        uptime = game_state.calculate_uptime()
        uptime_gauge.labels(game_id=game_id).set(uptime)
        entropy_gauge.labels(game_id=game_id).set(game_state.entropy)
        
        # Clean up
        del self.active_games[game_id]
        self.total_games += 1
        
        # Update games per second
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            games_per_second.set(self.total_games / elapsed)
    
    def record_round(self, game_id: str, round_num: int, duration: float):
        """Record round completion."""
        round_duration.observe(duration)
        if game_id in self.active_games:
            self.active_games[game_id]['rounds'] = round_num
    
    def record_service_deployment(self, game_id: str, service_type: str, player_id: int):
        """Record service deployment."""
        services_deployed.labels(type=service_type, player=f"player_{player_id}").inc()
        
        if game_id in self.active_games:
            deployments = self.active_games[game_id]['services_deployed']
            deployments[service_type] = deployments.get(service_type, 0) + 1
            services_gauge.labels(game_id=game_id, type=service_type).set(deployments[service_type])
    
    def record_service_failure(self, service_type: str, reason: str):
        """Record service failure."""
        services_failed.labels(type=service_type, reason=reason).inc()
    
    def record_cascade_failure(self):
        """Record cascade failure."""
        cascade_failures.inc()
    
    def record_chaos_event(self, severity: str):
        """Record chaos event."""
        chaos_events.labels(severity=severity).inc()
    
    def record_request(self, successful: bool):
        """Record request processing."""
        result = 'success' if successful else 'failure'
        requests_processed.labels(result=result).inc()
    
    def record_action(self, action_type: str, success: bool, latency: float):
        """Record player action."""
        result = 'success' if success else 'failure'
        action_success.labels(type=action_type, result=result).inc()
        action_latency.observe(latency)
    
    def update_resource_metrics(self):
        """Update system resource metrics."""
        try:
            import psutil
            process = psutil.Process()
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_usage.set(memory_mb)
        except ImportError:
            # psutil not installed
            pass


def run_monitored_games(num_games: int = 10, telemetry: TelemetryCollector = None):
    """Run games with telemetry collection."""
    
    if telemetry is None:
        telemetry = TelemetryCollector()
    
    strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE,
                 PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
    ai_manager = AIPlayerManager(strategies)
    
    for game_num in range(num_games):
        game_id = f"game_{game_num}"
        config = GameConfig(max_rounds=10, cooperative_mode=False)
        game_state = GameState(config, len(strategies))
        
        # Set strategies
        for i, player in enumerate(game_state.players):
            player.strategy = strategies[i]
        
        telemetry.start_game(game_id, config)
        
        # Game loop
        while not game_state.is_game_over():
            round_start = time.time()
            
            # Traffic phase
            if game_state.phase == "traffic":
                requests = game_state.generate_traffic()
                game_state.process_requests(requests)
                
                # Record requests
                for _ in range(game_state.successful_requests):
                    telemetry.record_request(True)
                for _ in range(game_state.failed_requests):
                    telemetry.record_request(False)
                
                game_state.phase = "action"
            
            # Action phase
            elif game_state.phase == "action":
                for player_id in range(len(game_state.players)):
                    player = game_state.players[player_id]
                    
                    while player.actions_remaining > 0:
                        action_start = time.time()
                        action = ai_manager.get_action(player_id, game_state)
                        
                        if action:
                            success = game_state.execute_action(player_id, action)
                            action_latency_ms = (time.time() - action_start) * 1000
                            
                            telemetry.record_action(action["type"], success, action_latency_ms)
                            
                            if success and action["type"] == "deploy":
                                telemetry.record_service_deployment(
                                    game_id, action["service_type"], player_id
                                )
                        else:
                            player.actions_remaining = 0
                
                game_state.phase = "resolution"
            
            # Resolution phase
            elif game_state.phase == "resolution":
                # Check for failures
                for service in game_state.services.values():
                    if service.state.value == "failed":
                        telemetry.record_service_failure(
                            service.service_type.value, "overload"
                        )
                    elif service.state.value == "cascading":
                        telemetry.record_cascade_failure()
                
                game_state.phase = "chaos"
            
            # Chaos phase
            elif game_state.phase == "chaos":
                # Record chaos event
                if game_state.entropy >= 3:
                    severity = "major" if game_state.entropy >= 7 else "minor"
                    telemetry.record_chaos_event(severity)
                
                game_state.chaos_event()
                game_state.advance_round()
                game_state.phase = "traffic"
                
                # Record round completion
                round_duration_sec = time.time() - round_start
                telemetry.record_round(game_id, game_state.round, round_duration_sec)
        
        # Game complete
        telemetry.end_game(game_id, game_state)
        telemetry.update_resource_metrics()
        
        # Progress update
        if (game_num + 1) % max(1, num_games // 10) == 0:
            print(f"Completed {game_num + 1}/{num_games} games")


def main():
    """Main telemetry server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline & Peril Telemetry Server")
    parser.add_argument("--port", type=int, default=8080,
                       help="Prometheus metrics port")
    parser.add_argument("--games", type=int, default=0,
                       help="Number of games to run (0 for server only)")
    parser.add_argument("--continuous", action="store_true",
                       help="Run games continuously")
    
    args = parser.parse_args()
    
    # Start Prometheus metrics server
    start_http_server(args.port)
    print(f"📊 Telemetry server started on port {args.port}")
    print(f"📈 Metrics available at http://localhost:{args.port}/metrics")
    
    telemetry = TelemetryCollector()
    
    if args.games > 0:
        print(f"Running {args.games} monitored games...")
        run_monitored_games(args.games, telemetry)
        print(f"Games complete. Metrics available at http://localhost:{args.port}/metrics")
    
    if args.continuous:
        print("Running continuous game simulation...")
        batch_num = 0
        while True:
            batch_num += 1
            print(f"Starting batch {batch_num} (10 games)...")
            run_monitored_games(10, telemetry)
            time.sleep(1)  # Brief pause between batches
    
    # Keep server running
    if args.games == 0 or args.continuous:
        print("Server running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
                telemetry.update_resource_metrics()
        except KeyboardInterrupt:
            print("\nTelemetry server stopped.")


if __name__ == "__main__":
    main()