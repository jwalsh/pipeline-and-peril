#!/usr/bin/env python3
"""
Quick Play - Start a Pipeline & Peril game for immediate interaction
"""

import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.game_state import GameState, GameConfig, ServiceType, ServiceState, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI

def create_interactive_game():
    """Create a game where the human is Player 1 and AI controls others."""
    
    print("🎮 Welcome to Pipeline & Peril!")
    print("=" * 50)
    
    # Create game
    config = GameConfig(max_rounds=15, cooperative_mode=False)
    game_state = GameState(config, 4)
    
    # Set strategies
    strategies = [PlayerStrategy.BALANCED, PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, PlayerStrategy.RANDOM]
    for i, player in enumerate(game_state.players):
        player.strategy = strategies[i]
        player.name = f"Player {i+1}"
    
    # You are Player 1 (index 0)
    game_state.players[0].name = "You"
    
    # Create AI manager for other players
    ai_strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, PlayerStrategy.RANDOM]
    ai_manager = AIPlayerManager(ai_strategies)
    
    print(f"You are Player 1 (Balanced strategy)")
    print(f"AI Players:")
    print(f"  Player 2: Aggressive")
    print(f"  Player 3: Defensive") 
    print(f"  Player 4: Random")
    print()
    
    return game_state, ai_manager

def show_game_state(game_state):
    """Display current game state."""
    print(f"\n📊 GAME STATUS - Round {game_state.round}")
    print("-" * 40)
    print(f"Phase: {game_state.phase.title()}")
    print(f"System Uptime: {game_state.calculate_uptime()*100:.1f}%")
    print(f"Entropy: {game_state.entropy}/10")
    print(f"Requests: {game_state.successful_requests}/{game_state.total_requests}")
    
    # Show recent dice rolls
    if game_state.dice_history:
        print(f"\n🎲 Recent Rolls:")
        for roll in game_state.dice_history[-3:]:
            print(f"  {roll['count']}{roll['dice_type']}: {roll['total']}")
    
    print(f"\n👤 YOUR STATUS (Player 1):")
    player = game_state.players[0]
    print(f"Resources: CPU {player.cpu}, Memory {player.memory}, Storage {player.storage}")
    print(f"Score: {player.score}")
    print(f"Actions remaining: {player.actions_remaining}/3")
    print(f"Services owned: {len(player.services_owned)}")
    
    if player.services_owned:
        print("Your services:")
        for service_id in player.services_owned:
            service = game_state.services[service_id]
            print(f"  - {service.service_type.value} at ({service.position[0]},{service.position[1]}): {service.state.value}")

def show_legal_actions(game_state, player_id=0):
    """Show available actions for player."""
    actions = game_state.get_legal_actions(player_id)
    
    if not actions:
        print("❌ No legal actions available")
        return []
    
    print(f"\n🎯 AVAILABLE ACTIONS ({len(actions)} total):")
    
    # Group actions by type
    deploy_actions = [a for a in actions if a["type"] == "deploy"]
    repair_actions = [a for a in actions if a["type"] == "repair"]
    scale_actions = [a for a in actions if a["type"] == "scale"]
    
    action_list = []
    index = 1
    
    if deploy_actions:
        print(f"\n🏗️  Deploy Services:")
        # Show one of each service type
        shown_types = set()
        for action in deploy_actions:
            service_type = action["service_type"]
            if service_type not in shown_types:
                pos = action["position"]
                cost_info = get_service_cost(service_type)
                print(f"  {index}. Deploy {service_type} at ({pos[0]},{pos[1]}) {cost_info}")
                action_list.append(action)
                shown_types.add(service_type)
                index += 1
        
        if len(deploy_actions) > len(shown_types):
            print(f"     ... and {len(deploy_actions) - len(shown_types)} more deployment options")
    
    if repair_actions:
        print(f"\n🔧 Repair Services:")
        for action in repair_actions:
            service = game_state.services[action["service_id"]]
            print(f"  {index}. Repair {service.service_type.value} (state: {service.state.value})")
            action_list.append(action)
            index += 1
    
    if scale_actions:
        print(f"\n📈 Scale Services:")
        for action in scale_actions:
            service = game_state.services[action["service_id"]]
            print(f"  {index}. Scale {service.service_type.value} (load: {service.load}/{service.capacity})")
            action_list.append(action)
            index += 1
    
    return action_list

def get_service_cost(service_type):
    """Get service cost information."""
    costs = {
        "compute": "(2 CPU, 2 Memory, 1 Storage)",
        "database": "(1 CPU, 2 Memory, 3 Storage)", 
        "cache": "(1 CPU, 3 Memory, 1 Storage)",
        "queue": "(1 CPU, 1 Memory, 2 Storage)",
        "load_balancer": "(2 CPU, 1 Memory, 1 Storage)",
        "api_gateway": "(1 CPU, 1 Memory, 1 Storage)"
    }
    return costs.get(service_type, "")

