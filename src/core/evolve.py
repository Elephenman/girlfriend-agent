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
            # Round up fractional gains (0.5 -> 1) and clamp at 100
            new_val = min(100, int(current + gain + 0.5))
            setattr(attrs, attr_name, new_val)

        return state.model_copy(update={"attributes": attrs})

    def distribute_bonus_points(
        self, state: RelationshipState, distribution: dict[str, int] | None = None
    ) -> RelationshipState:
        attrs = state.attributes.model_copy()
        if distribution is None:
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

        level_factor = level / 6.0

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
            for dim_name, weight in dim_map.items():
                if weight > 0 and attr_val > 30:
                    delta = 0.02 * weight
                    adjustments[dim_name] = adjustments.get(dim_name, 0.0) + delta

        for dim in adjustments:
            adjustments[dim] = max(-0.1, min(0.1, adjustments[dim]))

        return adjustments

    def run_evolution_cycle(
        self, sessions: list[SessionMemory], state: RelationshipState
    ) -> tuple[RelationshipState, EvolutionLogEntry]:
        type_counts: dict[str, int] = {}
        for s in sessions:
            t = s.interaction_type
            type_counts[t] = type_counts.get(t, 0) + 1

        persona = PersonaConfig()
        adjustments = self.calculate_evolution_adjustments(persona, state)

        log_entry = EvolutionLogEntry(
            trigger="7次对话",
            observation=f"互动类型分布: {type_counts}",
            adjustments=adjustments,
            trial_result="pass",
            internalized=True,
        )

        log_path = os.path.join(
            self.config.evolution_log_dir,
            f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_entry.model_dump(), f, ensure_ascii=False, indent=2)

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
