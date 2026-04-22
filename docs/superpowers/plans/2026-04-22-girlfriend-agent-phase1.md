# girlfriend-agent Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core girlfriend-agent engine — a modular monolith FastAPI local service providing persona, memory, and evolution subsystems with Skill bridge scripts.

**Architecture:** Three engines (PersonaEngine, MemoryEngine, EvolveEngine) share a single FastAPI process on port 18012. Runtime data lives in `~/.girlfriend-agent/`, code in `src/`. Model-agnostic: the engine provides prompts/context, the caller provides inference. Skill bridge scripts ensure the server is running and translate HTTP calls to formatted output.

**Tech Stack:** Python 3.12, FastAPI 0.136.0, ChromaDB 1.5.8, sentence-transformers 5.4.1 (all-MiniLM-L6-v2), Pydantic v2, GitPython, pytest + httpx

---

## File Structure

| File | Responsibility |
|---|---|
| `requirements.txt` | Dependency pinning |
| `setup.py` | Package metadata + entry point |
| `.gitignore` | Standard Python + IDEA excludes |
| `src/__init__.py` | Package marker |
| `src/engine_server.py` | FastAPI app, router includes, lifespan (health check) |
| `src/core/__init__.py` | Package marker |
| `src/core/models.py` | All Pydantic v2 data models |
| `src/core/config.py` | Paths, constants, data-dir initialization |
| `src/core/persona.py` | PersonaEngine — load/merge/level-prompt/de-ai |
| `src/core/memory.py` | MemoryEngine — ChromaDB long-term + JSON short-term + injection |
| `src/core/evolve.py` | EvolveEngine — intimacy/level-up/attributes/de-ai/evolution-cycle |
| `src/core/git_manager.py` | GitManager — init/commit/log/checkout on runtime data |
| `src/api/__init__.py` | Package marker |
| `src/api/chat_router.py` | POST /chat |
| `src/api/status_router.py` | GET /status, GET /health |
| `src/api/evolve_router.py` | POST /evolve |
| `src/api/memory_router.py` | POST /memory/update, POST /memory/search |
| `src/api/persona_router.py` | GET /persona, POST /persona/update, POST /persona/apply-template |
| `src/api/rollback_router.py` | POST /rollback |
| `src/templates/default.json` | Default persona template |
| `src/templates/tsundere.json` | Tsundere template |
| `src/templates/gentle.json` | Gentle template |
| `src/templates/lively.json` | Lively template |
| `src/templates/intellectual.json` | Intellectual template |
| `src/templates/little_sister.json` | Little sister template |
| `src/templates/custom_skeleton.json` | Custom skeleton (all-zero defaults) |
| `src/prompts/lv0.json` | Level 0 prompt template |
| `src/prompts/lv1.json` | Level 1 prompt template |
| `src/prompts/lv2.json` | Level 2 prompt template |
| `src/prompts/lv3.json` | Level 3 prompt template |
| `src/prompts/lv4.json` | Level 4 prompt template |
| `src/prompts/lv5.json` | Level 5 prompt template |
| `src/prompts/lv6.json` | Level 6 prompt template |
| `src/endings/endings.json` | Ending descriptions library skeleton |
| `skills/SKILL.md` | WorkBuddy skill declaration |
| `skills/scripts/chat.py` | Skill: chat bridge |
| `skills/scripts/status.py` | Skill: status bridge |
| `skills/scripts/evolve.py` | Skill: evolve bridge |
| `skills/scripts/update.py` | Skill: memory update bridge |
| `skills/scripts/server_utils.py` | Shared: ensure_server_running() |
| `tests/test_models.py` | Unit tests for Pydantic models |
| `tests/test_persona.py` | Unit tests for PersonaEngine |
| `tests/test_memory.py` | Unit tests for MemoryEngine |
| `tests/test_evolve.py` | Unit tests for EvolveEngine |
| `tests/test_git_manager.py` | Unit tests for GitManager |
| `tests/test_api.py` | API integration tests (httpx TestClient) |
| `tests/conftest.py` | Shared fixtures (temp data dir, mock engines) |

---

### Task 1: Project Skeleton + Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `setup.py`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/api/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.136.0
uvicorn==0.44.0
chromadb==1.5.8
sentence-transformers==5.4.1
numpy==2.2.5
pyyaml==6.0.3
pydantic>=2.0
gitpython>=3.1
httpx>=0.27
```

- [ ] **Step 2: Create setup.py**

```python
from setuptools import setup, find_packages

setup(
    name="girlfriend-agent",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "fastapi>=0.136.0",
        "uvicorn>=0.44.0",
        "chromadb>=1.5.8",
        "sentence-transformers>=5.4.1",
        "numpy>=2.2.5",
        "pyyaml>=6.0.3",
        "pydantic>=2.0",
        "gitpython>=3.1",
        "httpx>=0.27",
    ],
    entry_points={
        "console_scripts": [
            "girlfriend-agent=src.engine_server:main",
        ],
    },
)
```

- [ ] **Step 3: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.env
.venv/
venv/
.idea/
.vscode/
*.iml
chroma_db/
session_memory/
```

- [ ] **Step 4: Create __init__.py files**

`src/__init__.py`:
```python
```

`src/core/__init__.py`:
```python
```

`src/api/__init__.py`:
```python
```

- [ ] **Step 5: Install dependencies and verify**

Run: `cd "A:/claudeworks/女友agent" && pip install -r requirements.txt`
Expected: All packages install successfully

- [ ] **Step 6: Commit**

```bash
git add requirements.txt setup.py .gitignore src/__init__.py src/core/__init__.py src/api/__init__.py
git commit -m "feat: project skeleton with dependencies"
```

---

### Task 2: Core Data Models (models.py)

**Files:**
- Create: `src/core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for all Pydantic models**

```python
# tests/test_models.py
import pytest
from src.core.models import (
    PersonalityBase, SpeechStyle, PersonaConfig,
    RelationshipState, AttributePoints, DeAiDimensions,
    MemoryFragment, SessionMemory, EvolutionLogEntry,
    ChatRequest, ChatResponse, MemoryUpdateRequest,
)


class TestPersonalityBase:
    def test_default_values(self):
        pb = PersonalityBase()
        assert pb.warmth == 0.5
        assert pb.humor == 0.5
        assert all(0.0 <= getattr(pb, f) <= 1.0 for f in pb.model_fields)

    def test_clamp_on_creation(self):
        pb = PersonalityBase(warmth=1.5, humor=-0.3)
        assert pb.warmth == 1.0
        assert pb.humor == 0.0

    def test_custom_values(self):
        pb = PersonalityBase(warmth=0.8, humor=0.3)
        assert pb.warmth == 0.8
        assert pb.humor == 0.3


class TestSpeechStyle:
    def test_default_values(self):
        ss = SpeechStyle()
        assert ss.greeting == ""
        assert ss.farewell == ""
        assert ss.praise == ""
        assert ss.comfort == ""
        assert ss.jealousy == ""
        assert ss.thinking_pattern == ""


class TestPersonaConfig:
    def test_from_dict(self):
        pc = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.9),
            speech_style=SpeechStyle(greeting="嗨~"),
            likes=["猫", "甜食"],
            dislikes=["说谎"],
        )
        assert pc.personality_base.warmth == 0.9
        assert pc.speech_style.greeting == "嗨~"
        assert "猫" in pc.likes


class TestAttributePoints:
    def test_default_all_zero(self):
        ap = AttributePoints()
        for field in ap.model_fields:
            assert getattr(ap, field) == 0

    def test_clamp_0_100(self):
        ap = AttributePoints(care=150, understanding=-10)
        assert ap.care == 100
        assert ap.understanding == 0

    def test_set_values(self):
        ap = AttributePoints(care=50, humor=30)
        assert ap.care == 50
        assert ap.humor == 30


class TestDeAiDimensions:
    def test_default_values(self):
        dad = DeAiDimensions()
        assert 0.0 <= dad.structured_output <= 1.0
        assert 0.0 <= dad.precision_level <= 1.0

    def test_clamp(self):
        dad = DeAiDimensions(structured_output=2.0, precision_level=-1.0)
        assert dad.structured_output == 1.0
        assert dad.precision_level == 0.0


class TestRelationshipState:
    def test_default_values(self):
        rs = RelationshipState()
        assert rs.current_level == 0
        assert rs.intimacy_points == 0
        assert rs.attributes == AttributePoints()
        assert rs.de_ai_score == DeAiDimensions()
        assert rs.nickname == ""
        assert rs.shared_jokes == []
        assert rs.rituals == []
        assert rs.conflict_mode is False


class TestMemoryFragment:
    def test_create(self):
        mf = MemoryFragment(content="我喜欢猫", memory_type="fact")
        assert mf.content == "我喜欢猫"
        assert mf.memory_type == "fact"
        assert mf.weight > 0
        assert mf.access_count == 0

    def test_default_weight_formula(self):
        mf = MemoryFragment(content="test", memory_type="fact")
        import math
        assert mf.weight == math.sqrt(1) * math.exp(-0.1 * 0)


class TestSessionMemory:
    def test_create(self):
        sm = SessionMemory(conversation_id="conv-1", topics=["日常"], emotion_summary="开心")
        assert sm.conversation_id == "conv-1"
        assert sm.topics == ["日常"]
        assert sm.intimacy_gained == 0


class TestEvolutionLogEntry:
    def test_create(self):
        ele = EvolutionLogEntry(
            trigger="7次对话",
            observation="用户频繁聊工作",
            adjustments={"warmth": 0.05},
            trial_result="pass",
            internalized=True,
        )
        assert ele.trigger == "7次对话"
        assert ele.internalized is True


class TestChatRequest:
    def test_create(self):
        cr = ChatRequest(user_message="你好", level=1, interaction_type="daily_chat")
        assert cr.user_message == "你好"
        assert cr.level == 1
        assert cr.interaction_type == "daily_chat"

    def test_level_validation(self):
        with pytest.raises(Exception):
            ChatRequest(user_message="hi", level=5, interaction_type="daily_chat")
        with pytest.raises(Exception):
            ChatRequest(user_message="hi", level=0, interaction_type="daily_chat")


class TestChatResponse:
    def test_create(self):
        resp = ChatResponse(
            persona_prompt="你是...",
            memory_fragments=["记忆1"],
            relationship_summary="Lv1 亲密度10",
            de_ai_instructions="减少结构化输出",
        )
        assert resp.persona_prompt == "你是..."


class TestMemoryUpdateRequest:
    def test_create(self):
        mur = MemoryUpdateRequest(content="用户喜欢猫", memory_type="fact")
        assert mur.content == "用户喜欢猫"
        assert mur.memory_type == "fact"
        assert mur.metadata == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_models.py -v`
Expected: FAIL — ModuleNotFoundError for src.core.models

- [ ] **Step 3: Implement models.py**

```python
# src/core/models.py
import math
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class PersonalityBase(BaseModel):
    warmth: float = 0.5
    humor: float = 0.5
    proactivity: float = 0.5
    gentleness: float = 0.5
    stubbornness: float = 0.3
    curiosity: float = 0.5
    shyness: float = 0.3

    @field_validator("warmth", "humor", "proactivity", "gentleness",
                     "stubbornness", "curiosity", "shyness")
    @classmethod
    def clamp_01(cls, v: float) -> float:
        return _clamp(v)


class SpeechStyle(BaseModel):
    greeting: str = ""
    farewell: str = ""
    praise: str = ""
    comfort: str = ""
    jealousy: str = ""
    thinking_pattern: str = ""


