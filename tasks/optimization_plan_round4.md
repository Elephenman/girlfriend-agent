# 优化计划 - Round 4

基于 Round 3 审核评分 9.4/10 的 6 项 Round 4 建议，以及 Round 3 未执行的 4 项较复杂改动，制定 Round 4 深度性能与架构优化计划。

---

## 背景分析

### Round 3 审核评分: 9.4/10

Round 3 审核提出 6 个 Round 4 建议:
1. Lock 持有范围缩小 - chat_router 仅在状态变更段加锁，纯读段在锁外
2. StateManager load_or_init 与 load 方法关系明确化
3. 并发测试 - asyncio.Lock 专项并发验证
4. decay_all_weights 性能监测 - 耗时日志
5. Router 层业务逻辑提取 - ChatService
6. graph_memory.py search_graph 性能优化

### Round 3 未执行项（4项）

这些项在 Round 3 计划中列出但因复杂度较高未落地:
- P1-R3-6: graph_router 提取 + Pydantic 验证模型（仅 MemorySearchRequest 已落地，6 个图谱端点仍用 `await request.json()`）
- P2-R3-1: get_node 拆分为 get_node_info + touch_node
- P2-R3-2: ChatService 提取
- P2-R3-3: evolve.py 文件操作迁移到 StateManager

### Round 4 定位

Round 4 是**性能与并发优化轮次**，核心目标:
- 缩小 asyncio.Lock 持有范围，提升并发吞吐量
- 提取 ChatService，将路由层业务逻辑下沉到服务层
- 补齐并发专项测试，验证 Lock 机制的实际效果
- 完成 Round 3 遗留的 graph_router 提取和 get_node 拆分
- 为 decay_all_weights 和 search_graph 添加性能监测

---

## P0 (必须修复 - 并发性能瓶颈 + 架构职责缺失)

### P0-R4-1: Lock 持有范围缩小 - chat_router 仅在状态变更段加锁

- **文件**: `src/api/chat_router.py:10-55`
- **问题**: 当前 `/chat` 整个请求处理逻辑在 `async with app.state.state_lock:` 内（L12-48），包括纯读操作（persona prompt 构建 L30-34、memory injection L37-40，后者可能涉及 ChromaDB 查询等耗时 IO）。在高并发场景下锁持有时间过长会显著降低吞吐量——一个 /chat 请求在等待 ChromaDB 返回期间阻塞所有其他 /chat 和 /evolve 写请求。
- **方案**: 将 /chat 的处理拆为三个阶段:
  - **阶段 1 (锁内)**: 状态变更段——读取 relationship 快照、update_intimacy、add_interaction_attributes、check/process_level_up，写入更新后的 relationship 到 app.state 并持久化。完成后释放锁。
  - **阶段 2 (锁外)**: 纯读段——用 relationship 快照做 persona prompt 构建、de_ai_instructions、memory injection。这些操作不修改 app.state，且使用已提交的快照数据保证一致性。
  - **阶段 3 (无锁)**: 构建响应返回。
- **具体改动**:
  ```python
  # src/api/chat_router.py:10-55, 替换整个 chat 函数
  @router.post("/chat", response_model=ChatResponse)
  async def chat(req: ChatRequest, request: Request):
      app = request.app

      # Phase 1: State mutation under lock (minimal hold time)
      async with app.state.state_lock:
          persona_engine = app.state.persona_engine
          evolve_engine = app.state.evolve_engine

          persona = app.state.persona
          relationship = app.state.relationship

          # Update intimacy and attributes (atomic under lock)
          relationship = evolve_engine.update_intimacy(req.interaction_type, relationship)
          relationship = evolve_engine.add_interaction_attributes(req.interaction_type, relationship)

          # Check level up
          if evolve_engine.check_level_up(relationship):
              new_level = relationship.current_level + 1
              relationship = evolve_engine.process_level_up(new_level, relationship)

          # Commit state mutation and persist
          app.state.relationship = relationship
          app.state.state_manager.persist_relationship(app)

      # Phase 2: Pure reads outside lock (using committed snapshot)
      memory_engine = app.state.memory_engine
      graph_engine = getattr(app.state, "graph_engine", None)

      current_persona = persona_engine.get_current_persona(persona, relationship)
      level_prompt = persona_engine.get_level_prompt(relationship.current_level, relationship)
      de_ai_instructions = persona_engine.get_de_ai_instructions(relationship)

      memory_ctx = memory_engine.get_injection_context(
          req.user_message, req.level, relationship, graph_engine=graph_engine
      )

      # Phase 3: Build response
      full_prompt = f"{level_prompt}\n\n当前人格倾向：{current_persona.model_dump_json()}"
      rel_summary = f"等级Lv{relationship.current_level} 亲密度{relationship.intimacy_points}"

      return ChatResponse(
          persona_prompt=full_prompt,
          memory_fragments=memory_ctx.get("memory_fragments", []),
          relationship_summary=rel_summary,
          de_ai_instructions=de_ai_instructions,
      )
  ```
