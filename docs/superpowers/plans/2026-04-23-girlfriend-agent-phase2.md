# Phase 2 实施计划：LazyGraphRAG + 情景记忆

## 总览

Phase 2 在 Phase 1 基础上扩展记忆系统，新增4大功能模块：
1. **LazyGraphRAG 集成** — 基于图的情景记忆存储与推理
2. **情景记忆建图** — 从对话中提取实体/关系并构建知识图谱
3. **渐进式注入完善** — Level 1/2/3 完整实现（含图谱注入）
4. **记忆衰减与强化机制** — 艾宾浩斯曲线 + 强化规则

## 模块分工

### Agent A: LazyGraphRAG 集成 (graph_memory.py)
**核心文件**: `src/core/graph_memory.py` (新建)

功能：
- GraphMemoryEngine 类，管理情景记忆图谱
- 使用 NetworkX 构建内存图（节点=实体/事件，边=关系）
- 图持久化到 `~/.girlfriend-agent/data/graphrag_db/` (JSON序列化)
- 图遍历查询：BFS/DFS 从种子节点出发
- 关系推理：查找两个实体间的路径
- 时间线追踪：按时间排序的实体事件链
- 与 ChromaDB 协同：ChromaDB 存语义向量，GraphRAG 存关系结构

关键接口：
```python
class GraphMemoryEngine:
    def add_node(node_id, node_type, properties)  # 添加节点
    def add_edge(source, target, relation, properties)  # 添加边
    def search_graph(query, max_depth, max_nodes)  # 图遍历搜索
    def find_path(entity_a, entity_b, max_hops)  # 两实体间路径
    def get_timeline(entity_id)  # 时间线追踪
    def get_related(entity_id, max_depth)  # 关联实体
    def decay_graph_weights()  # 图节点/边权重衰减
    def reinforce_path(path_nodes)  # 路径强化
    def save_graph()  # 持久化
    def load_graph()  # 加载
    def get_stats()  # 图统计
```

数据模型（添加到 models.py）：
```python
class GraphNode(BaseModel):
    node_id: str
    node_type: str  # entity, event, topic, emotion
    label: str
    properties: dict = {}
    weight: float = 1.0
    created_date: str
    last_accessed: str
    access_count: int = 0

class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str  # caused, related_to, followed_by, about, felt_during
    properties: dict = {}
    weight: float = 1.0
    created_date: str

class GraphSearchResult(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    context_summary: str  # 路径描述文本
```

Config 扩展：
```python
# config.py 新增
@property
def graphrag_db_dir(self) -> str:
    return os.path.join(self.data_dir, "data", "graphrag_db")

GRAPH_NODE_TYPES = {"entity", "event", "topic", "emotion"}
GRAPH_EDGE_TYPES = {"caused", "related_to", "followed_by", "about", "felt_during"}
GRAPH_DEFAULT_MAX_DEPTH = 3
GRAPH_DEFAULT_MAX_NODES = 20
```

### Agent B: 情景记忆建图 (episodic_builder.py)
**核心文件**: `src/core/episodic_builder.py` (新建)

功能：
- EpisodicBuilder 类，从对话会话中提取结构化图数据
- 供调用方（Agent）使用的结构化接口：接收已提取的实体和关系
- 批量建图：每7次对话后自动触发
- 实体去重与合并：同名实体合并，更新属性
- 事件关联：将对话事件连接到已有实体
- 因果链构建：串联相关事件形成因果链

关键接口：
```python
class EpisodicBuilder:
    def extract_from_session(session)  # 从单个会话提取图数据
    def add_entity(entity_name, entity_type, properties)  # 添加实体
    def add_relation(source, target, relation_type)  # 添加关系
    def add_event(event_desc, related_entities, timestamp)  # 添加事件
    def build_causal_chain(event_ids)  # 构建因果链
    def merge_entities(entity_id_a, entity_id_b)  # 合并重复实体
    def batch_build(sessions)  # 批量建图
    def get_entity_context(entity_name)  # 获取实体完整上下文
```

数据模型（添加到 models.py）：
```python
class EntityExtraction(BaseModel):
    entity_name: str
    entity_type: str  # person, topic, activity, place, object
    properties: dict = {}

class RelationExtraction(BaseModel):
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float = 1.0

class EpisodicEvent(BaseModel):
    event_id: str
    description: str
    timestamp: str
    entities: list[str]  # 关联实体ID列表
    emotion: str = ""
    causal_links: list[str] = Field(default_factory=list)  # 因果关联事件ID
```

API 扩展（添加到 memory_router.py）：
```python
POST /memory/graph/add-entity     # 添加实体节点
POST /memory/graph/add-relation   # 添加关系边
POST /memory/graph/add-event      # 添加事件
POST /memory/graph/search         # 图搜索
POST /memory/graph/timeline       # 时间线查询
POST /memory/graph/batch-build    # 批量建图
GET  /memory/graph/stats          # 图统计
```

### Agent C: 渐进式注入完善 + 记忆衰减强化
**修改文件**: `src/core/memory.py`, `src/core/config.py`, `src/core/models.py`

功能：
- 完善 Level 1/2/3 注入逻辑（当前只有基础实现）
- Level 1: 3条记忆 + persona摘要 (~600字)
- Level 2: + 8条记忆 + 关系状态 + 近期情绪趋势 + 图谱关联摘要 (~2500字)
- Level 3: + 15条记忆 + 完整进化状态 + 图谱遍历结果 + 原始对话 (~5000字)
- 记忆衰减：基于艾宾浩斯曲线的精确衰减（而非当前简单的5%衰减）
- 记忆强化：检索命中强化 + 主动回忆强化 + 路径强化
- 情绪趋势计算：从session历史中提取情绪变化趋势
- 字数控制：按Level目标字数裁剪注入内容

关键改进：
```python
# memory.py 新增/修改方法
def compute_weight_precise(days, access_count)  # 精确艾宾浩斯衰减
def decay_all_weights_precise()  # 基于真实天数的衰减
def reinforce_memory(chunk_id, strength)  # 强化单条记忆
def reinforce_path(path_node_ids)  # 强化路径上所有节点
def compute_emotion_trend(sessions)  # 计算情绪趋势
def get_injection_context_v2(query, level, state, graph_engine)  # 完整注入
def estimate_char_count(context)  # 估算注入字数
def trim_to_budget(context, target_chars)  # 按字数裁剪
```

Config 新增：
```python
WEIGHT_DECAY_PRECISE = True  # 使用精确衰减
REINFORCE_STRENGTH_HIT = 0.1  # 检索命中强化值
REINFORCE_STRENGTH_RECALL = 0.2  # 主动回忆强化值
EMOTION_TREND_WINDOW = 10  # 情绪趋势窗口
INJECTION_LEVELS = {
    1: {"max_memories": 3, "approx_chars": 600, "include_graph": False},
    2: {"max_memories": 8, "approx_chars": 2500, "include_graph": True, "graph_depth": 1},
    3: {"max_memories": 15, "approx_chars": 5000, "include_graph": True, "graph_depth": 3},
}
```

## 验证标准

1. 单元测试：每个新模块 ≥ 80% 覆盖
2. 图操作：添加节点/边 → 搜索 → 路径查找 → 时间线
3. 建图：模拟7次对话 → 批量建图 → 实体去重 → 因果链
4. 注入：L1/L2/L3 各级别字数在目标 ±20% 内
5. 衰减：30天1次访问 → weight < 0.1；5次访问 → weight > 0.1
6. 集成：chat → memory + graph → 注入 → 字数验证
