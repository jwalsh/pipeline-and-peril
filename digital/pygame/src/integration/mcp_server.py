#!/usr/bin/env python3
"""
Pipeline & Peril - MCP Server Interface
Provides an MCP server for interactive gameplay through Claude.
"""

import json
import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import asdict

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engine.game_state import GameState, GameConfig, ServiceType, ServiceState, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI

try:
    import mcp
    from mcp.server import Server
    from mcp.types import Tool, TextContent, ImageContent
except ImportError:
    print("MCP not available - install with: pip install mcp")
    sys.exit(1)


class PipelinePerilMCPServer:
    """MCP Server for Pipeline & Peril game interaction."""
    
    def __init__(self):
        self.server = Server("pipeline-peril")
        self.games: Dict[str, GameState] = {}
        self.ai_managers: Dict[str, AIPlayerManager] = {}
        self.ui_instances: Dict[str, GameUI] = {}
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available MCP tools."""
        
        @self.server.call_tool()
        async def create_game(arguments: Dict[str, Any]) -> List[TextContent]:
            """Create a new game instance."""
            game_id = arguments.get("game_id", "default")
            players = arguments.get("players", 4)
            rounds = arguments.get("rounds", 10)
            cooperative = arguments.get("cooperative", False)
            
            # Create game configuration
            config = GameConfig(
                max_rounds=rounds,
                cooperative_mode=cooperative
            )
            
            # Initialize game
            game_state = GameState(config, players)
            
            # Set up AI for other players if human player specified
            human_player = arguments.get("human_player", None)
            strategies = [PlayerStrategy.AGGRESSIVE, PlayerStrategy.DEFENSIVE, 
                         PlayerStrategy.BALANCED, PlayerStrategy.RANDOM]
            
            if human_player is not None:
                # Remove human player from AI management
                ai_strategies = [s for i, s in enumerate(strategies) if i != human_player]
                ai_manager = AIPlayerManager(ai_strategies)
            else:
                ai_manager = AIPlayerManager(strategies)
            
            # Store instances
            self.games[game_id] = game_state
            self.ai_managers[game_id] = ai_manager
            
            return [TextContent(
                type="text",
                text=f"Game '{game_id}' created with {players} players, {rounds} rounds. "
                     f"Mode: {'Cooperative' if cooperative else 'Competitive'}. "
                     f"Human player: {human_player if human_player is not None else 'None (all AI)'}"
            )]
        
        @self.server.call_tool()
        async def get_game_state(arguments: Dict[str, Any]) -> List[TextContent]:
            """Get current game state as JSON."""
            game_id = arguments.get("game_id", "default")
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            game_state = self.games[game_id]
            state_dict = game_state.to_dict()
            
            return [TextContent(
                type="text",
                text=json.dumps(state_dict, indent=2)
            )]
        
        @self.server.call_tool()
        async def get_game_summary(arguments: Dict[str, Any]) -> List[TextContent]:
            """Get human-readable game summary."""
            game_id = arguments.get("game_id", "default")
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            game_state = self.games[game_id]
            
            summary = f"""
## Pipeline & Peril - Game Status

**Round:** {game_state.round}/{game_state.config.max_rounds}
**Phase:** {game_state.phase.title()}
**Entropy:** {game_state.entropy}/10
**System Uptime:** {game_state.calculate_uptime()*100:.1f}%
**Total Requests:** {game_state.total_requests}
**Successful:** {game_state.successful_requests}

### Players
"""
            
            for player in game_state.players:
                summary += f"""