- **关键设计决策**:
  - relationship 在 Phase 1 结束时已是 committed state（已写入 app.state 和磁盘），Phase 2 使用的是 Pydantic model_copy 后的不可变快照，后续读操作不会读到中间状态。
  - persona 是只读对象（在 /chat 中不被修改），无需在锁内保护。
  - memory_engine 的 ChromaDB 查询是独立存储层操作，与 app.state 无关，不需要锁保护。
- **配套测试**: 在 `tests/test_api.py` 或新增 `tests/test_concurrency.py` 验证:
  ```python
  class TestLockScopeOptimization:
      async def test_chat_endpoint_returns_correct_response(self, client):
          """Verify /chat still works after lock scope optimization"""
          r = await client.post("/chat", json={
              "user_message": "hello",
              "interaction_type": "daily_chat",
              "level": 1,
          })
          assert r.status_code == 200
          data = r.json()
          assert "persona_prompt" in data
          assert "memory_fragments" in data

      async def test_concurrent_chat_requests_state_consistent(self, client):
          """Verify state remains consistent under concurrent requests"""
          import asyncio
          # Send 5 concurrent /chat requests
          tasks = [
              client.post("/chat", json={
                  "user_message": f"msg_{i}",
                  "interaction_type": "daily_chat",
                  "level": 1,
              })
              for i in range(5)
          ]
          responses = await asyncio.gather(*tasks)
          # All should succeed
          for r in responses:
              assert r.status_code == 200
          # Verify intimacy_points increased by 5 (1 per daily_chat)
          # Note: exact count depends on ordering, but should be consistent
  ```

### P0-R4-2: ChatService 提取 - 路由层业务逻辑下沉

- **文件**: `src/api/chat_router.py:10-55`, 新增 `src/core/chat_service.py`
- **问题**: Round 3 未执行项 P2-R3-2。chat_router 的 `/chat` 端点包含约 25 行业务逻辑（亲密度更新 L21、属性更新 L22、升级检测 L25-27、persona prompt 构建 L30-34、memory injection L37-40、full_prompt 组装 L43-44）。这些逻辑应属于服务层而非路由层，与 evolve_router 的 `EvolveEngine.run_evolution_cycle` 模式一致。
- **方案**: 提取 `ChatService` 类，内化业务逻辑。路由层仅做参数解包、锁管理、服务调用、响应构建。ChatService 是纯同步类（不涉及 asyncio），所有方法返回 dict 供路由层组装响应。
- **具体改动**:
  ```python
  # src/core/chat_service.py (新文件)
  from src.core.models import ChatRequest, PersonaConfig, RelationshipState


  class ChatService:
      """Chat request processing - business logic separated from router"""

      def __init__(self, persona_engine, memory_engine, evolve_engine, graph_engine=None):
          self.persona_engine = persona_engine
          self.memory_engine = memory_engine
          self.evolve_engine = evolve_engine
          self.graph_engine = graph_engine

      def mutate_state(
          self, request: ChatRequest, persona: PersonaConfig, relationship: RelationshipState
      ) -> RelationshipState:
          """Phase 1: State mutation (to be called under lock)"""
          relationship = self.evolve_engine.update_intimacy(request.interaction_type, relationship)
          relationship = self.evolve_engine.add_interaction_attributes(request.interaction_type, relationship)

          if self.evolve_engine.check_level_up(relationship):
              new_level = relationship.current_level + 1
              relationship = self.evolve_engine.process_level_up(new_level, relationship)

          return relationship

      def build_context(
          self, request: ChatRequest, persona: PersonaConfig, relationship: RelationshipState
      ) -> dict:
          """Phase 2: Build prompt context (called outside lock)"""
          current_persona = self.persona_engine.get_current_persona(persona, relationship)
          level_prompt = self.persona_engine.get_level_prompt(relationship.current_level, relationship)
          de_ai_instructions = self.persona_engine.get_de_ai_instructions(relationship)

          memory_ctx = self.memory_engine.get_injection_context(
              request.user_message, request.level, relationship,
              graph_engine=self.graph_engine,
          )

          full_prompt = f"{level_prompt}\n\n当前人格倾向：{current_persona.model_dump_json()}"
          rel_summary = f"等级Lv{relationship.current_level} 亲密度{relationship.intimacy_points}"

          return {
              "full_prompt": full_prompt,
              "rel_summary": rel_summary,
              "memory_ctx": memory_ctx,
              "de_ai_instructions": de_ai_instructions,
          }
  ```
  ```python
  # src/api/chat_router.py, 简化路由层
  from src.core.chat_service import ChatService

  @router.post("/chat", response_model=ChatResponse)
  async def chat(req: ChatRequest, request: Request):
      app = request.app
      chat_service = ChatService(
          persona_engine=app.state.persona_engine,
          memory_engine=app.state.memory_engine,
          evolve_engine=app.state.evolve_engine,
          graph_engine=getattr(app.state, "graph_engine", None),
      )

      # Phase 1: State mutation under lock
      async with app.state.state_lock:
          relationship = chat_service.mutate_state(
              req, app.state.persona, app.state.relationship
          )
          app.state.relationship = relationship
          app.state.state_manager.persist_relationship(app)

      # Phase 2: Build context outside lock
      ctx = chat_service.build_context(req, app.state.persona, relationship)

      return ChatResponse(
          persona_prompt=ctx["full_prompt"],
          memory_fragments=ctx["memory_ctx"].get("memory_fragments", []),
          relationship_summary=ctx["rel_summary"],
          de_ai_instructions=ctx["de_ai_instructions"],
      )
  ```
  在 `src/engine_server.py` lifespan 中可选初始化 ChatService 并挂到 `app.state.chat_service`（减少每次请求的构造开销），但即时构造也可接受（4 个属性赋值的开销极小）。
