#!/usr/bin/env python3
"""
Generate screenshots for README demonstration.
"""

import sys
import os
import pygame
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.game_state import GameState, GameConfig, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI


def create_demo_screenshots():
    """Create demonstration screenshots for the README."""
    
    # Initialize pygame
    pygame.init()
    
    # Create game configuration
    config = GameConfig(max_rounds=10, cooperative_mode=False)
    strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, 
                 PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
    
    # Initialize game and AI
    game_state = GameState(config, len(strategies))
    for i, player in enumerate(game_state.players):
        player.strategy = strategies[i]
    
    ai_manager = AIPlayerManager(strategies)
    
    # Initialize UI
    ui = GameUI(1200, 800)
    
    screenshots = []
    
    # Screenshot 1: Initial game state
    ui.update(game_state, 0.0)
    ui.render()
    screenshot1 = ui.save_screenshot("pipeline_peril_initial_state.png")
    screenshots.append(screenshot1)
    print(f"Screenshot 1: {screenshot1}")
    
    # Simulate a few rounds to show progression
    for round_num in range(3):
        # Traffic phase
        requests = game_state.generate_traffic()
        game_state.process_requests(requests)
        
        # Action phase - AI players take actions
        for player_id in range(len(game_state.players)):
            player = game_state.players[player_id]
            actions_taken = 0
            while player.actions_remaining > 0 and actions_taken < 3:
                action = ai_manager.get_action(player_id, game_state)
                if action:
                    success = game_state.execute_action(player_id, action)
                    if success:
                        actions_taken += 1
                    else:
                        player.actions_remaining = 0
                else:
                    player.actions_remaining = 0
        
        # Chaos event
        game_state.chaos_event()
        game_state.advance_round()
        
        # Take screenshot after each round
        ui.update(game_state, 0.0)
        ui.render()
        screenshot = ui.save_screenshot(f"pipeline_peril_round_{round_num + 1}.png")
        screenshots.append(screenshot)
        print(f"Screenshot {round_num + 2}: {screenshot}")
    
    # Final screenshot with debug info
    ui.show_debug = True
    ui.update(game_state, 0.0)
    ui.render()
    screenshot_debug = ui.save_screenshot("pipeline_peril_debug_view.png")
    screenshots.append(screenshot_debug)
    print(f"Debug screenshot: {screenshot_debug}")
    
    # Game statistics screenshot
    ui.show_debug = False
    
    # Simulate game completion
    for _ in range(7):  # Complete remaining rounds
        requests = game_state.generate_traffic()
        game_state.process_requests(requests)
        
        # Quick AI actions
        for player_id in range(len(game_state.players)):
            player = game_state.players[player_id]
            while player.actions_remaining > 0:
                action = ai_manager.get_action(player_id, game_state)
                if action:
                    game_state.execute_action(player_id, action)
                else:
                    player.actions_remaining = 0
        
        game_state.chaos_event()
        game_state.advance_round()
    
    # Final game state
    ui.update(game_state, 0.0)
    ui.render()
    screenshot_final = ui.save_screenshot("pipeline_peril_final_state.png")
    screenshots.append(screenshot_final)
    print(f"Final screenshot: {screenshot_final}")
    
    ui.cleanup()
    
    print(f"\nGenerated {len(screenshots)} screenshots:")
    for screenshot in screenshots:
        print(f"  - {screenshot}")
    
    return screenshots


if __name__ == "__main__":
    screenshots = create_demo_screenshots()