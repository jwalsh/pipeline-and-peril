#!/usr/bin/env python3
"""
Pipeline & Peril - Experiment Visualization Utilities
Common visualization functions for experiment analysis.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import warnings

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False
    warnings.warn("Visualization libraries not installed. Run: pip install matplotlib seaborn pandas numpy")


class ExperimentVisualizer:
    """Visualization utilities for experiment data."""
    
    def __init__(self, experiment_name: str, data_dir: Path = None):
        """Initialize visualizer for a specific experiment."""
        self.experiment_name = experiment_name
        self.data_dir = data_dir or Path(f"experiments/{experiment_name}/data")
        self.artifact_dir = Path(f"experiments/{experiment_name}/artifacts/figures")
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        
        if HAS_VIZ:
            # Set style
            sns.set_style("whitegrid")
            plt.rcParams['figure.figsize'] = (10, 6)
            plt.rcParams['font.size'] = 12
    
    def load_jsonl_data(self, filename: str) -> List[Dict]:
        """Load data from JSON Lines file."""
        filepath = self.data_dir / "raw" / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        data = []
        with open(filepath, 'r') as f:
            for line in f:
                data.append(json.loads(line))
        return data
    
    def plot_dice_distribution(self, 
                              rolls: Dict[str, List[int]], 
                              save: bool = True) -> Optional[Tuple]:
        """Plot dice roll distributions."""
        if not HAS_VIZ:
            return None
        
        num_dice = len(rolls)
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for idx, (die_type, values) in enumerate(rolls.items()):
            if idx >= 6:
                break
            
            ax = axes[idx]
            
            # Create histogram
            max_val = int(die_type[1:])  # Extract number from 'd20' -> 20
            bins = range(1, max_val + 2)
            
            ax.hist(values, bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
            
            # Add expected line
            expected = (max_val + 1) / 2
            ax.axvline(expected, color='red', linestyle='--', 
                      label=f'Expected: {expected:.1f}')
            
            # Add actual mean
            actual = np.mean(values)
            ax.axvline(actual, color='green', linestyle='-', 
                      label=f'Actual: {actual:.1f}')
            
            ax.set_title(f'{die_type} Distribution (n={len(values)})')
            ax.set_xlabel('Roll Value')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for idx in range(num_dice, 6):
            axes[idx].set_visible(False)
        
        plt.suptitle(f'Dice Roll Distributions - {self.experiment_name}', fontsize=16)
        plt.tight_layout()
        
        if save:
            filepath = self.artifact_dir / "dice_distributions.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        return fig, axes
    
    def plot_success_rates(self, 
                          success_data: Dict[str, List[bool]], 
                          save: bool = True) -> Optional[Tuple]:
        """Plot success rates by category."""
        if not HAS_VIZ:
            return None
        
        # Calculate success rates
        categories = []
        rates = []
        counts = []
        confidence_intervals = []
        
        for category, successes in success_data.items():
            if successes:
                rate = sum(successes) / len(successes)
                categories.append(category)
                rates.append(rate * 100)
                counts.append(len(successes))
                
                # Calculate 95% confidence interval
                se = np.sqrt(rate * (1 - rate) / len(successes))
                ci = 1.96 * se * 100
                confidence_intervals.append(ci)
        
        # Create bar plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(categories))
        bars = ax.bar(x, rates, alpha=0.7, color='steelblue', edgecolor='black')
        
        # Add error bars for confidence intervals
        ax.errorbar(x, rates, yerr=confidence_intervals, fmt='none', 
                   color='black', capsize=5, capthick=2)
        
        # Add target zones
        ax.axhspan(75, 85, alpha=0.2, color='green', label='Target Range')
        ax.axhline(80, color='green', linestyle='--', alpha=0.5)
        
        # Customize plot
        ax.set_xlabel('Load Category', fontsize=12)
        ax.set_ylabel('Success Rate (%)', fontsize=12)
        ax.set_title(f'Service Check Success Rates - {self.experiment_name}', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 105)
        
        # Add value labels on bars
        for bar, rate, count in zip(bars, rates, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{rate:.1f}%\n(n={count})',
                   ha='center', va='bottom', fontsize=10)
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save:
            filepath = self.artifact_dir / "success_rates.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        return fig, ax
    
    def plot_cascade_analysis(self, 
                             cascade_data: List[Dict], 
                             save: bool = True) -> Optional[Tuple]:
        """Plot cascade failure analysis."""
        if not HAS_VIZ:
            return None
        
        df = pd.DataFrame(cascade_data)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: Cascade rate by number of dependencies
        ax1 = axes[0]
        grouped = df.groupby('dependent_services')['cascade_rate'].agg(['mean', 'std', 'count'])
        
        x = grouped.index
        y = grouped['mean'] * 100
        yerr = grouped['std'] * 100
        
        ax1.errorbar(x, y, yerr=yerr, marker='o', linestyle='-', 
                    capsize=5, capthick=2, markersize=8)
        
        ax1.set_xlabel('Number of Dependent Services', fontsize=12)
        ax1.set_ylabel('Average Cascade Rate (%)', fontsize=12)
        ax1.set_title('Cascade Failure Propagation', fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Distribution of cascade sizes
        ax2 = axes[1]
        cascade_sizes = df['cascade_failures'].value_counts().sort_index()
        
        ax2.bar(cascade_sizes.index, cascade_sizes.values, 
               alpha=0.7, color='coral', edgecolor='black')
        
        ax2.set_xlabel('Number of Cascade Failures', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_title('Distribution of Cascade Sizes', fontsize=14)
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(f'Cascade Failure Analysis - {self.experiment_name}', fontsize=16)
        plt.tight_layout()
        
        if save:
            filepath = self.artifact_dir / "cascade_analysis.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        return fig, axes
    
    def plot_latency_distribution(self, 
                                 latency_data: List[Dict], 
                                 save: bool = True) -> Optional[Tuple]:
        """Plot latency distribution analysis."""
        if not HAS_VIZ:
            return None
        
        df = pd.DataFrame(latency_data)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Plot 1: Latency distribution
        ax1 = axes[0, 0]
        ax1.hist(df['total_latency'], bins=20, alpha=0.7, 
                color='steelblue', edgecolor='black')
        ax1.set_xlabel('Total Latency', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('Latency Distribution', fontsize=14)
        
        # Add category boundaries
        ax1.axvline(3, color='green', linestyle='--', alpha=0.5, label='Fast')
        ax1.axvline(6, color='yellow', linestyle='--', alpha=0.5, label='Normal')
        ax1.axvline(9, color='orange', linestyle='--', alpha=0.5, label='Slow')
        ax1.axvline(12, color='red', linestyle='--', alpha=0.5, label='Timeout')
        ax1.legend()
        
        # Plot 2: Latency by hop count
        ax2 = axes[0, 1]
        hop_groups = df.groupby('hops')['total_latency'].agg(['mean', 'std'])
        
        ax2.errorbar(hop_groups.index, hop_groups['mean'], 
                    yerr=hop_groups['std'], marker='o', linestyle='-',
                    capsize=5, capthick=2, markersize=8)
        ax2.set_xlabel('Number of Hops', fontsize=12)
        ax2.set_ylabel('Average Latency', fontsize=12)
        ax2.set_title('Latency by Network Hops', fontsize=14)
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Cache effectiveness
        ax3 = axes[1, 0]
        cache_groups = df.groupby('has_cache')['total_latency'].mean()
        
        bars = ax3.bar(['No Cache', 'With Cache'], cache_groups.values, 
                      alpha=0.7, color=['coral', 'lightgreen'], edgecolor='black')
        
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=12)
        
        ax3.set_ylabel('Average Latency', fontsize=12)
        ax3.set_title('Cache Effectiveness', fontsize=14)
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Category distribution
        ax4 = axes[1, 1]
        category_counts = df['category'].value_counts()
        
        colors = {'fast': 'green', 'normal': 'yellow', 
                 'slow': 'orange', 'timeout': 'red'}
        bar_colors = [colors.get(cat, 'gray') for cat in category_counts.index]
        
        ax4.bar(category_counts.index, category_counts.values, 
               alpha=0.7, color=bar_colors, edgecolor='black')
        ax4.set_xlabel('Latency Category', fontsize=12)
        ax4.set_ylabel('Count', fontsize=12)
        ax4.set_title('Latency Category Distribution', fontsize=14)
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(f'Latency Analysis - {self.experiment_name}', fontsize=16)
        plt.tight_layout()
        
        if save:
            filepath = self.artifact_dir / "latency_analysis.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filepath}")
        
        return fig, axes
    
    def generate_summary_report(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate a summary report from experiment results."""
        if not results:
            return {}
        
        report = {
            'experiment': self.experiment_name,
            'total_iterations': len(results),
            'statistics': {}
        }
        
        # Extract and analyze different metrics
        if HAS_VIZ:
            df = pd.DataFrame(results)
            
            # Basic statistics
            report['statistics']['duration'] = {
                'total_seconds': df['duration_seconds'].sum(),
                'mean_ms': df['duration_seconds'].mean() * 1000,
                'std_ms': df['duration_seconds'].std() * 1000
            }
            
            report['statistics']['success_rate'] = {
                'overall': df['success'].mean() * 100,
                'failures': (~df['success']).sum()
            }
        
        # Save report
        report_path = self.artifact_dir.parent / "summary_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Summary report saved to: {report_path}")
        return report


def main():
    """Example usage of visualization utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visualize experiment results")
    parser.add_argument("experiment", help="Experiment name (e.g., 001-dice-mechanics)")
    parser.add_argument("--data-file", help="Data file name", 
                       default="latest.jsonl")
    
    args = parser.parse_args()
    
    visualizer = ExperimentVisualizer(args.experiment)
    
    try:
        # Load data
        data = visualizer.load_jsonl_data(args.data_file)
        print(f"Loaded {len(data)} records")
        
        # Generate visualizations based on experiment type
        if "dice" in args.experiment:
            # Extract dice rolls
            rolls = {}
            for record in data:
                if 'results' in record and 'dice_rolls' in record['results']:
                    for die, value in record['results']['dice_rolls'].items():
                        if die not in rolls:
                            rolls[die] = []
                        rolls[die].append(value)
            
            if rolls:
                visualizer.plot_dice_distribution(rolls)
        
        # Generate summary report
        visualizer.generate_summary_report(data)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure to run the experiment first!")


if __name__ == "__main__":
    main()