# Phase 3 实施计划：自进化引擎完善

## 总览

Phase 3 在 Phase 1+2 基础上完善进化引擎，4大功能：
1. **自进化观察周期** — 模式感知（话题/情绪/隐性需求），情境驱动微调
2. **人格参数微调逻辑** — 连续递减、观察驱动调整、安全约束完善
3. **进化终点方向计算** — 56种结局组合，结局描述生成，进化进度追踪
4. **回退机制** — 进化回退（单个周期），安全恢复，自动试错

## 现有代码分析

### evolve.py 已有基础
- `calculate_evolution_adjustments` — 仅基于属性>30的阈值做固定delta
- `run_evolution_cycle` — 简单统计互动类型分布，无模式分析
- `calculate_evolution_direction` — 仅返回primary/secondary属性名
- `check_conflict_trigger` — 仅gap>=5触发conflict_mode
- **缺少**: 模式观察、情境驱动、连续递减、结局生成、回退

### git_manager.py 已有基础
- `checkout` — 部分检出 config/ 和 data/evolution_log/
- `revert_last` — git revert HEAD
- **缺少**: 进化专用回退（只回退persona.json+evolution_log）

### endings.json 仅4种结局
- 需要扩展到覆盖8×7=56种属性组合

## 模块分工

### Agent A: 自进化观察周期 + 人格参数微调

**修改文件**: `src/core/evolve.py`, `src/core/models.py`

#### 自进化观察周期
- 新增 `observe_patterns(sessions)` 方法：分析近7次对话的模式
  - 话题分布统计：最近聊什么最多
  - 情绪基调分析：正面/负面/中性比例
  - 隐性需求推断：反复出现的主题暗示什么
  - 互动类型分布强化（已有基础，需深化）

- 修改 `run_evolution_cycle`：集成模式观察
  - 当前：仅统计类型分布 → 固定微调
  - 改进：模式观察 → 情境驱动微调 → 试探 → 记录

#### 人格参数微调逻辑
- 新增情境驱动微调 `calculate_context_driven_adjustments(patterns, persona, state)`
  - 基于观察到的模式动态调整：
    - 用户压力大 → warmth+0.1, proactivity+0.05
    - 用户开心 → humor+0.1, gentleness+0.05
    - 用户少说话 → proactivity-0.1, shyness+0.05
    - 协作多 → curiosity+0.1, understanding+0.05

- 实现连续递减安全机制：
  - 跟踪每个维度的连续调整次数
  - 连续3次上调同一维度 → 第4次幅度减半
  - 超过5次 → 停止调整该维度

- 新增 `EvolutionState` 模型跟踪调整历史

#### models.py 新增
```python
class ObservationPattern(BaseModel):
    topic_distribution: dict[str, int] = {}  # topic -> count
    emotion_tone: str = "neutral"  # positive, negative, neutral, mixed
    hidden_needs: list[str] = []  # 推断的隐性需求
    interaction_distribution: dict[str, int] = {}
    summary: str = ""

class EvolutionState(BaseModel):
    consecutive_adjustments: dict[str, int] = {}  # dim_name -> consecutive count
    total_cycles: int = 0
    last_adjustments: dict[str, float] = {}
    evolution_progress: dict[str, float] = {}  # 每个属性的进化进度
```

### Agent B: 进化终点方向计算

**修改文件**: `src/core/evolve.py`, `src/endings/endings.json`

#### 56种结局定义
- 扩展 endings.json 覆盖所有8×7=56种属性组合
- 每种结局包含：id, name, primary_attr, secondary_attr, description, behavior_pattern

#### 进化方向增强
- 新增 `generate_evolution_ending(state)` — 根据primary+secondary生成结局描述
- 新增 `calculate_evolution_progress(state)` — 计算各方向的进化进度
- 新增 `get_ending_description(ending_id)` — 获取结局详情
- 修改 `calculate_evolution_direction` — 返回更丰富信息（含进度、结局描述）

#### API扩展
- `GET /evolve/direction` — 获取当前进化方向
- `GET /evolve/endings` — 获取所有可能结局
- `GET /evolve/progress` — 获取进化进度

### Agent C: 回退机制完善

**修改文件**: `src/core/evolve.py`, `src/core/git_manager.py`, `src/api/evolve_router.py`, `src/api/rollback_router.py`

#### 进化回退
- 新增 `revert_evolution(evolve_engine, git_manager, state)` — 回退最近一次进化
  - 恢复 persona.json 到上一版本
  - 恢复 evolution_log 到上一版本
  - 保留记忆数据不变
  - 重算 relationship state

- 新增 `revert_to_version(commit_hash)` — 回退到指定版本
  - git checkout 指定 commit 的 config/
  - 重新加载引擎状态

#### 自动试错
- 修改 `run_evolution_cycle`：记录"试探结果"
  - 新增 trial_result 状态：pass / negative / neutral
  - negative → 自动回退本次调整
  - neutral → 保持但标记观察

- 新增 `evaluate_trial_result(sessions_after, sessions_before)` — 评估试探结果
  - 比较进化前后的互动模式
  - 互动减少 → negative
  - 情绪变差 → negative
  - 互动增加/情绪变好 → pass

#### API扩展
- `POST /evolve/revert` — 回退最近一次进化
- `POST /evolve/revert-to` — 回退到指定版本
- 修改 `POST /evolve` — 返回试探结果

#### git_manager.py 改进
- 新增 `get_evolution_commits()` — 只获取进化相关的commit
- 新增 `revert_evolution_commit()` — 回退单个进化commit
- .gitignore 中添加 graphrag_db/（Phase 2新增的数据目录）
