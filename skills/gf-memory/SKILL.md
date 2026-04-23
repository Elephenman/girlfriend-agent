---
name: gf-memory
description: "Use when the user wants to store, search, reinforce, or analyze memories — vector memory operations for long-term relationship knowledge."
---

# Memory Management

Manage the girlfriend-agent's long-term memory system.

## When to Use

- User wants to store something important discussed
- User asks "do you remember X?" — search memories
- Need to reinforce a memory to prevent decay
- Periodic memory maintenance (decay)
- Analyzing emotional trends

## Memory Operations

| Tool | Purpose |
|------|---------|
| memory_update_girlfriend | Store a new memory fragment |
| memory_search_girlfriend | Search by semantic similarity |
| memory_reinforce_girlfriend | Strengthen a memory to prevent decay |
| memory_decay_girlfriend | Execute time-based weight decay |
| memory_emotion_trend_girlfriend | Analyze emotional patterns |

## Storing Memories

`memory_update_girlfriend` parameters:
- `content` (required) — what to remember
- `memory_type` (optional) — one of:
  - `fact` — factual information ("她喜欢猫")
  - `preference` — likes/dislikes ("不喜欢辣的食物")
  - `event` — shared experience ("上周一起看了电影")
  - `emotion` — emotional moment ("今天她很开心的样子")

## Searching Memories

`memory_search_girlfriend` parameters:
- `query` (required) — search query
- `level` (optional) — injection level context (1-3)
- `n` (optional) — number of results (default 5)

## Memory Decay

Memories follow the Ebbinghaus forgetting curve. Call `memory_decay_girlfriend` periodically to:
- Reduce weights on rarely-accessed memories
- Keep frequently-referenced memories strong
- Also decays graph node weights

## Reinforcement

When a memory is referenced in conversation, call `memory_reinforce_girlfriend` with the `chunk_id` to strengthen its weight and prevent decay.