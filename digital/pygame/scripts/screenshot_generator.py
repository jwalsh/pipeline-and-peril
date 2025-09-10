#!/usr/bin/env python3
"""
Screenshot Generator for Pipeline & Peril
Generates game screenshots with or without display (headless mode).
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to set SDL to use dummy video driver for headless mode
def set_headless_mode():
    """Configure SDL for headless operation."""
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    print("Running in headless mode (no display required)")

# Import pygame after setting environment
import pygame
from engine.game_state import GameState, GameConfig, ServiceType, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI

class ScreenshotGenerator:
    """Generate screenshots at different game stages."""
    
    def __init__(self, headless: bool = False, width: int = 1200, height: int = 800):
        self.headless = headless
        self.width = width
        self.height = height
        self.screenshots = []
        
        if self.headless:
            set_headless_mode()
        
        # Initialize Pygame
        pygame.init()
        
    def setup_game_state(self, round_num: int = 0, phase: str = "traffic") -> GameState:
        """Create a game state for screenshot."""
        config = GameConfig(max_rounds=15, cooperative_mode=False)
        game_state = GameState(config, 4)
        
        # Set round and phase
        game_state.round = round_num
        game_state.phase = phase
        
        # Set player strategies
        strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE,
                     PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
        for i, player in enumerate(game_state.players):
            player.strategy = strategies[i]
            player.name = f"Player {i+1}"
        
        return game_state
    
    def generate_screenshot_sequence(self):
        """Generate a sequence of screenshots showing game progression."""
        output_dir = Path("screenshots")
        output_dir.mkdir(exist_ok=True)
        
        # Initialize UI
        ui = GameUI(self.width, self.height)
        
        scenarios = [
            # Early game with initial setup
            {
                "name": "01_game_start",
                "round": 1,
                "phase": "traffic",
                "setup": self._setup_early_game,
                "description": "Game start with initial services"
            },
            # Mid-game with dice roll visible
            {
                "name": "02_dice_traffic",
                "round": 3,
                "phase": "traffic",
                "setup": self._setup_mid_game_traffic,
                "description": "Traffic phase showing 2d10 dice roll"
            },
            # Action phase with multiple services
            {
                "name": "03_action_phase",
                "round": 5,
                "phase": "action",
                "setup": self._setup_action_phase,
                "description": "Action phase with service deployment"
            },
            # Cascade failure with d20 roll
            {
                "name": "04_cascade_failure",
                "round": 7,
                "phase": "resolution",
                "setup": self._setup_cascade_scenario,
                "description": "Cascade failure with d20 roll visible"
            },
            # Chaos event with d8 roll
            {
                "name": "05_chaos_event",
                "round": 8,
                "phase": "chaos",
                "setup": self._setup_chaos_scenario,
                "description": "Chaos phase with d8 roll and high entropy"
            },
            # Late game complex state
            {
                "name": "06_late_game",
                "round": 12,
                "phase": "traffic",
                "setup": self._setup_late_game,
                "description": "Complex late game with many services"
            }
        ]
        
        for scenario in scenarios:
            print(f"\nGenerating screenshot: {scenario['name']}")
            print(f"  {scenario['description']}")
            
            # Create game state
            game_state = self.setup_game_state(scenario['round'], scenario['phase'])
            
            # Apply scenario-specific setup
            scenario['setup'](game_state)
            
            # Update UI with game state
            ui.update(game_state, 0.016)  # 60 FPS frame time
            
            # Render frame
            ui.render()
            
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = output_dir / f"pipeline_peril_{scenario['name']}_{timestamp}.png"
            pygame.image.save(ui.screen, str(filename))
            
            self.screenshots.append({
                "file": str(filename),
                "scenario": scenario['name'],
                "description": scenario['description']
            })
            
            print(f"  Saved: {filename}")
            
            # Small delay for visual mode
            if not self.headless:
                pygame.time.wait(500)
        
        # Cleanup
        pygame.quit()
        
        return self.screenshots
    
    def _setup_early_game(self, game_state: GameState):
        """Setup early game state."""
        # Each player deploys initial load balancer
        positions = [(2, 1), (2, 4), (5, 1), (5, 4)]
        for i in range(4):
            game_state.execute_action(i, {
                "type": "deploy",
                "service_type": ServiceType.LOAD_BALANCER.value,
                "position": positions[i]
            })
        
        # Generate and show first traffic roll
        game_state.generate_traffic()
        
    def _setup_mid_game_traffic(self, game_state: GameState):
        """Setup mid-game with traffic dice visible."""
        # Deploy various services
        services = [
            (0, ServiceType.LOAD_BALANCER, (1, 2)),
            (0, ServiceType.COMPUTE, (2, 2)),
            (1, ServiceType.DATABASE, (3, 3)),
            (1, ServiceType.CACHE, (2, 3)),
            (2, ServiceType.QUEUE, (4, 2)),
            (2, ServiceType.API_GATEWAY, (4, 3)),
            (3, ServiceType.LOAD_BALANCER, (5, 2)),
        ]
        
        for player_id, service_type, pos in services:
            game_state.execute_action(player_id, {
                "type": "deploy",
                "service_type": service_type.value,
                "position": pos
            })
        
        # Generate traffic with dice roll
        game_state.generate_traffic()
        
        # Set some entropy
        game_state.entropy = 4
        
    def _setup_action_phase(self, game_state: GameState):
        """Setup action phase with deployment options."""
        # Setup board with services
        self._setup_mid_game_traffic(game_state)
        
        # Add more services and some damage
        services = [
            (0, ServiceType.COMPUTE, (3, 1)),
            (1, ServiceType.DATABASE, (3, 4)),
            (2, ServiceType.CACHE, (4, 1)),
        ]
        
        for player_id, service_type, pos in services:
            game_state.execute_action(player_id, {
                "type": "deploy",
                "service_type": service_type.value,
                "position": pos
            })
        
        # Damage some services
        for service_id in [2, 4]:
            if service_id in game_state.services:
                game_state.services[service_id].state = game_state.services[service_id].state.__class__.DEGRADED
                game_state.services[service_id].load = 7
        
    def _setup_cascade_scenario(self, game_state: GameState):
        """Setup cascade failure scenario."""
        self._setup_action_phase(game_state)
        
        # Trigger cascade check with d20 roll
        if game_state.services:
            # Get a service and mark it as failed
            service = list(game_state.services.values())[0]
            service.state = service.state.__class__.FAILED
            
            # Roll d20 for cascade
            game_state.roll_dice("d20", 1)
            
        game_state.entropy = 6
        
    def _setup_chaos_scenario(self, game_state: GameState):
        """Setup chaos event scenario."""
        self._setup_cascade_scenario(game_state)
        
        # High entropy triggers chaos
        game_state.entropy = 8
        
        # Roll d8 for chaos event
        rolls, chaos_roll = game_state.roll_dice("d8", 1)
        
        # Add some failed services
        for service_id in [1, 3]:
            if service_id in game_state.services:
                game_state.services[service_id].state = game_state.services[service_id].state.__class__.FAILED
        
    def _setup_late_game(self, game_state: GameState):
        """Setup complex late game state."""
        # Fill board with many services
        all_positions = [
            (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
            (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
            (2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5),
            (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
            (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5),
            (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
        ]
        
        service_types = list(ServiceType)
        
        # Deploy services across the board
        for i, pos in enumerate(all_positions[:20]):  # Deploy 20 services
            player_id = i % 4
            service_type = service_types[i % len(service_types)]
            
            success = game_state.execute_action(player_id, {
                "type": "deploy",
                "service_type": service_type.value,
                "position": pos
            })
        
        # Set various states
        for service_id, service in game_state.services.items():
            if service_id % 3 == 0:
                service.state = service.state.__class__.DEGRADED
                service.load = 6
            elif service_id % 5 == 0:
                service.state = service.state.__class__.OVERLOADED
                service.load = 12
        
        # High entropy late game
        game_state.entropy = 9
        
        # Generate traffic
        game_state.generate_traffic()
        
        # Update scores
        for i, player in enumerate(game_state.players):
            player.score = 50 + i * 10


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Pipeline & Peril screenshots")
    parser.add_argument("--headless", action="store_true",
                       help="Run in headless mode (no display required)")
    parser.add_argument("--width", type=int, default=1200,
                       help="Screenshot width")
    parser.add_argument("--height", type=int, default=800,
                       help="Screenshot height")
    parser.add_argument("--single", type=str,
                       help="Generate single screenshot scenario (e.g., 'cascade')")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PIPELINE & PERIL SCREENSHOT GENERATOR")
    print("=" * 60)
    
    if args.headless:
        print("Mode: Headless (no display)")
    else:
        print("Mode: Visual (display required)")
    
    print(f"Resolution: {args.width}x{args.height}")
    print()
    
    generator = ScreenshotGenerator(
        headless=args.headless,
        width=args.width,
        height=args.height
    )
    
    screenshots = generator.generate_screenshot_sequence()
    
    print("\n" + "=" * 60)
    print("SCREENSHOT GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated {len(screenshots)} screenshots:")
    
    for shot in screenshots:
        print(f"  - {shot['scenario']}: {shot['file']}")
    
    print("\nScreenshots saved to: screenshots/")


if __name__ == "__main__":
    main()