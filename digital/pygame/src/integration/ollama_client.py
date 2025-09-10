#!/usr/bin/env python3
"""
Pipeline & Peril - Ollama Integration Client
Enables Ollama models to play the game as intelligent agents.
"""

import json
import requests
import time
from typing import Dict, List, Optional, Any
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engine.game_state import GameState, ServiceType, ServiceState, PlayerStrategy


class OllamaGameClient:
    """Client for integrating Ollama models as game players."""
    
    def __init__(self, model_name: str = "qwen2.5-coder:7b", ollama_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.conversation_history = []
        
    def _call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Make a request to Ollama API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_response = result["message"]["content"]
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_response})
                
                # Keep history manageable
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-8:]
                
                return assistant_response
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error calling Ollama: {str(e)}"
    
    def choose_action(self, game_state: GameState, player_id: int) -> Optional[Dict]:
        """Have Ollama choose an action for the player."""
        
        system_prompt = """You are an expert distributed systems engineer playing Pipeline & Peril, a board game that simulates building resilient distributed systems.

Your goal is to build and maintain services while defending against system entropy and chaos events.

CRITICAL: You must respond with ONLY a valid JSON action object. No explanation, no markdown, just the JSON.

Service Types:
- load_balancer: Entry points for traffic (capacity: 10)
- compute: Process requests (capacity: 5) 
- database: Store data (capacity: 3)
- cache: Speed up access (capacity: 8)
- queue: Handle async tasks (capacity: 6)
- api_gateway: Route requests (capacity: 7)

Action Types:
1. {"type": "deploy", "service_type": "SERVICE_TYPE", "position": [row, col]}
2. {"type": "repair", "service_id": SERVICE_ID}
3. {"type": "scale", "service_id": SERVICE_ID}

Strategy: Build a robust network starting with load balancers, then add supporting services. Repair failing services immediately."""

        # Create game state summary for Ollama
        player = game_state.players[player_id]
        
        prompt = f"""GAME STATE - Round {game_state.round}:

YOUR STATUS (Player {player_id + 1}):
- Resources: CPU {player.cpu}, Memory {player.memory}, Storage {player.storage}
- Score: {player.score}
- Actions remaining: {player.actions_remaining}
- Services owned: {len(player.services_owned)}

SYSTEM STATUS:
- Total services: {len(game_state.services)}
- System uptime: {game_state.calculate_uptime()*100:.1f}%
- Entropy level: {game_state.entropy}/10
- Total requests: {game_state.total_requests}

YOUR SERVICES:"""

        for service_id in player.services_owned:
            if service_id in game_state.services:
                service = game_state.services[service_id]
                prompt += f"\n- {service.service_type.value} at ({service.position[0]},{service.position[1]}): {service.state.value}, load {service.load}/{service.capacity}"

        prompt += f"\n\nBOARD LAYOUT (8x6 grid):"
        
        # Show board occupancy
        for row in range(game_state.config.board_rows):
            row_str = f"\nRow {row}: "
            for col in range(game_state.config.board_cols):
                if (row, col) in game_state.board_grid:
                    service_id = game_state.board_grid[(row, col)]
                    service = game_state.services[service_id]
                    owner = service.owner
                    service_abbrev = service.service_type.value[:2].upper()
                    row_str += f"[P{owner}:{service_abbrev}] "
                else:
                    row_str += "[empty] "
            prompt += row_str

        # Get legal actions
        legal_actions = game_state.get_legal_actions(player_id)
        
        if not legal_actions:
            return None
        
        prompt += f"\n\nLEGAL ACTIONS ({len(legal_actions)} available):"
        
        # Show sample actions
        for i, action in enumerate(legal_actions[:5]):  # Show first 5
            if action["type"] == "deploy":
                cost_info = self._get_service_cost(action["service_type"])
                prompt += f"\n{i+1}. Deploy {action['service_type']} at {action['position']} {cost_info}"
            elif action["type"] == "repair":
                service = game_state.services[action["service_id"]]
                prompt += f"\n{i+1}. Repair {service.service_type.value} (state: {service.state.value})"
            elif action["type"] == "scale":
                service = game_state.services[action["service_id"]]
                prompt += f"\n{i+1}. Scale {service.service_type.value} (load: {service.load}/{service.capacity})"
        
        if len(legal_actions) > 5:
            prompt += f"\n... and {len(legal_actions) - 5} more actions"

        prompt += "\n\nChoose the BEST action for building a resilient distributed system. Respond with ONLY the JSON action:"

        # Get Ollama's response
        response = self._call_ollama(prompt, system_prompt)
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown formatting if present
            if response.startswith("```"):
                lines = response.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                response = '\n'.join(json_lines)
            
            # Parse JSON
            action = json.loads(response)
            
            # Validate action is legal
            if action in legal_actions:
                return action
            else:
                # Find closest legal action
                for legal_action in legal_actions:
                    if (legal_action["type"] == action.get("type") and
                        legal_action.get("service_type") == action.get("service_type")):
                        return legal_action
                
                # Fallback to first legal action
                return legal_actions[0]
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ollama response parsing error: {e}")
            print(f"Raw response: {response}")
            # Fallback to first legal action
            return legal_actions[0] if legal_actions else None
    
    def _get_service_cost(self, service_type: str) -> str:
        """Get resource cost information for a service type."""
        costs = {
            "compute": "(2 CPU, 2 Memory, 1 Storage)",
            "database": "(1 CPU, 2 Memory, 3 Storage)",
            "cache": "(1 CPU, 3 Memory, 1 Storage)",
            "queue": "(1 CPU, 1 Memory, 2 Storage)",
            "load_balancer": "(2 CPU, 1 Memory, 1 Storage)",
            "api_gateway": "(1 CPU, 1 Memory, 1 Storage)"
        }
        return costs.get(service_type, "")
    
    def get_strategy_description(self) -> str:
        """Get description of the AI's strategy."""
        prompt = """Describe your strategy for playing Pipeline & Peril in 2-3 sentences. 
        Focus on your approach to building distributed systems and handling failures."""
        
        return self._call_ollama(prompt)
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []


