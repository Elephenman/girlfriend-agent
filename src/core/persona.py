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
