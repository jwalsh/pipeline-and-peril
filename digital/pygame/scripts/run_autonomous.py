#!/usr/bin/env python3
"""
Pipeline & Peril - Autonomous Game Runner
Runs multiple games with AI players and collects statistics.
"""

import sys
import os
import argparse
import time
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.game_state import GameState, GameConfig, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI
import pygame


class GameRunner:
    """Runs autonomous games and collects statistics."""
    
    def __init__(self, config: GameConfig = None, strategies: List[PlayerStrategy] = None):
        self.config = config or GameConfig()
        self.strategies = strategies or [
            PlayerStrategy.AGGRESSIVE,
            PlayerStrategy.DEFENSIVE, 
            PlayerStrategy.BALANCED,
            PlayerStrategy.RANDOM
        ]
        
        self.ai_manager = AIPlayerManager(self.strategies)
        self.games_completed = 0
        self.results = []
        
        # Statistics tracking
        self.start_time = None
        self.total_games_requested = 0
        
    def run_single_game(self, game_id: int = 0, save_log: bool = False, 
                       verbose: bool = False) -> Dict:
        """Run a single autonomous game."""
        if verbose:
            print(f"Starting game {game_id}...")
        
        # Initialize game
        game_state = GameState(self.config, len(self.strategies))
        
        # Set player strategies
        for i, player in enumerate(game_state.players):
            if i < len(self.strategies):
                player.strategy = self.strategies[i]
        
        game_start_time = time.time()
        
        # Game loop
        while not game_state.is_game_over():
            # Traffic phase
            if game_state.phase == "traffic":
                requests = game_state.generate_traffic()
                game_state.process_requests(requests)
                game_state.phase = "action"
                
                if verbose:
                    print(f"  Round {game_state.round}: {requests} requests generated")
            
            # Action phase - each player takes actions
            elif game_state.phase == "action":
                actions_taken = 0
                
                for player_id in range(len(game_state.players)):
                    player = game_state.players[player_id]
                    
                    # AI player takes actions
                    while player.actions_remaining > 0:
                        action = self.ai_manager.get_action(player_id, game_state)
                        if action:
                            success = game_state.execute_action(player_id, action)
                            if success:
                                actions_taken += 1
                            else:
                                # If action failed, forfeit remaining actions
                                player.actions_remaining = 0
                        else:
                            # No valid actions available
                            player.actions_remaining = 0
                
                game_state.phase = "resolution"
                
                if verbose and actions_taken > 0:
                    print(f"    {actions_taken} actions taken by all players")
            
            # Resolution phase
            elif game_state.phase == "resolution":
                # Update service states based on current load
                for service in game_state.services.values():
                    if service.is_overloaded and service.state.value != "failed":
                        # Chance of degradation/failure
                        if service.load > service.capacity * 1.5:
                            if random.random() < 0.4:  # 40% chance
                                service.state = ServiceState.FAILED
                        elif service.load > service.capacity * 1.2:
                            if random.random() < 0.3:  # 30% chance
                                service.state = ServiceState.DEGRADED
                
                game_state.phase = "chaos"
            
            # Chaos phase
            elif game_state.phase == "chaos":
                game_state.chaos_event()
                game_state.advance_round()
                game_state.phase = "traffic"
                
                if verbose:
                    uptime = game_state.calculate_uptime()
                    print(f"  End of round {game_state.round}: {uptime*100:.1f}% uptime")
        
        # Game completed
        game_duration = time.time() - game_start_time
        
        # Determine results
        winner_id = game_state.get_winner()
        final_uptime = game_state.calculate_uptime()
        
        result = {
            "game_id": game_id,
            "duration": game_duration,
            "rounds": game_state.round,
            "winner": winner_id,
            "cooperative_success": winner_id == -1,  # -1 indicates team success
            "final_uptime": final_uptime,
            "total_requests": game_state.total_requests,
            "successful_requests": game_state.successful_requests,
            "final_entropy": game_state.entropy,
            "players": [
                {
                    "id": p.id,
                    "strategy": p.strategy.value,
                    "final_score": p.score,
                    "services_owned": len(p.services_owned),
                    "final_resources": {
                        "cpu": p.cpu,
                        "memory": p.memory,
                        "storage": p.storage
                    }
                }
                for p in game_state.players
            ],
            "services_final_state": [
                {
                    "id": s.id,
                    "type": s.service_type.value,
                    "final_state": s.state.value,
                    "final_load": s.load,
                    "capacity": s.capacity,
                    "bugs": s.bugs,
                    "owner": s.owner
                }
                for s in game_state.services.values()
            ]
        }
        
        # Save detailed log if requested
        if save_log:
            log_data = {
                "result": result,
                "game_state": game_state.to_dict(),
                "event_log": game_state.event_log
            }
            
            log_filename = f"data/logs/game_{game_id:06d}.json"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            with open(log_filename, 'w') as f:
                json.dump(log_data, f, indent=2)
        
        # Update AI performance
        player_results = [
            {
                "final_score": p.score,
                "final_uptime": final_uptime,
                "won": (winner_id == p.id),
                "services_built": len(p.services_owned)
            }
            for p in game_state.players
        ]
        self.ai_manager.update_all_performance(player_results)
        
        if verbose:
            print(f"Game {game_id} completed in {game_duration:.2f}s - "
                  f"Winner: {winner_id}, Uptime: {final_uptime*100:.1f}%")
        
        return result
    
    def run_multiple_games(self, num_games: int, save_logs: bool = False, 
                          verbose: bool = False, parallel: bool = False) -> List[Dict]:
        """Run multiple autonomous games."""
        self.start_time = time.time()
        self.total_games_requested = num_games
        results = []
        
        print(f"Running {num_games} autonomous games...")
        print(f"Strategies: {[s.value for s in self.strategies]}")
        print(f"Config: {self.config.max_rounds} rounds, "
              f"{'cooperative' if self.config.cooperative_mode else 'competitive'} mode")
        
        if parallel and num_games > 1:
            # Run games in parallel (limited threading for safety)
            max_threads = min(4, num_games)
            threads = []
            thread_results = {}
            
            def run_game_thread(game_id):
                thread_results[game_id] = self.run_single_game(
                    game_id, save_logs, verbose and num_games <= 10
                )
            
            for i in range(num_games):
                if len(threads) >= max_threads:
                    # Wait for a thread to complete
                    threads[0].join()
                    threads.pop(0)
                
                thread = threading.Thread(target=run_game_thread, args=(i,))
                thread.start()
                threads.append(thread)
            
            # Wait for all remaining threads
            for thread in threads:
                thread.join()
            
            # Collect results in order
            for i in range(num_games):
                results.append(thread_results[i])
        
        else:
            # Run games sequentially
            for i in range(num_games):
                result = self.run_single_game(i, save_logs, verbose and num_games <= 10)
                results.append(result)
                
                # Progress update
                if not verbose and (i + 1) % max(1, num_games // 10) == 0:
                    progress = (i + 1) / num_games * 100
                    elapsed = time.time() - self.start_time
                    eta = elapsed / (i + 1) * num_games - elapsed
                    print(f"Progress: {progress:.1f}% ({i+1}/{num_games}) - "
                          f"ETA: {eta:.1f}s")
        
        self.results = results
        self.games_completed = len(results)
        
        total_time = time.time() - self.start_time
        print(f"\nCompleted {self.games_completed} games in {total_time:.2f}s")
        print(f"Average: {total_time/self.games_completed:.3f}s per game")
        
        return results
    
    def analyze_results(self) -> Dict:
        """Analyze game results and generate statistics."""
        if not self.results:
            return {"error": "No games completed"}
        
        analysis = {
            "summary": {
                "total_games": len(self.results),
                "avg_duration": sum(r["duration"] for r in self.results) / len(self.results),
                "avg_rounds": sum(r["rounds"] for r in self.results) / len(self.results),
                "avg_uptime": sum(r["final_uptime"] for r in self.results) / len(self.results),
                "cooperative_success_rate": sum(1 for r in self.results if r["cooperative_success"]) / len(self.results)
            },
            "by_strategy": {},
            "service_statistics": {},
            "performance_trends": self.ai_manager.get_all_statistics()
        }
        
        # Strategy-specific analysis
        for strategy in self.strategies:
            strategy_results = []
            for result in self.results:
                for player in result["players"]:
                    if player["strategy"] == strategy.value:
                        strategy_results.append({
                            "score": player["final_score"],
                            "services": player["services_owned"],
                            "uptime": result["final_uptime"],
                            "won": (result["winner"] == player["id"])
                        })
            
            if strategy_results:
                analysis["by_strategy"][strategy.value] = {
                    "games": len(strategy_results),
                    "avg_score": sum(r["score"] for r in strategy_results) / len(strategy_results),
                    "avg_services": sum(r["services"] for r in strategy_results) / len(strategy_results),
                    "avg_uptime": sum(r["uptime"] for r in strategy_results) / len(strategy_results),
                    "win_rate": sum(1 for r in strategy_results if r["won"]) / len(strategy_results)
                }
        
        # Service type analysis
        service_stats = {}
        for result in self.results:
            for service in result["services_final_state"]:
                service_type = service["type"]
                if service_type not in service_stats:
                    service_stats[service_type] = {
                        "count": 0,
                        "avg_load": 0,
                        "failure_rate": 0,
                        "avg_bugs": 0
                    }
                
                stats = service_stats[service_type]
                stats["count"] += 1
                stats["avg_load"] += service["final_load"]
                if service["final_state"] == "failed":
                    stats["failure_rate"] += 1
                stats["avg_bugs"] += service["bugs"]
        
        # Calculate averages
        for service_type, stats in service_stats.items():
            if stats["count"] > 0:
                stats["avg_load"] /= stats["count"]
                stats["failure_rate"] /= stats["count"]
                stats["avg_bugs"] /= stats["count"]
        
        analysis["service_statistics"] = service_stats
        
        return analysis
    
    def save_results(self, filename: str = None):
        """Save results and analysis to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/analysis/results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "board_rows": self.config.board_rows,
                    "board_cols": self.config.board_cols,
                    "max_rounds": self.config.max_rounds,
                    "cooperative_mode": self.config.cooperative_mode
                },
                "strategies": [s.value for s in self.strategies]
            },
            "results": self.results,
            "analysis": self.analyze_results()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Results saved to {filename}")
        return filename


def main():
    """Main entry point for autonomous game runner."""
    parser = argparse.ArgumentParser(
        description="Run autonomous Pipeline & Peril games"
    )
    
    parser.add_argument("--games", type=int, default=10,
                       help="Number of games to run (default: 10)")
    parser.add_argument("--players", type=str, 
                       default="aggressive,defensive,balanced,random",
                       help="Comma-separated player strategies")
    parser.add_argument("--rounds", type=int, default=10,
                       help="Maximum rounds per game (default: 10)")
    parser.add_argument("--cooperative", action="store_true",
                       help="Enable cooperative mode (default: competitive)")
    parser.add_argument("--save-logs", action="store_true",
                       help="Save detailed logs for each game")
    parser.add_argument("--parallel", action="store_true",
                       help="Run games in parallel (faster but uses more resources)")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed progress information")
    parser.add_argument("--scenario", type=str,
                       help="Load predefined scenario configuration")
    parser.add_argument("--visual", action="store_true",
                       help="Run with visual interface (first game only)")
    
    args = parser.parse_args()
    
    # Parse player strategies
    strategy_map = {
        "aggressive": PlayerStrategy.AGGRESSIVE,
        "defensive": PlayerStrategy.DEFENSIVE,
        "balanced": PlayerStrategy.BALANCED,
        "random": PlayerStrategy.RANDOM
    }
    
    strategies = []
    for strategy_name in args.players.split(","):
        strategy_name = strategy_name.strip().lower()
        if strategy_name in strategy_map:
            strategies.append(strategy_map[strategy_name])
        else:
            print(f"Warning: Unknown strategy '{strategy_name}', using RANDOM")
            strategies.append(PlayerStrategy.RANDOM)
    
    # Create game configuration
    config = GameConfig(
        max_rounds=args.rounds,
        cooperative_mode=args.cooperative
    )
    
    # Load scenario if specified
    if args.scenario:
        scenario_file = f"data/configs/{args.scenario}.json"
        try:
            with open(scenario_file, 'r') as f:
                scenario_data = json.load(f)
                # Apply scenario modifications to config
                if "max_rounds" in scenario_data:
                    config.max_rounds = scenario_data["max_rounds"]
                if "cooperative_mode" in scenario_data:
                    config.cooperative_mode = scenario_data["cooperative_mode"]
                print(f"Loaded scenario: {args.scenario}")
        except FileNotFoundError:
            print(f"Warning: Scenario file {scenario_file} not found")
    
    # Create runner
    runner = GameRunner(config, strategies)
    
    # Visual mode for demonstration
    if args.visual and args.games >= 1:
        print("Running first game with visual interface...")
        
        # Initialize pygame
        ui = GameUI()
        
        # Run one game with visualization
        game_state = GameState(config, len(strategies))
        for i, player in enumerate(game_state.players):
            if i < len(strategies):
                player.strategy = strategies[i]
        
        running = True
        clock = pygame.time.Clock()
        
        while running and not game_state.is_game_over():
            dt = clock.tick(60) / 1000.0  # 60 FPS
            
            # Handle events
            for event in pygame.event.get():
                action = ui.handle_event(event)
                if action:
                    if action["type"] == "quit":
                        running = False
                    elif action["type"] == "save_screenshot":
                        filename = ui.save_screenshot()
                        print(f"Screenshot saved: {filename}")
                    elif action["type"] == "next_phase":
                        # Advance game state
                        if game_state.phase == "traffic":
                            requests = game_state.generate_traffic()
                            game_state.process_requests(requests)
                            game_state.phase = "action"
                        elif game_state.phase == "action":
                            # AI players take actions
                            for player_id in range(len(game_state.players)):
                                player = game_state.players[player_id]
                                while player.actions_remaining > 0:
                                    action = runner.ai_manager.get_action(player_id, game_state)
                                    if action:
                                        success = game_state.execute_action(player_id, action)
                                        if not success:
                                            player.actions_remaining = 0
                                    else:
                                        player.actions_remaining = 0
                            game_state.phase = "resolution"
                        elif game_state.phase == "resolution":
                            game_state.phase = "chaos"
                        elif game_state.phase == "chaos":
                            game_state.chaos_event()
                            game_state.advance_round()
                            game_state.phase = "traffic"
            
            # Update and render
            ui.update(game_state, dt)
            ui.render()
        
        # Take final screenshot
        final_screenshot = ui.save_screenshot("pipeline_peril_final_game.png")
        print(f"Final game screenshot: {final_screenshot}")
        
        ui.cleanup()
        
        # Continue with remaining games if any
        if args.games > 1:
            print(f"\nRunning remaining {args.games - 1} games without visualization...")
            results = runner.run_multiple_games(
                args.games - 1, args.save_logs, args.verbose, args.parallel
            )
    else:
        # Run all games without visualization
        results = runner.run_multiple_games(
            args.games, args.save_logs, args.verbose, args.parallel
        )
    
    # Analysis and output
    analysis = runner.analyze_results()
    
    print("\n" + "="*50)
    print("GAME ANALYSIS RESULTS")
    print("="*50)
    
    # Summary
    summary = analysis["summary"]
    print(f"Total Games: {summary['total_games']}")
    print(f"Average Duration: {summary['avg_duration']:.2f}s")
    print(f"Average Rounds: {summary['avg_rounds']:.1f}")
    print(f"Average Uptime: {summary['avg_uptime']*100:.1f}%")
    if config.cooperative_mode:
        print(f"Cooperative Success Rate: {summary['cooperative_success_rate']*100:.1f}%")
    
    # Strategy performance
    print("\nStrategy Performance:")
    for strategy, stats in analysis["by_strategy"].items():
        print(f"  {strategy.title()}:")
        print(f"    Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"    Avg Score: {stats['avg_score']:.1f}")
        print(f"    Avg Services: {stats['avg_services']:.1f}")
        print(f"    Avg Uptime: {stats['avg_uptime']*100:.1f}%")
    
    # Service statistics
    print("\nService Statistics:")
    for service_type, stats in analysis["service_statistics"].items():
        print(f"  {service_type.title()}:")
        print(f"    Built: {stats['count']} times")
        print(f"    Avg Load: {stats['avg_load']:.1f}")
        print(f"    Failure Rate: {stats['failure_rate']*100:.1f}%")
        print(f"    Avg Bugs: {stats['avg_bugs']:.1f}")
    
    # Save results
    results_file = runner.save_results()
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    # Fix import issues
    import random
    from enum import Enum
    
    # Add missing import that was referenced but not imported
    from engine.game_state import ServiceState
    
    main()