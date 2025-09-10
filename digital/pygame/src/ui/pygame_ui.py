#!/usr/bin/env python3
"""
Pipeline & Peril - PyGame UI Implementation
Visual interface for the distributed systems board game.
"""

import pygame
import math
import json
from typing import Dict, List, Tuple, Optional
from enum import Enum

from engine.game_state import GameState, Service, ServiceType, ServiceState, Player


class Colors:
    """Color constants for the UI."""
    # Background
    DARK_BLUE = (20, 25, 40)
    DARKER_BLUE = (15, 20, 30)
    
    # Service states
    HEALTHY = (76, 175, 80)      # Green
    DEGRADED = (255, 235, 59)    # Yellow
    OVERLOADED = (255, 152, 0)   # Orange
    FAILED = (244, 67, 54)       # Red
    CASCADING = (156, 39, 176)   # Purple
    
    # Service types
    COMPUTE = (76, 175, 80)      # Green
    DATABASE = (33, 150, 243)    # Blue
    CACHE = (156, 39, 176)       # Purple
    QUEUE = (255, 152, 0)        # Orange
    LOAD_BALANCER = (244, 67, 54) # Red
    API_GATEWAY = (0, 188, 212)  # Cyan
    
    # Players
    PLAYER_COLORS = [
        (244, 67, 54),   # Red
        (33, 150, 243),  # Blue
        (76, 175, 80),   # Green
        (255, 193, 7),   # Yellow
    ]
    
    # UI elements
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (200, 200, 200)
    
    # Network connections
    CONNECTION_ACTIVE = (0, 255, 255)    # Cyan
    CONNECTION_INACTIVE = (64, 64, 64)   # Dark gray


