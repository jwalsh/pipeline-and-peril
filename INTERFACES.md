# Pipeline & Peril - Complete Interface Documentation

## 🎮 Available Interfaces

The game provides **7 different interfaces** for play, analysis, and debugging:

### 1. PyGame Visual Interface (Port: Native Window)
```bash
# Full visual game with hexagonal board
uv run python scripts/run_autonomous.py --visual --games 1

# Controls:
# SPACE - Next phase
# D - Toggle debug overlay
# S - Save screenshot
# Click - Select hex
```

### 2. Web Interface (Port: 5000)
```bash
# Browser-based game with live updates
uv run python src/integration/web_server.py

# Open: http://localhost:5000
# Features:
# - Real-time board visualization
# - Click-to-play actions
# - Auto-refresh every 5 seconds
# - Screenshot generation
```

### 3. REST API (Port: 5000)
```bash
# HTTP endpoints for programmatic control
curl http://localhost:5000/api/game/default
curl -X POST http://localhost:5000/api/game -d '{"players": 4}'
curl -X POST http://localhost:5000/api/game/default/action -d '{"player_id": 0, "action": {...}}'

# Endpoints:
GET  /api/game/<id>              # Game state
POST /api/game                   # Create game
GET  /api/game/<id>/actions/<p>  # Legal actions
POST /api/game/<id>/action       # Execute action
POST /api/game/<id>/advance      # Next phase
POST /api/game/<id>/ai-turn      # AI actions
GET  /api/game/<id>/screenshot   # Base64 image
```

### 4. MCP Server (Port: stdio)
```bash
# Model Context Protocol for Claude integration
uv run python scripts/start_mcp_server.py

# Tools:
# - create_game
# - get_game_state
# - get_game_summary
# - get_legal_actions
# - execute_action
# - advance_phase
# - ai_suggestion
# - generate_screenshot
# - list_games
```

### 5. Ollama Integration (Port: 11434)
```bash
# LLM players via Ollama
uv run python src/integration/ollama_client.py \
  --models qwen2.5-coder:7b llama3.2:3b \
  --rounds 10

# Models play autonomously
# Decisions logged to console
```

### 6. Interactive CLI
```bash
# Text-based interactive game
uv run python scripts/quick_play.py

# Menu-driven interface
# Human vs 3 AI players
# Real-time board display
```

### 7. Telemetry Server (Port: 8080)
```bash
# Metrics and monitoring
uv run python src/integration/telemetry_server.py

# Prometheus metrics at :8080/metrics
# Game statistics dashboard
# Performance monitoring
```

## 📊 Logging & Debugging

### Enable Debug Logging
```bash
# Set environment variables
export PIPELINE_LOG_LEVEL=DEBUG
export PIPELINE_LOG_FILE=game.log
export PIPELINE_TELEMETRY=true

# Run with debug output
uv run python scripts/run_autonomous.py --games 10 --verbose
```

### Log Output Format
```
2025-09-10 19:00:00 [INFO] Game 1 started
2025-09-10 19:00:00 [DEBUG] Player 0: Deploy load_balancer at (1,1)
2025-09-10 19:00:00 [DEBUG] Service state: healthy, load: 0/10
2025-09-10 19:00:01 [WARN] Service overloaded: load 15/10
2025-09-10 19:00:01 [ERROR] Cascade failure triggered
2025-09-10 19:00:02 [INFO] Round 1 complete: uptime 85.3%
```

### Debug Overlays

#### PyGame Debug Mode (Press 'D')
- FPS counter
- Service IDs and states
- Connection count
- Load percentages
- Animation timing

#### Web Debug Panel
```javascript
// Browser console
window.debugMode = true;
// Shows:
// - Network request timing
// - Action queue
// - State transitions
// - WebSocket messages
```

## 🔍 Telemetry & Metrics

### Prometheus Metrics Export
```python
# metrics exposed at :8080/metrics
pipeline_games_total{status="completed"} 142
pipeline_uptime_average{strategy="defensive"} 0.187
pipeline_services_deployed{type="load_balancer"} 489
pipeline_cascade_failures_total 67
pipeline_chaos_events{severity="catastrophic"} 12
pipeline_game_duration_seconds{percentile="p99"} 0.073
```

### Grafana Dashboard Config
```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=pipeline
```

### OpenTelemetry Integration
```python
# Enable distributed tracing
from opentelemetry import trace
tracer = trace.get_tracer("pipeline-peril")

with tracer.start_as_current_span("game_round"):
    with tracer.start_as_current_span("traffic_phase"):
        requests = game_state.generate_traffic()
    with tracer.start_as_current_span("action_phase"):
        execute_actions()
```

