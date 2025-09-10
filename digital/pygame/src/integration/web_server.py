#!/usr/bin/env python3
"""
Pipeline & Peril - Web Server Interface
HTTP API and web interface for the game.
"""

from flask import Flask, jsonify, request, render_template_string, send_file
import json
import threading
import time
import io
import base64
from typing import Dict, Optional
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engine.game_state import GameState, GameConfig, PlayerStrategy
from players.ai_player import AIPlayerManager
from ui.pygame_ui import GameUI
import pygame

app = Flask(__name__)

# Global game instances
games: Dict[str, GameState] = {}
ai_managers: Dict[str, AIPlayerManager] = {}
game_lock = threading.Lock()

# HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pipeline & Peril - Web Interface</title>
    <style>
        body {
            font-family: 'Consolas', 'Monaco', monospace;
            background: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #00ff88;
            text-align: center;
            border-bottom: 2px solid #00ff88;
            padding-bottom: 10px;
        }
        .game-grid {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        .panel {
            background: #0f0f23;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
        }
        .panel h2 {
            color: #00ccff;
            margin-top: 0;
            font-size: 1.2em;
        }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .stat-item {
            background: #1a1a2e;
            padding: 8px;
            border-radius: 4px;
        }
        .stat-label {
            color: #888;
            font-size: 0.9em;
        }
        .stat-value {
            color: #00ff88;
            font-size: 1.2em;
            font-weight: bold;
        }
        .board {
            display: grid;
            grid-template-columns: repeat(6, 80px);
            gap: 2px;
            justify-content: center;
        }
        .hex {
            width: 80px;
            height: 70px;
            background: #2a2a3e;
            border: 1px solid #444;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            position: relative;
        }
        .hex.occupied {
            border-width: 2px;
        }
        .hex.healthy { background: #1a4a1a; border-color: #00ff00; }
        .hex.degraded { background: #4a4a1a; border-color: #ffff00; }
        .hex.overloaded { background: #4a2a1a; border-color: #ff8800; }
        .hex.failed { background: #4a1a1a; border-color: #ff0000; }
        .service-type {
            font-weight: bold;
            color: #fff;
        }
        .owner {
            position: absolute;
            top: 2px;
            right: 4px;
            font-size: 0.7em;
            padding: 2px 4px;
            border-radius: 3px;
        }
        .owner-0 { background: #ff4444; }
        .owner-1 { background: #4444ff; }
        .owner-2 { background: #44ff44; }
        .owner-3 { background: #ffff44; color: #000; }
        button {
            background: #00ff88;
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
            margin: 5px;
            font-family: inherit;
        }
        button:hover {
            background: #00cc66;
        }
        button:disabled {
            background: #444;
            color: #888;
            cursor: not-allowed;
        }
        .action-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        .player-panel {
            border-left: 3px solid #00ff88;
        }
        .player-inactive {
            opacity: 0.5;
            border-left-color: #444;
        }
        .screenshot {
            width: 100%;
            border-radius: 8px;
            margin-top: 10px;
        }
        .message {
            background: #1a4a1a;
            color: #00ff88;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            border-left: 3px solid #00ff88;
        }
        .error {
            background: #4a1a1a;
            color: #ff4444;
            border-left-color: #ff4444;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 Pipeline & Peril - Web Interface</h1>
        
        <div id="message" class="message" style="display: none;"></div>
        
        <div class="panel">
            <h2>Game Controls</h2>
            <div class="action-buttons">
                <button onclick="createGame()">New Game</button>
                <button onclick="getGameState()">Refresh State</button>
                <button onclick="advancePhase()">Advance Phase</button>
                <button onclick="takeAITurn()">AI Actions</button>
                <button onclick="getScreenshot()">Screenshot</button>
            </div>
        </div>
        
        <div class="game-grid">
            <div class="panel">
                <h2>Game Status</h2>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-label">Round</div>
                        <div class="stat-value" id="round">0/10</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Phase</div>
                        <div class="stat-value" id="phase">Setup</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Uptime</div>
                        <div class="stat-value" id="uptime">100%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Entropy</div>
                        <div class="stat-value" id="entropy">0/10</div>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h2>Game Board</h2>
                <div id="board" class="board"></div>
                <img id="screenshot" class="screenshot" style="display: none;" />
            </div>
            
            <div class="panel">
                <h2>Players</h2>
                <div id="players"></div>
            </div>
        </div>
        
        <div class="panel">
            <h2>Your Actions (Player 1)</h2>
            <div id="actions" class="action-buttons"></div>
        </div>
    </div>
    
    <script>
        let currentGameId = 'default';
        let autoRefresh = null;
        
        function showMessage(msg, isError = false) {
            const elem = document.getElementById('message');
            elem.textContent = msg;
            elem.className = isError ? 'message error' : 'message';
            elem.style.display = 'block';
            setTimeout(() => elem.style.display = 'none', 3000);
        }
        
        async function createGame() {
            const response = await fetch('/api/game', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    players: 4,
                    rounds: 10,
                    human_player: 0
                })
            });
            const data = await response.json();
            if (data.success) {
                currentGameId = data.game_id;
                showMessage('New game created! You are Player 1');
                getGameState();
                startAutoRefresh();
            }
        }
        
        async function getGameState() {
            const response = await fetch(`/api/game/${currentGameId}`);
            const data = await response.json();
            
            if (data.error) {
                showMessage(data.error, true);
                return;
            }
            
            // Update stats
            document.getElementById('round').textContent = `${data.round}/${data.max_rounds}`;
            document.getElementById('phase').textContent = data.phase;
            document.getElementById('uptime').textContent = `${(data.uptime * 100).toFixed(1)}%`;
            document.getElementById('entropy').textContent = `${data.entropy}/10`;
            
            // Update board
            updateBoard(data.board);
            
            // Update players
            updatePlayers(data.players);
            
            // Update actions if it's action phase and player 1's turn
            if (data.phase === 'action' && data.players[0].actions_remaining > 0) {
                updateActions();
            } else {
                document.getElementById('actions').innerHTML = '<p>No actions available</p>';
            }
        }
        
        function updateBoard(board) {
            const boardElem = document.getElementById('board');
            boardElem.innerHTML = '';
            
            for (let row = 0; row < 8; row++) {
                for (let col = 0; col < 6; col++) {
                    const hex = document.createElement('div');
                    hex.className = 'hex';
                    
                    const service = board[`${row},${col}`];
                    if (service) {
                        hex.classList.add('occupied', service.state);
                        hex.innerHTML = `
                            <span class="service-type">${service.type.toUpperCase().substring(0, 2)}</span>
                            <span class="owner owner-${service.owner}">P${service.owner + 1}</span>
                        `;
                    } else {
                        hex.textContent = `${row},${col}`;
                        hex.style.color = '#444';
                        hex.style.fontSize = '0.7em';
                    }
                    
                    boardElem.appendChild(hex);
                }
            }
        }
        
        function updatePlayers(players) {
            const playersElem = document.getElementById('players');
            playersElem.innerHTML = '';
            
            players.forEach((player, i) => {
                const playerDiv = document.createElement('div');
                playerDiv.className = `panel player-panel ${player.actions_remaining === 0 ? 'player-inactive' : ''}`;
                playerDiv.innerHTML = `
                    <h3>Player ${i + 1} (${player.strategy})</h3>
                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-label">Score</div>
                            <div class="stat-value">${player.score}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Services</div>
                            <div class="stat-value">${player.services_owned}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">CPU</div>
                            <div class="stat-value">${player.cpu}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Memory</div>
                            <div class="stat-value">${player.memory}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Storage</div>
                            <div class="stat-value">${player.storage}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Actions</div>
                            <div class="stat-value">${player.actions_remaining}/3</div>
                        </div>
                    </div>
                `;
                playersElem.appendChild(playerDiv);
            });
        }
        
        async function updateActions() {
            const response = await fetch(`/api/game/${currentGameId}/actions/0`);
            const data = await response.json();
            
            const actionsElem = document.getElementById('actions');
            actionsElem.innerHTML = '';
            
            if (data.actions && data.actions.length > 0) {
                data.actions.slice(0, 10).forEach((action, i) => {
                    const btn = document.createElement('button');
                    btn.textContent = `${action.type}: ${action.description}`;
                    btn.onclick = () => executeAction(action);
                    actionsElem.appendChild(btn);
                });
            }
        }
        
        async function executeAction(action) {
            const response = await fetch(`/api/game/${currentGameId}/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    player_id: 0,
                    action: action
                })
            });
            const data = await response.json();
            
            if (data.success) {
                showMessage(`Action executed: ${action.type}`);
                getGameState();
            } else {
                showMessage(data.error || 'Action failed', true);
            }
        }
        
        async function advancePhase() {
            const response = await fetch(`/api/game/${currentGameId}/advance`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                showMessage(data.message);
                getGameState();
            }
        }
        
        async function takeAITurn() {
            const response = await fetch(`/api/game/${currentGameId}/ai-turn`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                showMessage(`AI took ${data.actions_taken} actions`);
                getGameState();
            }
        }
        
        async function getScreenshot() {
            const response = await fetch(`/api/game/${currentGameId}/screenshot`);
            const data = await response.json();
            
            if (data.screenshot) {
                const img = document.getElementById('screenshot');
                img.src = 'data:image/png;base64,' + data.screenshot;
                img.style.display = 'block';
            }
        }
        
        function startAutoRefresh() {
            if (autoRefresh) clearInterval(autoRefresh);
            autoRefresh = setInterval(getGameState, 5000);
        }
        
        // Initialize
        createGame();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the web interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/game', methods=['POST'])
def create_game():
    """Create a new game."""
    data = request.json
    game_id = data.get('game_id', 'default')
    players = data.get('players', 4)
    rounds = data.get('rounds', 10)
    human_player = data.get('human_player', None)
    
    with game_lock:
        config = GameConfig(max_rounds=rounds, cooperative_mode=False)
        game_state = GameState(config, players)
        
        # Set strategies
        strategies = [PlayerStrategy.BALANCED, PlayerStrategy.AGGRESSIVE, 
                     PlayerStrategy.DEFENSIVE, PlayerStrategy.RANDOM]
        for i, player in enumerate(game_state.players):
            player.strategy = strategies[i % len(strategies)]
        
        # Create AI manager
        if human_player is not None:
            ai_strategies = [s for i, s in enumerate(strategies) if i != human_player]
        else:
            ai_strategies = strategies
        
        ai_manager = AIPlayerManager(ai_strategies)
        
        games[game_id] = game_state
        ai_managers[game_id] = ai_manager
    
    return jsonify({
        'success': True,
        'game_id': game_id,
        'players': players,
        'human_player': human_player
    })

@app.route('/api/game/<game_id>')
def get_game_state(game_id):
    """Get current game state."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game_state = games[game_id]
    
    # Build board representation
    board = {}
    for (row, col), service_id in game_state.board_grid.items():
        service = game_state.services[service_id]
        board[f"{row},{col}"] = {
            'type': service.service_type.value,
            'state': service.state.value,
            'owner': service.owner,
            'load': service.load,
            'capacity': service.capacity
        }
    
    return jsonify({
        'round': game_state.round,
        'max_rounds': game_state.config.max_rounds,
        'phase': game_state.phase,
        'uptime': game_state.calculate_uptime(),
        'entropy': game_state.entropy,
        'total_requests': game_state.total_requests,
        'successful_requests': game_state.successful_requests,
        'board': board,
        'players': [
            {
                'id': p.id,
                'strategy': p.strategy.value,
                'score': p.score,
                'cpu': p.cpu,
                'memory': p.memory,
                'storage': p.storage,
                'actions_remaining': p.actions_remaining,
                'services_owned': len(p.services_owned)
            }
            for p in game_state.players
        ]
    })

@app.route('/api/game/<game_id>/actions/<int:player_id>')
def get_legal_actions(game_id, player_id):
    """Get legal actions for a player."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game_state = games[game_id]
    actions = game_state.get_legal_actions(player_id)
    
    # Format actions for display
    formatted_actions = []
    for action in actions[:20]:  # Limit to 20 actions
        if action['type'] == 'deploy':
            desc = f"{action['service_type']} at {action['position']}"
        elif action['type'] == 'repair':
            service = game_state.services[action['service_id']]
            desc = f"{service.service_type.value}"
        elif action['type'] == 'scale':
            service = game_state.services[action['service_id']]
            desc = f"{service.service_type.value}"
        else:
            desc = "Unknown"
        
        formatted_actions.append({
            'type': action['type'],
            'description': desc,
            'action': action
        })
    
    return jsonify({'actions': formatted_actions})

@app.route('/api/game/<game_id>/action', methods=['POST'])
def execute_action(game_id):
    """Execute a player action."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    data = request.json
    player_id = data.get('player_id', 0)
    action = data.get('action')
    
    game_state = games[game_id]
    
    with game_lock:
        success = game_state.execute_action(player_id, action)
    
    return jsonify({'success': success})

@app.route('/api/game/<game_id>/advance', methods=['POST'])
def advance_phase(game_id):
    """Advance to next phase."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game_state = games[game_id]
    
    with game_lock:
        if game_state.phase == 'traffic':
            requests = game_state.generate_traffic()
            game_state.process_requests(requests)
            game_state.phase = 'action'
            message = f"Traffic phase: {requests} requests"
        elif game_state.phase == 'action':
            game_state.phase = 'resolution'
            message = "Moved to resolution phase"
        elif game_state.phase == 'resolution':
            game_state.phase = 'chaos'
            message = "Moved to chaos phase"
        elif game_state.phase == 'chaos':
            game_state.chaos_event()
            game_state.advance_round()
            game_state.phase = 'traffic'
            message = f"Round {game_state.round} started"
        else:
            message = "Unknown phase"
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/game/<game_id>/ai-turn', methods=['POST'])
def ai_turn(game_id):
    """Let AI players take their turns."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game_state = games[game_id]
    ai_manager = ai_managers[game_id]
    
    actions_taken = 0
    with game_lock:
        for player_id in range(1, len(game_state.players)):  # Skip player 0
            player = game_state.players[player_id]
            while player.actions_remaining > 0:
                action = ai_manager.get_action(player_id, game_state)
                if action:
                    success = game_state.execute_action(player_id, action)
                    if success:
                        actions_taken += 1
                    else:
                        player.actions_remaining = 0
                else:
                    player.actions_remaining = 0
    
    return jsonify({'success': True, 'actions_taken': actions_taken})

@app.route('/api/game/<game_id>/screenshot')
def get_screenshot(game_id):
    """Generate a screenshot of the game."""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    try:
        game_state = games[game_id]
        
        # Initialize pygame if needed
        if not pygame.get_init():
            pygame.init()
        
        # Create UI and render
        ui = GameUI(800, 600)
        ui.update(game_state, 0.0)
        ui.render()
        
        # Get surface as image
        surface = ui.screen
        buffer = io.BytesIO()
        pygame.image.save(surface, buffer, 'PNG')
        buffer.seek(0)
        
        # Encode as base64
        screenshot_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        ui.cleanup()
        
        return jsonify({'screenshot': screenshot_base64})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🎮 Pipeline & Peril Web Server")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)