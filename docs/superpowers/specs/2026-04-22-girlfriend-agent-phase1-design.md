---
title: girlfriend-agent Phase 1 设计文档
date: 2026-04-22
status: approved
---

# girlfriend-agent Phase 1 设计文档

## Context

根据《女友Agent产品设计文档 V2.0》，从零构建开源 AI 人格引擎的 Phase 1 核心引擎。项目定位为 WorkBuddy Skill/插件，模型无关（调用方提供推理），本地优先。环境已就绪：Python 3.12 + chromadb 1.5.8 + fastapi 0.136.0 + uvicorn 0.44.0 + sentence-transformers 5.4.1 + numpy 2.2.5 + pyyaml 6.0.3。

## 关键设计决策

| 决策项 | 选择 | 理由 |
|---|---|---|
| 架构模式 | 模块化单体 (FastAPI 本地服务) | Phase 1 需快速迭代，微服务过度设计 |
| 记忆提取 | 全部委托调用方 | 模型无关原则，引擎只提供写入接口 |
| 互动类型判定 | 调用方指定 | 最精准，引擎不做自动分类 |
| 实施范围 | 全量 Phase 1~5 按序推进 | 当前先做 Phase 1 核心引擎 |

---

## 1. 项目结构

### 代码仓库

```
girlfriend-agent/
├── requirements.txt
├── setup.py
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── engine_server.py          # FastAPI 主入口 (端口 18012)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py             # Pydantic 数据模型
│   │   ├── config.py             # 路径/常量/数据目录初始化
│   │   ├── persona.py            # 人格引擎
│   │   ├── memory.py             # 记忆引擎 (ChromaDB + 短期JSON)
│   │   ├── evolve.py             # 进化引擎
│   │   └── git_manager.py        # Git 回退管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat_router.py
│   │   ├── status_router.py
│   │   ├── evolve_router.py
│   │   ├── memory_router.py
│   │   ├── persona_router.py
│   │   └── rollback_router.py
│   ├── templates/                # 6预设人设 JSON + custom 骨架
│   ├── prompts/                  # lv0~lv6 prompt JSON
│   └── endings/                  # 结局描述库
├── skills/
│   ├── SKILL.md
│   └── scripts/                  # 4 Skill 脚本
└── tests/
```

### 运行时数据 (~/.girlfriend-agent/)

与代码仓库分离，首次启动自动初始化 + git init。

```
~/.girlfriend-agent/
├── data/
│   ├── chroma_db/                # 语义记忆向量库
│   ├── session_memory/           # 短期记忆 JSON
│   ├── evolution_log/            # 进化日志
│   └── interaction_log/          # 互动计数
├── config/
│   ├── persona.json              # 当前人设
│   ├── relationship.json         # 关系状态+属性+亲密度
│   ├── evolution.json            # 进化配置
│   ├── de_ai_dimensions.json     # 去AI味8维度评分
│   ├── attribute_points.json     # 属性加点记录
│   ├── settings.json             # 全局设置
│   └── level_prompts/            # 各等级 prompt 模板
├── templates/                    # 预设模板（本地缓存）
├── .git/
└── .gitignore                    # 排除 chroma_db/ 和 session_memory/
```

---

## 2. 核心数据模型 (models.py)

| 类 | 用途 | 关键字段 |
|---|---|---|
| PersonaConfig | 人设配置 | personality_base(PersonalityBase), speech_style(SpeechStyle), likes, dislikes |
| PersonalityBase | 人格7维度 | warmth, humor, proactivity, gentleness, stubbornness, curiosity, shyness (0.0~1.0) |
| SpeechStyle | 说话风格 | greeting, farewell, praise/comfort/jealousy/thinking_pattern |
| RelationshipState | 关系状态 | current_level, intimacy_points, attributes, de_ai_score, nickname, shared_jokes, rituals, conflict_mode |
| AttributePoints | 8属性加点 | care/understanding/expression/memory/humor/intuition/courage/sensitivity (0~100) |
| DeAiDimensions | 去AI味评分 | 8维度: structured_output, precision_level, emotion_naturalness, proactivity_randomness, chatter_ratio, mistake_rate, hesitation_rate, personal_depth |
| MemoryFragment | 单条记忆 | content, weight, memory_type, access_count, created_date, last_accessed |
| SessionMemory | 短期会话 | conversation_id, topics, emotion_summary, interaction_type, intimacy_gained |
| EvolutionLogEntry | 进化日志 | trigger, observation, adjustments, trial_result, internalized, timestamp |
| ChatRequest | API请求 | user_message, level(1/2/3), interaction_type |
| ChatResponse | API响应 | persona_prompt, memory_fragments, relationship_summary, de_ai_instructions |
| MemoryUpdateRequest | 记忆写入 | content, memory_type, metadata |

