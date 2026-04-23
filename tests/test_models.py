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
        assert all(0.0 <= getattr(pb, f) <= 1.0 for f in PersonalityBase.model_fields)

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
        for field in AttributePoints.model_fields:
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


class TestMemoryUpdateRequestValidation:
    def test_valid_memory_types(self):
        for mt in ["fact", "preference", "event", "emotion"]:
            mur = MemoryUpdateRequest(content="test", memory_type=mt)
            assert mur.memory_type == mt

    def test_invalid_memory_type_raises(self):
        with pytest.raises(Exception):
            MemoryUpdateRequest(content="test", memory_type="random_string")