## 📝 Requirements

### Python Dependencies
```toml
# pyproject.toml
[project]
dependencies = [
    "pygame>=2.6.0",      # Visual interface
    "flask>=3.1.0",       # Web server
    "requests>=2.32.0",   # HTTP client
    "numpy>=2.3.0",       # Array operations
    "plotly>=6.3.0",      # Dashboard charts
    "pandas>=2.3.0",      # Data analysis
    "pillow>=11.3.0",     # Image processing
]

[project.optional-dependencies]
telemetry = [
    "prometheus-client>=0.20.0",
    "opentelemetry-api>=1.24.0",
    "opentelemetry-sdk>=1.24.0",
]
```

### System Requirements
- Python 3.10+ (3.13 recommended)
- 100MB RAM per game instance
- 60ms average game completion
- Port availability: 5000, 8080
- Ollama daemon (optional)

## 🚀 Quick Start All Interfaces

```bash
# Terminal 1: Web Interface
uv run python src/integration/web_server.py

# Terminal 2: Telemetry
uv run python src/integration/telemetry_server.py

# Terminal 3: MCP Server
uv run python scripts/start_mcp_server.py

# Terminal 4: Visual Game
uv run python scripts/run_autonomous.py --visual --games 1

# Browser: Open http://localhost:5000
# Metrics: Open http://localhost:8080/metrics
# Grafana: Open http://localhost:3000 (if using Docker)
```

## 🔧 Configuration

### Environment Variables
```bash
PIPELINE_LOG_LEVEL=DEBUG|INFO|WARN|ERROR
PIPELINE_LOG_FILE=path/to/logfile.log
PIPELINE_TELEMETRY=true|false
PIPELINE_PORT_WEB=5000
PIPELINE_PORT_METRICS=8080
PIPELINE_OLLAMA_URL=http://localhost:11434
PIPELINE_GAME_SPEED=fast|normal|slow
PIPELINE_AI_DIFFICULTY=easy|normal|hard
```

### Config File (pipeline.yml)
```yaml
game:
  default_rounds: 10
  default_players: 4
  cooperative_mode: false
  max_entropy: 10
  
interfaces:
  web:
    enabled: true
    port: 5000
    auto_refresh: 5000
  
  telemetry:
    enabled: true
    port: 8080
    export_format: prometheus
  
  mcp:
    enabled: true
    tools: all
  
  ollama:
    enabled: true
    models:
      - qwen2.5-coder:7b
      - llama3.2:3b
    
logging:
  level: INFO
  file: game.log
  format: "%(asctime)s [%(levelname)s] %(message)s"
  
debugging:
  save_game_history: true
  export_replay: true
  profile_performance: false
```

## 🎯 Performance Monitoring

### Game Performance Metrics
```
Average game duration: 60ms
Services per second: 167
Requests processed: 2000/sec
Memory usage: 98MB
CPU usage: 12% (single core)
Network latency: <1ms local
```

### Bottleneck Analysis
```python
# Enable profiling
import cProfile
profiler = cProfile.Profile()
profiler.enable()
run_game()
profiler.disable()
profiler.dump_stats('game_profile.stats')

# Analyze with snakeviz
# pip install snakeviz
# snakeviz game_profile.stats
```

## 🐛 Common Debugging Scenarios

### Service Not Deploying
```python
# Check resources
print(f"Player resources: CPU={player.cpu}, Mem={player.memory}")
print(f"Service cost: {ServiceProperties.get_properties(service_type)}")

# Check board position
print(f"Position {position} occupied: {position in game_state.board_grid}")
```

### Cascade Failures
```python
# Enable cascade logging
game_state.log_event("cascade_failure", {
    "origin": failed_service.id,
    "affected": list(cascade_services),
    "depth": cascade_depth
})
```

### AI Decision Analysis
```python
# Log AI reasoning
action = ai_player.choose_action(game_state)
print(f"AI chose: {action}")
print(f"Score: {ai_player._score_action(action, game_state)}")
print(f"Alternatives: {legal_actions[:5]}")
```

## 📈 Analytics Dashboard

Access game analytics at http://localhost:5000/analytics with:
- Win rate by strategy
- Service deployment patterns
- Failure cascade visualization
- Uptime degradation curves
- Resource utilization heatmaps
- Player decision trees

This comprehensive interface suite allows you to play, analyze, debug, and monitor Pipeline & Peril from multiple angles!