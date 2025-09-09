#!/usr/bin/env python3
"""
Experiment 001: Dice Mechanics
Test and validate dice probability distributions for Pipeline & Peril.
"""

import sys
from pathlib import Path
import random
from typing import Dict, Any, List
from collections import Counter

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from runner import BaseExperiment


class DiceMechanicsExperiment(BaseExperiment):
    """Experiment to test dice mechanics and probabilities."""
    
    def setup(self):
        """Initialize dice configurations."""
        self.dice_types = {
            'd4': 4,
            'd6': 6,
            'd8': 8,
            'd10': 10,
            'd12': 12,
            'd20': 20
        }
        
        # Track statistics
        self.roll_distributions = {dice: Counter() for dice in self.dice_types}
        self.service_check_results = []
        self.cascade_chains = []
        
    def roll_die(self, die_type: str) -> int:
        """Roll a single die."""
        max_value = self.dice_types.get(die_type, 6)
        return random.randint(1, max_value)
    
    def roll_dice(self, die_type: str, count: int) -> List[int]:
        """Roll multiple dice of the same type."""
        return [self.roll_die(die_type) for _ in range(count)]
    
    def service_check(self, 
                     capacity: int, 
                     load: int, 
                     resources: int = 0,
                     bugs: int = 0) -> Dict[str, Any]:
        """Simulate a service check."""
        # Calculate effective capacity
        effective_capacity = capacity + resources - bugs
        
        # Calculate difficulty (what we need to roll)
        difficulty = max(10, load - effective_capacity + 10)
        
        # Roll d20 for check
        roll = self.roll_die('d20')
        success = roll >= difficulty
        
        return {
            'capacity': capacity,
            'load': load,
            'resources': resources,
            'bugs': bugs,
            'effective_capacity': effective_capacity,
            'difficulty': difficulty,
            'roll': roll,
            'success': success,
            'margin': roll - difficulty
        }
    
    def simulate_cascade(self, 
                        initial_failure: bool,
                        dependent_services: int) -> Dict[str, Any]:
        """Simulate cascade failure propagation."""
        failures = []
        
        if initial_failure:
            # Each dependent service gets +2 load
            for i in range(dependent_services):
                # Simulate dependent service check with extra load
                check = self.service_check(
                    capacity=3,  # Base capacity
                    load=5 + 2,  # Normal load + cascade load
                    resources=random.randint(0, 2)
                )
                failures.append(check['success'])
        
        total_failures = sum(1 for f in failures if not f)
        
        return {
            'initial_failure': initial_failure,
            'dependent_services': dependent_services,
            'cascade_failures': total_failures,
            'cascade_rate': total_failures / dependent_services if dependent_services > 0 else 0
        }
    
    def test_latency(self, hops: int, has_cache: bool = False) -> Dict[str, Any]:
        """Test latency calculations."""
        latencies = []
        
        for _ in range(hops):
            latency = self.roll_die('d12')
            latencies.append(latency)
        
        total_latency = sum(latencies)
        
        # Cache reduces latency by 1 step
        if has_cache and total_latency > 0:
            total_latency -= 1
        
        # Determine latency category
        if total_latency <= 3:
            category = 'fast'
            penalty = 0
        elif total_latency <= 6:
            category = 'normal'
            penalty = 1
        elif total_latency <= 9:
            category = 'slow'
            penalty = 2
        else:
            category = 'timeout'
            penalty = float('inf')
        
        return {
            'hops': hops,
            'has_cache': has_cache,
            'latencies': latencies,
            'total_latency': total_latency,
            'category': category,
            'penalty': penalty
        }
    
    def run_iteration(self, iteration: int) -> Dict[str, Any]:
        """Run a single iteration of dice mechanics testing."""
        results = {}
        
        # Test 1: Basic dice distributions
        dice_rolls = {}
        for die_type in self.dice_types:
            roll = self.roll_die(die_type)
            dice_rolls[die_type] = roll
            self.roll_distributions[die_type][roll] += 1
        results['dice_rolls'] = dice_rolls
        
        # Test 2: Service check under various loads
        load_scenarios = [
            ('light', 3),
            ('normal', 6),
            ('heavy', 9),
            ('overload', 12)
        ]
        
        service_checks = {}
        for scenario_name, load in load_scenarios:
            check = self.service_check(
                capacity=3,
                load=load,
                resources=random.randint(0, 3),
                bugs=random.randint(0, 2)
            )
            service_checks[scenario_name] = check
            self.service_check_results.append(check)
        results['service_checks'] = service_checks
        
        # Test 3: Cascade failure
        cascade = self.simulate_cascade(
            initial_failure=random.random() < 0.3,  # 30% chance of initial failure
            dependent_services=random.randint(1, 5)
        )
        self.cascade_chains.append(cascade)
        results['cascade'] = cascade
        
        # Test 4: Latency
        latency = self.test_latency(
            hops=random.randint(1, 4),
            has_cache=random.random() < 0.5
        )
        results['latency'] = latency
        
        # Test 5: Chaos event
        chaos_roll = self.roll_die('d8')
        chaos_level = min(4, 1 + iteration // 250)  # Increase every 250 iterations
        chaos_modified = chaos_roll + (chaos_level - 1) * 2
        results['chaos'] = {
            'roll': chaos_roll,
            'level': chaos_level,
            'modified': chaos_modified,
            'severity': 'low' if chaos_modified <= 4 else 'medium' if chaos_modified <= 8 else 'high'
        }
        
        return results
    
    def cleanup(self):
        """Analyze and save distribution statistics."""
        # Calculate success rates by load scenario
        from collections import defaultdict
        
        success_by_load = defaultdict(list)
        for check in self.service_check_results:
            load_category = 'light' if check['load'] <= 3 else \
                          'normal' if check['load'] <= 6 else \
                          'heavy' if check['load'] <= 9 else 'overload'
            success_by_load[load_category].append(check['success'])
        
        # Calculate success rates
        success_rates = {}
        for category, successes in success_by_load.items():
            if successes:
                rate = sum(successes) / len(successes) * 100
                success_rates[category] = f"{rate:.1f}%"
        
        # Print distribution analysis
        print("\n" + "="*60)
        print("DICE DISTRIBUTION ANALYSIS")
        print("="*60)
        
        for die_type, distribution in self.roll_distributions.items():
            if distribution:
                total_rolls = sum(distribution.values())
                avg = sum(k * v for k, v in distribution.items()) / total_rolls
                print(f"\n{die_type} (n={total_rolls}):")
                print(f"  Average: {avg:.2f}")
                print(f"  Expected: {(self.dice_types[die_type] + 1) / 2:.2f}")
                
        print("\n" + "="*60)
        print("SERVICE CHECK SUCCESS RATES")
        print("="*60)
        
        for category, rate in success_rates.items():
            print(f"  {category:10s}: {rate}")
        
        # Calculate cascade statistics
        if self.cascade_chains:
            avg_cascade_rate = sum(c['cascade_rate'] for c in self.cascade_chains) / len(self.cascade_chains)
            print(f"\nAverage cascade rate: {avg_cascade_rate*100:.1f}%")


def main():
    """Run the dice mechanics experiment."""
    from pathlib import Path
    
    # Create config if it doesn't exist
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        import yaml
        config = {
            'name': 'dice-mechanics',
            'version': '1.0.0',
            'description': 'Test dice probability distributions and game mechanics',
            'parameters': {
                'service_base_capacity': 3,
                'max_resources': 3,
                'max_bugs': 2,
                'cascade_load_increase': 2
            },
            'random_seed': 42,
            'max_iterations': 1000,
            'timeout_seconds': 60
        }
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
    
    # Run experiment
    experiment = DiceMechanicsExperiment(config_path)
    experiment.run()


if __name__ == "__main__":
    main()