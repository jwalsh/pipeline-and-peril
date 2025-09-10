#!/usr/bin/env python3
"""
Ollama Response Time Benchmark
Tests how fast different models respond to game decisions.
"""

import time
import requests
import json
import statistics
from typing import Dict, List
from datetime import datetime

class OllamaTimingBenchmark:
    """Benchmark Ollama response times for different models."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.results = []
        
    def test_queries(self) -> List[Dict[str, str]]:
        """Different complexity queries to test."""
        return [
            {
                "name": "simple_action",
                "prompt": "Choose action: deploy, repair, or scale? Reply with just the word.",
                "expected_length": "short"
            },
            {
                "name": "json_decision",
                "prompt": """Given these options, choose ONE and respond with JSON only:
1. {"type": "deploy", "service": "cache", "position": [2,3]}
2. {"type": "repair", "service_id": 5}
3. {"type": "scale", "service_id": 3}

Reply with your choice as valid JSON.""",
                "expected_length": "medium"
            },
            {
                "name": "game_analysis",
                "prompt": """Game state: Round 5, Entropy 7/10, Uptime 65%, 3 failed services.
You have 10 CPU, 8 Memory, 5 Storage.
Legal actions: deploy load_balancer, repair service_2, scale service_4.

What's the best action and why? Answer in one sentence.""",
                "expected_length": "medium"
            },
            {
                "name": "complex_reasoning",
                "prompt": """Analyze this distributed system scenario:
- 5 load balancers (2 degraded)
- 3 databases (1 failed, causing cascade)
- 8 compute nodes (50% capacity)
- Network partition affecting region 2
- DDoS attack increasing traffic 300%

Prioritize these actions and explain your reasoning briefly:
1. Deploy more load balancers
2. Repair failed database
3. Scale compute nodes
4. Implement rate limiting
5. Isolate affected region""",
                "expected_length": "long"
            }
        ]
    
    def measure_response_time(self, model: str, prompt: str, temperature: float = 0.7) -> Dict:
        """Measure single response time."""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 200,  # Limit response length
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Calculate tokens per second if available
                eval_count = result.get("eval_count", 0)
                eval_duration = result.get("eval_duration", 0) / 1e9  # Convert nanoseconds to seconds
                
                tokens_per_second = eval_count / eval_duration if eval_duration > 0 else 0
                
                return {
                    "success": True,
                    "response_time": response_time,
                    "response_length": len(response_text),
                    "tokens_generated": eval_count,
                    "tokens_per_second": tokens_per_second,
                    "model_load_time": result.get("load_duration", 0) / 1e9,
                    "eval_time": eval_duration,
                    "response_preview": response_text[:100]
                }
            else:
                return {
                    "success": False,
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response_time": 60.0,
                "error": "Timeout (60s)"
            }
        except Exception as e:
            return {
                "success": False,
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    def run_benchmark(self, models: List[str], iterations: int = 5):
        """Run complete benchmark suite."""
        print("=" * 70)
        print("OLLAMA RESPONSE TIME BENCHMARK")
        print("=" * 70)
        print(f"Models: {', '.join(models)}")
        print(f"Iterations per query: {iterations}")
        print()
        
        # Check Ollama is running
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print("❌ Cannot connect to Ollama API")
                return None
            
            available_models = [m["name"] for m in response.json().get("models", [])]
            print(f"Available models: {', '.join(available_models)}")
            print()
            
        except Exception as e:
            print(f"❌ Cannot connect to Ollama: {e}")
            print("Start Ollama with: ollama serve")
            return None
        
        queries = self.test_queries()
        
        for model in models:
            print(f"\n{'='*50}")
            print(f"Testing Model: {model}")
            print('='*50)
            
            # Check if model is available
            if model not in available_models:
                print(f"⚠️  Model {model} not found. Pulling...")
                try:
                    # Try to pull the model
                    pull_response = requests.post(
                        f"{self.ollama_url}/api/pull",
                        json={"name": model},
                        timeout=300  # 5 minutes for download
                    )
                    if pull_response.status_code == 200:
                        print(f"✅ Model {model} pulled successfully")
                    else:
                        print(f"❌ Failed to pull {model}")
                        continue
                except Exception as e:
                    print(f"❌ Error pulling model: {e}")
                    continue
            
            model_results = []
            
            # Warm up the model with a simple query
            print("Warming up model...")
            self.measure_response_time(model, "Hello", temperature=0.1)
            
            for query in queries:
                print(f"\n📝 Query: {query['name']}")
                print(f"   Expected: {query['expected_length']} response")
                
                query_times = []
                query_tokens = []
                
                for i in range(iterations):
                    result = self.measure_response_time(model, query["prompt"])
                    
                    if result["success"]:
                        query_times.append(result["response_time"])
                        if result.get("tokens_per_second"):
                            query_tokens.append(result["tokens_per_second"])
                        print(f"   Run {i+1}: {result['response_time']:.2f}s", end="")
                        if result.get("tokens_per_second"):
                            print(f" ({result['tokens_per_second']:.1f} tok/s)")
                        else:
                            print()
                    else:
                        print(f"   Run {i+1}: ❌ {result['error']}")
                    
                    # Small delay between requests
                    time.sleep(0.5)
                
                if query_times:
                    avg_time = statistics.mean(query_times)
                    std_dev = statistics.stdev(query_times) if len(query_times) > 1 else 0
                    min_time = min(query_times)
                    max_time = max(query_times)
                    
                    print(f"\n   📊 Stats:")
                    print(f"      Avg: {avg_time:.2f}s ± {std_dev:.2f}s")
                    print(f"      Min: {min_time:.2f}s, Max: {max_time:.2f}s")
                    
                    if query_tokens:
                        avg_tokens = statistics.mean(query_tokens)
                        print(f"      Avg tokens/s: {avg_tokens:.1f}")
                    
                    model_results.append({
                        "query": query["name"],
                        "avg_time": avg_time,
                        "std_dev": std_dev,
                        "min_time": min_time,
                        "max_time": max_time,
                        "avg_tokens_per_sec": statistics.mean(query_tokens) if query_tokens else 0
                    })
            
            self.results.append({
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "query_results": model_results
            })
        
        return self.analyze_results()
    
    def analyze_results(self) -> Dict:
        """Analyze and summarize benchmark results."""
        if not self.results:
            return {}
        
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        
        summary = {
            "models": {},
            "fastest_by_query": {},
            "recommendations": []
        }
        
        # Analyze by model
        for model_result in self.results:
            model = model_result["model"]
            query_results = model_result["query_results"]
            
            if query_results:
                all_times = [q["avg_time"] for q in query_results]
                avg_response_time = statistics.mean(all_times)
                
                summary["models"][model] = {
                    "avg_response_time": avg_response_time,
                    "suitable_for_realtime": avg_response_time < 2.0,  # Under 2 seconds
                    "suitable_for_game": avg_response_time < 5.0,      # Under 5 seconds
                    "query_breakdown": query_results
                }
                
                print(f"\n{model}:")
                print(f"  Average response: {avg_response_time:.2f}s")
                print(f"  Real-time suitable: {'✅' if avg_response_time < 2.0 else '❌'}")
                print(f"  Game suitable: {'✅' if avg_response_time < 5.0 else '⚠️' if avg_response_time < 10.0 else '❌'}")
        
        # Find fastest model for each query type
        print("\n" + "-" * 50)
        print("Fastest Model by Query Type:")
        
        query_names = set()
        for model_result in self.results:
            for q in model_result["query_results"]:
                query_names.add(q["query"])
        
        for query_name in query_names:
            fastest_model = None
            fastest_time = float('inf')
            
            for model_result in self.results:
                model = model_result["model"]
                for q in model_result["query_results"]:
                    if q["query"] == query_name and q["avg_time"] < fastest_time:
                        fastest_time = q["avg_time"]
                        fastest_model = model
            
            if fastest_model:
                summary["fastest_by_query"][query_name] = {
                    "model": fastest_model,
                    "time": fastest_time
                }
                print(f"  {query_name}: {fastest_model} ({fastest_time:.2f}s)")
        
        # Recommendations
        print("\n" + "-" * 50)
        print("Recommendations:")
        
        for model, stats in summary["models"].items():
            if stats["suitable_for_realtime"]:
                rec = f"✅ {model}: Excellent for real-time game play"
                summary["recommendations"].append(rec)
                print(f"  {rec}")
            elif stats["suitable_for_game"]:
                rec = f"⚠️  {model}: Acceptable for turn-based play"
                summary["recommendations"].append(rec)
                print(f"  {rec}")
            else:
                rec = f"❌ {model}: Too slow for interactive gaming"
                summary["recommendations"].append(rec)
                print(f"  {rec}")
        
        return summary
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ollama_timing_benchmark_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "benchmark": "Ollama Response Time Test",
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
                "summary": self.analyze_results() if self.results else {}
            }, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        return filename


def main():
    """Run the timing benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Ollama response times")
    parser.add_argument("--models", nargs="+",
                       default=["qwen2.5-coder:1.5b", "llama3.2:3b", "llama3.1:70b"],
                       help="Models to test (default includes fast, medium, and slow)")
    parser.add_argument("--iterations", type=int, default=3,
                       help="Iterations per query")
    parser.add_argument("--url", default="http://localhost:11434",
                       help="Ollama API URL")
    
    args = parser.parse_args()
    
    print("🎯 Testing Ollama response times for Pipeline & Peril")
    print("Models selected:")
    print("  - qwen2.5-coder:1.5b (small & fast)")
    print("  - llama3.2:3b (medium)")
    print("  - llama3.1:70b (large & slow - if available)")
    print()
    
    benchmark = OllamaTimingBenchmark(args.url)
    summary = benchmark.run_benchmark(args.models, args.iterations)
    
    if summary:
        benchmark.save_results()


if __name__ == "__main__":
    main()