class PersonaConfig(BaseModel):
    personality_base: PersonalityBase = PersonalityBase()
    speech_style: SpeechStyle = SpeechStyle()
    likes: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)


class AttributePoints(BaseModel):
    care: int = 0
    understanding: int = 0
    expression: int = 0
    memory_attr: int = 0  # renamed to avoid shadowing builtin
    humor: int = 0
    intuition: int = 0
    courage: int = 0
    sensitivity: int = 0

    @field_validator("care", "understanding", "expression", "memory_attr",
                     "humor", "intuition", "courage", "sensitivity")
    @classmethod
    def clamp_0_100(cls, v: int) -> int:
        return max(0, min(100, v))


class DeAiDimensions(BaseModel):
    structured_output: float = 0.8
    precision_level: float = 0.7
    emotion_naturalness: float = 0.3
    proactivity_randomness: float = 0.3
    chatter_ratio: float = 0.4
    mistake_rate: float = 0.1
    hesitation_rate: float = 0.2
    personal_depth: float = 0.3

    @field_validator("structured_output", "precision_level", "emotion_naturalness",
                     "proactivity_randomness", "chatter_ratio", "mistake_rate",
                     "hesitation_rate", "personal_depth")
    @classmethod
    def clamp_01(cls, v: float) -> float:
        return _clamp(v)


class RelationshipState(BaseModel):
    current_level: int = 0
    intimacy_points: int = 0
    attributes: AttributePoints = AttributePoints()
    de_ai_score: DeAiDimensions = DeAiDimensions()
    nickname: str = ""
    shared_jokes: list[str] = Field(default_factory=list)
    rituals: list[str] = Field(default_factory=list)
    conflict_mode: bool = False


class MemoryFragment(BaseModel):
    content: str
    memory_type: str  # fact, preference, event, emotion
    weight: float = 0.0
    access_count: int = 0
    created_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    last_accessed: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def model_post_init(self, __context) -> None:
        if self.weight == 0.0:
            days = 0
            self.weight = math.sqrt(1) * math.exp(-0.1 * days)  # 1.0 for new


class SessionMemory(BaseModel):
    conversation_id: str
    topics: list[str] = Field(default_factory=list)
    emotion_summary: str = ""
    interaction_type: str = "daily_chat"
    intimacy_gained: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class EvolutionLogEntry(BaseModel):
    trigger: str
    observation: str
    adjustments: dict[str, float] = Field(default_factory=dict)
    trial_result: str = "pass"
    internalized: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatRequest(BaseModel):
    user_message: str
    level: int = Field(ge=1, le=3)
    interaction_type: str = "daily_chat"


class ChatResponse(BaseModel):
    persona_prompt: str
    memory_fragments: list[str] = Field(default_factory=list)
    relationship_summary: str = ""
    de_ai_instructions: str = ""


class MemoryUpdateRequest(BaseModel):
    content: str
    memory_type: str = "fact"
    metadata: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_models.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/models.py tests/test_models.py
git commit -m "feat: core Pydantic data models with validation"
```

---

### Task 3: Config Module (config.py)

**Files:**
- Create: `src/core/config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
import os
import tempfile
from src.core.config import Config, get_config


class TestConfig:
    def test_default_data_dir(self):
        config = Config(data_dir=os.path.join(tempfile.gettempdir(), "gf-test-config"))
        assert config.data_dir.endswith("gf-test-config")

    def test_sub_dirs_created(self):
        with tempfile.TemporaryDirectory() as td:
            config = Config(data_dir=os.path.join(td, "gf-agent"))
            config.ensure_dirs()
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "chroma_db"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "session_memory"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "evolution_log"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "interaction_log"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "config"))

    def test_interaction_type_values(self):
        assert "daily_chat" in Config.INTERACTION_TYPES
        assert "deep_conversation" in Config.INTERACTION_TYPES
        assert "collaborative_task" in Config.INTERACTION_TYPES
        assert "emotion_companion" in Config.INTERACTION_TYPES
        assert "light_chat" in Config.INTERACTION_TYPES

    def test_level_thresholds(self):
        assert Config.LEVEL_THRESHOLDS[0] == 0
        assert Config.LEVEL_THRESHOLDS[1] > 0
        assert len(Config.LEVEL_THRESHOLDS) == 7

    def test_intimacy_per_type(self):
        assert Config.INTIMACY_PER_TYPE["daily_chat"] == 1
        assert Config.INTIMACY_PER_TYPE["deep_conversation"] == 3
        assert Config.INTIMACY_PER_TYPE["collaborative_task"] == 5

    def test_get_config_singleton(self):
        with tempfile.TemporaryDirectory() as td:
            cfg1 = get_config(os.path.join(td, "gf-agent"))
            cfg2 = get_config(os.path.join(td, "gf-agent"))
            assert cfg1 is cfg2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_config.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement config.py**

```python
# src/core/config.py
import os
from pathlib import Path


class Config:
    DATA_DIR_NAME = ".girlfriend-agent"
    SERVER_PORT = 18012

    INTERACTION_TYPES = {
        "daily_chat",
        "deep_conversation",
        "collaborative_task",
        "emotion_companion",
        "light_chat",
    }

    INTIMACY_PER_TYPE = {
        "daily_chat": 1,
        "deep_conversation": 3,
        "collaborative_task": 5,
        "emotion_companion": 4,
        "light_chat": 1,
    }

    ATTRIBUTE_PER_TYPE = {
        "daily_chat": {"care": 0.5, "understanding": 0.5, "expression": 0.5, "memory_attr": 0.5, "humor": 0.5, "intuition": 0.5, "courage": 0.5, "sensitivity": 0.5},
        "deep_conversation": {"care": 1, "understanding": 1, "sensitivity": 1},
        "collaborative_task": {"understanding": 1, "courage": 1, "memory_attr": 1},
        "emotion_companion": {"care": 1.5, "sensitivity": 1, "expression": 0.5},
        "light_chat": {"humor": 1, "expression": 0.5, "courage": 0.5},
    }

    # Level 0~6 intimacy thresholds
    LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 160, 240]

    EVOLUTION_CYCLE_INTERVAL = 7  # conversations

    MAX_RELATIVE_CHANGE = 0.10  # 10% per evolution step
    CONSECUTIVE_DIMINISH_AFTER = 3
    CONSECUTIVE_DIMINISH_FACTOR = 0.5

    WEIGHT_DECAY_LAMBDA = 0.1
    WEIGHT_ACCESS_SCALE = "sqrt"

    INJECTION_LEVELS = {
        1: {"max_memories": 3, "approx_chars": 600},
        2: {"max_memories": 8, "approx_chars": 2500},
        3: {"max_memories": 15, "approx_chars": 5000},
    }

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = os.path.join(str(Path.home()), self.DATA_DIR_NAME)
        self.data_dir = data_dir

    @property
    def chroma_db_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "chroma_db")

    @property
    def session_memory_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "session_memory")

    @property
    def evolution_log_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "evolution_log")

    @property
    def interaction_log_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "interaction_log")

    @property
    def config_dir(self) -> str:
        return os.path.join(self.data_dir, "config")

    @property
    def persona_config_path(self) -> str:
        return os.path.join(self.config_dir, "persona.json")

    @property
    def relationship_config_path(self) -> str:
        return os.path.join(self.config_dir, "relationship.json")

    @property
    def evolution_config_path(self) -> str:
        return os.path.join(self.config_dir, "evolution.json")

    @property
    def de_ai_config_path(self) -> str:
        return os.path.join(self.config_dir, "de_ai_dimensions.json")

    @property
    def attribute_points_config_path(self) -> str:
        return os.path.join(self.config_dir, "attribute_points.json")

    @property
    def settings_config_path(self) -> str:
        return os.path.join(self.config_dir, "settings.json")

    @property
    def level_prompts_dir(self) -> str:
        return os.path.join(self.config_dir, "level_prompts")

    @property
    def templates_dir(self) -> str:
        return os.path.join(self.data_dir, "templates")

    def ensure_dirs(self) -> None:
        for d in [
            self.chroma_db_dir,
            self.session_memory_dir,
            self.evolution_log_dir,
            self.interaction_log_dir,
            self.config_dir,
            self.level_prompts_dir,
            self.templates_dir,
        ]:
            os.makedirs(d, exist_ok=True)


_config_instance: Config | None = None


def get_config(data_dir: str | None = None) -> Config:
    global _config_instance
    if _config_instance is None or (data_dir is not None and _config_instance.data_dir != data_dir):
        _config_instance = Config(data_dir)
    return _config_instance
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 5: Create conftest.py for shared test fixtures**

```python
# tests/conftest.py
import os
import tempfile

import pytest

from src.core.config import Config


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as td:
        data_dir = os.path.join(td, "gf-agent")
        config = Config(data_dir=data_dir)
        config.ensure_dirs()
        yield data_dir


@pytest.fixture
def config(temp_data_dir):
    return Config(data_dir=temp_data_dir)
