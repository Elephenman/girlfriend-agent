# girlfriend-agent

> Open-source AI personality engine — persona context injection, memory management, and evolution system for character-driven conversations.

**Model-agnostic**: The engine provides prompts, memory, and behavioral instructions. The caller provides inference.

## Quick Start

```bash
pip install -r requirements.txt
python -m src.engine_server
# Server starts on http://127.0.0.1:18012
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Get persona prompt + memory injection + de-AI instructions |
| `/status` | GET | View relationship level, intimacy, attributes |
| `/health` | GET | Server health check |
| `/evolve` | POST | Run evolution cycle (personality micro-adjustments) |
| `/memory/update` | POST | Store a memory fragment |
| `/memory/search` | POST | Semantic search memories |
| `/persona` | GET | Load current persona config |
| `/persona/update` | POST | Update a persona field |
| `/persona/apply-template` | POST | Apply a preset persona template |
| `/rollback` | POST | Roll back state to a previous git commit |

## Chat Flow

```
1. Choose persona: POST /persona/apply-template {"template_id": "gentle"}
2. Chat:          POST /chat {"user_message": "...", "level": 1, "interaction_type": "daily_chat"}
3. Inject prompt into your LLM → LLM generates character-driven response
4. Extract key facts: POST /memory/update {"content": "...", "memory_type": "fact"}
5. Every 7 chats: POST /evolve → personality micro-adjustments + git commit
```

## Interaction Types

| Type | Intimacy Gain | When to Use |
|---|---|---|
| `daily_chat` | +1 | Casual everyday talk |
| `deep_conversation` | +3 | Deep sharing, inner thoughts |
| `collaborative_task` | +5 | Working together on something |
| `emotion_companion` | +4 | Comforting, caring, emotional support |
| `light_chat` | +1 | Joking, teasing, fun |

## Persona Templates

6 presets: `default`, `tsundere`, `gentle`, `lively`, `intellectual`, `little_sister` + `custom_skeleton` (all-neutral baseline).

## Evolution System

- **Intimacy → Level**: Thresholds at 10/30/60/100/160/240 points (Lv0→Lv6)
- **Level-up**: Awards 3 attribute bonus points + de-AI dimension updates
- **Attributes**: care, understanding, expression, memory, humor, intuition, courage, sensitivity (0~100)
- **De-AI**: 8 dimensions that reduce AI-like behavior as relationship deepens (structured_output, precision_level, emotion_naturalness, proactivity_randomness, chatter_ratio, mistake_rate, hesitation_rate, personal_depth)
- **Evolution cycle**: Every 7 conversations → analyze patterns → micro-adjust personality ≤10% per step → git commit
- **Conflict trigger**: 5+ conversation gap → conflict mode activates

## Memory System

- **Long-term**: ChromaDB with all-MiniLM-L6-v2 embeddings, cosine similarity, weight-based retrieval
- **Short-term**: JSON session files (last 10 conversations)
- **Injection levels**: L1 (3 memories ~600 chars), L2 (8 + sessions ~2500), L3 (15 + full state ~5000)
- **Weight formula**: `sqrt(access_count+1) * exp(-0.1 * days)` — frequently accessed recent memories rank higher

## Architecture

```
src/
├── engine_server.py          # FastAPI entry point (port 18012)
├── core/
│   ├── models.py             # Pydantic data models
│   ├── config.py             # Paths, constants, init
│   ├── persona.py            # Persona engine (attribute→personality fusion)
│   ├── memory.py             # Memory engine (ChromaDB + JSON + injection)
│   ├── evolve.py             # Evolution engine (intimacy/level/de-AI)
│   └── git_manager.py        # Git rollback management
├── api/                       # 6 FastAPI routers
├── templates/                 # 6 persona JSON templates
├── prompts/                   # 7 level prompt templates (Lv0~Lv6)
└── endings/                   # Ending descriptions
skills/
├── SKILL.md                   # WorkBuddy skill declaration
└── scripts/                   # 4 bridge scripts (chat/status/evolve/update)
```

## Testing

```bash
python -m pytest tests/ -v
# 79 tests covering all modules + API integration + full-chain
```

## Runtime Data

Stored at `~/.girlfriend-agent/`, auto-initialized on first start, git-managed for rollback:

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/             # Vector store (excluded from git)
│   ├── session_memory/        # Short-term JSON (excluded from git)
│   ├── evolution_log/         # Evolution history
│   └── interaction_log/       # Interaction counts
├── config/
│   ├── persona.json           # Current persona
│   ├── relationship.json      # Relationship state + attributes
│   └── settings.json          # Global settings
├── .git/                      # For rollback
```

## License

MIT