class HexGrid:
    """Hexagonal grid management for the game board."""
    
    def __init__(self, rows: int, cols: int, hex_size: int, offset_x: int, offset_y: int):
        self.rows = rows
        self.cols = cols
        self.hex_size = hex_size
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        # Calculate hex dimensions
        self.hex_width = hex_size * 2
        self.hex_height = int(hex_size * math.sqrt(3))
        
    def hex_to_pixel(self, row: int, col: int) -> Tuple[int, int]:
        """Convert hex coordinates to pixel coordinates."""
        x = self.offset_x + col * self.hex_width * 0.75
        y = self.offset_y + row * self.hex_height
        
        # Offset odd rows
        if row % 2 == 1:
            x += self.hex_width * 0.375
        
        return int(x), int(y)
    
    def pixel_to_hex(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Convert pixel coordinates to hex coordinates."""
        # Approximate conversion - good enough for click detection
        relative_x = x - self.offset_x
        relative_y = y - self.offset_y
        
        # Rough calculation
        row = int(relative_y / self.hex_height)
        col = int(relative_x / (self.hex_width * 0.75))
        
        # Adjust for odd row offset
        if row % 2 == 1:
            col = int((relative_x - self.hex_width * 0.375) / (self.hex_width * 0.75))
        
        # Validate bounds
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return row, col
        
        return None
    
    def draw_hex(self, surface: pygame.Surface, row: int, col: int, color: Tuple[int, int, int], 
                 border_color: Tuple[int, int, int] = None, border_width: int = 2):
        """Draw a hexagon at the specified grid position."""
        x, y = self.hex_to_pixel(row, col)
        
        # Calculate hex points
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = x + self.hex_size * math.cos(angle)
            py = y + self.hex_size * math.sin(angle)
            points.append((px, py))
        
        # Draw filled hexagon
        pygame.draw.polygon(surface, color, points)
        
        # Draw border
        if border_color:
            pygame.draw.polygon(surface, border_color, points, border_width)


class GameUI:
    """Main UI class for the PyGame implementation."""
    
    def __init__(self, width: int = 1200, height: int = 800):
        pygame.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pipeline & Peril - Distributed Systems Game")
        
        # Initialize fonts
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        # Game board setup
        self.hex_grid = HexGrid(
            rows=8, 
            cols=6, 
            hex_size=30,
            offset_x=50,
            offset_y=50
        )
        
        # UI state
        self.game_state = None
        self.selected_service = None
        self.show_debug = False
        self.animation_time = 0.0
        
        # Performance tracking
        self.clock = pygame.time.Clock()
        self.fps = 60
        
    def update(self, game_state: GameState, dt: float):
        """Update the UI with new game state."""
        self.game_state = game_state
        self.animation_time += dt
        
    def handle_event(self, event: pygame.event.Event) -> Optional[Dict]:
        """Handle pygame events and return game actions if any."""
        action = None
        
        if event.type == pygame.QUIT:
            return {"type": "quit"}
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                action = {"type": "next_phase"}
            elif event.key == pygame.K_d:
                self.show_debug = not self.show_debug
            elif event.key == pygame.K_s:
                action = {"type": "save_screenshot"}
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                hex_pos = self.hex_grid.pixel_to_hex(event.pos[0], event.pos[1])
                if hex_pos:
                    action = {"type": "hex_clicked", "position": hex_pos}
        
        return action
    
    def render(self):
        """Render the complete UI."""
        # Clear screen
        self.screen.fill(Colors.DARK_BLUE)
        
        if self.game_state:
            self._draw_game_board()
            self._draw_services()
            self._draw_connections()
            self._draw_ui_panels()
            self._draw_debug_info()
        else:
            self._draw_no_game_message()
        
        pygame.display.flip()
        return self.clock.tick(self.fps)
    
    def _draw_game_board(self):
        """Draw the hexagonal game board."""
        for row in range(self.hex_grid.rows):
            for col in range(self.hex_grid.cols):
                # Determine hex color
                if (row, col) in self.game_state.board_grid:
                    hex_color = Colors.LIGHT_GRAY
                else:
                    hex_color = Colors.DARKER_BLUE
                
                # Draw hex
                self.hex_grid.draw_hex(
                    self.screen, row, col, hex_color, Colors.GRAY, 1
                )
                
                # Draw coordinates (if debug mode)
                if self.show_debug:
                    x, y = self.hex_grid.hex_to_pixel(row, col)
                    coord_text = self.font_small.render(f"{row},{col}", True, Colors.WHITE)
                    text_rect = coord_text.get_rect(center=(x, y))
                    self.screen.blit(coord_text, text_rect)
    
    def _draw_services(self):
        """Draw all services on the board."""
        for service in self.game_state.services.values():
            self._draw_service(service)
    
    def _draw_service(self, service: Service):
        """Draw an individual service."""
        row, col = service.position
        x, y = self.hex_grid.hex_to_pixel(row, col)
        
        # Get service colors
        state_color = self._get_service_state_color(service.state)
        type_color = self._get_service_type_color(service.service_type)
        
        # Draw service hex with state color
        self.hex_grid.draw_hex(
            self.screen, row, col, state_color, Colors.BLACK, 3
        )
        
        # Draw service type icon (simplified as colored circle)
        pygame.draw.circle(self.screen, type_color, (x, y), 15)
        pygame.draw.circle(self.screen, Colors.BLACK, (x, y), 15, 2)
        
        # Draw service type abbreviation
        type_abbrev = self._get_service_type_abbrev(service.service_type)
        text = self.font_small.render(type_abbrev, True, Colors.WHITE)
        text_rect = text.get_rect(center=(x, y))
        self.screen.blit(text, text_rect)
        
        # Draw load indicator
        if service.load > 0:
            load_ratio = min(1.0, service.load / service.capacity)
            bar_width = 20
            bar_height = 4
            bar_x = x - bar_width // 2
            bar_y = y + 20
            
            # Background bar
            pygame.draw.rect(self.screen, Colors.GRAY, 
                           (bar_x, bar_y, bar_width, bar_height))
            
            # Load bar
            load_width = int(bar_width * load_ratio)
            load_color = Colors.HEALTHY if load_ratio < 0.8 else Colors.DEGRADED if load_ratio < 1.0 else Colors.FAILED
            pygame.draw.rect(self.screen, load_color,
                           (bar_x, bar_y, load_width, bar_height))
        
        # Draw bugs indicator
        if service.bugs > 0:
            bug_text = self.font_small.render(f"B{service.bugs}", True, Colors.FAILED)
            self.screen.blit(bug_text, (x - 10, y - 35))
        
        # Draw owner indicator
        if service.owner is not None:
            owner_color = Colors.PLAYER_COLORS[service.owner % len(Colors.PLAYER_COLORS)]
            pygame.draw.circle(self.screen, owner_color, (x + 20, y - 20), 5)
    
    def _draw_connections(self):
        """Draw connections between services."""
        for service in self.game_state.services.values():
            x1, y1 = self.hex_grid.hex_to_pixel(*service.position)
            
            for connected_id in service.connections:
                if connected_id in self.game_state.services:
                    connected_service = self.game_state.services[connected_id]
                    x2, y2 = self.hex_grid.hex_to_pixel(*connected_service.position)
                    
                    # Determine connection color based on service states
                    if (service.state == ServiceState.FAILED or 
                        connected_service.state == ServiceState.FAILED):
                        color = Colors.CONNECTION_INACTIVE
                        width = 1
                    else:
                        color = Colors.CONNECTION_ACTIVE
                        width = 2
                    
                    # Draw connection line
                    pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), width)
    
    def _draw_ui_panels(self):
        """Draw UI panels for game info and player stats."""
        # Game info panel (top right)
        self._draw_game_info_panel()
        
        # Player stats panel (bottom)
        self._draw_player_stats_panel()
        
        # Actions panel (right side)
        self._draw_actions_panel()
    
    def _draw_game_info_panel(self):
        """Draw game information panel."""
        panel_x = self.width - 250
        panel_y = 10
        panel_width = 240
        panel_height = 150
        
        # Background
        pygame.draw.rect(self.screen, Colors.DARKER_BLUE, 
                        (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, Colors.WHITE, 
                        (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Title
        title = self.font_medium.render("Game Status", True, Colors.WHITE)
        self.screen.blit(title, (panel_x + 10, panel_y + 10))
        
        # Game info
        y_offset = panel_y + 40
        info_lines = [
            f"Round: {self.game_state.round}",
            f"Phase: {self.game_state.phase.title()}",
            f"Entropy: {self.game_state.entropy}/10",
            f"Uptime: {self.game_state.calculate_uptime()*100:.1f}%",
            f"Requests: {self.game_state.total_requests}",
            f"Successful: {self.game_state.successful_requests}"
        ]
        
        for i, line in enumerate(info_lines):
            text = self.font_small.render(line, True, Colors.WHITE)
            self.screen.blit(text, (panel_x + 10, y_offset + i * 18))
    
    def _draw_player_stats_panel(self):
        """Draw player statistics panel."""
        panel_height = 120
        panel_y = self.height - panel_height - 10
        panel_width = self.width - 20
        
        # Background
        pygame.draw.rect(self.screen, Colors.DARKER_BLUE,
                        (10, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, Colors.WHITE,
                        (10, panel_y, panel_width, panel_height), 2)
        
        # Title
        title = self.font_medium.render("Player Statistics", True, Colors.WHITE)
        self.screen.blit(title, (20, panel_y + 10))
        
        # Player info
        player_width = panel_width // 4
        for i, player in enumerate(self.game_state.players):
            x_offset = 20 + i * player_width
            y_offset = panel_y + 40
            
            # Player color indicator
            color = Colors.PLAYER_COLORS[i % len(Colors.PLAYER_COLORS)]
            pygame.draw.circle(self.screen, color, (x_offset + 10, y_offset + 10), 8)
            
            # Player stats
            stats_lines = [
                f"Player {i + 1} ({player.strategy.value})",
                f"CPU: {player.cpu}  Memory: {player.memory}",
                f"Storage: {player.storage}  Score: {player.score}",
                f"Actions: {player.actions_remaining}/3",
                f"Services: {len(player.services_owned)}"
            ]
            
            for j, line in enumerate(stats_lines):
                text = self.font_small.render(line, True, Colors.WHITE)
                self.screen.blit(text, (x_offset + 25, y_offset + j * 15))
    
    def _draw_actions_panel(self):
        """Draw available actions panel."""
        panel_x = self.width - 250
        panel_y = 170
        panel_width = 240
        panel_height = 300
        
        # Background
        pygame.draw.rect(self.screen, Colors.DARKER_BLUE,
                        (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, Colors.WHITE,
                        (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Title
        title = self.font_medium.render("Controls", True, Colors.WHITE)
        self.screen.blit(title, (panel_x + 10, panel_y + 10))
        
        # Control instructions
        y_offset = panel_y + 40
        controls = [
            "SPACE - Next Phase",
            "D - Toggle Debug",
            "S - Screenshot",
            "Click - Select Hex",
            "",
            "Service Types:",
            "C - Compute (Green)",
            "D - Database (Blue)", 
            "A - Cache (Purple)",
            "Q - Queue (Orange)",
            "L - Load Balancer (Red)",
            "G - API Gateway (Cyan)"
        ]
        
        for i, control in enumerate(controls):
            if control:  # Skip empty lines
                text = self.font_small.render(control, True, Colors.WHITE)
                self.screen.blit(text, (panel_x + 10, y_offset + i * 18))
    
    def _draw_debug_info(self):
        """Draw debug information if enabled."""
        if not self.show_debug:
            return
        
        # Debug overlay
        debug_surface = pygame.Surface((self.width, self.height))
        debug_surface.set_alpha(128)
        debug_surface.fill(Colors.BLACK)
        self.screen.blit(debug_surface, (0, 0))
        
        # Debug text
        debug_info = [
            f"FPS: {self.clock.get_fps():.1f}",
            f"Animation Time: {self.animation_time:.1f}s",
            f"Services: {len(self.game_state.services)}",
            f"Connections: {sum(len(s.connections) for s in self.game_state.services.values())}",
            f"Selected: {self.selected_service}",
            "",
            "Service Details:"
        ]
        
        # Add service details
        for service in list(self.game_state.services.values())[:5]:  # Limit to 5 services
            debug_info.append(
                f"  {service.id}: {service.service_type.value} at {service.position}"
            )
            debug_info.append(
                f"    State: {service.state.value}, Load: {service.load}/{service.capacity}"
            )
        
        # Render debug text
        y_offset = 50
        for line in debug_info:
            if line:  # Skip empty lines
                text = self.font_small.render(line, True, Colors.WHITE)
                self.screen.blit(text, (50, y_offset))
            y_offset += 18
    
    def _draw_no_game_message(self):
        """Draw message when no game is loaded."""
        message = "No game loaded. Initialize a game to start playing."
        text = self.font_large.render(message, True, Colors.WHITE)
        text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text, text_rect)
    
    def _get_service_state_color(self, state: ServiceState) -> Tuple[int, int, int]:
        """Get color for service state."""
        color_map = {
            ServiceState.HEALTHY: Colors.HEALTHY,
            ServiceState.DEGRADED: Colors.DEGRADED,
            ServiceState.OVERLOADED: Colors.OVERLOADED,
            ServiceState.FAILED: Colors.FAILED,
            ServiceState.CASCADING: Colors.CASCADING
        }
        return color_map.get(state, Colors.GRAY)
    
    def _get_service_type_color(self, service_type: ServiceType) -> Tuple[int, int, int]:
        """Get color for service type."""
        color_map = {
            ServiceType.COMPUTE: Colors.COMPUTE,
            ServiceType.DATABASE: Colors.DATABASE,
            ServiceType.CACHE: Colors.CACHE,
            ServiceType.QUEUE: Colors.QUEUE,
            ServiceType.LOAD_BALANCER: Colors.LOAD_BALANCER,
            ServiceType.API_GATEWAY: Colors.API_GATEWAY
        }
        return color_map.get(service_type, Colors.WHITE)
    
    def _get_service_type_abbrev(self, service_type: ServiceType) -> str:
        """Get abbreviation for service type."""
        abbrev_map = {
            ServiceType.COMPUTE: "CP",
            ServiceType.DATABASE: "DB",
            ServiceType.CACHE: "CA",
            ServiceType.QUEUE: "QU",
            ServiceType.LOAD_BALANCER: "LB",
            ServiceType.API_GATEWAY: "AG"
        }
        return abbrev_map.get(service_type, "??")
    
    def save_screenshot(self, filename: str = None):
        """Save current screen as screenshot."""
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pipeline_peril_screenshot_{timestamp}.png"
        
        pygame.image.save(self.screen, filename)
        return filename
    
    def cleanup(self):
        """Clean up pygame resources."""
        pygame.quit()