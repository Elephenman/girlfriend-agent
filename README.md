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

---

## 中文版

# girlfriend-agent

> 开源 AI 人格引擎 — 提供人格化上下文注入、语义记忆管理、进化养成系统，让角色驱动型对话更真实。

**模型无关**：引擎提供 prompt、记忆、行为指令，调用方提供推理能力。

## 快速开始

```bash
pip install -r requirements.txt
python -m src.engine_server
# 服务启动在 http://127.0.0.1:18012
```

## API 接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/chat` | POST | 获取人格 prompt + 记忆注入 + 去AI味指令 |
| `/status` | GET | 查看关系等级、亲密度、属性 |
| `/health` | GET | 服务健康检查 |
| `/evolve` | POST | 执行进化周期（人格微调） |
| `/memory/update` | POST | 写入一条记忆 |
| `/memory/search` | POST | 语义搜索记忆 |
| `/persona` | GET | 加载当前人设配置 |
| `/persona/update` | POST | 更新人设字段 |
| `/persona/apply-template` | POST | 应用预设人设模板 |
| `/rollback` | POST | 回退到之前的 git 提交 |

## 对话流程

```
1. 选人设：POST /persona/apply-template {"template_id": "gentle"}
2. 聊天：  POST /chat {"user_message": "...", "level": 1, "interaction_type": "daily_chat"}
3. 将返回的 prompt 注入大模型 → 大模型生成人格化回复
4. 提取关键事实：POST /memory/update {"content": "...", "memory_type": "fact"}
5. 每7次对话：POST /evolve → 人格微调 + git 提交
```

## 互动类型

| 类型 | 亲密度增长 | 适用场景 |
|---|---|---|
| `daily_chat` | +1 | 日常闲聊 |
| `deep_conversation` | +3 | 深度对话、分享内心 |
| `collaborative_task` | +5 | 协作做事（一起写代码、计划等） |
| `emotion_companion` | +4 | 情感陪伴、安慰、关心 |
| `light_chat` | +1 | 轻松玩笑、搞笑 |

## 人设模板

6种预设：`default`（默认）、`tsundere`（傲娇）、`gentle`（温柔）、`lively`（元气）、`intellectual`（知性）、`little_sister`（妹妹），还有 `custom_skeleton`（自定义骨架，全中性基线）。

## 进化系统

- **亲密度 → 等级**：阈值 10/30/60/100/160/240（Lv0→Lv6）
- **升级奖励**：3点属性加点 + 去AI味维度更新
- **属性**：关心、理解、表达、记忆、幽默、直觉、勇气、细腻（0~100）
- **去AI味**：随关系深化自动降低AI感的8维度（结构化输出、精确度、情绪自然度、主动性随机性、闲聊比例、犯错率、犹豫率、个人深度）
- **进化周期**：每7次对话 → 分析模式 → 人格微调（单次≤10%）→ git 提交
- **冲突触发**：5次以上对话空档 → 冲突模式激活

## 记忆系统

- **长期记忆**：ChromaDB + all-MiniLM-L6-v2 向量嵌入，余弦相似度，权重检索
- **短期记忆**：JSON 会话文件（保留最近10次对话）
- **注入等级**：L1（3条记忆 ~600字）、L2（8条+会话 ~2500字）、L3（15条+完整状态 ~5000字）
- **权重公式**：`sqrt(访问次数+1) * exp(-0.1 * 天数)` — 被频繁访问的近期记忆权重更高

## 项目结构

```
src/
├── engine_server.py          # FastAPI 主入口（端口 18012）
├── core/
│   ├── models.py             # Pydantic 数据模型
│   ├── config.py             # 路径、常量、初始化
│   ├── persona.py            # 人格引擎（属性→人格映射融合）
│   ├── memory.py             # 记忆引擎（ChromaDB + JSON + 渐进注入）
│   ├── evolve.py             # 进化引擎（亲密度/升级/去AI味）
│   └── git_manager.py        # Git 回退管理
├── api/                       # 6个 FastAPI 路由
├── templates/                 # 6个 人设 JSON 模板
├── prompts/                   # 7个 等级 prompt 模板（Lv0~Lv6）
└── endings/                   # 结局描述库
skills/
├── SKILL.md                   # WorkBuddy Skill 声明
└── scripts/                   # 4个桥接脚本（聊天/状态/进化/记忆更新）
```

## 测试

```bash
python -m pytest tests/ -v
# 79个测试覆盖所有模块 + API集成 + 全链路
```

## 运行时数据

存储在 `~/.girlfriend-agent/`，首次启动自动初始化，git 管理支持回退：

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/             # 向量库（git 排除）
│   ├── session_memory/        # 短期记忆 JSON（git 排除）
│   ├── evolution_log/         # 进化日志
│   └── interaction_log/       # 互动计数
├── config/
│   ├── persona.json           # 当前人设
│   ├── relationship.json      # 关系状态 + 属性
│   └── settings.json          # 全局设置
├── .git/                      # 用于回退
```

## 许可证

MIT