class OllamaGameRunner:
    """Runs games with Ollama AI players."""
    
    def __init__(self, models: List[str] = None):
        if models is None:
            models = ["qwen2.5-coder:7b", "llama3.2:3b", "llama3.2:3b", "qwen2.5-coder:7b"]
        
        self.ollama_clients = []
        for model in models:
            client = OllamaGameClient(model)
            self.ollama_clients.append(client)
    
    def run_ollama_game(self, rounds: int = 10, verbose: bool = True) -> Dict:
        """Run a game with Ollama AI players."""
        from engine.game_state import GameConfig
        
        config = GameConfig(max_rounds=rounds, cooperative_mode=False)
        game_state = GameState(config, len(self.ollama_clients))
        
        # Set player strategies to indicate Ollama control
        strategies = [PlayerStrategy.BALANCED] * len(self.ollama_clients)
        for i, player in enumerate(game_state.players):
            player.strategy = strategies[i]
            player.name = f"Ollama-{self.ollama_clients[i].model_name.split(':')[0]}"
        
        if verbose:
            print(f"\n{'='*60}")
            print("PIPELINE & PERIL - OLLAMA AI GAME")
            print(f"{'='*60}")
            print(f"Players: {len(self.ollama_clients)}")
            print(f"Rounds: {rounds}")
            
            for i, client in enumerate(self.ollama_clients):
                print(f"  Player {i+1}: {client.model_name}")
        
        # Game loop
        game_start = time.time()
        
        while not game_state.is_game_over():
            if verbose:
                print(f"\n--- Round {game_state.round + 1} ---")
            
            # Traffic phase
            if game_state.phase == "traffic":
                requests = game_state.generate_traffic()
                game_state.process_requests(requests)
                game_state.phase = "action"
                
                if verbose:
                    print(f"🚦 Traffic: {requests} requests generated")
            
            # Action phase - Ollama players
            elif game_state.phase == "action":
                actions_taken = 0
                
                for player_id in range(len(game_state.players)):
                    player = game_state.players[player_id]
                    client = self.ollama_clients[player_id]
                    
                    while player.actions_remaining > 0:
                        if verbose:
                            print(f"  Player {player_id + 1} ({client.model_name}) thinking...")
                        
                        action = client.choose_action(game_state, player_id)
                        if action:
                            success = game_state.execute_action(player_id, action)
                            if success:
                                actions_taken += 1
                                if verbose:
                                    action_desc = f"{action['type']}"
                                    if action['type'] == 'deploy':
                                        action_desc += f" {action['service_type']} at {action['position']}"
                                    print(f"    ✅ {action_desc}")
                            else:
                                if verbose:
                                    print(f"    ❌ Action failed")
                                player.actions_remaining = 0
                        else:
                            player.actions_remaining = 0
                
                game_state.phase = "resolution"
                
                if verbose:
                    print(f"  Total actions: {actions_taken}")
            
            # Resolution phase
            elif game_state.phase == "resolution":
                game_state.phase = "chaos"
            
            # Chaos phase
            elif game_state.phase == "chaos":
                game_state.chaos_event()
                game_state.advance_round()
                game_state.phase = "traffic"
                
                if verbose:
                    uptime = game_state.calculate_uptime()
                    print(f"  Uptime: {uptime*100:.1f}%")
        
        game_duration = time.time() - game_start
        
        # Results
        winner_id = game_state.get_winner()
        final_uptime = game_state.calculate_uptime()
        
        if verbose:
            print(f"\n{'='*60}")
            print("GAME COMPLETED")
            print(f"{'='*60}")
            print(f"Duration: {game_duration:.1f}s")
            print(f"Winner: Player {winner_id + 1} ({self.ollama_clients[winner_id].model_name})")
            print(f"Final uptime: {final_uptime*100:.1f}%")
            print(f"Total requests: {game_state.total_requests}")
            
            print("\nFinal Scores:")
            for i, player in enumerate(game_state.players):
                print(f"  Player {i+1}: {player.score} points, {len(player.services_owned)} services")
        
        return {
            "duration": game_duration,
            "winner": winner_id,
            "final_uptime": final_uptime,
            "models": [client.model_name for client in self.ollama_clients],
            "final_scores": [p.score for p in game_state.players]
        }