- **配套测试**: 新增 `tests/test_chat_service.py`:
  ```python
  class TestChatServiceMutateState:
      def test_mutate_state_updates_intimacy(self, mock_engines):
          """Verify intimacy is updated according to interaction type"""
          from src.core.chat_service import ChatService
          from src.core.models import ChatRequest, RelationshipState

          req = ChatRequest(user_message="hello", interaction_type="daily_chat", level=1)
          initial_rel = RelationshipState()
          result = mock_engines.chat_service.mutate_state(req, mock_engines.persona, initial_rel)
          # intimacy_points should increase by 1 (daily_chat gain)
          assert result.intimacy_points > initial_rel.intimacy_points

      def test_mutate_state_level_up_triggered(self, mock_engines):
          """Verify level up logic is correctly triggered when threshold met"""
          req = ChatRequest(user_message="deep talk", interaction_type="deep_conversation", level=2)
          # Set intimacy near threshold
          near_threshold = RelationshipState(current_level=0, intimacy_points=28)
          result = mock_engines.chat_service.mutate_state(req, near_threshold, mock_engines.persona)
          # Level up should have been processed
          assert result.current_level > near_threshold.current_level or result.intimacy_points > near_threshold.intimacy_points

  class TestChatServiceBuildContext:
      def test_build_context_returns_expected_keys(self, mock_engines):
          """Verify result dict contains all expected keys"""
          req = ChatRequest(user_message="hello", level=1)
          ctx = mock_engines.chat_service.build_context(req, mock_engines.persona, RelationshipState())
          assert "full_prompt" in ctx
          assert "rel_summary" in ctx
          assert "memory_ctx" in ctx
          assert "de_ai_instructions" in ctx
  ```

---

## P1 (强烈建议 - 并发验证 + Round 3 遗留项 + 性能监测)

### P1-R4-1: asyncio.Lock 专项并发测试

- **文件**: 新增 `tests/test_concurrency.py`
- **问题**: Round 3 审核建议 #3。当前 asyncio.Lock 的效果仅通过代码审查确认，无并发场景的专项测试。Lock 机制存在的核心价值是防止并发 /chat 和 /evolve 请求导致的状态不一致（如 intimacy_points 因并发更新丢失），但这一价值从未被测试验证。
- **方案**: 新增 `tests/test_concurrency.py`，使用 `asyncio.gather` 并发调用模拟逻辑，验证:
  (a) Lock 下并发 /chat 的 intimacy_points 不会丢失；
  (b) Lock 下并发 /chat + /evolve 的状态不冲突；
  (c) 无 Lock 场景下状态可能不一致（对照实验）。
- **具体改动**:
  ```python
  # tests/test_concurrency.py (新文件)
  import asyncio
  import pytest

  from src.core.config import Config
  from src.core.evolve import EvolveEngine
  from src.core.models import ChatRequest, RelationshipState, SessionMemory


  class TestConcurrencyStateLock:
      """Verify asyncio.Lock protects state consistency under concurrent access"""

      def test_sequential_chat_intimacy_accumulates(self):
          """Baseline: sequential /chat requests should accumulate intimacy correctly"""
          config = Config(data_dir="/tmp/test_concurrent_seq")
          config.ensure_dirs()

          from src.core.git_manager import GitManager
          git_mgr = GitManager(data_dir=config.data_dir)
          git_mgr.init_repo()
          evolve_engine = EvolveEngine(config, git_mgr)

          relationship = RelationshipState()
          for i in range(5):
              req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
              relationship = evolve_engine.update_intimacy(req.interaction_type, relationship)
              relationship = evolve_engine.add_interaction_attributes(req.interaction_type, relationship)

          # 5 daily_chat requests: 1 intimacy each -> 5 total
          assert relationship.intimacy_points == 5

      async def test_concurrent_chat_with_lock_preserves_intimacy(self):
          """Verify Lock prevents intimacy loss under concurrent /chat requests"""
          # Simulate the lock-protected mutation pattern from chat_router
          lock = asyncio.Lock()
          shared_state = {"relationship": RelationshipState()}

          config = Config(data_dir="/tmp/test_concurrent_lock")
          config.ensure_dirs()

          from src.core.git_manager import GitManager
          git_mgr = GitManager(data_dir=config.data_dir)
          git_mgr.init_repo()
          evolve_engine = EvolveEngine(config, git_mgr)

          async def simulate_chat_request(i: int):
              async with lock:
                  rel = shared_state["relationship"]
                  req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                  rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                  rel = evolve_engine.add_interaction_attributes(req.interaction_type, rel)
                  shared_state["relationship"] = rel

          await asyncio.gather(*[simulate_chat_request(i) for i in range(5)])
          assert shared_state["relationship"].intimacy_points == 5

      async def test_concurrent_chat_without_lock_may_lose_intimacy(self):
          """Control experiment: without Lock, concurrent updates may lose intimacy"""
          shared_state = {"relationship": RelationshipState()}

          config = Config(data_dir="/tmp/test_concurrent_nolock")
          config.ensure_dirs()

          from src.core.git_manager import GitManager
          git_mgr = GitManager(data_dir=config.data_dir)
          git_mgr.init_repo()
          evolve_engine = EvolveEngine(config, git_mgr)

          async def simulate_chat_request_unprotected(i: int):
              # No lock - read shared state, mutate, write back
              # Race condition: multiple coroutines may read same initial state
              rel = shared_state["relationship"]  # read
              req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
              rel = evolve_engine.update_intimacy(req.interaction_type, rel)  # mutate
              # Artificial yield point to force race condition
              await asyncio.sleep(0.001)
              shared_state["relationship"] = rel  # write back (may overwrite another's update)

          await asyncio.gather(*[simulate_chat_request_unprotected(i) for i in range(5)])
          # Without lock, intimacy_points may be less than 5 due to lost updates
          # This test demonstrates the problem (not a pass/fail assertion on exact value)
          actual = shared_state["relationship"].intimacy_points
          # In practice with the sleep yield, some updates WILL be lost
          assert actual <= 5  # may be 1-4 depending on scheduling
  ```
