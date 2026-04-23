---
name: gf-graph
description: "Use when the user wants to manage the episodic knowledge graph — add entities/relations/events, search, view timelines, or batch-build from conversations."
---

# Episodic Knowledge Graph

Manage the girlfriend-agent's episodic memory graph.

## When to Use

- User wants to add knowledge entities (people, topics, places)
- User wants to link entities with relations
- User wants to record episodic events with emotions
- User wants to search the graph for context
- User wants to view an entity's timeline
- User wants to batch-process recent conversations into graph structure

## Graph Operations

| Tool | Purpose |
|------|---------|
| graph_add_entity_girlfriend | Add entity node (idempotent) |
| graph_add_relation_girlfriend | Add relation edge (strengthens on duplicate) |
| graph_add_event_girlfriend | Add episodic event |
| graph_search_girlfriend | BFS + inverted index search |
| graph_timeline_girlfriend | Chronological event timeline for an entity |
| graph_batch_build_girlfriend | Auto-build from recent sessions |
| graph_stats_girlfriend | Graph statistics |

## Adding Entities

`graph_add_entity_girlfriend`:
- `entity_name` (required) — e.g. "猫咪", "旅行"
- `entity_type` (optional) — entity, event, topic, or emotion
- Idempotent: existing entities merge properties, returns `created: false`

## Adding Relations

`graph_add_relation_girlfriend`:
- `source_entity` + `target_entity` (required) — entity names
- `relation_type` (optional) — caused, related_to, followed_by, about, felt_during
- Idempotent: duplicates strengthen the edge weight

## Adding Events

`graph_add_event_girlfriend`:
- `description` (required) — what happened
- `entities` (optional) — associated entity names
- `emotion` (optional) — emotion tag

## Searching

`graph_search_girlfriend` uses BFS with inverted index optimization:
- `query` (required) — entity name or keyword
- `max_depth` (optional, default 3) — traversal depth (1-10)
- `max_nodes` (optional, default 20) — result limit

## Batch Build

`graph_batch_build_girlfriend` auto-extracts entities and relations from recent conversation sessions. Call periodically to enrich the graph.