**Player {player.id + 1}** ({player.strategy.value}):
- Resources: CPU {player.cpu}, Memory {player.memory}, Storage {player.storage}
- Score: {player.score}
- Actions Remaining: {player.actions_remaining}/3
- Services Owned: {len(player.services_owned)}
"""
            
            summary += f"\n### Services on Board: {len(game_state.services)}\n"
            
            # Service breakdown by type
            service_counts = {}
            for service in game_state.services.values():
                service_type = service.service_type.value
                service_counts[service_type] = service_counts.get(service_type, 0) + 1
            
            for service_type, count in service_counts.items():
                summary += f"- {service_type.title()}: {count}\n"
            
            return [TextContent(type="text", text=summary)]
        
        @self.server.call_tool()
        async def get_legal_actions(arguments: Dict[str, Any]) -> List[TextContent]:
            """Get legal actions for a player."""
            game_id = arguments.get("game_id", "default")
            player_id = arguments.get("player_id", 0)
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            game_state = self.games[game_id]
            actions = game_state.get_legal_actions(player_id)
            
            if not actions:
                return [TextContent(type="text", text="No legal actions available")]
            
            action_text = f"**Legal actions for Player {player_id + 1}:**\n\n"
            
            for i, action in enumerate(actions[:10]):  # Limit to first 10
                if action["type"] == "deploy":
                    service_type = action["service_type"]
                    pos = action["position"]
                    action_text += f"{i+1}. Deploy {service_type} at ({pos[0]}, {pos[1]})\n"
                elif action["type"] == "repair":
                    service_id = action["service_id"]
                    service = game_state.services[service_id]
                    action_text += f"{i+1}. Repair {service.service_type.value} (ID: {service_id})\n"
                elif action["type"] == "scale":
                    service_id = action["service_id"]
                    service = game_state.services[service_id]
                    action_text += f"{i+1}. Scale {service.service_type.value} (ID: {service_id})\n"
            
            if len(actions) > 10:
                action_text += f"\n... and {len(actions) - 10} more actions"
            
            return [TextContent(type="text", text=action_text)]
        
        @self.server.call_tool()
        async def execute_action(arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a player action."""
            game_id = arguments.get("game_id", "default")
            player_id = arguments.get("player_id", 0)
            action = arguments.get("action")
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            if not action:
                return [TextContent(type="text", text="No action provided")]
            
            game_state = self.games[game_id]
            
            # Validate action format
            if isinstance(action, str):
                try:
                    action = json.loads(action)
                except json.JSONDecodeError:
                    return [TextContent(type="text", text="Invalid action format - must be valid JSON")]
            
            # Execute action
            success = game_state.execute_action(player_id, action)
            
            if success:
                result = f"✅ Action executed successfully: {action['type']}"
                if action["type"] == "deploy":
                    result += f" {action['service_type']} at {action['position']}"
                elif action["type"] in ["repair", "scale"]:
                    service = game_state.services[action["service_id"]]
                    result += f" {service.service_type.value}"
            else:
                result = f"❌ Action failed: {action['type']}"
            
            return [TextContent(type="text", text=result)]
        
        @self.server.call_tool()
        async def advance_phase(arguments: Dict[str, Any]) -> List[TextContent]:
            """Advance the game to the next phase."""
            game_id = arguments.get("game_id", "default")
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            game_state = self.games[game_id]
            ai_manager = self.ai_managers[game_id]
            
            if game_state.phase == "traffic":
                # Generate and process traffic
                requests = game_state.generate_traffic()
                game_state.process_requests(requests)
                game_state.phase = "action"
                
                result = f"🚦 Traffic phase: {requests} requests generated"
            
            elif game_state.phase == "action":
                # AI players take their actions
                actions_taken = 0
                for pid in range(len(game_state.players)):
                    player = game_state.players[pid]
                    while player.actions_remaining > 0:
                        action = ai_manager.get_action(pid, game_state)
                        if action:
                            success = game_state.execute_action(pid, action)
                            if success:
                                actions_taken += 1
                            else:
                                player.actions_remaining = 0
                        else:
                            player.actions_remaining = 0
                
                game_state.phase = "resolution"
                result = f"🎯 Action phase: {actions_taken} AI actions executed"
            
            elif game_state.phase == "resolution":
                # Auto-resolve service states
                game_state.phase = "chaos"
                result = "⚙️ Resolution phase: Service states updated"
            
            elif game_state.phase == "chaos":
                # Execute chaos event
                game_state.chaos_event()
                game_state.advance_round()
                game_state.phase = "traffic"
                
                uptime = game_state.calculate_uptime()
                result = f"🌪️ Chaos phase: Round {game_state.round} completed. Uptime: {uptime*100:.1f}%"
            
            else:
                result = f"Unknown phase: {game_state.phase}"
            
            return [TextContent(type="text", text=result)]
        
        @self.server.call_tool()
        async def ai_suggestion(arguments: Dict[str, Any]) -> List[TextContent]:
            """Get AI suggestion for player action."""
            game_id = arguments.get("game_id", "default")
            player_id = arguments.get("player_id", 0)
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            game_state = self.games[game_id]
            ai_manager = self.ai_managers[game_id]
            
            # Get AI suggestion
            suggested_action = ai_manager.get_action(player_id, game_state)
            
            if not suggested_action:
                return [TextContent(type="text", text="No AI suggestions available")]
            
            suggestion_text = f"🤖 **AI Suggestion for Player {player_id + 1}:**\n\n"
            
            if suggested_action["type"] == "deploy":
                service_type = suggested_action["service_type"]
                pos = suggested_action["position"]
                suggestion_text += f"Deploy **{service_type}** at position ({pos[0]}, {pos[1]})\n\n"
                suggestion_text += f"*Reasoning: This expands your network and improves capacity.*"
            
            elif suggested_action["type"] == "repair":
                service_id = suggested_action["service_id"]
                service = game_state.services[service_id]
                suggestion_text += f"Repair **{service.service_type.value}** (ID: {service_id})\n\n"
                suggestion_text += f"*Reasoning: This service is {service.state.value} and needs attention.*"
            
            elif suggested_action["type"] == "scale":
                service_id = suggested_action["service_id"]
                service = game_state.services[service_id]
                suggestion_text += f"Scale **{service.service_type.value}** (ID: {service_id})\n\n"
                suggestion_text += f"*Reasoning: This service has high load ({service.load}/{service.capacity}).*"
            
            suggestion_text += f"\n\nTo execute: `execute_action` with action: ```json\n{json.dumps(suggested_action, indent=2)}\n```"
            
            return [TextContent(type="text", text=suggestion_text)]
        
        @self.server.call_tool()
        async def generate_screenshot(arguments: Dict[str, Any]) -> List[Any]:
            """Generate a visual screenshot of the game board."""
            game_id = arguments.get("game_id", "default")
            
            if game_id not in self.games:
                return [TextContent(type="text", text=f"Game '{game_id}' not found")]
            
            try:
                # Initialize pygame if needed
                import pygame
                if not pygame.get_init():
                    pygame.init()
                
                # Create or get UI instance
                if game_id not in self.ui_instances:
                    self.ui_instances[game_id] = GameUI(1200, 800)
                
                ui = self.ui_instances[game_id]
                game_state = self.games[game_id]
                
                # Update and render
                ui.update(game_state, 0.0)
                ui.render()
                
                # Save screenshot
                filename = f"pipeline_peril_{game_id}_round_{game_state.round}.png"
                screenshot_path = ui.save_screenshot(filename)
                
                return [
                    TextContent(type="text", text=f"Screenshot saved: {screenshot_path}"),
                    ImageContent(type="image", data=open(screenshot_path, "rb").read())
                ]
            
            except Exception as e:
                return [TextContent(type="text", text=f"Screenshot failed: {str(e)}")]
        
        @self.server.call_tool()
        async def list_games(arguments: Dict[str, Any]) -> List[TextContent]:
            """List all active game instances."""
            if not self.games:
                return [TextContent(type="text", text="No active games")]
            
            game_list = "**Active Games:**\n\n"
            for game_id, game_state in self.games.items():
                game_list += f"- **{game_id}**: Round {game_state.round}/{game_state.config.max_rounds}, "
                game_list += f"Phase: {game_state.phase}, "
                game_list += f"Uptime: {game_state.calculate_uptime()*100:.1f}%\n"
            
            return [TextContent(type="text", text=game_list)]


