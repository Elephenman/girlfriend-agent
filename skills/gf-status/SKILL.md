---
name: gf-status
description: "Use when the user wants to check the relationship status — level, intimacy points, attributes, de-AI scores, nickname, and conflict mode."
---

# View Relationship Status

Check the current state of the girlfriend-agent relationship.

## When to Use

- User asks "what's our status?" or "how close are we?"
- User wants to see attribute progress
- User wants to check de-AI (naturalness) scores
- Periodic relationship health check

## How to Use

Call MCP tool **status_girlfriend** (no parameters required).

## Response Format

Returns:
- **current_level** — relationship level (1-5+)
- **intimacy_points** — accumulated intimacy score
- **nickname** — character's nickname for the user
- **conflict_mode** — whether currently in conflict resolution mode
- **attributes** — 8 attribute scores (care/understanding/expression/memory/humor/intuition/courage/sensitivity)
- **de_ai_score** — 4 naturalness dimensions (emotional_naturalness, behavioral_naturalness, language_naturalness, boundary_naturalness)

## Health Check

For engine status, call **health_girlfriend** to verify:
- MCP server is running
- Embedding model is loaded

## Presenting to User

Format the response as a readable summary:
```
关系等级: Lv{level}
亲密度: {intimacy_points}
昵称: {nickname}

属性:
  关心     ████████░░ 80
  理解     ██████░░░░ 60
  ...

去AI味评分:
  情感自然度  0.85
  行为自然度  0.72
  ...
```