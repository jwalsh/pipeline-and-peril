#!/usr/bin/env python3
"""
Ollama Personality Experiment for Pipeline & Peril
Tests different AI personalities and response times for game decisions.
"""

import json
import time
import requests
import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.game_state import GameState, GameConfig, ServiceType, PlayerStrategy


@dataclass
class PersonalityProfile:
    """AI personality configuration."""
    name: str
    description: str
    system_prompt: str
    temperature: float = 0.7
    top_p: float = 0.9


class OllamaPersonalityTester:
    """Tests different personalities with Ollama models."""
    
    # Define distinct personalities
    PERSONALITIES = {
        "aggressive_sre": PersonalityProfile(
            name="Aggressive SRE",
            description="Move fast and break things approach",
            system_prompt="""You are an aggressive Site Reliability Engineer playing Pipeline & Peril.
Your philosophy: "Move fast and break things, then fix them faster."
You prioritize rapid deployment and scaling over careful planning.
You believe in chaos engineering and stress testing systems to their limits.
You take calculated risks for performance gains.
Always respond with a single JSON action - no explanation.""",
            temperature=0.8
        ),
        
        "defensive_architect": PersonalityProfile(
            name="Defensive Architect",
            description="Conservative, reliability-first approach",
            system_prompt="""You are a defensive Systems Architect playing Pipeline & Peril.
Your philosophy: "An ounce of prevention is worth a pound of cure."
You prioritize redundancy, fault tolerance, and graceful degradation.
You believe in over-provisioning resources and maintaining healthy margins.
You avoid risks and prefer proven, stable patterns.
Always respond with a single JSON action - no explanation.""",
            temperature=0.5
        ),
        
        "chaos_engineer": PersonalityProfile(
            name="Chaos Engineer",
            description="Embrace chaos to build resilience",
            system_prompt="""You are a Chaos Engineer playing Pipeline & Peril.
Your philosophy: "The best way to avoid failure is to fail constantly."
You intentionally stress systems to find weak points.
You believe entropy is inevitable and systems must be antifragile.
You make unpredictable choices to test system boundaries.
Always respond with a single JSON action - no explanation.""",
            temperature=0.9
        ),
        
        "cost_optimizer": PersonalityProfile(
            name="Cost Optimizer",
            description="Efficiency and resource optimization focused",
            system_prompt="""You are a Cost-Conscious DevOps Engineer playing Pipeline & Peril.
Your philosophy: "Do more with less - optimize every resource."
You carefully balance performance with resource consumption.
You prefer autoscaling and just-in-time provisioning.
You analyze cost/benefit for every decision.
Always respond with a single JSON action - no explanation.""",
            temperature=0.6
        ),
        
        "startup_hacker": PersonalityProfile(
            name="Startup Hacker",
            description="Scrappy, fast iteration approach",
            system_prompt="""You are a Startup Engineer playing Pipeline & Peril.
Your philosophy: "Ship it now, perfect it later."
You favor quick wins and iterative improvements.
You're comfortable with technical debt if it means faster delivery.
You prioritize user-facing features over infrastructure.
Always respond with a single JSON action - no explanation.""",
            temperature=0.75
        ),
        
        "enterprise_guardian": PersonalityProfile(
            name="Enterprise Guardian",
            description="Process-driven, compliance-focused approach",
            system_prompt="""You are an Enterprise Infrastructure Manager playing Pipeline & Peril.
Your philosophy: "Stability, security, and compliance above all."
You follow strict change management procedures.
You prioritize audit trails and monitoring over speed.
You prefer proven, vendor-supported solutions.
Always respond with a single JSON action - no explanation.""",
            temperature=0.4
        ),
        
        "ml_optimizer": PersonalityProfile(
            name="ML Optimizer",
            description="Data-driven, pattern-recognition approach",
            system_prompt="""You are a Machine Learning Engineer playing Pipeline & Peril.
Your philosophy: "Let the data guide decisions."
You analyze patterns and probabilities before acting.
You prefer solutions that learn and adapt over time.
You see system behavior as a optimization problem.
Always respond with a single JSON action - no explanation.""",
            temperature=0.65
        ),
        
        "security_paranoid": PersonalityProfile(
            name="Security Paranoid",
            description="Zero-trust, defense-in-depth approach",
            system_prompt="""You are a Security Engineer playing Pipeline & Peril.
Your philosophy: "Assume breach, verify everything, trust nothing."
You prioritize security boundaries and isolation.
You prefer defense-in-depth with multiple fallback layers.
You see every connection as a potential attack vector.
Always respond with a single JSON action - no explanation.""",
            temperature=0.3
        )
    }
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.results = []
        
    def create_test_scenario(self) -> GameState:
        """Create a consistent test scenario for all personalities."""
        config = GameConfig(max_rounds=10, cooperative_mode=False)
        game_state = GameState(config, 4)
        
        # Set up a mid-game scenario with interesting choices
        game_state.round = 5
        game_state.entropy = 5
        
        # Deploy some initial services
        services_to_deploy = [
            (0, ServiceType.LOAD_BALANCER, (2, 2)),
            (1, ServiceType.DATABASE, (3, 3)),
            (2, ServiceType.CACHE, (4, 2)),
            (3, ServiceType.COMPUTE, (2, 4)),
            (0, ServiceType.API_GATEWAY, (3, 2)),
        ]
        
        for player_id, service_type, pos in services_to_deploy:
            game_state.execute_action(player_id, {
                "type": "deploy",
                "service_type": service_type.value,
                "position": pos
            })
        
        # Set some services to degraded state
        for service_id in [2, 4]:
            if service_id in game_state.services:
                service = game_state.services[service_id]
                service.state = service.state.__class__.DEGRADED
                service.load = 7
        
        # Generate some traffic
        game_state.total_requests = 100
        game_state.successful_requests = 75
        game_state.failed_requests = 25
        
        return game_state
    
    def test_personality(self, model: str, personality: PersonalityProfile, 
                        game_state: GameState, player_id: int = 0) -> Dict:
        """Test a single personality's response time and decision."""
        
        # Get legal actions
        legal_actions = game_state.get_legal_actions(player_id)
        if not legal_actions:
            return {
                "error": "No legal actions available",
                "response_time": 0
            }
        
        # Create prompt
        player = game_state.players[player_id]
        prompt = self._create_decision_prompt(game_state, player, legal_actions)
        
        # Measure response time
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": personality.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": personality.temperature,
                        "top_p": personality.top_p,
                        "num_predict": 100  # Limit response length
                    }
                },
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                assistant_response = result["message"]["content"]
                
                # Try to parse the action
                try:
                    # Clean response
                    assistant_response = assistant_response.strip()
                    if assistant_response.startswith("```"):
                        # Extract JSON from markdown
                        lines = assistant_response.split('\n')
                        json_lines = []
                        in_json = False
                        for line in lines:
                            if line.startswith("```"):
                                in_json = not in_json
                                continue
                            if in_json:
                                json_lines.append(line)
                        assistant_response = '\n'.join(json_lines)
                    
                    action = json.loads(assistant_response)
                    
                    return {
                        "model": model,
                        "personality": personality.name,
                        "response_time": response_time,
                        "action": action,
                        "action_type": action.get("type", "unknown"),
                        "raw_response": assistant_response[:200],
                        "temperature": personality.temperature,
                        "success": True
                    }
                    
                except json.JSONDecodeError as e:
                    return {
                        "model": model,
                        "personality": personality.name,
                        "response_time": response_time,
                        "error": f"JSON parse error: {e}",
                        "raw_response": assistant_response[:200],
                        "success": False
                    }
            else:
                return {
                    "model": model,
                    "personality": personality.name,
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}",
                    "success": False
                }
                
        except requests.exceptions.Timeout:
            return {
                "model": model,
                "personality": personality.name,
                "response_time": 30.0,
                "error": "Timeout",
                "success": False
            }
        except Exception as e:
            return {
                "model": model,
                "personality": personality.name,
                "response_time": time.time() - start_time,
                "error": str(e),
                "success": False
            }
    
    def _create_decision_prompt(self, game_state: GameState, player: Any, 
                               legal_actions: List[Dict]) -> str:
        """Create a decision prompt for the AI."""
        prompt = f"""GAME STATE:
Round: {game_state.round}
System Uptime: {game_state.calculate_uptime()*100:.1f}%
Entropy: {game_state.entropy}/10
Your Resources: CPU={player.cpu}, Memory={player.memory}, Storage={player.storage}
Your Score: {player.score}

CURRENT SERVICES:
Total: {len(game_state.services)}
Healthy: {sum(1 for s in game_state.services.values() if s.state.value == "healthy")}
Degraded: {sum(1 for s in game_state.services.values() if s.state.value == "degraded")}
Failed: {sum(1 for s in game_state.services.values() if s.state.value == "failed")}

TOP 3 LEGAL ACTIONS:"""
        
        # Show sample actions
        for i, action in enumerate(legal_actions[:3]):
            if action["type"] == "deploy":
                prompt += f"\n{i+1}. Deploy {action['service_type']} at {action['position']}"
            elif action["type"] == "repair":
                prompt += f"\n{i+1}. Repair service {action['service_id']}"
            elif action["type"] == "scale":
                prompt += f"\n{i+1}. Scale service {action['service_id']}"
        
        prompt += f"\n\nTotal {len(legal_actions)} actions available."
        prompt += "\n\nChoose ONE action as JSON. Example: {\"type\": \"deploy\", \"service_type\": \"cache\", \"position\": [2, 3]}"
        
        return prompt
    
    def run_experiment(self, models: List[str], iterations: int = 3):
        """Run the full experiment across models and personalities."""
        print("=" * 70)
        print("OLLAMA PERSONALITY EXPERIMENT")
        print("=" * 70)
        print(f"Models: {', '.join(models)}")
        print(f"Personalities: {len(self.PERSONALITIES)}")
        print(f"Iterations per combination: {iterations}")
        print()
        
        total_tests = len(models) * len(self.PERSONALITIES) * iterations
        test_count = 0
        
        for model in models:
            print(f"\nTesting model: {model}")
            print("-" * 50)
            
            for personality_key, personality in self.PERSONALITIES.items():
                print(f"  {personality.name}: ", end="", flush=True)
                
                personality_results = []
                
                for iteration in range(iterations):
                    test_count += 1
                    
                    # Create fresh game state for each test
                    game_state = self.create_test_scenario()
                    
                    # Test the personality
                    result = self.test_personality(model, personality, game_state)
                    result["iteration"] = iteration + 1
                    result["timestamp"] = datetime.now().isoformat()
                    
                    personality_results.append(result)
                    
                    # Progress indicator
                    if result["success"]:
                        print("✓", end="", flush=True)
                    else:
                        print("✗", end="", flush=True)
                    
                    # Small delay between requests
                    time.sleep(0.5)
                
                # Calculate stats for this personality
                successful_results = [r for r in personality_results if r["success"]]
                if successful_results:
                    avg_time = sum(r["response_time"] for r in successful_results) / len(successful_results)
                    success_rate = len(successful_results) / len(personality_results) * 100
                    print(f" | Avg: {avg_time:.2f}s | Success: {success_rate:.0f}%")
                else:
                    print(" | All failed")
                
                self.results.extend(personality_results)
                
                # Progress
                print(f"    Progress: {test_count}/{total_tests} ({test_count/total_tests*100:.1f}%)")
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict:
        """Analyze experiment results."""
        analysis = {
            "total_tests": len(self.results),
            "successful_tests": sum(1 for r in self.results if r.get("success", False)),
            "by_model": {},
            "by_personality": {},
            "fastest_combinations": [],
            "most_reliable": []
        }
        
        # Group by model
        for result in self.results:
            model = result.get("model", "unknown")
            if model not in analysis["by_model"]:
                analysis["by_model"][model] = {
                    "tests": 0,
                    "successes": 0,
                    "total_time": 0,
                    "actions": {}
                }
            
            analysis["by_model"][model]["tests"] += 1
            if result.get("success"):
                analysis["by_model"][model]["successes"] += 1
                analysis["by_model"][model]["total_time"] += result["response_time"]
                
                action_type = result.get("action_type", "unknown")
                analysis["by_model"][model]["actions"][action_type] = \
                    analysis["by_model"][model]["actions"].get(action_type, 0) + 1
        
        # Group by personality
        for result in self.results:
            personality = result.get("personality", "unknown")
            if personality not in analysis["by_personality"]:
                analysis["by_personality"][personality] = {
                    "tests": 0,
                    "successes": 0,
                    "total_time": 0,
                    "actions": {}
                }
            
            analysis["by_personality"][personality]["tests"] += 1
            if result.get("success"):
                analysis["by_personality"][personality]["successes"] += 1
                analysis["by_personality"][personality]["total_time"] += result["response_time"]
                
                action_type = result.get("action_type", "unknown")
                analysis["by_personality"][personality]["actions"][action_type] = \
                    analysis["by_personality"][personality]["actions"].get(action_type, 0) + 1
        
        # Find fastest successful combinations
        successful_results = [r for r in self.results if r.get("success")]
        successful_results.sort(key=lambda x: x["response_time"])
        analysis["fastest_combinations"] = [
            {
                "model": r["model"],
                "personality": r["personality"],
                "time": r["response_time"],
                "action": r.get("action_type")
            }
            for r in successful_results[:5]
        ]
        
        return analysis
    
    def save_results(self, filename: str = None):
        """Save experiment results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ollama_personality_experiment_{timestamp}.json"
        
        output_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        analysis = self.analyze_results()
        
        with open(filepath, 'w') as f:
            json.dump({
                "experiment": "Ollama Personality Test",
                "timestamp": datetime.now().isoformat(),
                "raw_results": self.results,
                "analysis": analysis
            }, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
        return filepath


def main():
    """Run the personality experiment."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Ollama AI personalities in Pipeline & Peril")
    parser.add_argument("--models", nargs="+", 
                       default=["qwen2.5-coder:7b", "llama3.2:3b"],
                       help="Ollama models to test")
    parser.add_argument("--iterations", type=int, default=3,
                       help="Number of iterations per personality/model combination")
    parser.add_argument("--url", default="http://localhost:11434",
                       help="Ollama API URL")
    parser.add_argument("--personalities", nargs="+",
                       help="Specific personalities to test (default: all)")
    
    args = parser.parse_args()
    
    tester = OllamaPersonalityTester(args.url)
    
    # Filter personalities if specified
    if args.personalities:
        tester.PERSONALITIES = {
            k: v for k, v in tester.PERSONALITIES.items()
            if v.name in args.personalities or k in args.personalities
        }
    
    # Check Ollama is running
    try:
        response = requests.get(f"{args.url}/api/tags")
        if response.status_code != 200:
            print("Error: Cannot connect to Ollama API")
            print(f"Make sure Ollama is running at {args.url}")
            return
    except:
        print(f"Error: Cannot connect to Ollama at {args.url}")
        print("Start Ollama with: ollama serve")
        return
    
    # Run experiment
    results = tester.run_experiment(args.models, args.iterations)
    
    # Print summary
    print("\n" + "=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)
    
    print(f"\nTotal Tests: {results['total_tests']}")
    print(f"Successful: {results['successful_tests']} ({results['successful_tests']/results['total_tests']*100:.1f}%)")
    
    print("\nBy Model:")
    for model, stats in results["by_model"].items():
        if stats["successes"] > 0:
            avg_time = stats["total_time"] / stats["successes"]
            print(f"  {model}:")
            print(f"    Success Rate: {stats['successes']}/{stats['tests']} ({stats['successes']/stats['tests']*100:.1f}%)")
            print(f"    Avg Response Time: {avg_time:.2f}s")
            print(f"    Actions: {stats['actions']}")
    
    print("\nFastest Combinations:")
    for combo in results["fastest_combinations"]:
        print(f"  {combo['model']} + {combo['personality']}: {combo['time']:.2f}s ({combo['action']})")
    
    # Save results
    tester.save_results()


if __name__ == "__main__":
    main()