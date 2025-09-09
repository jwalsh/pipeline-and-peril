#!/usr/bin/env python3
"""
Pipeline & Peril - Experiment Tracking Dashboard
Centralized tracking and reporting for all experiments.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib

try:
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("Install plotly for dashboard generation: pip install plotly pandas")


@dataclass
class ExperimentStatus:
    """Status of a single experiment."""
    id: str
    name: str
    phase: int
    status: str  # planned, in_progress, completed, blocked
    progress: float  # 0-100
    start_date: Optional[str]
    end_date: Optional[str]
    metrics: Dict[str, Any]
    blockers: List[str]
    next_steps: List[str]


class ExperimentTracker:
    """Central tracker for all experiments."""
    
    def __init__(self, db_path: str = "experiments/tracking.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._initialize_db()
        
    def _initialize_db(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phase INTEGER NOT NULL,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT,
                data TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')
        
        self.conn.commit()
    
    def register_experiment(self, exp_id: str, name: str, phase: int):
        """Register a new experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO experiments (id, name, phase, status)
            VALUES (?, ?, ?, 'planned')
        ''', (exp_id, name, phase))
        self.conn.commit()
        
        self.log_event(exp_id, 'registered', f'Experiment {name} registered')
    
    def update_status(self, exp_id: str, status: str, progress: float = None):
        """Update experiment status."""
        cursor = self.conn.cursor()
        
        if progress is not None:
            cursor.execute('''
                UPDATE experiments 
                SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, progress, exp_id))
        else:
            cursor.execute('''
                UPDATE experiments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, exp_id))
        
        self.conn.commit()
        
        # Log status change
        self.log_event(exp_id, 'status_change', f'Status changed to {status}')
        
        # Set dates based on status
        if status == 'in_progress':
            cursor.execute('''
                UPDATE experiments 
                SET start_date = CURRENT_TIMESTAMP 
                WHERE id = ? AND start_date IS NULL
            ''', (exp_id,))
        elif status == 'completed':
            cursor.execute('''
                UPDATE experiments 
                SET end_date = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (exp_id,))
        
        self.conn.commit()
    
    def record_metric(self, exp_id: str, metric_name: str, value: float):
        """Record a metric for an experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO metrics (experiment_id, metric_name, metric_value)
            VALUES (?, ?, ?)
        ''', (exp_id, metric_name, value))
        self.conn.commit()
    
    def log_event(self, exp_id: str, event_type: str, description: str, data: Dict = None):
        """Log an event for an experiment."""
        cursor = self.conn.cursor()
        data_json = json.dumps(data) if data else None
        cursor.execute('''
            INSERT INTO events (experiment_id, event_type, description, data)
            VALUES (?, ?, ?, ?)
        ''', (exp_id, event_type, description, data_json))
        self.conn.commit()
    
    def get_experiment_status(self, exp_id: str) -> Optional[ExperimentStatus]:
        """Get current status of an experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM experiments WHERE id = ?
        ''', (exp_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Get latest metrics
        cursor.execute('''
            SELECT metric_name, metric_value 
            FROM metrics 
            WHERE experiment_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (exp_id,))
        
        metrics = {name: value for name, value in cursor.fetchall()}
        
        # Get blockers (events of type 'blocker')
        cursor.execute('''
            SELECT description 
            FROM events 
            WHERE experiment_id = ? AND event_type = 'blocker'
            ORDER BY timestamp DESC
        ''', (exp_id,))
        
        blockers = [row[0] for row in cursor.fetchall()]
        
        # Get next steps (events of type 'next_step')
        cursor.execute('''
            SELECT description 
            FROM events 
            WHERE experiment_id = ? AND event_type = 'next_step'
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (exp_id,))
        
        next_steps = [row[0] for row in cursor.fetchall()]
        
        return ExperimentStatus(
            id=row[0],
            name=row[1],
            phase=row[2],
            status=row[3],
            progress=row[4],
            start_date=row[5],
            end_date=row[6],
            metrics=metrics,
            blockers=blockers,
            next_steps=next_steps
        )
    
    def get_phase_progress(self, phase: int) -> Dict[str, Any]:
        """Get progress for all experiments in a phase."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                AVG(progress) as avg_progress
            FROM experiments
            WHERE phase = ?
        ''', (phase,))
        
        row = cursor.fetchone()
        return {
            'phase': phase,
            'total': row[0],
            'completed': row[1],
            'in_progress': row[2],
            'blocked': row[3],
            'average_progress': row[4] or 0
        }
    
    def generate_dashboard(self, output_path: str = "experiments/dashboard.html"):
        """Generate HTML dashboard with all experiment tracking."""
        if not HAS_PLOTLY:
            print("Plotly not installed. Cannot generate dashboard.")
            return
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Overall Progress', 'Phase Status',
                'Experiment Timeline', 'Metrics Trends',
                'Risk Matrix', 'Resource Burn'
            ),
            specs=[
                [{'type': 'indicator'}, {'type': 'bar'}],
                [{'type': 'scatter'}, {'type': 'scatter'}],
                [{'type': 'scatter'}, {'type': 'bar'}]
            ]
        )
        
        # 1. Overall Progress Gauge
        overall_progress = self._calculate_overall_progress()
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=overall_progress,
                title={'text': "Overall Progress"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 25], 'color': "lightgray"},
                        {'range': [25, 50], 'color': "gray"},
                        {'range': [50, 75], 'color': "lightblue"},
                        {'range': [75, 100], 'color': "blue"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=1, col=1
        )
        
        # 2. Phase Status Bar Chart
        phase_data = self._get_phase_summary()
        fig.add_trace(
            go.Bar(
                x=[f"Phase {p['phase']}" for p in phase_data],
                y=[p['average_progress'] for p in phase_data],
                marker_color=['green' if p['average_progress'] > 75 else 
                             'yellow' if p['average_progress'] > 25 else 
                             'red' for p in phase_data]
            ),
            row=1, col=2
        )
        
        # 3. Experiment Timeline
        timeline_data = self._get_timeline_data()
        if timeline_data:
            fig.add_trace(
                go.Scatter(
                    x=timeline_data['dates'],
                    y=timeline_data['experiments'],
                    mode='markers+lines',
                    marker=dict(size=10, color=timeline_data['colors'])
                ),
                row=2, col=1
            )
        
        # 4. Metrics Trends
        metrics_data = self._get_metrics_trends()
        for metric_name, values in metrics_data.items():
            fig.add_trace(
                go.Scatter(
                    x=values['timestamps'],
                    y=values['values'],
                    name=metric_name,
                    mode='lines+markers'
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title_text="Pipeline & Peril - Experiment Tracking Dashboard",
            showlegend=True,
            height=1200,
            template='plotly_white'
        )
        
        # Save to HTML
        fig.write_html(output_path)
        print(f"Dashboard saved to {output_path}")
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall project progress."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT AVG(progress) FROM experiments
        ''')
        result = cursor.fetchone()[0]
        return result if result else 0
    
    def _get_phase_summary(self) -> List[Dict]:
        """Get summary for all phases."""
        phases = []
        for phase in range(1, 9):
            phases.append(self.get_phase_progress(phase))
        return phases
    
    def _get_timeline_data(self) -> Dict:
        """Get timeline data for visualization."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, start_date, end_date, status
            FROM experiments
            WHERE start_date IS NOT NULL
            ORDER BY start_date
        ''')
        
        experiments = []
        dates = []
        colors = []
        
        status_colors = {
            'completed': 'green',
            'in_progress': 'yellow',
            'blocked': 'red',
            'planned': 'gray'
        }
        
        for row in cursor.fetchall():
            experiments.append(row[1])
            dates.append(row[2])
            colors.append(status_colors.get(row[4], 'gray'))
        
        return {
            'experiments': experiments,
            'dates': dates,
            'colors': colors
        }
    
    def _get_metrics_trends(self) -> Dict:
        """Get metrics trends over time."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT metric_name, metric_value, timestamp
            FROM metrics
            ORDER BY timestamp
            LIMIT 1000
        ''')
        
        metrics = {}
        for name, value, timestamp in cursor.fetchall():
            if name not in metrics:
                metrics[name] = {'values': [], 'timestamps': []}
            metrics[name]['values'].append(value)
            metrics[name]['timestamps'].append(timestamp)
        
        return metrics
    
    def generate_report(self) -> Dict:
        """Generate comprehensive tracking report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'overall_progress': self._calculate_overall_progress(),
            'phases': self._get_phase_summary(),
            'experiments': []
        }
        
        # Get all experiments
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM experiments')
        
        for (exp_id,) in cursor.fetchall():
            status = self.get_experiment_status(exp_id)
            if status:
                report['experiments'].append(asdict(status))
        
        # Calculate risk score
        blocked_count = sum(1 for exp in report['experiments'] 
                          if exp['status'] == 'blocked')
        report['risk_score'] = min(100, blocked_count * 20)
        
        # Calculate velocity
        cursor.execute('''
            SELECT COUNT(*) 
            FROM experiments 
            WHERE status = 'completed' 
            AND end_date > datetime('now', '-7 days')
        ''')
        report['weekly_velocity'] = cursor.fetchone()[0]
        
        return report


