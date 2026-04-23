import math
import uuid
from datetime import datetime

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
            created = datetime.strptime(self.created_date, "%Y-%m-%d")
            days = (datetime.now() - created).days
            self.weight = math.sqrt(1) * math.exp(-0.1 * days)


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

    @field_validator("interaction_type")
    @classmethod
    def validate_interaction_type(cls, v: str) -> str:
        from src.core.config import Config
        valid_types = set(Config.INTIMACY_PER_TYPE.keys())
        if v not in valid_types:
            raise ValueError(f"interaction_type must be one of {valid_types}, got '{v}'")
        return v


class ChatResponse(BaseModel):
    persona_prompt: str
    memory_fragments: list[str] = Field(default_factory=list)
    relationship_summary: str = ""
    de_ai_instructions: str = ""


class MemoryUpdateRequest(BaseModel):
    content: str
    memory_type: str = "fact"
    metadata: dict = Field(default_factory=dict)


class GraphNode(BaseModel):
    node_id: str
    node_type: str = "entity"  # entity, event, topic, emotion
    label: str
    properties: dict = Field(default_factory=dict)
    weight: float = 1.0
    created_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    last_accessed: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    access_count: int = 0


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str = "related_to"  # caused, related_to, followed_by, about, felt_during
    properties: dict = Field(default_factory=dict)
    weight: float = 1.0
    created_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


class GraphSearchResult(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    context_summary: str = ""


class EpisodicEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    description: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    entities: list[str] = Field(default_factory=list)
    emotion: str = ""
    causal_links: list[str] = Field(default_factory=list)


class ObservationPattern(BaseModel):
    topic_distribution: dict[str, int] = Field(default_factory=dict)
    emotion_tone: str = "neutral"  # positive, negative, neutral, mixed
    hidden_needs: list[str] = Field(default_factory=list)
    interaction_distribution: dict[str, int] = Field(default_factory=dict)
    summary: str = ""


class EvolutionState(BaseModel):
    consecutive_adjustments: dict[str, int] = Field(default_factory=dict)  # dim_name -> 连续调整次数
    total_cycles: int = 0
    last_adjustments: dict[str, float] = Field(default_factory=dict)
    evolution_progress: dict[str, float] = Field(default_factory=dict)  # 每个属性的进化进度 0.0~1.0