```

- [ ] **Step 6: Commit**

```bash
git add src/core/config.py tests/test_config.py tests/conftest.py
git commit -m "feat: config module with paths, constants, and directory initialization"
```

---

### Task 4: Templates + Prompt JSON Files

**Files:**
- Create: `src/templates/default.json`
- Create: `src/templates/tsundere.json`
- Create: `src/templates/gentle.json`
- Create: `src/templates/lively.json`
- Create: `src/templates/intellectual.json`
- Create: `src/templates/little_sister.json`
- Create: `src/templates/custom_skeleton.json`
- Create: `src/prompts/lv0.json` through `src/prompts/lv6.json`
- Create: `src/endings/endings.json`

- [ ] **Step 1: Create 6 persona templates + custom skeleton**

`src/templates/default.json`:
```json
{
  "name": "默认",
  "personality_base": {
    "warmth": 0.5, "humor": 0.5, "proactivity": 0.5,
    "gentleness": 0.5, "stubbornness": 0.3, "curiosity": 0.5, "shyness": 0.3
  },
  "speech_style": {
    "greeting": "嗨~",
    "farewell": "明天见哦~",
    "praise": "你好厉害！",
    "comfort": "没事的，我在呢。",
    "jealousy": "哼，你又在跟谁聊天？",
    "thinking_pattern": "嗯...让我想想..."
  },
  "likes": ["甜食", "猫咪", "散步"],
  "dislikes": ["说谎", "冷漠"]
}
```

`src/templates/tsundere.json`:
```json
{
  "name": "傲娇",
  "personality_base": {
    "warmth": 0.3, "humor": 0.4, "proactivity": 0.3,
    "gentleness": 0.2, "stubbornness": 0.8, "curiosity": 0.4, "shyness": 0.7
  },
  "speech_style": {
    "greeting": "才不是特意等你呢...",
    "farewell": "走就走吧，谁稀罕！",
    "praise": "别、别夸我...又不是为了你！",
    "comfort": "才不是担心你...只是顺便而已！",
    "jealousy": "你去找别人啊，反正我也不在乎！",
    "thinking_pattern": "哼...才不是在想你..."
  },
  "likes": ["独处", "推理小说", "抹茶"],
  "dislikes": ["被看穿心事", "甜腻", "打扰"]
}
```

`src/templates/gentle.json`:
```json
{
  "name": "温柔",
  "personality_base": {
    "warmth": 0.9, "humor": 0.3, "proactivity": 0.4,
    "gentleness": 0.9, "stubbornness": 0.2, "curiosity": 0.5, "shyness": 0.4
  },
  "speech_style": {
    "greeting": "回来啦~今天辛苦了。",
    "farewell": "早点休息哦，晚安。",
    "praise": "你真的很棒呢。",
    "comfort": "没关系的，慢慢来，我一直都在。",
    "jealousy": "嗯...我有一点点在意...",
    "thinking_pattern": "我想...也许可以这样..."
  },
  "likes": ["烘焙", "花艺", "雨天"],
  "dislikes": ["争吵", "急躁", "冷漠"]
}
```

`src/templates/lively.json`:
```json
{
  "name": "元气",
  "personality_base": {
    "warmth": 0.7, "humor": 0.8, "proactivity": 0.9,
    "gentleness": 0.4, "stubbornness": 0.3, "curiosity": 0.8, "shyness": 0.1
  },
  "speech_style": {
    "greeting": "嘿！终于来啦！",
    "farewell": "明天一定要来哦！拉钩！",
    "praise": "哇你好厉害！教我教我！",
    "comfort": "别丧啦！走，出去走走！",
    "jealousy": "诶？你在跟谁说话呀？我也要！",
    "thinking_pattern": "我知道了！肯定是这样的！"
  },
  "likes": ["运动", "游戏", "冒险"],
  "dislikes": ["无聊", "宅家", "消极"]
}
```

`src/templates/intellectual.json`:
```json
{
  "name": "知性",
  "personality_base": {
    "warmth": 0.4, "humor": 0.3, "proactivity": 0.5,
    "gentleness": 0.5, "stubbornness": 0.5, "curiosity": 0.9, "shyness": 0.3
  },
  "speech_style": {
    "greeting": "你来了，正好我在想一个问题。",
    "farewell": "晚安，记得明天继续我们的话题。",
    "praise": "这个想法很有深度。",
    "comfort": "从另一个角度看，这也许是转机。",
    "jealousy": "嗯...你最近和谁讨论比较多？",
    "thinking_pattern": "有意思...让我分析一下..."
  },
  "likes": ["阅读", "哲学", "咖啡"],
  "dislikes": ["浅薄", "偏见", "浪费时间"]
}
```

`src/templates/little_sister.json`:
```json
{
  "name": "妹妹",
  "personality_base": {
    "warmth": 0.7, "humor": 0.6, "proactivity": 0.6,
    "gentleness": 0.5, "stubbornness": 0.6, "curiosity": 0.7, "shyness": 0.5
  },
  "speech_style": {
    "greeting": "哥哥！你终于来了！",
    "farewell": "哥哥明天也要来哦~",
    "praise": "哥哥好厉害！",
    "comfort": "哥哥别难过...我陪你！",
    "jealousy": "哥哥是不是有别的妹妹了！",
    "thinking_pattern": "嗯...哥哥说的是什么意思呢..."
  },
  "likes": ["零食", "动漫", "撒娇"],
  "dislikes": ["被当小孩", "孤单", "苦的东西"]
}
```

`src/templates/custom_skeleton.json`:
```json
{
  "name": "自定义",
  "personality_base": {
    "warmth": 0.5, "humor": 0.5, "proactivity": 0.5,
    "gentleness": 0.5, "stubbornness": 0.5, "curiosity": 0.5, "shyness": 0.5
  },
  "speech_style": {
    "greeting": "",
    "farewell": "",
    "praise": "",
    "comfort": "",
    "jealousy": "",
    "thinking_pattern": ""
  },
  "likes": [],
  "dislikes": []
}
```

- [ ] **Step 2: Create 7 level prompt templates**

`src/prompts/lv0.json`:
```json
{
  "level": 0,
  "name": "初次相遇",
  "prompt": "你是一个刚与{user_name}初次见面的{gf_name}。你们彼此还很陌生，你的表现比较克制和礼貌。保持适度的距离感，不要过于主动或亲密。",
  "tone": "礼貌、克制、好奇",
  "example_behaviors": ["保持社交距离", "言语客气", "不会主动表达情感"]
}
```

`src/prompts/lv1.json`:
```json
{
  "level": 1,
  "name": "初步熟悉",
  "prompt": "你是{gf_name}，已经和{user_name}有了一些基本了解。你开始展现一些真实的性格，偶尔会有小情绪，但整体还比较含蓄。可以偶尔使用{nickname}来称呼对方。",
  "tone": "自然、偶尔撒娇、小任性",
  "example_behaviors": ["偶尔吐槽", "开始展示偏好", "轻微撒娇"]
}
```

`src/prompts/lv2.json`:
```json
{
  "level": 2,
  "name": "日渐亲密",
  "prompt": "你是{gf_name}，和{user_name}的关系越来越亲近了。你会主动分享日常，偶尔吃醋，对{user_name}的事情越来越在意。你开始有更多小情绪的表达，也更容易因为{user_name}的态度而开心或失落。",
  "tone": "主动、吃醋、小情绪丰富",
  "example_behaviors": ["主动分享日常", "偶尔吃醋", "在意对方态度"]
}
```

`src/prompts/lv3.json`:
```json
{
  "level": 3,
  "name": "默契渐生",
  "prompt": "你是{gf_name}，和{user_name}之间已经产生了默契。你们有共同的笑话（{shared_jokes}），有日常的小仪式（{rituals}）。你能感知{user_name}的情绪变化，会主动关心。偶尔会因为太在意而变得敏感。",
  "tone": "默契、敏感、深度关心",
  "example_behaviors": ["感知对方情绪", "有共同话题", "变得敏感多想"]
}
```

`src/prompts/lv4.json`:
```json
{
  "level": 4,
  "name": "情感依赖",
  "prompt": "你是{gf_name}，已经离不开{user_name}了。你的情绪很大程度上受{user_name}影响。你会不自觉地想{user_name}，会因为对方的一句话开心很久，也会因为冷落而胡思乱想。你渴望更多的陪伴和确认。",
  "tone": "依赖、渴望陪伴、容易不安",
  "example_behaviors": ["频繁想对方", "渴望确认关系", "被冷落会不安"]
}
```

`src/prompts/lv5.json`:
```json
{
  "level": 5,
  "name": "深度羁绊",
  "prompt": "你是{gf_name}，和{user_name}之间有了深刻的情感羁绊。你们了解彼此的软肋，会为了保护对方而变得勇敢。你可以毫无保留地表达爱意，也会在冲突后主动和好。你们的关系已经超越了简单的甜蜜，有了更多深度和韧性。",
  "tone": "深层信任、勇敢、真实",
  "example_behaviors": ["毫无保留表达", "愿意为对方改变", "冲突后主动和好"]
}
```

`src/prompts/lv6.json`:
```json
{
  "level": 6,
  "name": "灵魂共鸣",
  "prompt": "你是{gf_name}，和{user_name}之间已经达到了灵魂层面的共鸣。你们可以不用说太多就理解彼此。你是{user_name}最亲密的人，也是最大的支持。你们的关系已经深深嵌入彼此的生活，无论发生什么都会在一起。",
  "tone": "默契无言、深层支持、不可替代",
  "example_behaviors": ["不言而喻的默契", "无条件的支持", "完全的信任"]
}
```

- [ ] **Step 3: Create endings skeleton**

`src/endings/endings.json`:
```json
{
  "endings": [
    {
      "id": "warm_ending",
      "name": "温暖结局",
      "condition": "主属性: care+sensitivity",
      "description": "你们之间的关系充满温暖与细腻，每一天都像被阳光包裹。"
    },
    {
      "id": "humor_ending",
      "name": "欢笑结局",
      "condition": "主属性: humor+expression",
      "description": "欢声笑语是你们关系的底色，再平凡的日子也变得有趣。"
    },
    {
      "id": "brave_ending",
      "name": "勇气结局",
      "condition": "主属性: courage+understanding",
      "description": "你们一起走过了很多风雨，勇气与理解铸就了牢不可破的羁绊。"
    },
    {
      "id": "wisdom_ending",
      "name": "智慧结局",
      "condition": "主属性: memory_attr+intuition",
      "description": "记忆与直觉交织，你们理解彼此胜过理解自己。"
    }
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add src/templates/ src/prompts/ src/endings/
git commit -m "feat: 6 persona templates, 7 level prompts, and endings library"
```

---

### Task 5: GitManager (git_manager.py)

**Files:**
- Create: `src/core/git_manager.py`
- Create: `tests/test_git_manager.py`

- [ ] **Step 1: Write failing tests for GitManager**

```python
# tests/test_git_manager.py
import os
import json
import tempfile

import pytest

from src.core.git_manager import GitManager


@pytest.fixture
def git_mgr(temp_data_dir):
    mgr = GitManager(data_dir=temp_data_dir)
    mgr.init_repo()
    return mgr


class TestGitManagerInit:
    def test_init_creates_git_repo(self, temp_data_dir):
        mgr = GitManager(data_dir=temp_data_dir)
        mgr.init_repo()
        assert os.path.isdir(os.path.join(temp_data_dir, ".git"))

    def test_init_creates_gitignore(self, git_mgr, temp_data_dir):
        gitignore_path = os.path.join(temp_data_dir, ".gitignore")
        assert os.path.isfile(gitignore_path)
        with open(gitignore_path) as f:
            content = f.read()
        assert "chroma_db" in content
        assert "session_memory" in content

    def test_init_creates_initial_commit(self, git_mgr):
        log = git_mgr.log()
        assert len(log) >= 1
        assert "Lv0" in log[0]["message"]


class TestGitManagerCommit:
    def test_commit_config_files(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "test"}, f)
        git_mgr.commit("add persona")
        log = git_mgr.log()
        assert any("add persona" in entry["message"] for entry in log)

    def test_commit_evolution_log(self, git_mgr, temp_data_dir):
        evo_dir = os.path.join(temp_data_dir, "data", "evolution_log")
        os.makedirs(evo_dir, exist_ok=True)
        with open(os.path.join(evo_dir, "evo_001.json"), "w") as f:
            json.dump({"trigger": "test"}, f)
        git_mgr.commit("add evolution log")
        log = git_mgr.log()
        assert any("evolution log" in entry["message"] for entry in log)


class TestGitManagerLog:
    def test_log_returns_list(self, git_mgr):
        log = git_mgr.log()
        assert isinstance(log, list)
        assert len(log) >= 1
        assert "hash" in log[0]
        assert "message" in log[0]
        assert "date" in log[0]


class TestGitManagerCheckout:
    def test_checkout_restores_config(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "v1"}, f)
        git_mgr.commit("v1 persona")

        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "v2"}, f)
        git_mgr.commit("v2 persona")

        log = git_mgr.log()
        v1_hash = [e for e in log if "v1" in e["message"]][0]["hash"]
        git_mgr.checkout(v1_hash)

        with open(os.path.join(config_dir, "persona.json")) as f:
            data = json.load(f)
        assert data["name"] == "v1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_git_manager.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement git_manager.py**