def initialize_tracking():
    """Initialize tracking for all planned experiments."""
    tracker = ExperimentTracker()
    
    experiments = [
        # Phase 1
        ("001-dice-mechanics", "Dice Mechanics Validation", 1),
        ("002-service-states", "Service State Transitions", 1),
        ("003-cascade-failures", "Cascade Failure Propagation", 1),
        # Phase 2
        ("004-cli-prototype", "CLI Game Engine", 2),
        ("005-game-ai", "AI Opponent Development", 2),
        ("006-balance-testing", "Automated Balance Testing", 2),
        # Phase 3
        ("007-component-design", "Physical Component Design", 3),
        ("008-print-and-play", "Print-and-Play Version", 3),
        ("009-playtesting-alpha", "Alpha Playtesting", 3),
        # Phase 4
        ("010-art-style", "Art Direction", 4),
        ("011-iconography", "Icon System Design", 4),
        ("012-board-layout", "Board Layout Design", 4),
        # Phase 5
        ("013-web-prototype", "Web Implementation", 5),
        ("014-multiplayer", "Multiplayer System", 5),
        ("015-tutorial-system", "Interactive Tutorial", 5),
        # Phase 6
        ("016-curriculum", "Educational Curriculum", 6),
        ("017-workshops", "Workshop Materials", 6),
        ("018-assessments", "Learning Assessments", 6),
        # Phase 7
        ("019-manufacturing", "Manufacturing Options", 7),
        ("020-packaging", "Package Design", 7),
        ("021-distribution", "Distribution Channels", 7),
        # Phase 8
        ("022-beta-release", "Beta Program", 8),
        ("023-community", "Community Building", 8),
        ("024-feedback-loop", "Feedback Integration", 8),
    ]
    
    for exp_id, name, phase in experiments:
        tracker.register_experiment(exp_id, name, phase)
    
    print(f"Initialized tracking for {len(experiments)} experiments")
    
    # Set initial statuses
    tracker.update_status("001-dice-mechanics", "in_progress", 20)
    tracker.record_metric("001-dice-mechanics", "dice_rolls_tested", 1000)
    
    return tracker


def main():
    """Main entry point for tracking system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Experiment Tracking System")
    parser.add_argument("--init", action="store_true", help="Initialize tracking")
    parser.add_argument("--status", help="Get status of experiment")
    parser.add_argument("--update", help="Update experiment status")
    parser.add_argument("--progress", type=float, help="Set progress (0-100)")
    parser.add_argument("--dashboard", action="store_true", help="Generate dashboard")
    parser.add_argument("--report", action="store_true", help="Generate report")
    
    args = parser.parse_args()
    
    if args.init:
        tracker = initialize_tracking()
        tracker.generate_dashboard()
    else:
        tracker = ExperimentTracker()
        
        if args.status:
            status = tracker.get_experiment_status(args.status)
            if status:
                print(json.dumps(asdict(status), indent=2))
            else:
                print(f"Experiment {args.status} not found")
        
        if args.update and args.progress is not None:
            tracker.update_status(args.update, "in_progress", args.progress)
            print(f"Updated {args.update} to {args.progress}% complete")
        
        if args.dashboard:
            tracker.generate_dashboard()
        
        if args.report:
            report = tracker.generate_report()
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()