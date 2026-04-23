# girlfriend-agent

> Open-source AI personality engine — persona context injection, episodic memory, evolution system, and rollback for character-driven conversations.

**Model-agnostic**: The engine provides prompts, memory, and behavioral instructions. The caller provides inference.

## Quick Start

```bash
pip install -r requirements.txt
python -m src.engine_server
# Server starts on http://127.0.0.1:18012
```

## API Endpoints

### Chat & Status

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Get persona prompt + memory injection + de-AI instructions |
| `/status` | GET | View relationship level, intimacy, attributes |
| `/health` | GET | Server health check |

### Persona

| Endpoint | Method | Description |
|---|---|---|
| `/persona` | GET | Load current persona config |
| `/persona/update` | POST | Update a persona field |
| `/persona/apply-template` | POST | Apply a preset persona template |

### Memory (Vector)

| Endpoint | Method | Description |
|---|---|---|
| `/memory/update` | POST | Store a memory fragment |
| `/memory/search` | POST | Semantic search memories |
| `/memory/reinforce` | POST | Reinforce memory weight |
| `/memory/decay` | POST | Trigger memory decay (vector + graph) |
| `/memory/emotion-trend` | POST | Get emotion trend from recent sessions |

### Memory (Graph / Episodic)

| Endpoint | Method | Description |
|---|---|---|
| `/graph/add-entity` | POST | Add entity node to episodic graph |
| `/graph/add-relation` | POST | Add relation edge to episodic graph |
| `/graph/add-event` | POST | Add event to episodic graph |
| `/graph/search` | POST | Search episodic graph |
| `/graph/timeline` | POST | Get entity timeline |
| `/graph/batch-build` | POST | Batch build graph from recent sessions |
| `/graph/stats` | GET | Get graph statistics |

### Evolution

| Endpoint | Method | Description |
|---|---|---|
| `/evolve` | POST | Run evolution cycle (observation + micro-adjustments) |
| `/evolve/direction` | GET | Get current evolution direction + ending |
| `/evolve/endings` | GET | List all 56 possible endings |
| `/evolve/progress` | GET | Get attribute evolution progress |
| `/evolve/history` | GET | Get evolution commit history |
| `/evolve/revert` | POST | Revert last evolution adjustment |
| `/evolve/revert-to` | POST | Revert to a specific version |

### Rollback

| Endpoint | Method | Description |
|---|---|---|
| `/rollback` | POST | Roll back state to a previous git commit |

## Chat Flow

