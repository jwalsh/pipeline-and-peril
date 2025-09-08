# Pipeline & Peril - Game Rules

## Objective

Build a resilient distributed system that can handle incoming traffic while defending against The Static's chaos.

## Setup

1. Place the game board in the center
2. Each player takes a character board (Developer, Architect, Data Engineer, or DevOps)
3. Create dice pools:
   - Resource pool: 10d6 per player
   - Chaos pool: 5d8
   - Traffic pool: 10d10
4. Shuffle event cards

## Turn Structure

### Phase 1: Traffic Generation
- Roll 2d10 to determine incoming requests
- Distribute load tokens across services

### Phase 2: Player Actions (3 actions each)
- **Build**: Add a new service tile (cost: 2 actions)
- **Connect**: Create network paths between services (cost: 1 action)
- **Allocate**: Assign d6 resource dice to services (cost: 1 action)
- **Debug**: Remove bugs from services (roll d20 vs bug's d4 severity)
- **Scale**: Add capacity to existing service (cost: varies)

### Phase 3: Resolution
- Each service must roll d20 ≥ (load - allocated resources) or fail
- Failed services cascade failures to dependencies
- Roll d12 for each network hop to determine latency

### Phase 4: Chaos
- Roll d8 on chaos table
- Apply effects (network partitions, CPU spikes, disk failures, etc.)
- Spawn bugs on affected services

## Winning Conditions

**Cooperative**: Survive 10 rounds with system uptime >80%
**Competitive**: Score points for handled requests minus penalties for failures

## Character Abilities

**Developer**: Reroll failed service checks once per turn
**Architect**: Create redundant paths for free
**Data Engineer**: Reduce latency by one step  
**DevOps**: Ignore one chaos event per round