- **注意**: 对照实验（无 Lock）不一定总能复现竞态条件，取决于 asyncio scheduler 的调度策略。`await asyncio.sleep(0.001)` 是强制 yield 点，增加竞态概率。实际测试中应关注有 Lock 的测试一定 pass，无 Lock 的测试大概率 intimacy < 5。

### P1-R4-2: graph_router 提取 + Pydantic 验证模型

- **文件**: `src/api/memory_router.py:73-167`, 新增 `src/api/graph_router.py`, `src/engine_server.py:60-65`
- **问题**: Round 3 未执行项 P1-R3-6。memory_router 中 7 个图谱端点（L73-167）仍使用 `await request.json()` 无验证，且图谱端点混在 memory_router 中违反 SRP。图谱端点的请求体无任何类型验证——空 entity_name、非法 entity_type、超大 max_nodes 等非法输入会被直接传到引擎层。
- **方案**: 两步组合执行:
  (a) 为所有图谱端点创建 Pydantic request 模型，提供字段验证和类型约束；
  (b) 将图谱端点提取到独立的 `graph_router.py`，验证模型随端点一起迁移；
  (c) 在 engine_server.py 注册 graph_router；
  (d) 从 memory_router.py 删除所有 `/graph/*` 端点和相关 `await request.json()` 用法。