```
1. Choose persona:    POST /persona/apply-template {"template_id": "gentle"}
2. Chat:              POST /chat {"user_message": "...", "level": 1, "interaction_type": "daily_chat"}
3. Inject prompt into your LLM → LLM generates character-driven response
4. Extract key facts: POST /memory/update {"content": "...", "memory_type": "fact"}
5. Build episodic:    POST /graph/add-entity {"entity_name": "火山图", "entity_type": "topic"}
6. Every 7 chats:     POST /evolve → observe patterns → micro-adjust personality → git commit
7. Check direction:   GET /evolve/direction → see which ending you're heading toward
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
- **De-AI**: 8 dimensions that reduce AI-like behavior as relationship deepens
- **Evolution cycle**: Every 7 conversations → observe patterns (topics, emotions, hidden needs) → context-driven micro-adjustments ≤10% per step → git commit
- **Consecutive diminishing**: 3+ consecutive same-direction adjustments → halved; 5+ → stopped
- **Conflict trigger**: 5+ conversation gap → conflict mode activates
- **56 endings**: 8 attributes × 7 secondary = 56 unique evolution endings (e.g. warm guardian, humor partner,默契知己)
- **Rollback**: Revert last evolution or any historical version via git

## Memory System

### Three-tier Architecture

| Layer | Storage | Lifespan | Capacity |
|---|---|---|---|
| Perception | Agent context window | Single conversation | Context window |
| Short-term | JSON `session_memory/` | Last 10 sessions | KB-level |
| Long-term semantic | ChromaDB (all-MiniLM-L6-v2) | Permanent | Unlimited |
| Long-term episodic | LazyGraphRAG (NetworkX) | Permanent | Unlimited |

### Progressive Injection (Level 1/2/3)

| Level | Memories | Extras | ~Chars | When |
|---|---|---|---|---|
| L1 | 3 | Persona summary | ~600 | Default |
| L2 | 8 | Relationship + emotion trend + graph context | ~2500 | Deep topic |
| L3 | 15 | Full evolution state + graph traversal + raw sessions | ~5000 | Complex reasoning |

### Weight & Decay

- **Vector weight**: `sqrt(access_count+1) * exp(-λ * days)` — Ebbinghaus-based, configurable λ
- **Graph weight**: Same formula with independent decay rate
- **Reinforcement**: Hit reinforcement (+0.1) + recall reinforcement (+0.2) + path reinforcement
- **Decay API**: `/memory/decay` applies precise decay to both vector and graph memories

## Claude Code Plugin

girlfriend-agent can be used as a **Claude Code plugin** — skills + slash commands + MCP tools + session hooks, all in one package.

### Plugin Structure

```
.claude-plugin/plugin.json        # Plugin manifest
.mcp.json                         # MCP server config (stdio transport)
skills/                           # 7 skills with SKILL.md
├── gf-intro/                     # Introduction skill (auto-injected on session start)
├── gf-chat/                      # Chat skill
├── gf-status/                    # Status skill
├── gf-evolve/                    # Evolution skill
├── gf-memory/                    # Memory skill
├── gf-persona/                   # Persona skill
├── gf-graph/                     # Graph skill
└── scripts/                      # CLI bridge scripts (backup interface)
commands/                         # Slash commands
├── gf-chat.md                    # /gf-chat
├── gf-status.md                  # /gf-status
├── gf-evolve.md                  # /gf-evolve
├── gf-memory.md                  # /gf-memory
├── gf-persona.md                 # /gf-persona
└── gf-graph.md                   # /gf-graph
agents/                           # Agent definitions
└── girlfriend-persona.md         # Character response agent
hooks/                            # Session hooks
├── hooks.json                    # Hook configuration
├── session-start                 # Context injection on startup
└── run-hook.cmd                  # Windows/Unix polyglot wrapper
```

### Using in Claude Code

1. Add this repo as a plugin in Claude Code settings
2. The MCP server starts automatically (via `.mcp.json`)
3. On session start, the `gf-intro` skill content is injected as context
4. Use slash commands: `/gf-chat`, `/gf-status`, `/gf-evolve`, `/gf-memory`, `/gf-persona`, `/gf-graph`
5. All 26 MCP tools are available: `chat_girlfriend`, `status_girlfriend`, `evolve_run_girlfriend`, etc.

### MCP Tools (26)

All tools have `_girlfriend` suffix to avoid name conflicts:

| Category | Tools |
|---|---|
| Chat | chat_girlfriend |
| Status | status_girlfriend, health_girlfriend |
| Persona | persona_get_girlfriend, persona_update_girlfriend, persona_apply_template_girlfriend |
| Memory | memory_update_girlfriend, memory_search_girlfriend, memory_reinforce_girlfriend, memory_decay_girlfriend, memory_emotion_trend_girlfriend |
| Graph | graph_add_entity_girlfriend, graph_add_relation_girlfriend, graph_add_event_girlfriend, graph_search_girlfriend, graph_timeline_girlfriend, graph_batch_build_girlfriend, graph_stats_girlfriend |
| Evolution | evolve_run_girlfriend, evolve_direction_girlfriend, evolve_endings_girlfriend, evolve_progress_girlfriend, evolve_history_girlfriend, evolve_revert_girlfriend, evolve_revert_to_girlfriend |
| Rollback | rollback_girlfriend |

## Testing

```bash
python -m pytest tests/ -v
# 544 tests covering all modules + API integration + full-chain
```

## Runtime Data

Stored at `~/.girlfriend-agent/`, auto-initialized on first start, git-managed for rollback:

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/             # Vector store (excluded from git)
│   ├── session_memory/        # Short-term JSON (excluded from git)
│   ├── graphrag_db/           # Episodic graph (excluded from git)
│   ├── evolution_log/         # Evolution history
│   └── interaction_log/       # Interaction counts
├── config/
│   ├── persona.json           # Current persona
│   ├── relationship.json      # Relationship state + attributes
│   ├── evolution.json         # Evolution state (consecutive tracking)
│   └── settings.json          # Global settings
├── .git/                      # For rollback
```

