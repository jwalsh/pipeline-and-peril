#!/usr/bin/env python3
"""
Pipeline & Peril - Experiment Runner Framework
A standardized framework for running reproducible experiments.
"""

import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    name: str
    version: str
    description: str
    parameters: Dict[str, Any]
    random_seed: Optional[int] = None
    max_iterations: int = 1000
    timeout_seconds: int = 3600
    output_dir: str = "artifacts"
    data_dir: str = "data"


@dataclass
class ExperimentResult:
    """Result from a single experiment run."""
    experiment_id: str
    session_id: str
    timestamp: str
    parameters: Dict[str, Any]
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    duration_seconds: float
    success: bool
    error: Optional[str] = None


class BaseExperiment(ABC):
    """Base class for all experiments."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize experiment with configuration."""
        self.config_path = config_path or Path("config.yaml")
        self.config = self._load_config()
        self.session_id = str(uuid4())
        self.results: List[ExperimentResult] = []
        self.start_time = None
        self.end_time = None
        
        # Create output directories
        self.output_dir = Path(self.config.output_dir)
        self.data_dir = Path(self.config.data_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Set random seed for reproducibility
        if self.config.random_seed:
            self._set_random_seed(self.config.random_seed)
    
    def _load_config(self) -> ExperimentConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return ExperimentConfig(
                name="unnamed_experiment",
                version="1.0.0",
                description="No description provided",
                parameters={}
            )
        
        with open(self.config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return ExperimentConfig(**config_dict)
    
    def _set_random_seed(self, seed: int):
        """Set random seed for reproducibility."""
        import random
        import numpy as np
        
        random.seed(seed)
        np.random.seed(seed)
        logger.info(f"Random seed set to {seed}")
    
    @abstractmethod
    def setup(self):
        """Setup experiment before running."""
        pass
    
    @abstractmethod
    def run_iteration(self, iteration: int) -> Dict[str, Any]:
        """Run a single iteration of the experiment."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup after experiment completion."""
        pass
    
    def validate_parameters(self) -> bool:
        """Validate experiment parameters."""
        return True
    
    def run(self) -> List[ExperimentResult]:
        """Run the complete experiment."""
        logger.info(f"Starting experiment: {self.config.name} v{self.config.version}")
        logger.info(f"Session ID: {self.session_id}")
        
        # Validate parameters
        if not self.validate_parameters():
            logger.error("Parameter validation failed")
            return []
        
        # Setup
        self.start_time = time.time()
        self.setup()
        
        # Run iterations
        for i in range(self.config.max_iterations):
            if time.time() - self.start_time > self.config.timeout_seconds:
                logger.warning(f"Timeout reached after {i} iterations")
                break
            
            try:
                # Run single iteration
                iteration_start = time.time()
                results = self.run_iteration(i)
                duration = time.time() - iteration_start
                
                # Create result object
                result = ExperimentResult(
                    experiment_id=f"{self.config.name}-{self.config.version}",
                    session_id=self.session_id,
                    timestamp=datetime.utcnow().isoformat(),
                    parameters=self.config.parameters,
                    results=results,
                    metadata={
                        "iteration": i,
                        "config_version": self.config.version
                    },
                    duration_seconds=duration,
                    success=True
                )
                
                self.results.append(result)
                
                # Log progress
                if (i + 1) % 100 == 0:
                    logger.info(f"Completed {i + 1} iterations")
                
            except Exception as e:
                logger.error(f"Error in iteration {i}: {e}")
                result = ExperimentResult(
                    experiment_id=f"{self.config.name}-{self.config.version}",
                    session_id=self.session_id,
                    timestamp=datetime.utcnow().isoformat(),
                    parameters=self.config.parameters,
                    results={},
                    metadata={"iteration": i},
                    duration_seconds=0,
                    success=False,
                    error=str(e)
                )
                self.results.append(result)
        
        # Cleanup
        self.end_time = time.time()
        self.cleanup()
        
        # Save results
        self._save_results()
        
        # Generate summary
        self._print_summary()
        
        return self.results
    
    def _save_results(self):
        """Save results to JSON Lines file."""
        output_file = self.data_dir / f"raw/{self.session_id}.jsonl"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            for result in self.results:
                f.write(json.dumps(asdict(result)) + '\n')
        
        logger.info(f"Results saved to {output_file}")
    
    def _print_summary(self):
        """Print experiment summary."""
        total_duration = self.end_time - self.start_time
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        print("\n" + "="*60)
        print(f"Experiment: {self.config.name} v{self.config.version}")
        print(f"Session: {self.session_id}")
        print("="*60)
        print(f"Total iterations: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {successful/len(self.results)*100:.2f}%")
        print(f"Total duration: {total_duration:.2f} seconds")
        print(f"Average iteration: {total_duration/len(self.results)*1000:.2f} ms")
        print("="*60)


class ExperimentOrchestrator:
    """Orchestrate multiple experiments."""
    
    def __init__(self):
        self.experiments: List[BaseExperiment] = []
        self.results: Dict[str, List[ExperimentResult]] = {}
    
    def add_experiment(self, experiment: BaseExperiment):
        """Add an experiment to the orchestrator."""
        self.experiments.append(experiment)
    
    def run_all(self, parallel: bool = False):
        """Run all experiments."""
        if parallel:
            self._run_parallel()
        else:
            self._run_sequential()
    
    def _run_sequential(self):
        """Run experiments sequentially."""
        for experiment in self.experiments:
            logger.info(f"Running {experiment.config.name}")
            results = experiment.run()
            self.results[experiment.config.name] = results
    
    def _run_parallel(self):
        """Run experiments in parallel."""
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for experiment in self.experiments:
                future = executor.submit(experiment.run)
                futures.append((experiment.config.name, future))
            
            for name, future in futures:
                self.results[name] = future.result()
    
    def generate_report(self):
        """Generate a summary report of all experiments."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "experiments": {}
        }
        
        for name, results in self.results.items():
            successful = sum(1 for r in results if r.success)
            report["experiments"][name] = {
                "total_runs": len(results),
                "successful": successful,
                "failed": len(results) - successful,
                "success_rate": successful / len(results) * 100 if results else 0
            }
        
        report_file = Path("artifacts/orchestrator_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        return report


def main():
    """Main entry point for running experiments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Pipeline & Peril experiments")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"),
                       help="Path to configuration file")
    parser.add_argument("--parallel", action="store_true",
                       help="Run experiments in parallel")
    
    args = parser.parse_args()
    
    # This would be overridden by specific experiment implementations
    logger.error("This is the base runner. Use a specific experiment's run.py instead.")
    sys.exit(1)


if __name__ == "__main__":
    main()