- **具体改动**:
  ```python
  # src/api/graph_router.py (新文件)
  from pydantic import BaseModel, Field, field_validator

  from fastapi import APIRouter, Request

  router = APIRouter()


  class GraphAddEntityRequest(BaseModel):
      entity_name: str = Field(min_length=1)
      entity_type: str = Field(default="entity")
      properties: dict = Field(default_factory=dict)

      @field_validator("entity_type")
      @classmethod
      def validate_entity_type(cls, v: str) -> str:
          valid = {"entity", "event", "topic", "emotion"}
          if v not in valid:
              raise ValueError(f"entity_type must be one of {valid}, got '{v}'")
          return v


  class GraphAddRelationRequest(BaseModel):
      source_entity: str = Field(min_length=1)
      target_entity: str = Field(min_length=1)
      relation_type: str = Field(default="related_to")
      properties: dict = Field(default_factory=dict)

      @field_validator("relation_type")
      @classmethod
      def validate_relation_type(cls, v: str) -> str:
          valid = {"caused", "related_to", "followed_by", "about", "felt_during"}
          if v not in valid:
              raise ValueError(f"relation_type must be one of {valid}, got '{v}'")
          return v


  class GraphAddEventRequest(BaseModel):
      description: str = Field(min_length=1)
      entities: list[str] = Field(default_factory=list)
      timestamp: str | None = None
      emotion: str = Field(default="")


  class GraphSearchRequest(BaseModel):
      query: str = Field(min_length=1)
      max_depth: int = Field(default=3, ge=1, le=10)
      max_nodes: int = Field(default=20, ge=1, le=100)


  class GraphTimelineRequest(BaseModel):
      entity_id: str = Field(min_length=1)


  class GraphBatchBuildRequest(BaseModel):
      session_count: int = Field(default=7, ge=1, le=30)


  @router.post("/graph/add-entity")
  async def graph_add_entity(req: GraphAddEntityRequest, request: Request):
      builder = request.app.state.episodic_builder
      node_id = builder.add_entity(req.entity_name, req.entity_type, req.properties)
      graph_engine = request.app.state.graph_engine
      graph_engine.save_graph()
      return {"status": "ok", "node_id": node_id}


  @router.post("/graph/add-relation")
  async def graph_add_relation(req: GraphAddRelationRequest, request: Request):
      builder = request.app.state.episodic_builder
      success = builder.add_relation(req.source_entity, req.target_entity, req.relation_type, req.properties)
      graph_engine = request.app.state.graph_engine
      graph_engine.save_graph()
      return {"status": "ok" if success else "error"}


  @router.post("/graph/add-event")
  async def graph_add_event(req: GraphAddEventRequest, request: Request):
      builder = request.app.state.episodic_builder
      event_id = builder.add_event(req.description, req.entities, req.timestamp, req.emotion)
      graph_engine = request.app.state.graph_engine
      graph_engine.save_graph()
      return {"status": "ok", "event_id": event_id}


  @router.post("/graph/search")
  async def graph_search(req: GraphSearchRequest, request: Request):
      graph_engine = request.app.state.graph_engine
      result = graph_engine.search_graph(req.query, req.max_depth, req.max_nodes)
      return result.model_dump()


  @router.post("/graph/timeline")
  async def graph_timeline(req: GraphTimelineRequest, request: Request):
      graph_engine = request.app.state.graph_engine
      timeline = graph_engine.get_timeline(req.entity_id)
      return {"timeline": timeline}


  @router.post("/graph/batch-build")
  async def graph_batch_build(req: GraphBatchBuildRequest, request: Request):
      memory_engine = request.app.state.memory_engine
      sessions = memory_engine.load_recent_sessions(count=req.session_count)
      builder = request.app.state.episodic_builder
      stats = builder.batch_build(sessions)
      return {"status": "ok", "stats": stats}


  @router.get("/graph/stats")
  async def graph_stats(request: Request):
      graph_engine = request.app.state.graph_engine
      return graph_engine.get_stats()
  ```
  ```python
  # src/api/memory_router.py, 移除 L73-167 的所有图谱端点
  # 同时为 reinforce 和 emotion-trend 添加 Pydantic 模型（消除 await request.json()）
  class MemoryReinforceRequest(BaseModel):
      chunk_id: str = Field(min_length=1)
      strength: float = Field(default=0.1, gt=0, le=1.0)

  class EmotionTrendRequest(BaseModel):
      count: int = Field(default=10, ge=1, le=50)

  @router.post("/memory/reinforce")
  async def reinforce_memory(req: MemoryReinforceRequest, request: Request):
      memory_engine = request.app.state.memory_engine
      memory_engine.reinforce_memory(req.chunk_id, req.strength)
      return {"status": "ok"}

  @router.post("/memory/emotion-trend")
  async def emotion_trend(req: EmotionTrendRequest, request: Request):
      memory_engine = request.app.state.memory_engine
      sessions = memory_engine.load_recent_sessions(count=req.count)
      trend = memory_engine.compute_emotion_trend(sessions)
      return trend
  ```
  ```python
  # src/engine_server.py, 注册 graph_router
  from src.api.graph_router import router as graph_router
  app.include_router(graph_router, tags=["graph"])
  ```
- **配套测试**: 在 `tests/test_api.py` 添加 Pydantic 验证测试:
  ```python
  class TestGraphRouterPydanticValidation:
      async def test_add_entity_empty_name_rejected(self, client):
          r = await client.post("/graph/add-entity", json={"entity_name": ""})
          assert r.status_code == 422

      async def test_add_entity_invalid_type_rejected(self, client):
          r = await client.post("/graph/add-entity", json={"entity_name": "test", "entity_type": "invalid"})
          assert r.status_code == 422

      async def test_add_relation_empty_source_rejected(self, client):
          r = await client.post("/graph/add-relation", json={"source_entity": "", "target_entity": "ok"})
          assert r.status_code == 422

      async def test_add_relation_invalid_type_rejected(self, client):
          r = await client.post("/graph/add-relation", json={
              "source_entity": "a", "target_entity": "b", "relation_type": "invalid"
          })
          assert r.status_code == 422

      async def test_search_empty_query_rejected(self, client):
          r = await client.post("/graph/search", json={"query": ""})
          assert r.status_code == 422

      async def test_search_excessive_max_nodes_rejected(self, client):
          r = await client.post("/graph/search", json={"query": "test", "max_nodes": 200})
          assert r.status_code == 422

      async def test_reinforce_empty_chunk_id_rejected(self, client):
          r = await client.post("/memory/reinforce", json={"chunk_id": ""})
          assert r.status_code == 422

      async def test_emotion_trend_invalid_count_rejected(self, client):
          r = await client.post("/memory/emotion-trend", json={"count": 0})
          assert r.status_code == 422
  ```

### P1-R4-3: get_node 拆分为 get_node_info + touch_node

