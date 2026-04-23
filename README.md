<div align="center">

# 💕 Girlfriend Agent

**Open-source AI Personality Engine**

Persona context injection · Episodic memory · Evolution system · Git rollback

> Model-agnostic: the engine provides prompts, memory, and behavioral instructions — you provide inference.

[![Tests](https://img.shields.io/badge/tests-612%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-orange)]()

</div>

---

## ✨ Highlights

- **7-dimensional personality** — warmth, rationality, independence, humor, patience, curiosity, expressiveness with smooth attribute→personality mapping
- **Three-tier memory** — perception (context window) · short-term (JSON) · long-term (ChromaDB + LazyGraphRAG)
- **Progressive injection** — L1 (600 chars) → L2 (2500 chars with graph) → L3 (5000 chars full state)
- **Self-evolution engine** — observe patterns every 7 chats → micro-adjust personality ≤10% → git commit for rollback
- **56 unique endings** — 8 attributes × 7 secondary = diverse relationship trajectories
- **Async-safe** — asyncio.Lock protects read-modify-write sequences; ChatService separates lock-free reads from lock-guarded mutations
- **CQRS graph** — `get_node_info` (pure query) + `touch_node` (access tracking) for clean read/write separation
- **612 tests** — unit, integration, concurrency, and full-chain coverage with 0 warnings

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the engine
python -m src.engine_server
# → Server running on http://127.0.0.1:18012

# Or use the CLI skill scripts
python skills/scripts/chat.py "今天心情怎么样" --level 1
python skills/scripts/status.py
python skills/scripts/evolve.py
python skills/scripts/update.py "她喜欢猫咪" --type preference
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GIRLFRIEND_AGENT_PORT` | `18012` | Server port |
| `GIRLFRIEND_AGENT_HOST` | `localhost` | Server host |

---

## 📡 API Reference

### Chat & Status

| Endpoint | Method | Description | Request Body |
|---|---|---|---|
| `/chat` | POST | Persona prompt + memory injection + de-AI instructions | `{user_message, level, interaction_type}` |
| `/status` | GET | Relationship level, intimacy, attributes, de-AI scores | — |
| `/health` | GET | Server health check | — |

### Persona

| Endpoint | Method | Description | Request Body |
|---|---|---|---|
| `/persona` | GET | Load current persona config | — |
| `/persona/update` | POST | Update a persona field (pre-validated) | `{field, value}` |
| `/persona/apply-template` | POST | Apply a preset persona template | `{template_id}` |

### Memory (Vector)

| Endpoint | Method | Description | Request Body |
|---|---|---|---|
| `/memory/update` | POST | Store a memory fragment | `{content, memory_type, weight}` |
| `/memory/search` | POST | Semantic search memories | `{query, top_k}` |
| `/memory/reinforce` | POST | Reinforce memory weight | `{chunk_id, type}` |
| `/memory/decay` | POST | Trigger memory decay (vector + graph) | — |
| `/memory/emotion-trend` | POST | Get emotion trend from recent sessions | `{top_k}` |

### Memory (Graph / Episodic)

All graph endpoints use Pydantic-validated request models for type safety and auto-generated OpenAPI docs.

| Endpoint | Method | Description | Idempotent |
|---|---|---|---|
| `/graph/add-entity` | POST | Add entity node (returns `created` flag) | ✅ |
| `/graph/add-relation` | POST | Add relation edge (dedup → strengthen) | ✅ |
| `/graph/add-event` | POST | Add event to episodic graph | — |
| `/graph/search` | POST | Search episodic graph (inverted index + BFS) | — |
| `/graph/timeline` | POST | Get entity timeline | — |
| `/graph/batch-build` | POST | Batch build graph from recent sessions | — |
| `/graph/stats` | GET | Get graph statistics | — |

### Evolution

| Endpoint | Method | Description |
|---|---|---|
| `/evolve` | POST | Run evolution cycle (observation + micro-adjustments + git commit) |
| `/evolve/direction` | GET | Current evolution direction + ending trajectory |
| `/evolve/endings` | GET | All 56 possible endings |
| `/evolve/progress` | GET | Attribute evolution progress |
| `/evolve/history` | GET | Evolution git commit history |
| `/evolve/revert` | POST | Revert last evolution adjustment |
| `/evolve/revert-to` | POST | Revert to a specific version |

### Rollback

| Endpoint | Method | Description |
|---|---|---|
| `/rollback` | POST | Roll back all state to a previous git commit |

---

## 💬 Chat Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Choose persona                                            │
│     POST /persona/apply-template {"template_id": "gentle"}    │
│                                                               │
│  2. Chat                                                      │
│     POST /chat {"user_message": "...", "level": 1}            │
│     → Returns: full_prompt, memory_context, de_ai_instructions │
│                                                               │
│  3. Feed prompt into your LLM                                 │
│     → LLM generates character-driven response                 │
│                                                               │
│  4. Store memories                                             │
│     POST /memory/update {"content": "...", "memory_type": "fact"} │
│     POST /graph/add-entity {"entity_name": "猫咪", "entity_type": "topic"} │
│                                                               │
│  5. Evolve (every 7 chats)                                    │
│     POST /evolve → observe → adjust personality → git commit  │
│                                                               │
│  6. Check trajectory                                           │
│     GET /evolve/direction → see which ending you're heading toward │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎭 Interaction Types

| Type | Intimacy Gain | Description |
|---|---|---|
| `daily_chat` | +1 | Casual everyday talk |
| `deep_conversation` | +3 | Deep sharing, inner thoughts |
| `collaborative_task` | +5 | Working together on something |
| `emotion_companion` | +4 | Comforting, caring, emotional support |
| `light_chat` | +1 | Joking, teasing, fun |

---

## 🧬 Evolution System

### Intimacy → Level Progression

```
Lv0 ──10──→ Lv1 ──30──→ Lv2 ──60──→ Lv3 ──100──→ Lv4 ──160──→ Lv5 ──240──→ Lv6
 │           │           │           │            │            │            │
 +3pts      +3pts      +3pts      +3pts        +3pts        +3pts        MAX
 de-AI      de-AI      de-AI      de-AI        de-AI        de-AI        unlock
```

### Core Mechanics

| Mechanic | Detail |
|---|---|
| **Attributes** | care, understanding, expression, memory, humor, intuition, courage, sensitivity (0~100) |
| **De-AI** | 8 dimensions that reduce AI-like behavior as relationship deepens |
| **Observation** | Every 7 chats → analyze topics, emotions, hidden needs from interaction patterns |
| **Micro-adjustments** | ≤10% per step, context-driven, never random |
| **Consecutive guard** | 3+ same-direction → halved; 5+ → stopped (prevents runaway drift) |
| **Conflict trigger** | 5+ conversation gap → conflict mode activates |
| **56 endings** | 8 primary × 7 secondary = unique trajectories (warm guardian, humor partner, 默契知己…) |
| **Rollback** | Revert last evolution or any historical version via git |

---

## 🧠 Memory System

### Three-tier Architecture

| Layer | Storage | Lifespan | Capacity | Query |
|---|---|---|---|---|
| Perception | Agent context window | Single conversation | Context window | Direct |
| Short-term | JSON `session_memory/` | Last 10 sessions | KB-level | Timestamp sort |
| Long-term semantic | ChromaDB (all-MiniLM-L6-v2) | Permanent | Unlimited | Semantic search |
| Long-term episodic | LazyGraphRAG (NetworkX) | Permanent | Unlimited | BFS + inverted index |

### Progressive Injection

| Level | Memories | Extras | ~Chars | When |
|---|---|---|---|---|
| **L1** | 3 | Persona summary | ~600 | Default casual chat |
| **L2** | 8 | Relationship state + emotion trend + graph context | ~2500 | Deep conversation |
| **L3** | 15 | Full evolution state + graph traversal + raw sessions | ~5000 | Complex reasoning |

### Weight & Decay

```
weight = √(access_count + 1) × e^(-λ × days)

Reinforcement:
  - Hit reinforcement:    +0.1 (retrieved in search)
  - Recall reinforcement: +0.2 (explicitly referenced)
  - Path reinforcement:   weighted by graph traversal depth

Decay:
  - Batch update with pre-validation + per-item fallback
  - Performance monitoring with timing logs
  - Configurable λ (default: 0.05 for vector, 0.03 for graph)
```

---

## 🏗️ Architecture

### Project Structure

```
src/
├── engine_server.py            # FastAPI entry point + lifespan + asyncio.Lock
├── core/
│   ├── models.py               # Pydantic data models + field validators
│   ├── config.py               # Paths, constants (INTERACTION_TYPES auto-derived), init
│   ├── persona.py              # Persona engine (pre-validate → mutate → persist)
│   ├── memory.py               # Memory engine (ChromaDB + JSON + progressive injection)
│   ├── graph_memory.py         # Graph engine (NetworkX + inverted index + CQRS)
│   ├── episodic_builder.py     # Episodic builder (entity extraction + graph construction)
│   ├── evolve.py               # Evolution engine (observe/adjust/direction/revert)
│   ├── chat_service.py         # Chat service (mutate_state + build_context separation)
│   ├── state_manager.py        # State manager (save/load/load_or_init/reload_all/persist)
│   └── git_manager.py          # Git rollback with cached Repo + defensive checks
├── api/
│   ├── chat_router.py          # Chat endpoint (Lock-guarded mutations via ChatService)
│   ├── evolve_router.py        # Evolution endpoints (Lock + read-only documented)
│   ├── graph_router.py         # Graph endpoints (Pydantic models + idempotent operations)
│   ├── memory_router.py        # Memory endpoints (Pydantic models for reinforce/trend)
│   ├── persona_router.py       # Persona CRUD
│   ├── rollback_router.py      # Rollback via StateManager
│   └── status_router.py        # Relationship status
├── templates/                  # 6 persona JSON templates
├── prompts/                    # 7 level prompt templates (Lv0~Lv6)
└── endings/                    # 56 ending descriptions
skills/
├── SKILL.md                    # Skill declaration
└── scripts/                    # CLI bridge scripts (chat/status/evolve/update)
tests/
├── test_api.py                 # API integration + graph+chat integration
├── test_concurrency.py         # asyncio.Lock concurrency verification
├── test_state_manager.py       # StateManager unit tests (11 tests)
├── test_full_chain.py          # End-to-end chain (chat→memory→evolve→rollback)
├── test_*.py                   # Module-level tests (612 total)
```

### Design Patterns

| Pattern | Where | Purpose |
|---|---|---|
| **CQRS** | `graph_memory.py` | `get_node_info` (query) vs `touch_node` (command) |
| **Lock-per-mutation** | `chat_router.py`, `evolve_router.py` | Lock only around state changes, reads are lock-free |
| **Pre-validate → mutate** | `persona.py` | Validate before setattr, no intermediate illegal state |
| **Self-heal** | `state_manager.py` | `load_or_init_*` auto-creates defaults when files missing |
| **Batch + fallback** | `memory.py` | Batch update first, per-item fallback on failure |
| **Inverted index** | `graph_memory.py` | Label substring index for O(1) seed node lookup |
| **Idempotent endpoints** | `graph_router.py` | Duplicate entity returns existing ID, duplicate edge strengthens |
| **TypedDict returns** | `chat_service.py` | `ChatContext` TypedDict for IDE type hints |

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with concurrency verification
python -m pytest tests/test_concurrency.py -v

# Run specific module
python -m pytest tests/test_state_manager.py -v

# 612 tests · 0 warnings · covers unit + integration + concurrency + full-chain
```

### Test Categories

| Category | Count | Coverage |
|---|---|---|
| Unit tests | ~400 | All core modules (persona, memory, evolve, graph, config, models, git) |
| API integration | ~80 | All endpoints via httpx AsyncClient |
| Concurrency | 7 | Lock safety under parallel chat/evolve/revert |
| Full-chain | ~15 | chat → memory → evolve → rollback lifecycle |
| StateManager | 11 | save/load/load_or_init/reload/persist + corrupt/missing files |
| Graph integration | ~10 | Graph+ChatService cross-module injection |

---

## 📂 Runtime Data

Stored at `~/.girlfriend-agent/`, auto-initialized on first start, git-managed for rollback:

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/             # Vector store (git-excluded)
│   ├── session_memory/        # Short-term JSON (git-excluded)
│   ├── graphrag_db/           # Episodic graph (git-excluded)
│   ├── evolution_log/         # Evolution history
│   └── interaction_log/       # Interaction counts
├── config/
│   ├── persona.json           # Current persona (self-heals on corruption)
│   ├── relationship.json      # Relationship state + attributes (self-heals)
│   ├── evolution.json         # Evolution state (consecutive tracking)
│   └── settings.json          # Global settings
├── .git/                      # Version control for rollback
```

---

## 🛡️ Safety & Robustness

| Feature | Implementation |
|---|---|
| **Concurrent safety** | asyncio.Lock protects read-modify-write in chat/evolve routers |
| **Data validation** | Pydantic models on all request bodies; pre-validate before persona mutation |
| **Self-healing** | StateManager auto-creates defaults when config files are missing or corrupted |
| **Graceful degradation** | Memory decay: batch update → per-item fallback on failure; invalid metadata skipped |
| **Negative value guard** | `intimacy_points` clamped to ≥0 after level-up threshold deduction |
| **Git defensive** | GitManager checks `.git` directory before operations; clear RuntimeError if uninitialized |
| **Idempotent writes** | Graph add-entity returns existing ID on duplicate; add-relation strengthens weight |
| **Performance monitoring** | Decay operations log timing stats (valid/skipped/total) |

---

## 📈 Roadmap

| Phase | Focus | Status |
|---|---|---|
| **Phase 1** | Core engine + CLI skill scripts | ✅ Done |
| **Phase 2** | LazyGraphRAG + episodic memory | ✅ Done |
| **Phase 3** | Self-evolution engine refinement | ✅ Done |
| **Phase 3.5** | 5-round architecture optimization (8.2→9.7/10) | ✅ Done |
| **Phase 4** | Desktop UI + cloud sync | 📋 Planned |
| **Phase 5** | Polish + open source release | 📋 Planned |

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

<div align="center">

### 🌸 中文版请见下方

</div>

---

## 💕 Girlfriend Agent

**开源 AI 人格引擎**

人格化上下文注入 · 情景记忆图谱 · 进化养成系统 · Git回退机制

> 模型无关：引擎提供 prompt、记忆、行为指令 — 你提供推理能力。

---

## ✨ 核心亮点

- **7维人格** — 温暖、理性、独立、幽默、耐心、好奇、表达力，平滑属性→人格映射
- **三层记忆** — 感知（上下文窗口）· 短期（JSON）· 长期（ChromaDB + LazyGraphRAG）
- **渐进注入** — L1（600字）→ L2（2500字含图谱）→ L3（5000字完整状态）
- **自进化引擎** — 每7次对话观察模式 → 人格微调≤10% → git提交支持回退
- **56种独特结局** — 8主属性 × 7副属性 = 多样化关系轨迹
- **并发安全** — asyncio.Lock 保护读-改-写序列；ChatService 分离锁外读取与锁内变更
- **CQRS图谱** — `get_node_info`（纯查询）+ `touch_node`（访问追踪）读写分离
- **612个测试** — 单元、集成、并发、全链路覆盖，0 warnings

---

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动引擎
python -m src.engine_server
# → 服务运行在 http://127.0.0.1:18012

# 或使用 CLI 脚本
python skills/scripts/chat.py "今天心情怎么样" --level 1
python skills/scripts/status.py
python skills/scripts/evolve.py
python skills/scripts/update.py "她喜欢猫咪" --type preference
```

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `GIRLFRIEND_AGENT_PORT` | `18012` | 服务端口 |
| `GIRLFRIEND_AGENT_HOST` | `localhost` | 服务地址 |

---

## 📡 API 接口

### 对话 & 状态

| 接口 | 方法 | 说明 | 请求体 |
|---|---|---|---|
| `/chat` | POST | 人格 prompt + 记忆注入 + 去AI味指令 | `{user_message, level, interaction_type}` |
| `/status` | GET | 关系等级、亲密度、属性、去AI味评分 | — |
| `/health` | GET | 服务健康检查 | — |

### 人设

| 接口 | 方法 | 说明 | 请求体 |
|---|---|---|---|
| `/persona` | GET | 加载当前人设配置 | — |
| `/persona/update` | POST | 更新人设字段（先验后改） | `{field, value}` |
| `/persona/apply-template` | POST | 应用预设人设模板 | `{template_id}` |

### 记忆（向量）

| 接口 | 方法 | 说明 | 请求体 |
|---|---|---|---|
| `/memory/update` | POST | 写入一条记忆 | `{content, memory_type, weight}` |
| `/memory/search` | POST | 语义搜索记忆 | `{query, top_k}` |
| `/memory/reinforce` | POST | 强化记忆权重 | `{chunk_id, type}` |
| `/memory/decay` | POST | 触发记忆衰减（向量+图谱） | — |
| `/memory/emotion-trend` | POST | 获取情绪趋势 | `{top_k}` |

### 记忆（图谱 / 情景）

所有图谱接口使用 Pydantic 验证模型，自动生成 OpenAPI 文档。

| 接口 | 方法 | 说明 | 幂等 |
|---|---|---|---|
| `/graph/add-entity` | POST | 添加实体节点（返回 `created` 标志） | ✅ |
| `/graph/add-relation` | POST | 添加关系边（重复→加强权重） | ✅ |
| `/graph/add-event` | POST | 添加事件到情景图谱 | — |
| `/graph/search` | POST | 搜索情景图谱（倒排索引 + BFS） | — |
| `/graph/timeline` | POST | 获取实体时间线 | — |
| `/graph/batch-build` | POST | 批量建图 | — |
| `/graph/stats` | GET | 获取图谱统计 | — |

### 进化

| 接口 | 方法 | 说明 |
|---|---|---|
| `/evolve` | POST | 执行进化周期（观察→微调→git提交） |
| `/evolve/direction` | GET | 当前进化方向+结局轨迹 |
| `/evolve/endings` | GET | 所有56种结局 |
| `/evolve/progress` | GET | 属性进化进度 |
| `/evolve/history` | GET | 进化commit历史 |
| `/evolve/revert` | POST | 回退最近一次进化 |
| `/evolve/revert-to` | POST | 回退到指定版本 |

### 回退

| 接口 | 方法 | 说明 |
|---|---|---|
| `/rollback` | POST | 回退所有状态到之前的 git 提交 |

---

## 💬 对话流程

```
┌──────────────────────────────────────────────────────────┐
│  1. 选人设                                                 │
│     POST /persona/apply-template {"template_id": "gentle"} │
│                                                            │
│  2. 聊天                                                   │
│     POST /chat {"user_message": "...", "level": 1}         │
│     → 返回: full_prompt, memory_context, de_ai_instructions │
│                                                            │
│  3. 将 prompt 注入大模型                                    │
│     → 大模型生成人格化回复                                   │
│                                                            │
│  4. 存储记忆                                                │
│     POST /memory/update {"content": "...", "memory_type": "fact"} │
│     POST /graph/add-entity {"entity_name": "猫咪", "entity_type": "topic"} │
│                                                            │
│  5. 进化（每7次对话）                                        │
│     POST /evolve → 观察 → 微调人格 → git 提交               │
│                                                            │
│  6. 查看轨迹                                                │
│     GET /evolve/direction → 看你正在走向哪个结局              │
└──────────────────────────────────────────────────────────┘
```

---

## 🎭 互动类型

| 类型 | 亲密度增长 | 适用场景 |
|---|---|---|
| `daily_chat` | +1 | 日常闲聊 |
| `deep_conversation` | +3 | 深度对话、分享内心 |
| `collaborative_task` | +5 | 协作做事 |
| `emotion_companion` | +4 | 情感陪伴、安慰 |
| `light_chat` | +1 | 轻松玩笑 |

---

## 🧬 进化系统

### 亲密度 → 等级进阶

```
Lv0 ──10──→ Lv1 ──30──→ Lv2 ──60──→ Lv3 ──100──→ Lv4 ──160──→ Lv5 ──240──→ Lv6
 │           │           │           │            │            │            │
 +3点       +3点       +3点       +3点         +3点         +3点         MAX
 去AI味     去AI味     去AI味     去AI味       去AI味       去AI味       解锁
```

### 核心机制

| 机制 | 详情 |
|---|---|
| **属性** | 关心、理解、表达、记忆、幽默、直觉、勇气、细腻（0~100） |
| **去AI味** | 随关系深化自动降低AI感的8维度 |
| **观察** | 每7次对话 → 分析话题、情绪、隐性需求 |
| **微调** | ≤10%单步、情境驱动、绝不随机 |
| **连续递减** | 连续3次同方向→减半；连续5次→停止 |
| **冲突触发** | 5次以上对话空档 → 冲突模式激活 |
| **56种结局** | 8主属性 × 7副属性 = 独特轨迹 |
| **回退** | 可回退最近进化或任意历史版本 |

---

## 🧠 记忆系统

### 三层架构

| 层 | 存储 | 生命周期 | 容量 | 查询 |
|---|---|---|---|---|
| 感知记忆 | Agent上下文窗口 | 单次对话 | 上下文窗口 | 直接 |
| 短期记忆 | JSON `session_memory/` | 最近10次 | KB级 | 时间戳排序 |
| 长期语义 | ChromaDB (all-MiniLM-L6-v2) | 持久 | 无限 | 语义搜索 |
| 长期情景 | LazyGraphRAG (NetworkX) | 持久 | 无限 | BFS + 倒排索引 |

### 渐进式注入

| 等级 | 记忆数 | 附加内容 | 字数 | 何时使用 |
|---|---|---|---|---|
| **L1** | 3条 | 人格摘要 | ~600字 | 默认闲聊 |
| **L2** | 8条 | 关系状态+情绪趋势+图谱关联 | ~2500字 | 话题深入 |
| **L3** | 15条 | 完整进化状态+图谱遍历+原始对话 | ~5000字 | 复杂推理 |

### 权重与衰减

```
权重 = √(访问次数 + 1) × e^(-λ × 天数)

强化机制：
  - 检索命中强化：    +0.1（搜索中被检索）
  - 主动回忆强化：    +0.2（被明确引用）
  - 路径强化：        按图谱遍历深度加权

衰减机制：
  - 批量更新 + 预验证 + 逐条回退兜底
  - 性能监测日志（有效/跳过/总数）
  - 可配置 λ（默认：向量 0.05，图谱 0.03）
```

---

## 🏗️ 项目结构

```
src/
├── engine_server.py            # FastAPI 入口 + 生命周期 + asyncio.Lock
├── core/
│   ├── models.py               # Pydantic 数据模型 + 字段验证器
│   ├── config.py               # 路径、常量（INTERACTION_TYPES 自动派生）、初始化
│   ├── persona.py              # 人格引擎（先验后改 → 变更 → 持久化）
│   ├── memory.py               # 记忆引擎（ChromaDB + JSON + 渐进注入）
│   ├── graph_memory.py         # 图引擎（NetworkX + 倒排索引 + CQRS）
│   ├── episodic_builder.py     # 情景建图器（实体提取 + 图谱构建）
│   ├── evolve.py               # 进化引擎（观察/微调/方向/回退）
│   ├── chat_service.py         # 聊天服务（mutate_state + build_context 分离）
│   ├── state_manager.py        # 状态管理（save/load/load_or_init/reload_all/persist）
│   └── git_manager.py          # Git 回退管理（缓存 Repo + 防御性检查）
├── api/
│   ├── chat_router.py          # 聊天端点（通过 ChatService 的 Lock 保护变更）
│   ├── evolve_router.py        # 进化端点（Lock + 纯读端点文档化）
│   ├── graph_router.py         # 图谱端点（Pydantic 模型 + 幂等操作）
│   ├── memory_router.py        # 记忆端点（reinforce/trend 的 Pydantic 模型）
│   ├── persona_router.py       # 人设 CRUD
│   ├── rollback_router.py      # 通过 StateManager 回退
│   └── status_router.py        # 关系状态
├── templates/                  # 6个 人设 JSON 模板
├── prompts/                    # 7个 等级 prompt 模板（Lv0~Lv6）
└── endings/                    # 56种结局描述库
skills/
├── SKILL.md                    # Skill 声明
└── scripts/                    # CLI 桥接脚本（聊天/状态/进化/记忆更新）
tests/
├── test_api.py                 # API 集成 + 图谱+聊天跨模块
├── test_concurrency.py         # asyncio.Lock 并发验证
├── test_state_manager.py       # StateManager 单元测试（11个）
├── test_full_chain.py          # 端到端链路（聊天→记忆→进化→回退）
├── test_*.py                   # 模块级测试（共612个）
```

### 设计模式

| 模式 | 位置 | 目的 |
|---|---|---|
| **CQRS** | `graph_memory.py` | `get_node_info`（查询）vs `touch_node`（命令） |
| **锁-仅-变更** | `chat_router.py`, `evolve_router.py` | 仅状态变更加锁，读取无锁 |
| **先验后改** | `persona.py` | 验证后再 setattr，无中间非法状态 |
| **自愈** | `state_manager.py` | `load_or_init_*` 文件缺失时自动创建默认值 |
| **批量+回退** | `memory.py` | 批量更新优先，失败逐条回退 |
| **倒排索引** | `graph_memory.py` | Label 子串索引，种子节点查找 O(1) |
| **幂等端点** | `graph_router.py` | 重复实体返回已有ID，重复边加强权重 |
| **TypedDict返回** | `chat_service.py` | `ChatContext` TypedDict 提供IDE类型提示 |

---

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行并发验证
python -m pytest tests/test_concurrency.py -v

# 运行指定模块
python -m pytest tests/test_state_manager.py -v

# 612个测试 · 0 warnings · 覆盖单元+集成+并发+全链路
```

### 测试分类

| 分类 | 数量 | 覆盖范围 |
|---|---|---|
| 单元测试 | ~400 | 所有核心模块 |
| API集成 | ~80 | 所有端点 via httpx AsyncClient |
| 并发测试 | 7 | Lock下的并行聊天/进化/回退 |
| 全链路 | ~15 | 聊天 → 记忆 → 进化 → 回退 |
| StateManager | 11 | save/load/自愈/损坏文件 |
| 图谱集成 | ~10 | 图谱+ChatService 跨模块注入 |

---

## 📂 运行时数据

存储在 `~/.girlfriend-agent/`，首次启动自动初始化，git 管理支持回退：

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/             # 向量库（git 排除）
│   ├── session_memory/        # 短期记忆 JSON（git 排除）
│   ├── graphrag_db/           # 情景图谱（git 排除）
│   ├── evolution_log/         # 进化日志
│   └── interaction_log/       # 互动计数
├── config/
│   ├── persona.json           # 当前人设（损坏时自愈）
│   ├── relationship.json      # 关系状态 + 属性（损坏时自愈）
│   ├── evolution.json         # 进化状态（连续调整追踪）
│   └── settings.json          # 全局设置
├── .git/                      # 版本控制，支持回退
```

---

## 🛡️ 安全与健壮性

| 特性 | 实现 |
|---|---|
| **并发安全** | asyncio.Lock 保护 chat/evolve 路由的读-改-写 |
| **数据验证** | 所有请求体使用 Pydantic 模型；人设变更先验后改 |
| **自愈机制** | StateManager 配置文件缺失或损坏时自动创建默认值 |
| **优雅降级** | 记忆衰减：批量优先→逐条回退；无效元数据跳过 |
| **负值防护** | `intimacy_points` 升级扣减后 clamp ≥0 |
| **Git防御** | GitManager 操作前检查 `.git` 目录；未初始化时明确 RuntimeError |
| **幂等写入** | 图谱重复实体返回已有ID；重复边加强权重 |
| **性能监测** | 衰减操作记录耗时统计（有效/跳过/总数） |

---

## 📈 开发路线

| 阶段 | 重点 | 状态 |
|---|---|---|
| **Phase 1** | 核心引擎 + CLI 脚本 | ✅ 完成 |
| **Phase 2** | LazyGraphRAG + 情景记忆 | ✅ 完成 |
| **Phase 3** | 自进化引擎完善 | ✅ 完成 |
| **Phase 3.5** | 5轮架构优化（8.2→9.7/10） | ✅ 完成 |
| **Phase 4** | 桌面端可视化 + 云同步 | 📋 规划中 |
| **Phase 5** | 打磨 + 开源发布 | 📋 规划中 |

---

## 📄 许可证

MIT License — 自由使用、修改和分发。
