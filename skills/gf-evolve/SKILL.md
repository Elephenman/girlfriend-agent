---
name: gf-evolve
description: "Use when the user wants to trigger evolution — personality micro-adjustments, level-up processing, and relationship progression. Should be called every ~7 conversations."
---

# Evolution Cycle

Run the girlfriend-agent evolution system to progress the relationship.

## When to Use

- User asks to "evolve" or "level up"
- After ~7 conversations (recommended cadence)
- User wants to see personality growth direction
- User wants to check possible endings

## Evolution Operations

| Tool | Purpose |
|------|---------|
| evolve_run_girlfriend | Run a full evolution cycle |
| evolve_direction_girlfriend | Check which ending trajectory we're heading toward |
| evolve_endings_girlfriend | List all 56 possible endings |
| evolve_progress_girlfriend | See attribute progress (0.0-1.0) |
| evolve_history_girlfriend | View git history of evolution adjustments |
| evolve_revert_girlfriend | Revert last evolution step |
| evolve_revert_to_girlfriend | Revert to specific commit hash |

## Evolution Cycle Details

`evolve_run_girlfriend` performs:
1. Analyzes recent sessions for patterns (topics, emotions, hidden needs)
2. Micro-adjusts personality dimensions (≤10% change per step)
3. Processes level-up if intimacy threshold reached
4. Git commits the adjustment for rollback capability

## Ending System

56 unique endings (8 primary attributes × 7 secondary dimensions):
- Each ending represents a relationship trajectory
- Direction is determined by accumulated attribute changes
- Examples: "温柔守护者", "知性伴侣", "活泼搭档"

## Reverting

- `evolve_revert_girlfriend` — undo the last evolution step
- `evolve_revert_to_girlfriend` — revert to a specific commit (requires commit hash from `evolve_history_girlfriend`)