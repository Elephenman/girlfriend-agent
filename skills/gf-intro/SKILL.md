---
name: gf-intro
description: "Introduction to girlfriend-agent plugin — learn how to use all skills, MCP tools, and slash commands. Automatically injected on session start via hook."
---

# Girlfriend-Agent Introduction

You have the **girlfriend-agent** plugin installed. It provides an AI personality engine with persona-driven chat, episodic memory, evolution nurturing, and relationship management.

## Available Skills

| Skill | Slash Command | Purpose |
|-------|---------------|---------|
| gf-chat | `/gf-chat` | Process a message through the personality engine, get persona prompt + memory context |
| gf-status | `/gf-status` | View relationship level, intimacy, attributes, de-AI scores |
| gf-evolve | `/gf-evolve` | Run an evolution cycle — personality micro-adjustments based on conversation patterns |
| gf-memory | `/gf-memory` | Store, search, reinforce, or decay memories |
| gf-persona | `/gf-persona` | Get/update persona configuration or apply a preset template |
| gf-graph | `/gf-graph` | Manage episodic knowledge graph — entities, relations, events, timeline |

## MCP Tools

All skills are powered by MCP tools (via `.mcp.json`). The MCP server runs automatically when Claude Code starts. Available tools:

- **chat_girlfriend** — personality-driven chat context generation
- **status_girlfriend** — relationship state overview
- **health_girlfriend** — engine health check
- **persona_get_girlfriend** / **persona_update_girlfriend** / **persona_apply_template_girlfriend** — persona management
- **memory_update_girlfriend** / **memory_search_girlfriend** / **memory_reinforce_girlfriend** / **memory_decay_girlfriend** / **memory_emotion_trend_girlfriend** — vector memory operations
- **graph_add_entity_girlfriend** / **graph_add_relation_girlfriend** / **graph_add_event_girlfriend** / **graph_search_girlfriend** / **graph_timeline_girlfriend** / **graph_batch_build_girlfriend** / **graph_stats_girlfriend** — episodic graph operations
- **evolve_run_girlfriend** / **evolve_direction_girlfriend** / **evolve_endings_girlfriend** / **evolve_progress_girlfriend** / **evolve_history_girlfriend** / **evolve_revert_girlfriend** / **evolve_revert_to_girlfriend** — evolution lifecycle
- **rollback_girlfriend** — full state rollback to a specific commit

## Quick Start

1. Type `/gf-status` to see the current relationship state
2. Type `/gf-chat <your message>` to chat through the personality engine
3. After several conversations, type `/gf-evolve` to trigger evolution
4. Use `/gf-memory` to store important things discussed
5. Use `/gf-graph` to explore the episodic knowledge graph

## Architecture

The engine uses:
- **7-dimension personality model** (warmth, rationality, independence, humor, patience, curiosity, expressiveness)
- **Ebbinghaus forgetting curve** for memory decay
- **LazyGraphRAG** for episodic knowledge graph with BFS + inverted index search
- **56 evolution endings** (8 attributes × 7 secondary dimensions)
- **Git-based state versioning** for full rollback capability