## Development Phases

| Phase | Focus | Status |
|---|---|---|
| Phase 1 | Core engine + Skill | Done |
| Phase 2 | LazyGraphRAG + episodic memory | Done |
| Phase 3 | Self-evolution engine refinement | Done |
| Phase 4 | Desktop UI + cloud sync | Planned |
| Phase 5 | Polish + open source release | Planned |

---

## 中文版

# girlfriend-agent

> 开源 AI 人格引擎 — 提供人格化上下文注入、情景记忆图谱、进化养成系统、Git回退机制，让角色驱动型对话更真实。

**模型无关**：引擎提供 prompt、记忆、行为指令，调用方提供推理能力。

## 快速开始

```bash
pip install -r requirements.txt
python -m src.engine_server
# 服务启动在 http://127.0.0.1:18012
```

## API 接口

### 对话 & 状态

| 接口 | 方法 | 说明 |
|---|---|---|
| `/chat` | POST | 获取人格 prompt + 记忆注入 + 去AI味指令 |
| `/status` | GET | 查看关系等级、亲密度、属性 |
| `/health` | GET | 服务健康检查 |

### 人设

| 接口 | 方法 | 说明 |
|---|---|---|
| `/persona` | GET | 加载当前人设配置 |
| `/persona/update` | POST | 更新人设字段 |
| `/persona/apply-template` | POST | 应用预设人设模板 |

### 记忆（向量）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/memory/update` | POST | 写入一条记忆 |
| `/memory/search` | POST | 语义搜索记忆 |
| `/memory/reinforce` | POST | 强化记忆权重 |
| `/memory/decay` | POST | 触发记忆衰减（向量+图谱） |
| `/memory/emotion-trend` | POST | 获取情绪趋势 |

### 记忆（图谱 / 情景）

| 接口 | 方法 | 说明 |
|---|---|---|
| `/graph/add-entity` | POST | 添加实体节点到情景图谱 |
| `/graph/add-relation` | POST | 添加关系边到情景图谱 |
| `/graph/add-event` | POST | 添加事件到情景图谱 |
| `/graph/search` | POST | 搜索情景图谱 |
| `/graph/timeline` | POST | 获取实体时间线 |
| `/graph/batch-build` | POST | 批量建图 |
| `/graph/stats` | GET | 获取图谱统计 |

### 进化

| 接口 | 方法 | 说明 |
|---|---|---|
| `/evolve` | POST | 执行进化周期（观察→微调→提交） |
| `/evolve/direction` | GET | 获取当前进化方向+结局 |
| `/evolve/endings` | GET | 获取所有56种结局 |
| `/evolve/progress` | GET | 获取属性进化进度 |
| `/evolve/history` | GET | 获取进化commit历史 |
| `/evolve/revert` | POST | 回退最近一次进化 |
| `/evolve/revert-to` | POST | 回退到指定版本 |

### 回退

| 接口 | 方法 | 说明 |
|---|---|---|
| `/rollback` | POST | 回退到之前的 git 提交 |

## 对话流程

```
1. 选人设：    POST /persona/apply-template {"template_id": "gentle"}
2. 聊天：      POST /chat {"user_message": "...", "level": 1, "interaction_type": "daily_chat"}
3. 将返回的 prompt 注入大模型 → 大模型生成人格化回复
4. 提取关键事实：POST /memory/update {"content": "...", "memory_type": "fact"}
5. 构建情景记忆：POST /graph/add-entity {"entity_name": "火山图", "entity_type": "topic"}
6. 每7次对话：  POST /evolve → 观察模式 → 人格微调 → git 提交
7. 查看进化方向：GET /evolve/direction → 看你正在走向哪个结局
```

## 互动类型

| 类型 | 亲密度增长 | 适用场景 |
|---|---|---|
| `daily_chat` | +1 | 日常闲聊 |
| `deep_conversation` | +3 | 深度对话、分享内心 |
| `collaborative_task` | +5 | 协作做事 |
| `emotion_companion` | +4 | 情感陪伴、安慰 |
| `light_chat` | +1 | 轻松玩笑 |

## 人设模板

6种预设：`default`（默认）、`tsundere`（傲娇）、`gentle`（温柔）、`lively`（元气）、`intellectual`（知性）、`little_sister`（妹妹），还有 `custom_skeleton`（自定义骨架）。