def main():
    """Main entry point for Ollama integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Play Pipeline & Peril with Ollama AI")
    parser.add_argument("--models", nargs="+", default=["qwen2.5-coder:7b"],
                       help="Ollama models to use as players")
    parser.add_argument("--rounds", type=int, default=10,
                       help="Number of rounds")
    parser.add_argument("--games", type=int, default=1,
                       help="Number of games to play")
    
    args = parser.parse_args()
    
    # Ensure we have 4 models for 4 players
    models = args.models
    while len(models) < 4:
        models.append(models[0])  # Repeat first model
    models = models[:4]  # Limit to 4 players
    
    runner = OllamaGameRunner(models)
    
    results = []
    for game_num in range(args.games):
        if args.games > 1:
            print(f"\n🎮 Starting Game {game_num + 1}/{args.games}")
        
        result = runner.run_ollama_game(args.rounds, verbose=True)
        results.append(result)
    
    if args.games > 1:
        # Summary statistics
        print(f"\n{'='*60}")
        print(f"SUMMARY ({args.games} games)")
        print(f"{'='*60}")
        
        avg_duration = sum(r["duration"] for r in results) / len(results)
        avg_uptime = sum(r["final_uptime"] for r in results) / len(results)
        
        print(f"Average duration: {avg_duration:.1f}s")
        print(f"Average uptime: {avg_uptime*100:.1f}%")
        
        # Winner statistics
        winner_counts = {}
        for result in results:
            winner_model = result["models"][result["winner"]]
            winner_counts[winner_model] = winner_counts.get(winner_model, 0) + 1
        
        print("\nWin rates:")
        for model, wins in winner_counts.items():
            win_rate = wins / args.games * 100
            print(f"  {model}: {wins}/{args.games} ({win_rate:.1f}%)")


if __name__ == "__main__":
    main()