async def main():
    """Main server entry point."""
    server_instance = PipelinePerilMCPServer()
    
    # Configure tools
    server_instance.server.list_tools = lambda: [
        Tool(
            name="create_game",
            description="Create a new Pipeline & Peril game instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Unique game identifier"},
                    "players": {"type": "number", "description": "Number of players (2-4)"},
                    "rounds": {"type": "number", "description": "Maximum rounds"},
                    "cooperative": {"type": "boolean", "description": "Cooperative mode"},
                    "human_player": {"type": "number", "description": "Human player ID (0-3, optional)"}
                }
            }
        ),
        Tool(
            name="get_game_state",
            description="Get complete game state as JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"}
                }
            }
        ),
        Tool(
            name="get_game_summary",
            description="Get human-readable game summary",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"}
                }
            }
        ),
        Tool(
            name="get_legal_actions",
            description="Get legal actions for a player",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"},
                    "player_id": {"type": "number", "description": "Player ID (0-3)"}
                }
            }
        ),
        Tool(
            name="execute_action",
            description="Execute a player action",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"},
                    "player_id": {"type": "number", "description": "Player ID (0-3)"},
                    "action": {"type": "object", "description": "Action to execute"}
                }
            }
        ),
        Tool(
            name="advance_phase",
            description="Advance game to next phase (AI will auto-play)",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"}
                }
            }
        ),
        Tool(
            name="ai_suggestion",
            description="Get AI suggestion for player action",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"},
                    "player_id": {"type": "number", "description": "Player ID (0-3)"}
                }
            }
        ),
        Tool(
            name="generate_screenshot",
            description="Generate visual screenshot of game board",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "Game identifier"}
                }
            }
        ),
        Tool(
            name="list_games",
            description="List all active game instances",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
    
    # Run the server
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())