## 进化系统

- **亲密度 → 等级**：阈值 10/30/60/100/160/240（Lv0→Lv6）
- **升级奖励**：3点属性加点 + 去AI味维度更新
- **属性**：关心、理解、表达、记忆、幽默、直觉、勇气、细腻（0~100）
- **去AI味**：随关系深化自动降低AI感的8维度
- **进化周期**：每7次对话 → 观察模式（话题、情绪、隐性需求） → 情境驱动微调（单次≤10%）→ git 提交
- **连续递减**：连续3次同方向调整→减半；连续5次→停止
- **冲突触发**：5次以上对话空档 → 冲突模式激活
- **56种结局**：8属性×7副属性 = 56种独特进化结局
- **回退机制**：可回退最近进化或任意历史版本

## 记忆系统

### 三层架构

| 层 | 存储 | 生命周期 | 容量 |
|---|---|---|---|
| 感知记忆 | Agent上下文窗口 | 单次对话 | 上下文窗口 |
| 短期记忆 | JSON `session_memory/` | 最近10次 | KB级 |
| 长期语义 | ChromaDB (all-MiniLM-L6-v2) | 持久 | 无限 |
| 长期情景 | LazyGraphRAG (NetworkX) | 持久 | 无限 |

### 渐进式注入（Level 1/2/3）

| 等级 | 记忆数 | 附加内容 | 字数 | 何时使用 |
|---|---|---|---|---|
| L1 | 3条 | 人格摘要 | ~600字 | 默认 |
| L2 | 8条 | 关系状态+情绪趋势+图谱关联 | ~2500字 | 话题深入 |
| L3 | 15条 | 完整进化状态+图谱遍历+原始对话 | ~5000字 | 复杂推理 |

### 权重与衰减

- **向量权重**：`sqrt(访问次数+1) * exp(-λ * 天数)` — 艾宾浩斯遗忘曲线，可配置λ
- **图谱权重**：同公式，独立衰减率
- **强化**：检索命中强化(+0.1) + 主动回忆强化(+0.2) + 路径强化
- **衰减API**：`/memory/decay` 同时对向量和图谱执行精确衰减

## 项目结构

```
src/
├── engine_server.py          # FastAPI 主入口（端口 18012）
├── core/
│   ├── models.py             # Pydantic 数据模型
│   ├── config.py             # 路径、常量、初始化
│   ├── persona.py            # 人格引擎（属性→人格映射融合）
│   ├── memory.py             # 记忆引擎（ChromaDB + JSON + 渐进注入）
│   ├── graph_memory.py       # 图记忆引擎（NetworkX 情景图谱）
│   ├── episodic_builder.py   # 情景建图器（实体提取+图谱构建）
│   ├── evolve.py             # 进化引擎（观察/微调/方向/回退）
│   └── git_manager.py        # Git 回退管理
├── api/                       # 7个 FastAPI 路由
├── templates/                 # 6个 人设 JSON 模板
├── prompts/                   # 7个 等级 prompt 模板（Lv0~Lv6）
└── endings/                   # 56种结局描述库
skills/
├── SKILL.md                   # WorkBuddy Skill 声明
└── scripts/                   # 4个桥接脚本（聊天/状态/进化/记忆更新）
tests/
├── test_*.py                  # 544个测试覆盖所有模块
```

## 测试

```bash
python -m pytest tests/ -v
# 544个测试覆盖所有模块 + API集成 + 全链路
```

## 运行时数据

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
│   ├── persona.json           # 当前人设
│   ├── relationship.json      # 关系状态 + 属性
│   ├── evolution.json         # 进化状态（连续调整追踪）
│   └── settings.json          # 全局设置
├── .git/                      # 用于回退
```

## 开发阶段

| 阶段 | 重点 | 状态 |
|---|---|---|
| Phase 1 | 核心引擎 + Skill | 完成 |
| Phase 2 | LazyGraphRAG + 情景记忆 | 完成 |
| Phase 3 | 自进化引擎完善 | 完成 |
| Phase 4 | 桌面端可视化 + 云同步 | 规划中 |
| Phase 5 | 打磨 + 开源发布 | 规划中 |

## 许可证

MIT