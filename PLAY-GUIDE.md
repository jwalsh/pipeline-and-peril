# Pipeline & Peril - Interactive Play Guide

## Quick Start

You can now play Pipeline & Peril interactively through Claude! The game features autonomous AI players and a complete distributed systems simulation.

## Demo Results (10 Games)

- **Average Game Duration**: 60ms per game
- **Defensive Strategy Dominance**: 90% win rate
- **System Degradation**: Uptime drops from 100% to ~8% over 15 rounds
- **Service Deployment**: Load Balancers most popular (171 deployments)

## Playing the Game

### Option 1: Autonomous Analysis
```bash
cd digital/pygame

# Run 10 games with full analysis
uv run python scripts/run_autonomous.py --games 10 --verbose

# Generate visual screenshots
uv run python scripts/screenshot_demo.py
```

### Option 2: Interactive MCP Server (Recommended)
```bash
cd digital/pygame

# Start the MCP server for Claude integration
uv run python scripts/start_mcp_server.py
```

Then use these MCP tools through Claude:

- `create_game` - Start a new game (specify human_player=0 to play as Player 1)
- `get_game_summary` - See current game state
- `get_legal_actions` - See what moves you can make
- `execute_action` - Make your move
- `ai_suggestion` - Get AI advice
- `advance_phase` - Let AI players take their turns
- `generate_screenshot` - See the visual board
- `list_games` - See all active games

### Option 3: Visual Interface
```bash
cd digital/pygame

# Run with PyGame visual interface
uv run python scripts/run_autonomous.py --visual --games 1
```

## Game Mechanics

### Service Types
- **Load Balancer** (Red LB): Entry points for traffic
- **Compute** (Green CP): Process requests
- **Database** (Blue DB): Store data
- **Cache** (Purple CA): Speed up access
- **Queue** (Orange QU): Handle async tasks
- **API Gateway** (Cyan AG): Route requests

### Turn Flow
1. **Traffic Phase**: 2d10 requests generated
2. **Action Phase**: Each player takes 3 actions
3. **Resolution Phase**: Services handle load
4. **Chaos Phase**: System-wide events

### Player Strategies
- **Aggressive**: Rapid expansion, high risk
- **Defensive**: Stability focus, repair priority
- **Balanced**: Mixed approach
- **Random**: Unpredictable decisions

## Example Interactive Session

```
You: Create a new game where I'm Player 1
Claude: [Uses create_game with human_player=0]

You: What's the current game state?
Claude: [Uses get_game_summary to show board]

You: What actions can I take?
Claude: [Uses get_legal_actions for your player]

You: I want to deploy a Database at position (2,3)
Claude: [Uses execute_action with deploy action]

You: Let the AI players take their turns
Claude: [Uses advance_phase to progress game]

You: Show me the board
Claude: [Uses generate_screenshot to show visual state]
```

## Key Features

- **Real-time Strategy**: Make decisions under entropy pressure
- **Educational Value**: Learn distributed systems concepts
- **Visual Feedback**: See your service network grow
- **AI Opponents**: 4 different strategic personalities
- **Performance Analytics**: Track success metrics
- **Chaos Events**: Handle unexpected system failures

## Understanding the Display

### Service States (Colors)
- **Green**: Healthy services
- **Yellow**: Degraded (overloaded but functional)
- **Orange**: Overloaded (near failure)
- **Red**: Failed services
- **Purple**: Cascading failures

### Load Indicators
- Bar under each service shows current load vs capacity
- Load percentage displays when >80%

### Player Ownership
- Colored dots show which player owns each service
- Resource counts and scores in bottom panel

Start playing by asking Claude to create a game for you!