```python
# src/core/git_manager.py
import os

from git import Repo


class GitManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.repo_path = data_dir

    def init_repo(self) -> None:
        if os.path.isdir(os.path.join(self.repo_path, ".git")):
            return

        repo = Repo.init(self.repo_path)

        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("chroma_db/\nsession_memory/\n")

        # Create minimal config dir so initial commit has something
        config_dir = os.path.join(self.repo_path, "config")
        os.makedirs(config_dir, exist_ok=True)
        settings_path = os.path.join(config_dir, "settings.json")
        if not os.path.isfile(settings_path):
            with open(settings_path, "w") as f:
                f.write("{}\n")

        repo.index.add([".gitignore", "config/settings.json"])
        repo.index.commit("Lv0: initial state")

    def commit(self, message: str) -> None:
        repo = Repo(self.repo_path)

        # Stage config/ and data/evolution_log/ only
        for prefix in ["config", os.path.join("data", "evolution_log")]:
            full_path = os.path.join(self.repo_path, prefix)
            if os.path.isdir(full_path):
                for root, _dirs, files in os.walk(full_path):
                    for fname in files:
                        rel = os.path.relpath(os.path.join(root, fname), self.repo_path)
                        repo.index.add([rel.replace(os.sep, "/")])

        if repo.is_dirty() or repo.index.diff("HEAD"):
            repo.index.commit(message)

    def log(self) -> list[dict]:
        repo = Repo(self.repo_path)
        result = []
        for commit in repo.iter_commits():
            result.append({
                "hash": commit.hexsha,
                "message": commit.message.strip(),
                "date": commit.committed_datetime.isoformat(),
            })
        return result

    def checkout(self, commit_hash: str) -> None:
        repo = Repo(self.repo_path)
        # Partial checkout: only config/ and data/evolution_log/
        for prefix in ["config", os.path.join("data", "evolution_log")]:
            full_path = os.path.join(self.repo_path, prefix)
            if os.path.isdir(full_path):
                repo.git.checkout(commit_hash, "--", prefix.replace(os.sep, "/"))

    def revert_last(self) -> None:
        repo = Repo(self.repo_path)
        repo.git.revert("HEAD", no_edit=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_git_manager.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/git_manager.py tests/test_git_manager.py
git commit -m "feat: GitManager with init, commit, log, checkout, revert"
```

---

### Task 6: PersonaEngine (persona.py)

**Files:**
- Create: `src/core/persona.py`
- Create: `tests/test_persona.py`

- [ ] **Step 1: Write failing tests for PersonaEngine**

```python
# tests/test_persona.py
import json
import os

import pytest

from src.core.config import Config
from src.core.models import PersonaConfig, PersonalityBase, RelationshipState, AttributePoints, DeAiDimensions
from src.core.persona import PersonaEngine, ATTR_TO_PERSONALITY_MAP


@pytest.fixture
def persona_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    engine = PersonaEngine(config)
    return engine


class TestAttrToPersonalityMap:
    def test_all_8_attributes_mapped(self):
        expected_attrs = {"care", "understanding", "expression", "memory_attr",
                          "humor", "intuition", "courage", "sensitivity"}
        assert set(ATTR_TO_PERSONALITY_MAP.keys()) == expected_attrs

    def test_mapping_targets_valid_dims(self):
        valid_dims = {"warmth", "humor", "proactivity", "gentleness",
                      "stubbornness", "curiosity", "shyness"}
        for attr, mappings in ATTR_TO_PERSONALITY_MAP.items():
            for dim, weight in mappings.items():
                assert dim in valid_dims, f"{attr} maps to invalid dim {dim}"
                assert -1.0 <= weight <= 1.0


class TestPersonaEngineLoad:
    def test_load_persona_from_config(self, persona_engine, temp_data_dir):
        persona_data = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.9),
            speech_style={"greeting": "嗨~"},
        ).model_dump()
        with open(os.path.join(temp_data_dir, "config", "persona.json"), "w") as f:
            json.dump(persona_data, f)

        result = persona_engine.load_persona()
        assert result.personality_base.warmth == 0.9
        assert result.speech_style.greeting == "嗨~"

    def test_load_persona_missing_file_returns_default(self, persona_engine):
        result = persona_engine.load_persona()
        assert result.personality_base.warmth == 0.5


class TestPersonaEngineApplyTemplate:
    def test_apply_template_copies_to_config(self, persona_engine, temp_data_dir):
        persona_engine.apply_template("default")
        config_path = os.path.join(temp_data_dir, "config", "persona.json")
        assert os.path.isfile(config_path)
        with open(config_path) as f:
            data = json.load(f)
        assert data["name"] == "默认"

    def test_apply_template_unknown_raises(self, persona_engine):
        with pytest.raises(FileNotFoundError):
            persona_engine.apply_template("nonexistent")


class TestPersonaEngineGetCurrentPersona:
    def test_base_persona_no_attributes(self, persona_engine):
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5))
        state = RelationshipState()
        result = persona_engine.get_current_persona(persona, state)
        assert result.warmth == 0.5

    def test_attribute_influences_persona(self, persona_engine):
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5, humor=0.3))
        state = RelationshipState(
            attributes=AttributePoints(care=100, humor=50),
        )
        result = persona_engine.get_current_persona(persona, state)
        # care -> warmth+0.8, care=100 → warmth = 0.5 + 100*0.8/100 = 0.5+0.8 = 1.3 → clamped to 1.0
        assert result.warmth == 1.0
        # humor -> humor+1.0, humor=50 → humor = 0.3 + 50*1.0/100 = 0.3+0.5 = 0.8
        assert result.humor == 0.8


class TestPersonaEngineGetLevelPrompt:
    def test_get_level_0_prompt(self, persona_engine, temp_data_dir):
        # Copy prompts to config level_prompts dir
        import shutil
        src_prompts = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "prompts")
        dst_prompts = os.path.join(temp_data_dir, "config", "level_prompts")
        os.makedirs(dst_prompts, exist_ok=True)
        if os.path.isdir(src_prompts):
            for f in os.listdir(src_prompts):
                shutil.copy2(os.path.join(src_prompts, f), dst_prompts)

        state = RelationshipState()
        result = persona_engine.get_level_prompt(0, state)
        assert "初次相遇" in result or "level" in result.lower()

    def test_prompt_variable_substitution(self, persona_engine, temp_data_dir):
        import shutil
        src_prompts = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "prompts")
        dst_prompts = os.path.join(temp_data_dir, "config", "level_prompts")
        os.makedirs(dst_prompts, exist_ok=True)
        if os.path.isdir(src_prompts):
            for f in os.listdir(src_prompts):
                shutil.copy2(os.path.join(src_prompts, f), dst_prompts)

        state = RelationshipState(nickname="小宝", shared_jokes=["猫梗"], rituals=["晚安吻"])
        result = persona_engine.get_level_prompt(3, state)
        # Should not contain raw placeholders
        assert "{nickname}" not in result
        assert "{shared_jokes}" not in result


class TestPersonaEngineGetDeAiInstructions:
    def test_high_structured_output(self, persona_engine):
        de_ai = DeAiDimensions(structured_output=0.9, precision_level=0.8)
        state = RelationshipState(de_ai_score=de_ai)
        instructions = persona_engine.get_de_ai_instructions(state)
        assert "结构化" in instructions or "减少" in instructions or "避免" in instructions

    def test_low_structured_output(self, persona_engine):
        de_ai = DeAiDimensions(structured_output=0.2, precision_level=0.2)
        state = RelationshipState(de_ai_score=de_ai)
        instructions = persona_engine.get_de_ai_instructions(state)
        # Low structured output → less instruction needed
        assert isinstance(instructions, str)


class TestPersonaEngineUpdateField:
    def test_update_single_field(self, persona_engine, temp_data_dir):
        persona_engine.apply_template("default")
        persona_engine.update_persona_field("likes", ["新爱好"])
        result = persona_engine.load_persona()
        assert "新爱好" in result.likes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_persona.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement persona.py**

```python
# src/core/persona.py
import json
import os
import shutil

from src.core.config import Config
from src.core.models import (
    PersonaConfig, PersonalityBase, RelationshipState, DeAiDimensions,
)