def show_board(game_state):
    """Show a simple text representation of the board."""
    print(f"\n🗺️  BOARD STATE (8x6 grid):")
    print("   ", end="")
    for col in range(6):
        print(f"  {col}  ", end="")
    print()
    
    for row in range(8):
        print(f"{row}: ", end="")
        for col in range(6):
            if (row, col) in game_state.board_grid:
                service_id = game_state.board_grid[(row, col)]
                service = game_state.services[service_id]
                owner = service.owner
                service_abbrev = service.service_type.value[:2].upper()
                print(f"P{owner}:{service_abbrev}", end=" ")
            else:
                print(".....", end=" ")
        print()

def advance_ai_turns(game_state, ai_manager):
    """Let AI players take their turns."""
    print(f"\n🤖 AI players taking actions...")
    
    actions_taken = 0
    for player_id in range(1, len(game_state.players)):  # Skip player 0 (human)
        player = game_state.players[player_id]
        player_actions = 0
        
        while player.actions_remaining > 0:
            # Adjust AI manager index (subtract 1 since human is player 0)
            ai_index = player_id - 1
            if ai_index < len(ai_manager.ai_players):
                action = ai_manager.ai_players[ai_index].choose_action(game_state)
                if action:
                    success = game_state.execute_action(player_id, action)
                    if success:
                        actions_taken += 1
                        player_actions += 1
                        action_desc = action["type"]
                        if action["type"] == "deploy":
                            action_desc += f" {action['service_type']}"
                        print(f"  Player {player_id + 1}: {action_desc}")
                    else:
                        player.actions_remaining = 0
                else:
                    player.actions_remaining = 0
            else:
                player.actions_remaining = 0
    
    print(f"AI took {actions_taken} total actions")

def main():
    """Main interactive game loop."""
    game_state, ai_manager = create_interactive_game()
    
    try:
        # Game loop
        while not game_state.is_game_over():
            
            # Traffic phase
            if game_state.phase == "traffic":
                requests = game_state.generate_traffic()
                game_state.process_requests(requests)
                game_state.phase = "action"
                
                # Show dice rolls
                if game_state.last_dice_roll:
                    roll = game_state.last_dice_roll
                    print(f"\n🎲 DICE ROLL: {roll['count']}{roll['dice_type']} = {roll['rolls']} = {roll['total']}")
                
                print(f"🚦 TRAFFIC PHASE: {requests} requests generated")
                
                show_game_state(game_state)
                show_board(game_state)
                
                continue
            
            # Action phase - Your turn first
            elif game_state.phase == "action":
                
                # Your actions
                player = game_state.players[0]
                while player.actions_remaining > 0:
                    show_game_state(game_state)
                    action_list = show_legal_actions(game_state, 0)
                    
                    if not action_list:
                        break
                    
                    try:
                        choice = input(f"\nChoose action (1-{len(action_list)}, 'skip' to skip remaining, 'board' to see board): ").strip().lower()
                        
                        if choice == 'skip':
                            player.actions_remaining = 0
                            break
                        elif choice == 'board':
                            show_board(game_state)
                            continue
                        elif choice.isdigit():
                            choice_num = int(choice)
                            if 1 <= choice_num <= len(action_list):
                                action = action_list[choice_num - 1]
                                success = game_state.execute_action(0, action)
                                if success:
                                    action_desc = action["type"]
                                    if action["type"] == "deploy":
                                        action_desc += f" {action['service_type']} at {action['position']}"
                                    print(f"✅ {action_desc}")
                                else:
                                    print("❌ Action failed")
                            else:
                                print("Invalid choice")
                        else:
                            print("Invalid input. Enter a number, 'skip', or 'board'")
                    except (ValueError, KeyboardInterrupt):
                        print("\nGame interrupted")
                        return
                
                # AI players take actions
                advance_ai_turns(game_state, ai_manager)
                
                game_state.phase = "resolution"
            
            # Resolution phase
            elif game_state.phase == "resolution":
                game_state.phase = "chaos"
            
            # Chaos phase
            elif game_state.phase == "chaos":
                print(f"\n🌪️  CHAOS PHASE")
                game_state.chaos_event()
                
                # Show chaos dice roll if it happened
                if game_state.entropy >= 3 and game_state.last_dice_roll and game_state.last_dice_roll['dice_type'] == 'd8':
                    roll = game_state.last_dice_roll
                    print(f"🎲 CHAOS ROLL: {roll['dice_type']} = {roll['rolls'][0]}")
                
                game_state.advance_round()
                game_state.phase = "traffic"
                
                uptime = game_state.calculate_uptime()
                print(f"End of round {game_state.round}: {uptime*100:.1f}% uptime")
                
                if game_state.round % 3 == 0:  # Show board every 3 rounds
                    show_board(game_state)
        
        # Game over
        winner_id = game_state.get_winner()
        final_uptime = game_state.calculate_uptime()
        
        print(f"\n{'='*50}")
        print("🏁 GAME OVER")
        print(f"{'='*50}")
        print(f"Winner: Player {winner_id + 1}")
        print(f"Final uptime: {final_uptime*100:.1f}%")
        print(f"Your score: {game_state.players[0].score}")
        
        print(f"\nFinal scores:")
        for i, player in enumerate(game_state.players):
            print(f"  Player {i+1}: {player.score} points")
        
    except KeyboardInterrupt:
        print(f"\n\nGame interrupted. Thanks for playing!")

if __name__ == "__main__":
    main()