---

## 3. 人格模块 (persona.py)

```
PersonaEngine
├── load_persona()                    # 从 config/persona.json 加载
├── apply_template(template_id)       # 从 templates/ 复制到 config/
├── get_current_persona(state)        # 基础人格 + 属性映射融合
├── get_level_prompt(level, state)    # 加载 lv{N}.json，填充 {user_name}/{gf_name}/{nickname}
├── get_de_ai_instructions(state)     # 8维度 → 行为规则文本
└── update_persona_field(field, val)  # 单字段更新
```

**属性→人格映射 (ATTR_TO_PERSONALITY_MAP)**:

| 属性 | 影响维度 |
|---|---|
| care | warmth+0.8, gentleness+0.2 |
| understanding | proactivity+0.3, shyness-0.1 |
| expression | humor+0.4, proactivity+0.3, shyness-0.3 |
| memory | curiosity+0.5, proactivity+0.5 |
| humor | humor+1.0 |
| intuition | proactivity+0.6, curiosity+0.4 |
| courage | stubbornness+0.5, proactivity+0.3, shyness-0.2 |
| sensitivity | warmth+0.4, shyness+0.3, gentleness+0.3 |

融合公式：`current_dim = clamp(base_dim + Σ(attr_value * mapping_weight / 100), 0.0, 1.0)`

---

## 4. 记忆模块 (memory.py)

```
MemoryEngine
├── [长期 - ChromaDB]
│   ├── store_memory(content, type, metadata)   # 写入，自动计算初始weight
│   ├── search_memories(query, n, level)         # 语义搜索 + weight过滤
│   ├── update_memory_access(chunk_id)           # 命中后更新access_count + weight
│   └── decay_all_weights()                      # 批量衰减
│
├── [短期 - JSON]
│   ├── save_session(session)                    # 写 session_memory/{conv_id}.json
│   ├── load_recent_sessions(count=10)           # 按时间倒序
│   └── cleanup_old_sessions(keep=10)            # 保留最近10次
│
├── [渐进式注入]
│   └── get_injection_context(query, level, state)
│       ├── Level 1: 3条记忆 + persona摘要 (~600字)
│       ├── Level 2: 8条记忆 + 关系状态 + 情绪趋势 (~2500字)
│       └── Level 3: 15条记忆 + 完整进化状态 (~5000字)
│
└── compute_weight(days, access_count)            # sqrt(n) * exp(-0.1*d)
```

**关键决策**:
- 记忆提取全部委托调用方，引擎只提供 `store_memory` 接收已提取的事实
- ChromaDB weight 存为字符串避免 float 精度问题
- embedding 使用 all-MiniLM-L6-v2 (384维, 本地运行)
- search 先取 n_results*2 再按 weight 在 Python 层过滤

---

## 5. 进化模块 (evolve.py)

```
EvolveEngine
├── update_intimacy(interaction_type, state)     # 调用方指定类型
├── check_level_up(state)                        # 检查升级阈值
├── process_level_up(new_level, state)            # 升级 + 奖励3点
├── add_interaction_attributes(type, state)       # 按类型加属性
├── distribute_bonus_points(state)                # auto/manual
├── update_de_ai_score(state)                     # 等级+属性→8维度
├── get_de_ai_behavior_rules(de_ai)               # 维度→行为规则
├── run_evolution_cycle(sessions, state)          # 7次对话→微调→日志→commit
├── check_conflict_trigger(state)                 # >5次空档→冲突
└── calculate_evolution_direction(state)           # 主+副属性→结局
```

**互动→亲密度/属性映射** (调用方指定 interaction_type):

| 类型 | 亲密度 | 属性加点 |
|---|---|---|
| daily_chat | +1 | 均分+0.5 |
| deep_conversation | +3 | 关心+1, 理解+1, 细腻+1 |
| collaborative_task | +5 | 理解+1, 勇气+1, 记忆+1 |
| emotion_companion | +4 | 关心+1.5, 细腻+1, 表达+0.5 |
| light_chat | +1 | 幽默+1, 表达+0.5, 勇气+0.5 |

**进化微调安全机制**:
- 单次 ≤ 10% 相对变化
- 绝对值 clamp 0.0~1.0
- 连续3次上调同一维度 → 第4次幅度减半