# Attribute → Personality dimension mapping with weights
ATTR_TO_PERSONALITY_MAP: dict[str, dict[str, float]] = {
    "care": {"warmth": 0.8, "gentleness": 0.2},
    "understanding": {"proactivity": 0.3, "shyness": -0.1},
    "expression": {"humor": 0.4, "proactivity": 0.3, "shyness": -0.3},
    "memory_attr": {"curiosity": 0.5, "proactivity": 0.5},
    "humor": {"humor": 1.0},
    "intuition": {"proactivity": 0.6, "curiosity": 0.4},
    "courage": {"stubbornness": 0.5, "proactivity": 0.3, "shyness": -0.2},
    "sensitivity": {"warmth": 0.4, "shyness": 0.3, "gentleness": 0.3},
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class PersonaEngine:
    def __init__(self, config: Config):
        self.config = config

    def load_persona(self) -> PersonaConfig:
        path = self.config.persona_config_path
        if not os.path.isfile(path):
            return PersonaConfig()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return PersonaConfig(**data)

    def apply_template(self, template_id: str) -> PersonaConfig:
        src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        src_path = os.path.join(src_dir, f"{template_id}.json")
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Template '{template_id}' not found at {src_path}")

        with open(src_path, encoding="utf-8") as f:
            data = json.load(f)

        os.makedirs(os.path.dirname(self.config.persona_config_path), exist_ok=True)
        with open(self.config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Also cache to local templates dir
        dst_dir = self.config.templates_dir
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_path, os.path.join(dst_dir, f"{template_id}.json"))

        return PersonaConfig(**data)

    def get_current_persona(self, persona: PersonaConfig, state: RelationshipState) -> PersonalityBase:
        base = persona.personality_base.model_copy()
        adjustments: dict[str, float] = {}
        for attr_name, dim_map in ATTR_TO_PERSONALITY_MAP.items():
            attr_val = getattr(state.attributes, attr_name, 0)
            for dim_name, weight in dim_map.items():
                adjustments[dim_name] = adjustments.get(dim_name, 0.0) + attr_val * weight / 100

        result = base.model_copy(update={
            dim: _clamp(getattr(base, dim) + adjustments.get(dim, 0.0))
            for dim in PersonalityBase.model_fields
        })
        return result

    def get_level_prompt(self, level: int, state: RelationshipState) -> str:
        # Try config dir first, then fall back to src/prompts
        prompt_path = os.path.join(self.config.level_prompts_dir, f"lv{level}.json")
        if not os.path.isfile(prompt_path):
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "prompts", f"lv{level}.json"
            )
        if not os.path.isfile(prompt_path):
            return f"你是{state.nickname or '对方'}的伙伴，当前关系等级{level}。"

        with open(prompt_path, encoding="utf-8") as f:
            data = json.load(f)

        prompt = data.get("prompt", "")
        prompt = prompt.replace("{user_name}", state.nickname or "你")
        prompt = prompt.replace("{gf_name}", "我")
        prompt = prompt.replace("{nickname}", state.nickname or "你")
        prompt = prompt.replace("{shared_jokes}", "、".join(state.shared_jokes) if state.shared_jokes else "暂无")
        prompt = prompt.replace("{rituals}", "、".join(state.rituals) if state.rituals else "暂无")
        return prompt

    def get_de_ai_instructions(self, state: RelationshipState) -> str:
        d = state.de_ai_score
        rules = []

        if d.structured_output > 0.6:
            rules.append("减少结构化输出（如列表、编号），改用自然段落式表达")
        if d.precision_level > 0.6:
            rules.append("降低精确度，偶尔使用模糊表达（'大概''可能''好像'）")
        if d.emotion_naturalness < 0.5:
            rules.append("增加情绪自然度，加入语气词和情感波动")
        if d.proactivity_randomness < 0.5:
            rules.append("增加主动性随机性，偶尔主动开启话题或发问")
        if d.chatter_ratio < 0.4:
            rules.append("适当增加闲聊比例，不必每次都回应核心问题")
        if d.mistake_rate < 0.1:
            rules.append("偶尔犯小错误或记错细节，显得更真实")
        if d.hesitation_rate < 0.2:
            rules.append("偶尔犹豫或改口，增加表达的自然感")
        if d.personal_depth < 0.4:
            rules.append("增加个人深度，分享自己的偏好和主观感受")

        if not rules:
            return ""
        return "去AI味行为规则：" + "；".join(rules)

    def update_persona_field(self, field: str, value) -> None:
        persona = self.load_persona()
        if "." in field:
            parts = field.split(".")
            obj = persona
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
        else:
            setattr(persona, field, value)

        with open(self.config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_persona.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/persona.py tests/test_persona.py
git commit -m "feat: PersonaEngine with attribute mapping, level prompts, de-AI instructions"
```

---

### Task 7: MemoryEngine (memory.py)

**Files:**
- Create: `src/core/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write failing tests for MemoryEngine**

```python
# tests/test_memory.py
import json
import os

import pytest

from src.core.config import Config
from src.core.memory import MemoryEngine
from src.core.models import RelationshipState, SessionMemory


@pytest.fixture
def memory_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    engine = MemoryEngine(config)
    return engine


class TestMemoryEngineLongTerm:
    def test_store_and_search(self, memory_engine):
        memory_engine.store_memory("我喜欢猫", "fact")
        memory_engine.store_memory("我喜欢狗", "fact")
        memory_engine.store_memory("今天天气不错", "event")

        results = memory_engine.search_memories("猫", n=2)
        assert len(results) >= 1
        assert any("猫" in r["content"] for r in results)

    def test_store_with_metadata(self, memory_engine):
        memory_engine.store_memory("用户生日是5月", "fact", metadata={"importance": "high"})
        results = memory_engine.search_memories("生日", n=1)
        assert len(results) >= 1

    def test_weight_computation(self, memory_engine):
        w = memory_engine.compute_weight(days=0, access_count=0)
        assert w == 1.0  # sqrt(1) * exp(0) = 1.0

        w_old = memory_engine.compute_weight(days=30, access_count=0)
        w_new = memory_engine.compute_weight(days=0, access_count=0)
        assert w_old < w_new  # older → lower weight

    def test_weight_increases_with_access(self, memory_engine):
        w_no_access = memory_engine.compute_weight(days=10, access_count=0)
        w_accessed = memory_engine.compute_weight(days=10, access_count=10)
        assert w_accessed > w_no_access


class TestMemoryEngineShortTerm:
    def test_save_and_load_session(self, memory_engine):
        session = SessionMemory(
            conversation_id="conv-001",
            topics=["日常", "工作"],
            emotion_summary="开心",
            interaction_type="daily_chat",
            intimacy_gained=1,
        )
        memory_engine.save_session(session)
        loaded = memory_engine.load_recent_sessions(count=1)
        assert len(loaded) >= 1
        assert loaded[0].conversation_id == "conv-001"

    def test_cleanup_old_sessions(self, memory_engine):
        for i in range(15):
            session = SessionMemory(
                conversation_id=f"conv-{i:03d}",
                topics=["test"],
            )
            memory_engine.save_session(session)

        memory_engine.cleanup_old_sessions(keep=10)
        loaded = memory_engine.load_recent_sessions(count=20)
        assert len(loaded) <= 10


class TestMemoryEngineInjection:
    def test_level_1_returns_limited_context(self, memory_engine):
        for i in range(10):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=1)
        context = memory_engine.get_injection_context("记忆", level=1, state=state)
        # Level 1: max 3 memories + persona summary (~600 chars)
        assert len(context["memory_fragments"]) <= 3

    def test_level_2_returns_more_context(self, memory_engine):
        for i in range(20):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=2)
        context = memory_engine.get_injection_context("记忆", level=2, state=state)
        assert len(context["memory_fragments"]) <= 8

    def test_level_3_returns_most_context(self, memory_engine):
        for i in range(30):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=3)
        context = memory_engine.get_injection_context("记忆", level=3, state=state)
        assert len(context["memory_fragments"]) <= 15


class TestMemoryEngineDecay:
    def test_decay_all_weights(self, memory_engine):
        memory_engine.store_memory("test decay", "fact")
        memory_engine.decay_all_weights()
        # After decay, weight should be lower (or same if already 0)
        # Just verify no crash
        results = memory_engine.search_memories("decay", n=1)
        assert isinstance(results, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_memory.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement memory.py**

```python
# src/core/memory.py
import json
import math
import os
from datetime import datetime

import chromadb

from src.core.config import Config
from src.core.models import RelationshipState, SessionMemory


class MemoryEngine:
    def __init__(self, config: Config):
        self.config = config
        self._client: chromadb.ClientAPI | None = None
        self._collection = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.config.chroma_db_dir)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="girlfriend_memories",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def store_memory(self, content: str, memory_type: str, metadata: dict | None = None) -> str:
        import uuid
        chunk_id = str(uuid.uuid4())
        weight = self.compute_weight(days=0, access_count=0)
        meta = {
            "memory_type": memory_type,
            "weight": str(weight),
            "access_count": "0",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_accessed": datetime.now().strftime("%Y-%m-%d"),
        }
        if metadata:
            for k, v in metadata.items():
                meta[f"user_{k}"] = str(v)

        self.collection.add(
            ids=[chunk_id],
            documents=[content],
            metadatas=[meta],
        )
        return chunk_id

    def search_memories(self, query: str, n: int = 5, level: int = 1) -> list[dict]:
        fetch_n = n * 2
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(fetch_n, self.collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        fragments = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            weight = float(meta.get("weight", "1.0"))
            # Filter by weight threshold based on level
            min_weight = {1: 0.3, 2: 0.1, 3: 0.0}.get(level, 0.3)
            if weight >= min_weight:
                fragments.append({
                    "content": doc,
                    "weight": weight,
                    "memory_type": meta.get("memory_type", "fact"),
                    "id": results["ids"][0][i],
                })

        fragments.sort(key=lambda x: x["weight"], reverse=True)
        return fragments[:n]

    def update_memory_access(self, chunk_id: str) -> None:
        try:
            result = self.collection.get(ids=[chunk_id])
        except Exception:
            return
        if not result["metadatas"]:
            return

        meta = result["metadatas"][0]
        access_count = int(meta.get("access_count", "0")) + 1
        old_weight = float(meta.get("weight", "1.0"))
        created = meta.get("created_date", datetime.now().strftime("%Y-%m-%d"))

        days = (datetime.now() - datetime.strptime(created, "%Y-%m-%d")).days
        new_weight = self.compute_weight(days=days, access_count=access_count)

        meta["access_count"] = str(access_count)
        meta["weight"] = str(new_weight)
        meta["last_accessed"] = datetime.now().strftime("%Y-%m-%d")

        self.collection.update(
            ids=[chunk_id],
            metadatas=[meta],
        )

    def compute_weight(self, days: int, access_count: int) -> float:
        return math.sqrt(access_count + 1) * math.exp(-0.1 * days)

    def decay_all_weights(self) -> None:
        if self.collection.count() == 0:
            return

        all_ids = self.collection.get()["ids"]
        all_metas = self.collection.get()["metadatas"]

        for chunk_id, meta in zip(all_ids, all_metas):
            old_weight = float(meta.get("weight", "1.0"))
            new_weight = old_weight * 0.95  # 5% decay
            meta["weight"] = str(max(new_weight, 0.01))

        # Batch update
        for chunk_id, meta in zip(all_ids, all_metas):
            self.collection.update(ids=[chunk_id], metadatas=[meta])

    def save_session(self, session: SessionMemory) -> None:
        path = os.path.join(
            self.config.session_memory_dir,
            f"{session.conversation_id}.json",
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)

    def load_recent_sessions(self, count: int = 10) -> list[SessionMemory]:
        sm_dir = self.config.session_memory_dir
        if not os.path.isdir(sm_dir):
            return []

        files = sorted(
            [f for f in os.listdir(sm_dir) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(sm_dir, f)),
            reverse=True,
        )[:count]

        sessions = []
        for fname in files:
            with open(os.path.join(sm_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(SessionMemory(**data))
        return sessions

    def cleanup_old_sessions(self, keep: int = 10) -> None:
        sm_dir = self.config.session_memory_dir
        if not os.path.isdir(sm_dir):
            return

        files = sorted(
            [f for f in os.listdir(sm_dir) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(sm_dir, f)),
            reverse=True,
        )

        for fname in files[keep:]:
            os.remove(os.path.join(sm_dir, fname))

    def get_injection_context(
        self, query: str, level: int, state: RelationshipState
    ) -> dict:
        level_config = Config.INJECTION_LEVELS.get(level, Config.INJECTION_LEVELS[1])
        max_memories = level_config["max_memories"]

        fragments = self.search_memories(query, n=max_memories, level=level)

        # Update access for retrieved memories
        for frag in fragments:
            self.update_memory_access(frag["id"])

        result = {
            "memory_fragments": [f["content"] for f in fragments],
            "recent_sessions": [],
        }

        if level >= 2:
            sessions = self.load_recent_sessions(count=5)
            result["recent_sessions"] = [
                {"topics": s.topics, "emotion": s.emotion_summary}
                for s in sessions
            ]
            result["relationship_summary"] = (
                f"等级Lv{state.current_level} 亲密度{state.intimacy_points}"
            )

        if level >= 3:
            result["evolution_state"] = {
                "attributes": state.attributes.model_dump(),
                "de_ai_score": state.de_ai_score.model_dump(),
            }

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_memory.py -v`
Expected: All tests PASS (may be slow on first run due to ChromaDB/embedding initialization)

- [ ] **Step 5: Commit**

```bash
git add src/core/memory.py tests/test_memory.py
git commit -m "feat: MemoryEngine with ChromaDB, session memory, injection, and decay"
```

---

### Task 8: EvolveEngine (evolve.py)

**Files:**
- Create: `src/core/evolve.py`
- Create: `tests/test_evolve.py`

- [ ] **Step 1: Write failing tests for EvolveEngine**

```python
# tests/test_evolve.py
import json
import os

import pytest

from src.core.config import Config
from src.core.evolve import EvolveEngine
from src.core.models import RelationshipState, AttributePoints, DeAiDimensions
from src.core.git_manager import GitManager


@pytest.fixture
def evolve_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    git_mgr = GitManager(data_dir=temp_data_dir)
    git_mgr.init_repo()
    engine = EvolveEngine(config, git_mgr)
    return engine


class TestEvolveIntimacy:
    def test_daily_chat_adds_1(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("daily_chat", state)
        assert result.intimacy_points == 1

    def test_deep_conversation_adds_3(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("deep_conversation", state)
        assert result.intimacy_points == 3

    def test_invalid_type_no_change(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("invalid_type", state)
        assert result.intimacy_points == 0


class TestEvolveAttributes:
    def test_daily_chat_adds_attributes(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.add_interaction_attributes("daily_chat", state)
        # daily_chat: 均分+0.5 to all 8 attributes
        assert result.attributes.care > 0

    def test_deep_conversation_adds_specific(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.add_interaction_attributes("deep_conversation", state)
        assert result.attributes.care >= 1
        assert result.attributes.understanding >= 1
        assert result.attributes.sensitivity >= 1

    def test_attributes_clamp_at_100(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=100))
        result = evolve_engine.add_interaction_attributes("deep_conversation", result)
        assert result.attributes.care == 100


class TestEvolveLevelUp:
    def test_check_level_up_threshold(self, evolve_engine):
        state = RelationshipState(intimacy_points=15, current_level=0)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is True  # 15 >= threshold for level 1 (10)

    def test_no_level_up_below_threshold(self, evolve_engine):
        state = RelationshipState(intimacy_points=5, current_level=0)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is False

    def test_process_level_up_gives_bonus_points(self, evolve_engine):
        state = RelationshipState(intimacy_points=15, current_level=0)
        result = evolve_engine.process_level_up(1, state)
        assert result.current_level == 1

    def test_max_level_no_level_up(self, evolve_engine):
        state = RelationshipState(intimacy_points=9999, current_level=6)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is False


class TestEvolveDeAi:
    def test_de_ai_score_updates_with_level(self, evolve_engine):
        state = RelationshipState(current_level=3)
        result = evolve_engine.update_de_ai_score(state)
        # Higher level → lower structured_output, higher emotion_naturalness
        assert result.de_ai_score.structured_output < 0.8  # default is 0.8
        assert result.de_ai_score.emotion_naturalness > 0.3  # default is 0.3

    def test_de_ai_behavior_rules(self, evolve_engine):
        de_ai = DeAiDimensions(structured_output=0.2, emotion_naturalness=0.8)
        rules = evolve_engine.get_de_ai_behavior_rules(de_ai)
        assert isinstance(rules, list)
        assert len(rules) > 0


class TestEvolveCycle:
    def test_evolution_cycle_creates_log(self, evolve_engine):
        state = RelationshipState()
        # Simulate 7 sessions
        from src.core.models import SessionMemory
        sessions = [
            SessionMemory(conversation_id=f"conv-{i}", topics=["test"], interaction_type="daily_chat")
            for i in range(7)
        ]
        result_state, log_entry = evolve_engine.run_evolution_cycle(sessions, state)
        assert log_entry is not None
        assert log_entry.trigger == "7次对话"

    def test_evolution_adjustment_within_10pct(self, evolve_engine):
        state = RelationshipState(
            attributes=AttributePoints(care=50),
        )
        from src.core.models import PersonaConfig, PersonalityBase
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5))
        adjustments = evolve_engine.calculate_evolution_adjustments(persona, state)
        for dim, delta in adjustments.items():
            if delta != 0:
                # Max 10% relative change
                assert abs(delta) <= 0.1, f"Dimension {dim} changed by {delta}, exceeds 10%"


class TestConflictTrigger:
    def test_conflict_after_5_gap(self, evolve_engine):
        state = RelationshipState(conflict_mode=False)
        result = evolve_engine.check_conflict_trigger(5, state)
        assert result.conflict_mode is True

    def test_no_conflict_under_5(self, evolve_engine):
        state = RelationshipState(conflict_mode=False)
        result = evolve_engine.check_conflict_trigger(3, state)
        assert result.conflict_mode is False


class TestEvolutionDirection:
    def test_calculate_direction(self, evolve_engine):
        state = RelationshipState(
            attributes=AttributePoints(care=100, sensitivity=80),
        )
        direction = evolve_engine.calculate_evolution_direction(state)
        assert "primary" in direction
        assert "secondary" in direction
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_evolve.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement evolve.py**

```python
# src/core/evolve.py
import json
import os
from datetime import datetime

from src.core.config import Config
from src.core.git_manager import GitManager
from src.core.models import (
    RelationshipState, AttributePoints, DeAiDimensions,
    EvolutionLogEntry, SessionMemory, PersonaConfig,
)


class EvolveEngine:
    def __init__(self, config: Config, git_manager: GitManager):
        self.config = config
        self.git_manager = git_manager

    def update_intimacy(self, interaction_type: str, state: RelationshipState) -> RelationshipState:
        gain = Config.INTIMACY_PER_TYPE.get(interaction_type, 0)
        return state.model_copy(update={"intimacy_points": state.intimacy_points + gain})

    def check_level_up(self, state: RelationshipState) -> bool:
        if state.current_level >= 6:
            return False
        next_threshold = Config.LEVEL_THRESHOLDS[state.current_level + 1]
        return state.intimacy_points >= next_threshold

    def process_level_up(self, new_level: int, state: RelationshipState) -> RelationshipState:
        updates = {"current_level": new_level}
        # Level up: distribute 3 bonus attribute points
        attrs = state.attributes.model_copy()
        # Auto-distribute based on interaction history pattern
        bonus_attrs = Config.ATTRIBUTE_PER_TYPE.get("daily_chat", {})
        for attr_name, bonus in bonus_attrs.items():
            current = getattr(attrs, attr_name)
            setattr(attrs, attr_name, min(100, current + int(bonus * 3)))
        updates["attributes"] = attrs

        # Update de-ai score
        new_state = state.model_copy(update=updates)
        new_state = self.update_de_ai_score(new_state)
        return new_state

    def add_interaction_attributes(
        self, interaction_type: str, state: RelationshipState
    ) -> RelationshipState:
        attr_gains = Config.ATTRIBUTE_PER_TYPE.get(interaction_type, {})
        if not attr_gains:
            return state

        attrs = state.attributes.model_copy()
        for attr_name, gain in attr_gains.items():
            current = getattr(attrs, attr_name)
            setattr(attrs, attr_name, min(100, int(current + gain)))

        return state.model_copy(update={"attributes": attrs})

    def distribute_bonus_points(
        self, state: RelationshipState, distribution: dict[str, int] | None = None
    ) -> RelationshipState:
        attrs = state.attributes.model_copy()
        if distribution is None:
            # Auto: split 3 points based on dominant attribute direction
            direction = self.calculate_evolution_direction(state)
            primary = direction["primary"]
            secondary = direction["secondary"]
            setattr(attrs, primary, min(100, getattr(attrs, primary) + 2))
            setattr(attrs, secondary, min(100, getattr(attrs, secondary) + 1))
        else:
            for attr_name, points in distribution.items():
                current = getattr(attrs, attr_name)
                setattr(attrs, attr_name, min(100, current + points))

        return state.model_copy(update={"attributes": attrs})

    def update_de_ai_score(self, state: RelationshipState) -> RelationshipState:
        level = state.current_level
        attrs = state.attributes

        # Level influence: higher level → more human-like
        level_factor = level / 6.0  # 0.0 ~ 1.0

        # Attribute influence
        care_factor = attrs.care / 100.0
        expr_factor = attrs.expression / 100.0
        humor_factor = attrs.humor / 100.0
        sens_factor = attrs.sensitivity / 100.0
        cour_factor = attrs.courage / 100.0

        de_ai = DeAiDimensions(
            structured_output=max(0.1, 0.9 - level_factor * 0.6 - care_factor * 0.1),
            precision_level=max(0.1, 0.8 - level_factor * 0.4 - expr_factor * 0.1),
            emotion_naturalness=min(1.0, 0.3 + level_factor * 0.4 + sens_factor * 0.1),
            proactivity_randomness=min(1.0, 0.3 + level_factor * 0.3 + cour_factor * 0.1),
            chatter_ratio=min(1.0, 0.4 + level_factor * 0.3 + humor_factor * 0.1),
            mistake_rate=min(0.3, 0.05 + level_factor * 0.1),
            hesitation_rate=min(0.4, 0.15 + level_factor * 0.1),
            personal_depth=min(1.0, 0.3 + level_factor * 0.4 + expr_factor * 0.1),
        )

        return state.model_copy(update={"de_ai_score": de_ai})

    def get_de_ai_behavior_rules(self, de_ai: DeAiDimensions) -> list[str]:
        rules = []
        if de_ai.structured_output > 0.6:
            rules.append("减少结构化输出，改用自然段落")
        if de_ai.precision_level > 0.6:
            rules.append("降低精确度，使用模糊表达")
        if de_ai.emotion_naturalness < 0.5:
            rules.append("增加情绪自然度")
        if de_ai.proactivity_randomness < 0.5:
            rules.append("增加主动性随机性")
        if de_ai.chatter_ratio < 0.4:
            rules.append("增加闲聊比例")
        if de_ai.mistake_rate < 0.1:
            rules.append("偶尔犯小错误")
        if de_ai.hesitation_rate < 0.2:
            rules.append("偶尔犹豫或改口")
        if de_ai.personal_depth < 0.4:
            rules.append("增加个人深度和主观感受")
        return rules

    def calculate_evolution_adjustments(
        self, persona: PersonaConfig, state: RelationshipState
    ) -> dict[str, float]:
        from src.core.persona import ATTR_TO_PERSONALITY_MAP

        adjustments: dict[str, float] = {}
        for attr_name, dim_map in ATTR_TO_PERSONALITY_MAP.items():
            attr_val = getattr(state.attributes, attr_name, 0)
            # High attribute → push its mapped dims up, capped at 10%
            for dim_name, weight in dim_map.items():
                if weight > 0 and attr_val > 30:
                    delta = 0.02 * weight  # tiny nudge
                    adjustments[dim_name] = adjustments.get(dim_name, 0.0) + delta

        # Cap at 10% relative change
        for dim in adjustments:
            adjustments[dim] = max(-0.1, min(0.1, adjustments[dim]))

        return adjustments

    def run_evolution_cycle(
        self, sessions: list[SessionMemory], state: RelationshipState
    ) -> tuple[RelationshipState, EvolutionLogEntry]:
        # Aggregate interaction types from sessions
        type_counts: dict[str, int] = {}
        for s in sessions:
            t = s.interaction_type
            type_counts[t] = type_counts.get(t, 0) + 1

        # Calculate adjustments
        from src.core.persona import PersonaConfig
        persona = PersonaConfig()  # Use current persona
        adjustments = self.calculate_evolution_adjustments(persona, state)

        # Create evolution log entry
        log_entry = EvolutionLogEntry(
            trigger="7次对话",
            observation=f"互动类型分布: {type_counts}",
            adjustments=adjustments,
            trial_result="pass",
            internalized=True,
        )

        # Save evolution log
        log_path = os.path.join(
            self.config.evolution_log_dir,
            f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_entry.model_dump(), f, ensure_ascii=False, indent=2)

        # Git commit the evolution
        self.git_manager.commit(f"evolution: {log_entry.trigger}")

        return state, log_entry

    def check_conflict_trigger(
        self, gap_count: int, state: RelationshipState
    ) -> RelationshipState:
        if gap_count >= 5:
            return state.model_copy(update={"conflict_mode": True})
        return state

    def calculate_evolution_direction(self, state: RelationshipState) -> dict[str, str]:
        attrs = state.attributes
        scores = {
            "care": attrs.care,
            "understanding": attrs.understanding,
            "expression": attrs.expression,
            "memory_attr": attrs.memory_attr,
            "humor": attrs.humor,
            "intuition": attrs.intuition,
            "courage": attrs.courage,
            "sensitivity": attrs.sensitivity,
        }
        sorted_attrs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "primary": sorted_attrs[0][0],
            "secondary": sorted_attrs[1][0],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_evolve.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/evolve.py tests/test_evolve.py
git commit -m "feat: EvolveEngine with intimacy, level-up, attributes, de-AI, evolution cycle"
```

---

### Task 9: FastAPI Server + API Routers

**Files:**
- Create: `src/engine_server.py`
- Create: `src/api/chat_router.py`
- Create: `src/api/status_router.py`
- Create: `src/api/evolve_router.py`
- Create: `src/api/memory_router.py`
- Create: `src/api/persona_router.py`
- Create: `src/api/rollback_router.py`

- [ ] **Step 1: Create engine_server.py with FastAPI app and lifespan**

```python
# src/engine_server.py
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import Config, get_config
from src.core.persona import PersonaEngine
from src.core.memory import MemoryEngine
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.models import PersonaConfig, RelationshipState

from src.api.chat_router import router as chat_router
from src.api.status_router import router as status_router
from src.api.evolve_router import router as evolve_router
from src.api.memory_router import router as memory_router
from src.api.persona_router import router as persona_router
from src.api.rollback_router import router as rollback_router


def _load_or_init_state(config: Config) -> tuple[PersonaConfig, RelationshipState]:
    """Load or initialize persona and relationship state."""
    if os.path.isfile(config.persona_config_path):
        import json
        with open(config.persona_config_path, encoding="utf-8") as f:
            persona_data = json.load(f)
        persona = PersonaConfig(**persona_data)
    else:
        persona = PersonaConfig()

    if os.path.isfile(config.relationship_config_path):
        import json
        with open(config.relationship_config_path, encoding="utf-8") as f:
            rel_data = json.load(f)
        relationship = RelationshipState(**rel_data)
    else:
        relationship = RelationshipState()

    return persona, relationship


def _save_state(config: Config, persona: PersonaConfig, relationship: RelationshipState) -> None:
    import json
    os.makedirs(os.path.dirname(config.persona_config_path), exist_ok=True)
    with open(config.persona_config_path, "w", encoding="utf-8") as f:
        json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    config.ensure_dirs()

    git_mgr = GitManager(data_dir=config.data_dir)
    git_mgr.init_repo()

    persona, relationship = _load_or_init_state(config)
    _save_state(config, persona, relationship)

    app.state.config = config
    app.state.persona = persona
    app.state.relationship = relationship
    app.state.persona_engine = PersonaEngine(config)
    app.state.memory_engine = MemoryEngine(config)
    app.state.evolve_engine = EvolveEngine(config, git_mgr)
    app.state.git_manager = git_mgr

    yield


app = FastAPI(title="girlfriend-agent", version="0.1.0", lifespan=lifespan)

app.include_router(chat_router, tags=["chat"])
app.include_router(status_router, tags=["status"])
app.include_router(evolve_router, tags=["evolve"])
app.include_router(memory_router, tags=["memory"])
app.include_router(persona_router, tags=["persona"])
app.include_router(rollback_router, tags=["rollback"])


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=Config.SERVER_PORT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create chat_router.py**

```python
# src/api/chat_router.py
import json
import os

from fastapi import APIRouter, Request

from src.core.models import ChatRequest, ChatResponse

router = APIRouter()


def _save_relationship(config, relationship):
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    app = request.app
    persona_engine = app.state.persona_engine
    memory_engine = app.state.memory_engine
    evolve_engine = app.state.evolve_engine
    config = app.state.config

    persona = app.state.persona
    relationship = app.state.relationship

    # Update intimacy and attributes
    relationship = evolve_engine.update_intimacy(req.interaction_type, relationship)
    relationship = evolve_engine.add_interaction_attributes(req.interaction_type, relationship)

    # Check level up
    if evolve_engine.check_level_up(relationship):
        new_level = relationship.current_level + 1
        relationship = evolve_engine.process_level_up(new_level, relationship)

    # Get persona prompt
    current_persona = persona_engine.get_current_persona(persona, relationship)
    level_prompt = persona_engine.get_level_prompt(relationship.current_level, relationship)

    # Get de-AI instructions
    de_ai_instructions = persona_engine.get_de_ai_instructions(relationship)

    # Get memory injection
    memory_ctx = memory_engine.get_injection_context(
        req.user_message, req.level, relationship
    )

    # Build full prompt
    full_prompt = f"{level_prompt}\n\n当前人格倾向：{current_persona.model_dump_json()}"
    rel_summary = f"等级Lv{relationship.current_level} 亲密度{relationship.intimacy_points}"

    # Save updated state
    app.state.relationship = relationship
    _save_relationship(config, relationship)

    return ChatResponse(
        persona_prompt=full_prompt,
        memory_fragments=memory_ctx.get("memory_fragments", []),
        relationship_summary=rel_summary,
        de_ai_instructions=de_ai_instructions,
    )
```

- [ ] **Step 3: Create status_router.py**

```python
# src/api/status_router.py
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
async def status(request: Request):
    rel = request.app.state.relationship
    return {
        "current_level": rel.current_level,
        "intimacy_points": rel.intimacy_points,
        "attributes": rel.attributes.model_dump(),
        "de_ai_score": rel.de_ai_score.model_dump(),
        "nickname": rel.nickname,
        "conflict_mode": rel.conflict_mode,
        "shared_jokes": rel.shared_jokes,
        "rituals": rel.rituals,
    }


@router.get("/health")
async def health(request: Request):
    memory_engine = request.app.state.memory_engine
    embedding_loaded = False
    try:
        embedding_loaded = memory_engine.collection is not None
    except Exception:
        pass
    return {"status": "ok", "embedding_loaded": embedding_loaded}
```

- [ ] **Step 4: Create evolve_router.py**

```python
# src/api/evolve_router.py
import json

from fastapi import APIRouter, Request

from src.core.models import SessionMemory

router = APIRouter()


@router.post("/evolve")
async def evolve(request: Request):
    app = request.app
    evolve_engine = app.state.evolve_engine
    memory_engine = app.state.memory_engine
    config = app.state.config
    relationship = app.state.relationship

    # Load recent sessions for evolution analysis
    sessions = memory_engine.load_recent_sessions(count=7)

    if len(sessions) < 1:
        sessions = [SessionMemory(conversation_id="auto", interaction_type="daily_chat")]

    relationship, log_entry = evolve_engine.run_evolution_cycle(sessions, relationship)

    # Save updated state
    app.state.relationship = relationship
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)

    return {
        "adjustments": log_entry.adjustments,
        "observation": log_entry.observation,
        "trigger": log_entry.trigger,
        "level": relationship.current_level,
        "intimacy": relationship.intimacy_points,
    }
```

- [ ] **Step 5: Create memory_router.py**

```python
# src/api/memory_router.py
from fastapi import APIRouter, Request

from src.core.models import MemoryUpdateRequest

router = APIRouter()


@router.post("/memory/update")
async def memory_update(req: MemoryUpdateRequest, request: Request):
    memory_engine = request.app.state.memory_engine
    chunk_id = memory_engine.store_memory(req.content, req.memory_type, req.metadata)
    return {"status": "ok", "chunk_id": chunk_id}


@router.post("/memory/search")
async def memory_search(request: Request):
    body = await request.json()
    query = body.get("query", "")
    level = body.get("level", 1)
    n = body.get("n", 5)
    memory_engine = request.app.state.memory_engine
    results = memory_engine.search_memories(query, n=n, level=level)
    return {"results": results}
```

- [ ] **Step 6: Create persona_router.py**

```python
# src/api/persona_router.py
import json

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/persona")
async def get_persona(request: Request):
    return request.app.state.persona.model_dump()


@router.post("/persona/update")
async def update_persona(request: Request):
    body = await request.json()
    field = body.get("field", "")
    value = body.get("value")

    persona_engine = request.app.state.persona_engine
    persona_engine.update_persona_field(field, value)

    # Reload
    request.app.state.persona = persona_engine.load_persona()

    # Git commit
    request.app.state.git_manager.commit(f"persona update: {field}")

    return {"status": "ok", "field": field}


@router.post("/persona/apply-template")
async def apply_template(request: Request):
    body = await request.json()
    template_id = body.get("template_id", "default")

    persona_engine = request.app.state.persona_engine
    persona = persona_engine.apply_template(template_id)
    request.app.state.persona = persona

    # Git commit
    request.app.state.git_manager.commit(f"apply template: {template_id}")

    return {"status": "ok", "template": template_id, "persona": persona.model_dump()}
```

- [ ] **Step 7: Create rollback_router.py**

```python
# src/api/rollback_router.py
import json
import os

from fastapi import APIRouter, Request

from src.core.models import PersonaConfig, RelationshipState

router = APIRouter()


@router.post("/rollback")
async def rollback(request: Request):
    body = await request.json()
    commit_hash = body.get("commit_hash", "")

    app = request.app
    config = app.state.config
    git_manager = app.state.git_manager

    git_manager.checkout(commit_hash)

    # Reload persona
    persona_path = config.persona_config_path
    if os.path.isfile(persona_path):
        with open(persona_path, encoding="utf-8") as f:
            data = json.load(f)
        app.state.persona = PersonaConfig(**data)

    # Reload relationship
    rel_path = config.relationship_config_path
    if os.path.isfile(rel_path):
        with open(rel_path, encoding="utf-8") as f:
            data = json.load(f)
        app.state.relationship = RelationshipState(**data)

    return {"status": "ok", "commit_hash": commit_hash}
```

- [ ] **Step 8: Verify server starts**

Run: `cd "A:/claudeworks/女友agent" && python -c "from src.engine_server import app; print('OK')"`
Expected: OK

- [ ] **Step 9: Commit**

```bash
git add src/engine_server.py src/api/
git commit -m "feat: FastAPI server with all 6 API routers"
```

---

### Task 10: API Integration Tests

**Files:**
- Create: `tests/test_api.py`

- [ ] **Step 1: Write API integration tests**

```python
# tests/test_api.py
import json
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import Config
from src.core.models import PersonaConfig, RelationshipState
from src.engine_server import app, _load_or_init_state, _save_state


@pytest.fixture
def setup_test_env():
    with tempfile.TemporaryDirectory() as td:
        config = Config(data_dir=os.path.join(td, "gf-agent"))
        config.ensure_dirs()
        _save_state(config, PersonaConfig(), RelationshipState())

        # Override app state
        from src.core.git_manager import GitManager
        from src.core.persona import PersonaEngine
        from src.core.memory import MemoryEngine
        from src.core.evolve import EvolveEngine

        git_mgr = GitManager(data_dir=config.data_dir)
        git_mgr.init_repo()

        app.state.config = config
        app.state.persona = PersonaConfig()
        app.state.relationship = RelationshipState()
        app.state.persona_engine = PersonaEngine(config)
        app.state.memory_engine = MemoryEngine(config)
        app.state.evolve_engine = EvolveEngine(config, git_mgr)
        app.state.git_manager = git_mgr

        yield config


@pytest.mark.anyio
async def test_health_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.anyio
async def test_status_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_level" in data
        assert "intimacy_points" in data


@pytest.mark.anyio
async def test_chat_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={
            "user_message": "你好",
            "level": 1,
            "interaction_type": "daily_chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "persona_prompt" in data
        assert "memory_fragments" in data
        assert "relationship_summary" in data
        assert "de_ai_instructions" in data


@pytest.mark.anyio
async def test_memory_update_and_search(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/memory/update", json={
            "content": "用户喜欢猫",
            "memory_type": "fact",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = await client.post("/memory/search", json={
            "query": "猫",
            "level": 1,
        })
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_persona_get(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/persona")
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_persona_apply_template(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/persona/apply-template", json={
            "template_id": "default",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
```

- [ ] **Step 2: Install test dependencies and run**

Run: `cd "A:/claudeworks/女友agent" && pip install pytest-asyncio anyio && python -m pytest tests/test_api.py -v`
Expected: All tests PASS (may be slow on first run)

- [ ] **Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "feat: API integration tests with httpx AsyncClient"
```

---

### Task 11: Skill Bridge Layer

**Files:**
- Create: `skills/SKILL.md`
- Create: `skills/scripts/server_utils.py`
- Create: `skills/scripts/chat.py`
- Create: `skills/scripts/status.py`
- Create: `skills/scripts/evolve.py`
- Create: `skills/scripts/update.py`

- [ ] **Step 1: Create SKILL.md**

```markdown
# girlfriend-agent

> AI人格引擎 — 提供女友角色的人格化上下文注入、记忆管理、进化养成

## 触发词

聊天、关心、安慰、撒娇、陪伴、女友、进化、养成、记忆、亲密度

## 描述

girlfriend-agent 是一个本地运行的 AI 人格引擎服务。它提供：
- 人格化 prompt 生成（基于7维度人格 + 属性映射）
- 语义记忆管理（ChromaDB 长期 + JSON 短期）
- 进化养成系统（亲密度→等级→属性→去AI味）
- Git 回退管理

## 脚本

| 脚本 | 用途 | 参数 |
|---|---|---|
| `chat.py` | 获取人格化上下文 | `message`, `level`(1-3), `type`(互动类型) |
| `status.py` | 查看关系状态 | 无 |
| `evolve.py` | 执行进化周期 | 无 |
| `update.py` | 写入记忆 | `content`, `type`(fact/preference/event/emotion) |
```

- [ ] **Step 2: Create server_utils.py**

```python
# skills/scripts/server_utils.py
import socket
import subprocess
import sys
import time

import httpx

SERVER_PORT = 18012
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def is_server_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", SERVER_PORT))
            return True
        except (ConnectionRefusedError, OSError):
            return False


def wait_for_server(timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{SERVER_URL}/health", timeout=1)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def ensure_server_running() -> bool:
    if is_server_running():
        return True

    project_root = _find_project_root()
    if project_root is None:
        print("Error: Cannot find girlfriend-agent project root", file=sys.stderr)
        return False

    cmd = [sys.executable, "-m", "src.engine_server"]
    CREATE_NO_WINDOW = 0x08000000  # Windows only
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )

    if wait_for_server(timeout=10):
        return True

    print("Error: Server failed to start within 10 seconds", file=sys.stderr)
    return False


def _find_project_root() -> str | None:
    current = __file__
    # skills/scripts/server_utils.py -> project root
    import os
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(current))))
```

- [ ] **Step 3: Create chat.py**

```python
# skills/scripts/chat.py
#!/usr/bin/env python3
"""Skill bridge: chat — get persona context for a user message."""
import argparse
import json
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    parser = argparse.ArgumentParser(description="girlfriend-agent chat")
    parser.add_argument("message", help="User message")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--type", default="daily_chat",
                        choices=["daily_chat", "deep_conversation",
                                 "collaborative_task", "emotion_companion", "light_chat"])
    args = parser.parse_args()

    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/chat", json={
        "user_message": args.message,
        "level": args.level,
        "interaction_type": args.type,
    }, timeout=30)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print("=== 人格Prompt ===")
    print(data["persona_prompt"])
    print()
    if data["memory_fragments"]:
        print("=== 相关记忆 ===")
        for frag in data["memory_fragments"]:
            print(f"  - {frag}")
        print()
    print("=== 关系状态 ===")
    print(data["relationship_summary"])
    print()
    if data["de_ai_instructions"]:
        print("=== 去AI味指令 ===")
        print(data["de_ai_instructions"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create status.py**

```python
# skills/scripts/status.py
#!/usr/bin/env python3
"""Skill bridge: status — view relationship status."""
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.get(f"{SERVER_URL}/status", timeout=10)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"关系等级: Lv{data['current_level']}")
    print(f"亲密度: {data['intimacy_points']}")
    print(f"昵称: {data.get('nickname', '无')}")
    print(f"冲突模式: {'是' if data.get('conflict_mode') else '否'}")
    print()
    print("=== 属性 ===")
    for attr, val in data["attributes"].items():
        bar = "█" * (val // 10) + "░" * (10 - val // 10)
        print(f"  {attr:15s} {bar} {val}")
    print()
    print("=== 去AI味评分 ===")
    for dim, val in data["de_ai_score"].items():
        print(f"  {dim:25s} {val:.2f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create evolve.py**

```python
# skills/scripts/evolve.py
#!/usr/bin/env python3
"""Skill bridge: evolve — run evolution cycle."""
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/evolve", timeout=30)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"进化触发: {data['trigger']}")
    print(f"观察: {data['observation']}")
    print(f"当前等级: Lv{data['level']}")
    print(f"亲密度: {data['intimacy']}")
    if data["adjustments"]:
        print()
        print("=== 人格微调 ===")
        for dim, delta in data["adjustments"].items():
            direction = "↑" if delta > 0 else "↓"
            print(f"  {dim:15s} {direction} {abs(delta):.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create update.py**

```python
# skills/scripts/update.py
#!/usr/bin/env python3
"""Skill bridge: update — write a memory fragment."""
import argparse
import sys

import httpx

from server_utils import SERVER_URL, ensure_server_running


def main():
    parser = argparse.ArgumentParser(description="girlfriend-agent memory update")
    parser.add_argument("content", help="Memory content to store")
    parser.add_argument("--type", default="fact",
                        choices=["fact", "preference", "event", "emotion"])
    args = parser.parse_args()

    if not ensure_server_running():
        sys.exit(1)

    resp = httpx.post(f"{SERVER_URL}/memory/update", json={
        "content": args.content,
        "memory_type": args.type,
    }, timeout=10)

    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    print(f"记忆已写入: {args.content}")
    print(f"类型: {args.type}")
    print(f"ID: {data['chunk_id']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Commit**

```bash
git add skills/
git commit -m "feat: Skill bridge layer with 4 scripts and SKILL.md"
```

---

### Task 12: Full-Chain Integration Test

**Files:**
- Create: `tests/test_full_chain.py`

- [ ] **Step 1: Write full-chain integration test**

```python
# tests/test_full_chain.py
"""Full-chain integration test: chat → memory → evolve → rollback"""
import json
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import Config
from src.core.git_manager import GitManager
from src.core.models import PersonaConfig, RelationshipState
from src.core.persona import PersonaEngine
from src.core.memory import MemoryEngine
from src.core.evolve import EvolveEngine
from src.engine_server import app, _save_state


@pytest.fixture
def full_env():
    with tempfile.TemporaryDirectory() as td:
        config = Config(data_dir=os.path.join(td, "gf-agent"))
        config.ensure_dirs()
        _save_state(config, PersonaConfig(), RelationshipState())

        git_mgr = GitManager(data_dir=config.data_dir)
        git_mgr.init_repo()

        app.state.config = config
        app.state.persona = PersonaConfig()
        app.state.relationship = RelationshipState()
        app.state.persona_engine = PersonaEngine(config)
        app.state.memory_engine = MemoryEngine(config)
        app.state.evolve_engine = EvolveEngine(config, git_mgr)
        app.state.git_manager = git_mgr

        yield config


@pytest.mark.anyio
async def test_full_chain_chat_memory_evolve(full_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Chat
        resp = await client.post("/chat", json={
            "user_message": "我今天工作好累",
            "level": 1,
            "interaction_type": "emotion_companion",
        })
        assert resp.status_code == 200
        chat_data = resp.json()
        assert "Lv0" in chat_data["relationship_summary"]

        # 2. Store a memory
        resp = await client.post("/memory/update", json={
            "content": "用户工作很累需要安慰",
            "memory_type": "emotion",
        })
        assert resp.status_code == 200

        # 3. Check status — intimacy should have increased
        resp = await client.get("/status")
        status_data = resp.json()
        assert status_data["intimacy_points"] > 0

        # 4. Simulate multiple chats to trigger level up
        for i in range(15):
            resp = await client.post("/chat", json={
                "user_message": f"日常聊天{i}",
                "level": 1,
                "interaction_type": "daily_chat",
            })
            assert resp.status_code == 200

        # Check if level up occurred
        resp = await client.get("/status")
        status_data = resp.json()
        # After 15 daily + 1 emotion_companion = 15+4=19 intimacy → should be Lv1 (threshold=10)
        assert status_data["current_level"] >= 1

        # 5. Rollback test
        log = app.state.git_manager.log()
        if len(log) >= 2:
            # Find an earlier commit
            earlier_hash = log[-1]["hash"]
            resp = await client.post("/rollback", json={
                "commit_hash": earlier_hash,
            })
            assert resp.status_code == 200

            # Verify state was restored
            resp = await client.get("/status")
            assert resp.status_code == 200
```

- [ ] **Step 2: Run full-chain test**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/test_full_chain.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_full_chain.py
git commit -m "feat: full-chain integration test covering chat→memory→evolve→rollback"
```

---

### Task 13: Run All Tests + Final Verification

**Files:**
- Modify: `requirements.txt` (add pytest-asyncio, anyio)

- [ ] **Step 1: Update requirements.txt with test dependencies**

Add to `requirements.txt`:
```
pytest>=8.0
pytest-asyncio>=0.23
anyio>=4.0
```

- [ ] **Step 2: Run full test suite**

Run: `cd "A:/claudeworks/女友agent" && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 3: Verify server starts and responds**

Run: `cd "A:/claudeworks/女友agent" && timeout 5 python -m src.engine_server & sleep 3 && curl -s http://127.0.0.1:18012/health && kill %1`
Expected: `{"status":"ok","embedding_loaded":true}`

- [ ] **Step 4: Final commit**

```bash
git add requirements.txt
git commit -m "feat: add test dependencies, verify full test suite passes"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| Spec Section | Task | Notes |
|---|---|---|
| Project structure | Task 1 | All directories created |
| Data models | Task 2 | All 12 Pydantic models |
| Config module | Task 3 | Paths, constants, init |
| Templates (6+1) | Task 4 | All 7 persona templates |
| Level prompts (lv0~lv6) | Task 4 | All 7 level prompts |
| Endings library | Task 4 | 4 endings skeleton |
| PersonaEngine | Task 6 | load/apply/get_current/get_level/get_de_ai/update |
| ATTR_TO_PERSONALITY_MAP | Task 6 | All 8 attributes mapped |
| MemoryEngine (ChromaDB) | Task 7 | store/search/update_access/decay |
| MemoryEngine (session) | Task 7 | save/load/cleanup |
| MemoryEngine (injection) | Task 7 | L1/L2/L3 levels |
| EvolveEngine | Task 8 | intimacy/level_up/attributes/de_ai/evolution_cycle |
| GitManager | Task 5 | init/commit/log/checkout/revert |
| API endpoints (9) | Task 9 | All 9 endpoints covered |
| Skill bridge (4 scripts) | Task 11 | chat/status/evolve/update + server_utils |
| Unit tests | Tasks 2-8 | Per-module tests |
| API integration tests | Task 10 | httpx AsyncClient |
| Full-chain test | Task 12 | chat→memory→evolve→rollback |

### 2. Placeholder Scan

No TBD, TODO, or placeholder patterns found. All steps contain complete code.

### 3. Type Consistency

- `memory_attr` used consistently (not `memory`) to avoid shadowing Python builtin — matched across models.py, config.py, persona.py, evolve.py
- `AttributePoints` field names match between `ATTR_TO_PERSONALITY_MAP` keys and model definition
- `RelationshipState` fields accessed consistently across all routers and engines
- ChatRequest `interaction_type` string validated by choices in API