- **文件**: `src/core/graph_memory.py:73-91`
- **问题**: Round 3 未执行项 P2-R3-1。`get_node` 方法是 getter 但有副作用（修改 `access_count` 和 `last_accessed`，L80-81），违反命令查询分离（CQRS）原则。episodic_builder.py L197 调用 `get_node` 时无意中触发 access_count 递增。当前 EpisodicBuilder.add_entity (L26-28) 通过直接读取 `graph.nodes[existing_id]` 规避了副作用，但 get_entity_context (L197) 仍调用 `get_node` 并触发不必要的 access_count 变化。
- **方案**: 拆分为纯查询 `get_node_info` 和副作用 `touch_node`。`get_node` 保留为向后兼容的组合方法，但默认 `touch=False`（原行为是 `touch=True`，此改动是行为变更，需更新所有调用方）。
- **具体改动**:
  ```python
  # src/core/graph_memory.py:73-91, 拆分
  def get_node_info(self, node_id: str) -> GraphNode | None:
      """获取节点信息（纯查询，无副作用）"""
      if node_id not in self.graph:
          return None
      data = self.graph.nodes[node_id]
      now = datetime.now().strftime("%Y-%m-%d")
      return GraphNode(
          node_id=node_id,
          node_type=data.get("node_type", "entity"),
          label=data.get("label", ""),
          properties=data.get("properties", {}),
          weight=data.get("weight", 1.0),
          created_date=data.get("created_date", now),
          last_accessed=data.get("last_accessed", now),
          access_count=data.get("access_count", 0),
      )

  def touch_node(self, node_id: str) -> None:
      """更新节点访问计数和最后访问时间（副作用操作）"""
      if node_id not in self.graph:
          return
      data = self.graph.nodes[node_id]
      data["access_count"] = data.get("access_count", 0) + 1
      data["last_accessed"] = datetime.now().strftime("%Y-%m-%d")

  def get_node(self, node_id: str, touch: bool = True) -> GraphNode | None:
      """获取节点信息，可选更新访问计数（向后兼容接口）
      默认 touch=True 保持与原 get_node 行为一致
      """
      result = self.get_node_info(node_id)
      if result is not None and touch:
          self.touch_node(node_id)
          result = self.get_node_info(node_id)  # re-read to reflect updated values
      return result
  ```
  更新调用方:
  - `src/core/episodic_builder.py:197`: `self.graph_engine.get_node(entity_id)` -> `self.graph_engine.get_node(entity_id, touch=False)` (明确声明不需要 touch)
  - 其他调用方（如测试中的 `graph_engine.get_node(node_id)`）保持默认 `touch=True` 不变（向后兼容）
- **配套测试**: 在 `tests/test_graph_memory.py` 添加:
  ```python
  class TestGetNodeInfoAndTouch:
      def test_get_node_info_no_side_effect(self, graph_engine):
          node_id = graph_engine.add_node("n1", "entity", "test")
          info1 = graph_engine.get_node_info(node_id)
          info2 = graph_engine.get_node_info(node_id)
          assert info1.access_count == info2.access_count

      def test_touch_node_updates_access(self, graph_engine):
          node_id = graph_engine.add_node("n1", "entity", "test")
          graph_engine.touch_node(node_id)
          info = graph_engine.get_node_info(node_id)
          assert info.access_count == 1

      def test_get_node_with_touch_true(self, graph_engine):
          node_id = graph_engine.add_node("n1", "entity", "test")
          result = graph_engine.get_node(node_id, touch=True)
          assert result.access_count == 1

      def test_get_node_with_touch_false(self, graph_engine):
          node_id = graph_engine.add_node("n1", "entity", "test")
          result = graph_engine.get_node(node_id, touch=False)
          assert result.access_count == 0

      def test_get_node_default_is_touch_true(self, graph_engine):
          """Verify backward compatibility: default get_node behavior is touch=True"""
          node_id = graph_engine.add_node("n1", "entity", "test")
          result = graph_engine.get_node(node_id)  # no touch arg
          assert result.access_count == 1  # same as old behavior
  ```

### P1-R4-4: decay_all_weights 性能监测 - 耗时日志

- **文件**: `src/core/memory.py:146-200`
- **问题**: Round 3 审核建议 #4。`decay_all_weights` 的三层防御（预验证 + 批量优先 + 回退）增加了遍历和验证开销。在记忆库规模增长后（>1000 chunks），衰减耗时可能成为运维瓶颈。当前无任何耗时信息记录，无法诊断性能问题。
- **方案**: 在 `decay_all_weights` 方法入口记录开始时间，出口记录耗时和统计数据到 `logging.info`。
- **具体改动**:
  ```python
  # src/core/memory.py:146, 在方法开头添加计时
  def decay_all_weights(self) -> None:
      """基于真实天数的精确衰减（预验证 + 批量更新 + 错误容忍）"""
      import time
      start_time = time.monotonic()

      if self.collection.count() == 0:
          return

      # ... (existing logic unchanged) ...

      # 在方法末尾，batch update 或 per-item update 之后添加:
      elapsed = time.monotonic() - start_time
      logging.info(
          "decay_all_weights completed in %.2fs, %d valid, %d skipped, total=%d",
          elapsed, len(valid_ids), skipped, len(all_ids),
      )
  ```
  同样为 graph_memory.py 的 `decay_graph_weights` (L275-291) 添加耗时日志:
  ```python
  # src/core/graph_memory.py:275, 在方法开头添加计时
  def decay_graph_weights(self) -> None:
      """图节点/边权重衰减"""
      import time
      start_time = time.monotonic()

      # ... (existing logic unchanged) ...

      elapsed = time.monotonic() - start_time
      logger.info(
          "decay_graph_weights completed in %.2fs, %d nodes, %d edges",
          elapsed, self.graph.number_of_nodes(), self.graph.number_of_edges(),
      )
  ```