---

## 6. API 服务

FastAPI 本地服务，端口 18012。模块化单体架构，三个引擎在同一进程中共享内存。

| 端点 | 方法 | 请求体 | 核心调用链 |
|---|---|---|---|
| `/chat` | POST | `{user_message, level, interaction_type}` | persona.get_level_prompt + get_de_ai_instructions + memory.get_injection_context + evolve.update_intimacy |
| `/status` | GET | - | load relationship.json |
| `/evolve` | POST | - | evolve.run_evolution_cycle + apply_adjustments + git.commit |
| `/memory/update` | POST | `{content, memory_type, metadata}` | memory.store_memory |
| `/memory/search` | POST | `{query, level}` | memory.search + update_access |
| `/persona` | GET | - | persona.load_persona |
| `/persona/update` | POST | `{field, value}` | persona.update_field + git.commit |
| `/persona/apply-template` | POST | `{template_id}` | persona.apply_template + git.commit |
| `/rollback` | POST | `{commit_hash}` | git.checkout(config+evolution_log) + reload engines |
| `/health` | GET | - | `{status, embedding_loaded}` |

---

## 7. Skill 桥接层

**SKILL.md** — WorkBuddy Skill 声明，触发词：聊天/关心/安慰/撒娇/陪伴/女友/进化/养成/记忆/亲密度

**4个脚本** (薄壳: 确保服务运行 → HTTP调用 → 格式化输出):

- `chat.py` → POST /chat，输出人格prompt+记忆+去AI味指令
- `status.py` → GET /status，输出关系状态表格
- `evolve.py` → POST /evolve，输出进化调整结果
- `update.py` → POST /memory/update，输出写入确认

`ensure_server_running()`: socket检测18012 → 未运行则Popen后台启动(Windows CREATE_NO_WINDOW) → 轮询/health最多10秒

---

## 8. Git 回退管理 (git_manager.py)

```
GitManager
├── init_repo()          # git init + .gitignore + initial commit "Lv0"
├── commit(message)      # git add config/ data/evolution_log/ + commit
├── log()                # git log --oneline → [{hash, message, date}]
├── checkout(hash)       # git checkout hash -- config/ data/evolution_log/（部分检出）
└── revert_last()        # git revert HEAD
```

**关键**: checkout 只回退 config/ 和 data/evolution_log/，不动 chroma_db/ 和 session_memory/。.gitignore 排除这两目录。

---

## 9. 核心数据流

```
用户消息 → Agent识别Skill → chat.py(message, level, type)
→ HTTP POST /chat
→ [并行] persona prompt + de_ai指令 + 记忆注入 + 亲密度更新
→ ChatResponse 返回
→ chat.py 格式化输出 → Agent注入上下文 → 大模型人格化回答
→ [后台] Agent主动调用 /memory/update 写入关键事实
```

进化周期：每7次对话 → /evolve → 分析→微调→日志→git commit

升级：intimacy达阈值 → process_level_up → 属性奖励+去AI味调整+git commit

回退：/rollback → git checkout → 重新加载引擎状态

---

## 10. Phase 1 开发步骤

### Iteration 1: 基础骨架 (Day 1-2)
- 项目目录 + requirements.txt + .gitignore + setup.py
- models.py (所有Pydantic模型)
- config.py (路径/常量/初始化)
- 6模板JSON + 7等级prompt JSON + 结局库骨架
- git init

### Iteration 2: 人格模块 (Day 3-4)
- PersonaEngine 全部方法
- ATTR_TO_PERSONALITY_MAP 映射
- test_persona.py

### Iteration 3: 记忆模块 (Day 5-7)
- MemoryEngine 全部方法
- ChromaDB集成 + embedding
- 渐进式注入 L1/L2/L3
- test_memory.py

### Iteration 4: 进化模块 (Day 8-10)
- EvolveEngine 全部方法
- GitManager
- test_evolve.py

### Iteration 5: FastAPI + Skill + 集成 (Day 11-14)
- engine_server.py + 6个API路由
- 4 Skill脚本 + SKILL.md
- test_api.py + 全链路测试
- README.md

---

## 11. 验证方案

1. 单元测试: pytest 覆盖每个模块核心函数
2. API测试: httpx/TestClient 测试所有端点
3. 全链路: chat.py → engine → 输出格式/字数验证
4. 进化: 模拟7次对话 → evolve → persona.json微调 + git commit
5. 回退: rollback到前一版本 → config恢复 + 记忆保留
6. ChromaDB: store → search → 语义匹配 + weight衰减