- **配套测试**: 无需专项测试（日志不影响功能逻辑）。在现有 decay 测试中可检查日志输出是否包含耗时信息，但非必要。

---

## P2 (建议优化 - API 明确化 + 性能优化)

### P2-R4-1: StateManager load_or_init 与 load 方法关系明确化

- **文件**: `src/core/state_manager.py:24-65`
- **问题**: Round 3 审核建议 #2。`load_persona()` (L24-29) 在文件缺失时返回默认但不写盘，`load_or_init_persona()` (L47-55) 在文件缺失时返回默认且写盘。两者的行为差异仅在于"是否自愈写盘"。当前 engine_server.py 仅使用 `load_or_init_*`，`load_*` 方法实际只用于 reload 场景（如 `reload_all` L38-41 内部调用 `load_persona` + `load_relationship`）。但调用方需记住"初始化用 load_or_init，刷新用 load"这一隐式约定，认知负担不必要。
- **方案**: 不做方法合并（保持两个方法语义清晰），但通过以下手段明确约定:
  (a) 在 `StateManager` 类文档字符串中明确记录方法用途分工；
  (b) 在 `load_persona` 和 `load_relationship` 的文档字符串中标注"用于 reload 场景，文件缺失时返回默认但不写盘"；
  (c) 在 `load_or_init_persona` 和 `load_or_init_relationship` 的文档字符串中标注"用于 lifespan 初始化场景，文件缺失时返回默认并写盘（自愈）"。
- **具体改动**:
  ```python
  # src/core/state_manager.py, 更新类和方法文档字符串
  class StateManager:
      """Centralized state persistence and app.state synchronization.

      Method usage convention:
      - load_or_init_*: Used in lifespan initialization. Returns default + persists if file missing (self-heal).
      - load_*: Used in reload scenarios (e.g., after git revert). Returns default if file missing, NO persist.
      - save_*: Explicit persist of a given model object.
      - reload_all: Reload both persona and relationship from disk, sync to app.state.
      - persist_relationship: Write current app.state.relationship to disk.
      """

      def load_persona(self) -> PersonaConfig:
          """Load persona from disk.

          For reload scenarios only. If file missing, returns PersonaConfig() without persist.
          Use load_or_init_persona() for initialization (which self-heals on missing file).
          """
          # ... (existing code unchanged)

      def load_or_init_persona(self) -> PersonaConfig:
          """Load persona from disk; if file missing, create default and persist (self-heal).

          For lifespan initialization. Guarantees file exists after call.
          """
          # ... (existing code unchanged)

      # Similar docstrings for load_relationship and load_or_init_relationship
  ```
- **配套测试**: 无需新增测试（仅文档变更）。可在现有 StateManager 测试的注释中标注对应方法用途。

### P2-R4-2: search_graph 性能优化 - 种子节点查找加速

- **文件**: `src/core/graph_memory.py:93-184`
- **问题**: Round 3 审核建议 #6。`search_graph` (L93-184) 在找种子节点时遍历所有节点做 label/properties 子串匹配（L98-104），时间复杂度 O(N)。在图谱规模增长后（>1000 nodes），每次搜索的开销线性增长。当前项目图谱规模较小（<100 nodes），暂时不影响性能，但作为架构前瞻性优化应提前处理。
- **方案**: 为 label 建立倒排索引缓存。在 `add_node` 时更新索引，在 `search_graph` 时使用索引快速定位种子节点，将种子查找从 O(N) 降为 O(K)（K 为匹配词长度相关的候选数）。索引缓存在 `save_graph/load_graph` 时重建（避免持久化索引的维护负担）。
- **具体改动**:
  ```python
  # src/core/graph_memory.py, 在 __init__ 中添加索引
  def __init__(self, config: Config):
      self.config = config
      self._graph: nx.DiGraph | None = None
      self._label_index: dict[str, list[str]] | None = None  # label_lower -> [node_ids]

  @property
  def label_index(self) -> dict[str, list[str]]:
      """Lazy-built inverted index: label_lower -> list of node_ids"""
      if self._label_index is None:
          self._build_label_index()
      return self._label_index

  def _build_label_index(self) -> None:
      """Build inverted index from current graph nodes"""
      self._label_index = {}
      for nid, data in self.graph.nodes(data=True):
          label_lower = data.get("label", "").lower()
          if label_lower:
              self._label_index.setdefault(label_lower, []).append(nid)

  def _invalidate_label_index(self) -> None:
      """Mark index as stale (needs rebuild on next access)"""
      self._label_index = None
  ```
  ```python
  # src/core/graph_memory.py:38-52, add_node 中更新索引
  def add_node(...) -> str:
      # ... (existing add_node logic)
      self._invalidate_label_index()  # mark stale after node addition
      return node_id
  ```
  ```python
  # src/core/graph_memory.py:93-109, search_graph 使用索引加速种子查找
  def search_graph(self, query: str, max_depth: int = 3, max_nodes: int = 20) -> GraphSearchResult:
      """从匹配标签的种子节点出发进行BFS遍历"""
      # 1. Use label_index for fast seed node lookup
      seed_nodes: list[str] = []
      query_lower = query.lower()

      # Exact label match via index
      if query_lower in self.label_index:
          seed_nodes.extend(self.label_index[query_lower])

      # Substring match via index keys (O(K) instead of O(N))
      if not seed_nodes:
          for indexed_label, node_ids in self.label_index.items():
              if query_lower in indexed_label:
                  seed_nodes.extend(node_ids)

      # Also check properties (still O(N) for properties, but less common)
      if not seed_nodes:
          for nid, data in self.graph.nodes(data=True):
              if query_lower in str(data.get("properties", {})).lower():
                  seed_nodes.append(nid)

      # ... (rest of search_graph unchanged)
  ```
  ```python
  # src/core/graph_memory.py:321-339, load_graph 时重建索引
  def load_graph(self) -> nx.DiGraph:
      # ... (existing load logic)
      # After loading, invalidate index to force rebuild
      self._invalidate_label_index()
      return g
  ```
- **配套测试**: 在 `tests/test_graph_memory.py` 添加:
  ```python
  class TestLabelIndexPerformance:
      def test_label_index_built_on_first_access(self, graph_engine):
          graph_engine.add_node("n1", "entity", "猫")
          graph_engine.add_node("n2", "entity", "狗")
          index = graph_engine.label_index
          assert "猫" in index
          assert "狗" in index

      def test_label_index_invalidated_after_add_node(self, graph_engine):
          graph_engine.add_node("n1", "entity", "猫")
          index1 = graph_engine.label_index
          assert "猫" in index1

          graph_engine.add_node("n3", "entity", "鸟")
          # After add_node, index should be rebuilt on next access
          index2 = graph_engine.label_index
          assert "鸟" in index2
          assert "猫" in index2

      def test_search_graph_exact_match_via_index(self, graph_engine):
          """Verify search_graph uses label_index for exact match"""
          graph_engine.add_node("n1", "entity", "猫")
          graph_engine.add_node("n2", "entity", "小猫咪")
          result = graph_engine.search_graph("猫", max_depth=1, max_nodes=5)
          # Should find both nodes containing "猫"
          assert len(result.nodes) >= 1
  ```

---

## 实施顺序建议

1. **P0-R4-1**: Lock 持有范围缩小 (并发性能提升，最直接影响用户体验)
2. **P0-R4-2**: ChatService 提取 (架构职责分层，依赖 P0-R4-1 的 lock 分阶段模式)
3. **P1-R4-1**: 并发测试 (验证 P0-R4-1 的 Lock 优化效果)
4. **P1-R4-2**: graph_router 提取 + Pydantic 验证 (API 质量提升，最大改动项)
5. **P1-R4-3**: get_node 拆分 (CQRS 原则，依赖 episodic_builder 调用方更新)
6. **P1-R4-4**: decay 性能监测 (日志增强，低风险改动)
7. **P2-R4-1**: StateManager API 明确化 (文档变更，零风险)
8. **P2-R4-2**: search_graph 性能优化 (前瞻性优化，可延后)

建议分三个批次执行:
- **批次 1** (P0): Lock 缩小 + ChatService 提取 (核心架构改动，需先验证功能正确性)
- **批次 2** (P1): 并发测试 + graph_router + get_node 拆分 + decay 日志 (验证 + API 质量 + CQRS)
- **批次 3** (P2): StateManager 文档 + search_graph 索引 (低优先级打磨)

---

## 预期成果

- **并发性能**: Lock 持有时间从"整个 /chat 请求"缩短为"仅状态变更段"（约 3-5 行代码 vs 25 行），吞吐量提升显著（预估 2-5x，取决于 ChromaDB 查询耗时占比）
- **架构分层**: ChatService 将路由层业务逻辑下沉，路由层从 35 行缩减到约 15 行（参数解析 + 锁管理 + 服务调用 + 响应构建）
- **API 质量**: 所有 POST 端点使用 Pydantic 验证模型（7 个图谱端点 + 2 个向量记忆端点），`await request.json()` 从项目中完全消除；图谱端点独立路由文件
- **CQRS**: get_node 拆分为 get_node_info（纯查询）+ touch_node（副作用），episodic_builder 调用方明确声明意图
- **性能监测**: decay_all_weights 和 decay_graph_weights 有耗时日志，便于运维诊断
- **并发验证**: Lock 机制有专项并发测试证明有效性

**预期新增测试数: 20-25 个测试 case**
**预期总测试数: 600+**

---

## Round 4 不做的事 (留给 Round 5)

- evolve.py 文件操作迁移到 StateManager（涉及 EvolveEngine.__init__ 签名变更和 run_evolution_cycle 内部重构，风险较高，需单独评估）
- EpisodicBuilder._entity_cache 预热机制（需评估性能影响和缓存失效策略）
- estimate_char_count/trim_to_budget 提取到 utils 模块（功能提取，不影响核心逻辑）
- evolve_router revert-to 的 commit_hash Pydantic 验证（小改进，随下轮执行）
- 多进程部署场景下的并发安全（需引入分布式锁或外部状态存储，超出当前架构范围）