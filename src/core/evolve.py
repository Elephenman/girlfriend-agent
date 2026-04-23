import json
import os
from datetime import datetime

from src.core.config import Config
from src.core.git_manager import GitManager
from src.core.models import (
    RelationshipState, DeAiDimensions,
    EvolutionLogEntry, SessionMemory, PersonaConfig,
    ObservationPattern, EvolutionState,
)
from src.core.persona import _clamp


class EvolveEngine:
    # 情境驱动微调映射
    CONTEXT_ADJUSTMENT_RULES: dict[str, dict[str, float]] = {
        "negative": {  # 用户压力大
            "warmth": 0.1,
            "proactivity": 0.05,
            "gentleness": 0.08,
        },
        "positive": {  # 用户开心
            "humor": 0.1,
            "gentleness": 0.05,
            "proactivity": 0.05,
        },
        "mixed": {  # 情绪波动
            "warmth": 0.05,
            "curiosity": 0.05,
        },
        "neutral": {},  # 无特殊调整
    }

    # 隐性需求调整映射
    NEED_ADJUSTMENT_MAP: dict[str, dict[str, float]] = {
        "需要更多关心和理解": {"warmth": 0.08, "gentleness": 0.05, "shyness": -0.03},
        "倾向深度交流，需要情感共鸣": {"curiosity": 0.08, "warmth": 0.05},
        "倾向轻松互动，需要快乐和陪伴": {"humor": 0.08, "proactivity": 0.05},
    }

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

        # Deduct the threshold points for the new level
        threshold = Config.LEVEL_THRESHOLDS[new_level]
        updates["intimacy_points"] = state.intimacy_points - threshold

        # Level up: distribute 3 bonus attribute points via auto-allocation
        attrs = state.attributes.model_copy()
        direction = self.calculate_evolution_direction(state)
        primary = direction["primary"]
        secondary = direction["secondary"]
        setattr(attrs, primary, min(100, getattr(attrs, primary) + 2))
        setattr(attrs, secondary, min(100, getattr(attrs, secondary) + 1))
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

    # ------------------------------------------------------------------
    # 观察与模式识别
    # ------------------------------------------------------------------

    def observe_patterns(self, sessions: list[SessionMemory]) -> ObservationPattern:
        """分析近7次对话的模式：话题分布、情绪基调、隐性需求"""
        if not sessions:
            return ObservationPattern(summary="无对话数据")

        # 1. 话题分布
        topic_dist: dict[str, int] = {}
        for s in sessions:
            for topic in s.topics:
                topic_dist[topic] = topic_dist.get(topic, 0) + 1

        # 2. 互动类型分布
        type_dist: dict[str, int] = {}
        for s in sessions:
            t = s.interaction_type
            type_dist[t] = type_dist.get(t, 0) + 1

        # 3. 情绪基调分析
        emotion_tone = self._analyze_emotion_tone(sessions)

        # 4. 隐性需求推断
        hidden_needs = self._infer_hidden_needs(sessions, topic_dist, emotion_tone)

        # 5. 生成摘要
        top_topics = sorted(topic_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        summary_parts: list[str] = []
        if top_topics:
            summary_parts.append(f"主要话题: {', '.join(t for t, _ in top_topics)}")
        summary_parts.append(f"情绪基调: {emotion_tone}")
        if hidden_needs:
            summary_parts.append(f"隐性需求: {', '.join(hidden_needs)}")
        top_types = sorted(type_dist.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_types:
            summary_parts.append(f"互动类型: {', '.join(f'{t}({c}次)' for t, c in top_types)}")

        return ObservationPattern(
            topic_distribution=topic_dist,
            emotion_tone=emotion_tone,
            hidden_needs=hidden_needs,
            interaction_distribution=type_dist,
            summary="; ".join(summary_parts),
        )

    def _analyze_emotion_tone(self, sessions: list[SessionMemory]) -> str:
        """分析情绪基调"""
        positive_kw = {"开心", "高兴", "快乐", "满意", "兴奋", "轻松", "愉快", "欣慰", "喜欢", "爱"}
        negative_kw = {"焦虑", "难过", "压力", "担心", "沮丧", "疲惫", "烦躁", "不开心", "累", "烦", "害怕", "紧张"}

        pos = 0
        neg = 0
        for s in sessions:
            emo = s.emotion_summary
            if any(k in emo for k in positive_kw):
                pos += 1
            elif any(k in emo for k in negative_kw):
                neg += 1

        total = pos + neg
        if total == 0:
            return "neutral"
        if pos > neg * 2:
            return "positive"
        if neg > pos * 2:
            return "negative"
        return "mixed"

    def _infer_hidden_needs(self, sessions: list[SessionMemory],
                            topic_dist: dict[str, int],
                            emotion_tone: str) -> list[str]:
        """从模式和情绪中推断隐性需求"""
        needs: list[str] = []

        # 压力相关
        if emotion_tone == "negative":
            needs.append("需要更多关心和理解")

        # 话题反复出现 → 深入需求
        for topic, count in topic_dist.items():
            if count >= 3:
                needs.append(f"对{topic}有持续关注，可能需要更深入的支持")

        # 互动类型推断
        type_dist: dict[str, int] = {}
        for s in sessions:
            t = s.interaction_type
            type_dist[t] = type_dist.get(t, 0) + 1

        deep_ratio = (type_dist.get("deep_conversation", 0) + type_dist.get("emotion_companion", 0)) / max(len(sessions), 1)
        if deep_ratio > 0.5:
            needs.append("倾向深度交流，需要情感共鸣")

        light_ratio = type_dist.get("light_chat", 0) / max(len(sessions), 1)
        if light_ratio > 0.5:
            needs.append("倾向轻松互动，需要快乐和陪伴")

        return needs[:5]  # 最多5个

    # ------------------------------------------------------------------
    # 情境驱动微调
    # ------------------------------------------------------------------

    def calculate_context_driven_adjustments(
        self, patterns: ObservationPattern, persona: PersonaConfig, state: RelationshipState
    ) -> dict[str, float]:
        """基于观察到的模式进行情境驱动微调"""
        adjustments: dict[str, float] = {}

        # 1. 基于情绪基调
        emotion_rules = self.CONTEXT_ADJUSTMENT_RULES.get(patterns.emotion_tone, {})
        for dim, delta in emotion_rules.items():
            adjustments[dim] = adjustments.get(dim, 0.0) + delta

        # 2. 基于隐性需求
        for need in patterns.hidden_needs:
            need_rules = self.NEED_ADJUSTMENT_MAP.get(need, {})
            for dim, delta in need_rules.items():
                adjustments[dim] = adjustments.get(dim, 0.0) + delta

        # 3. 基于属性映射（原有逻辑，作为基础）
        from src.core.persona import ATTR_TO_PERSONALITY_MAP
        for attr_name, dim_map in ATTR_TO_PERSONALITY_MAP.items():
            attr_val = getattr(state.attributes, attr_name, 0)
            for dim_name, weight in dim_map.items():
                if weight > 0 and attr_val > 30:
                    delta = 0.02 * weight
                    adjustments[dim_name] = adjustments.get(dim_name, 0.0) + delta

        # 4. 应用安全约束
        for dim in adjustments:
            adjustments[dim] = max(-0.1, min(0.1, adjustments[dim]))

        return adjustments

    def run_evolution_cycle(
        self, sessions: list[SessionMemory], state: RelationshipState
    ) -> tuple[RelationshipState, EvolutionLogEntry]:
        # 1. 观察模式
        patterns = self.observe_patterns(sessions)

        # 2. Load persona
        from src.core.persona import PersonaEngine
        persona_engine = PersonaEngine(self.config)
        persona = persona_engine.load_persona()

        # 3. 计算情境驱动微调
        adjustments = self.calculate_context_driven_adjustments(patterns, persona, state)

        # 4. 加载进化状态（跟踪连续调整）
        evo_state = self._load_evolution_state()

        # 5. 应用连续递减
        for dim in list(adjustments.keys()):
            consecutive = evo_state.consecutive_adjustments.get(dim, 0)
            if adjustments[dim] > 0:
                # 连续3次上调 → 减半
                if consecutive >= Config.CONSECUTIVE_DIMINISH_AFTER:
                    adjustments[dim] *= Config.CONSECUTIVE_DIMINISH_FACTOR
                # 超过5次 → 不再调整
                if consecutive >= 5:
                    adjustments[dim] = 0.0
            # 更新连续计数
            if adjustments[dim] > 0:
                evo_state.consecutive_adjustments[dim] = consecutive + 1
            elif adjustments[dim] < 0:
                evo_state.consecutive_adjustments[dim] = 0
            else:
                # 方向改变，重置计数
                if evo_state.last_adjustments.get(dim, 0) > 0 and adjustments.get(dim, 0) <= 0:
                    evo_state.consecutive_adjustments[dim] = 0

        # 5b. 上次有但本次缺失的维度 → 重置连续计数
        for dim in list(evo_state.consecutive_adjustments.keys()):
            if dim not in adjustments and evo_state.last_adjustments.get(dim, 0) > 0:
                evo_state.consecutive_adjustments[dim] = 0

        # 6. 应用调整到 persona
        base = persona.personality_base.model_copy()
        for dim_name, delta in adjustments.items():
            if hasattr(base, dim_name):
                current = getattr(base, dim_name)
                setattr(base, dim_name, _clamp(current + delta))
        persona.personality_base = base
        with open(self.config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)

        # 7. 更新进化状态
        evo_state.total_cycles += 1
        evo_state.last_adjustments = dict(adjustments)
        # 计算进化进度
        evo_state.evolution_progress = self._calculate_progress(state)
        self._save_evolution_state(evo_state)

        # 8. 写进化日志
        log_entry = EvolutionLogEntry(
            trigger=f"7次对话 (情绪:{patterns.emotion_tone})",
            observation=patterns.summary,
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

    def _load_evolution_state(self) -> EvolutionState:
        """加载进化状态"""
        evo_path = self.config.evolution_config_path
        if os.path.exists(evo_path):
            with open(evo_path, encoding="utf-8") as f:
                data = json.load(f)
            return EvolutionState(**data)
        return EvolutionState()

    def _save_evolution_state(self, evo_state: EvolutionState) -> None:
        """保存进化状态"""
        evo_path = self.config.evolution_config_path
        os.makedirs(os.path.dirname(evo_path), exist_ok=True)
        with open(evo_path, "w", encoding="utf-8") as f:
            json.dump(evo_state.model_dump(), f, ensure_ascii=False, indent=2)

    def _calculate_progress(self, state: RelationshipState) -> dict[str, float]:
        """计算各属性的进化进度 (0.0~1.0)"""
        attrs = state.attributes
        progress: dict[str, float] = {}
        for attr_name in ["care", "understanding", "expression", "memory_attr",
                          "humor", "intuition", "courage", "sensitivity"]:
            val = getattr(attrs, attr_name, 0)
            progress[attr_name] = val / 100.0
        return progress

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

    # ------------------------------------------------------------------
    # 进化终点方向与结局系统
    # ------------------------------------------------------------------

    def generate_evolution_ending(self, state: RelationshipState) -> dict:
        """根据属性分布生成进化结局描述"""
        direction = self.calculate_evolution_direction(state)
        primary = direction["primary"]
        secondary = direction["secondary"]

        ending = self._find_ending(primary, secondary)
        if not ending:
            # 尝试反向
            ending = self._find_ending(secondary, primary)
        if not ending:
            ending = {
                "id": f"{primary}_{secondary}_ending",
                "name": "未知结局",
                "description": "你们的羁绊独一无二，无法用已知的类型定义。",
                "behavior_pattern": "独特",
            }

        # 计算进化进度
        progress = self._calculate_direction_progress(state, primary, secondary)

        return {
            "ending": ending,
            "direction": direction,
            "progress": progress,
        }

    def _find_ending(self, primary: str, secondary: str) -> dict | None:
        """从结局库查找匹配的结局"""
        endings = self._load_endings()
        target_id = f"{primary}_{secondary}_ending"
        for e in endings:
            if e.get("id") == target_id:
                return e
            if e.get("primary_attr") == primary and e.get("secondary_attr") == secondary:
                return e
        return None

    def _load_endings(self) -> list[dict]:
        """加载结局库"""
        # 先从运行时数据目录加载（用户可自定义）
        custom_path = os.path.join(self.config.data_dir, "endings", "custom_endings.json")
        if os.path.exists(custom_path):
            with open(custom_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("endings", [])

        # 再从模板目录
        templates_path = os.path.join(self.config.templates_dir, "endings.json")
        if os.path.exists(templates_path):
            with open(templates_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("endings", [])

        # 最后从代码内置
        builtin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "endings", "endings.json")
        if os.path.exists(builtin_path):
            with open(builtin_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("endings", [])

        return []

    def _calculate_direction_progress(self, state: RelationshipState,
                                       primary: str, secondary: str) -> dict:
        """计算进化方向的进度"""
        primary_val = getattr(state.attributes, primary, 0)
        secondary_val = getattr(state.attributes, secondary, 0)

        # 进度 = (主属性 + 副属性) / 200
        overall = (primary_val + secondary_val) / 200.0

        return {
            "primary_attr": primary,
            "primary_value": primary_val,
            "secondary_attr": secondary,
            "secondary_value": secondary_val,
            "overall_progress": round(overall, 3),
        }

    def get_full_evolution_direction(self, state: RelationshipState) -> dict:
        """获取完整进化方向信息（含结局和进度）"""
        return self.generate_evolution_ending(state)

    # ------------------------------------------------------------------
    # 回退机制
    # ------------------------------------------------------------------

    def revert_last_evolution(self) -> dict:
        """回退最近一次进化调整

        通过 git revert 回退 persona.json 和 evolution_log 的变更，
        然后重新加载 persona 和进化状态。
        """
        success = self.git_manager.revert_evolution_commit()

        if success:
            # 重新加载 persona（已被 git revert 恢复）
            from src.core.persona import PersonaEngine
            persona_engine = PersonaEngine(self.config)
            persona = persona_engine.load_persona()

            # 重置进化状态中的连续计数
            evo_state = self._load_evolution_state()
            evo_state.consecutive_adjustments = {}
            evo_state.last_adjustments = {}
            self._save_evolution_state(evo_state)

            return {
                "success": True,
                "message": "已回退最近一次进化调整",
                "current_persona": persona.personality_base.model_dump(),
            }

        return {
            "success": False,
            "message": "回退失败：没有可回退的进化记录",
        }

    def revert_to_version(self, commit_hash: str) -> dict:
        """回退到指定版本的进化状态"""
        try:
            # Validate commit exists
            from git import Repo
            repo = Repo(self.git_manager.repo_path)
            repo.git.cat_file("-t", commit_hash)  # will raise if hash is invalid

            self.git_manager.checkout(commit_hash)

            # Commit the checkout result so HEAD reflects the reverted state
            self.git_manager.commit(f"rollback: revert to {commit_hash[:8]}")

            # 重新加载状态
            from src.core.persona import PersonaEngine
            persona_engine = PersonaEngine(self.config)
            persona = persona_engine.load_persona()

            # 重置进化状态
            evo_state = self._load_evolution_state()
            evo_state.consecutive_adjustments = {}
            evo_state.last_adjustments = {}
            self._save_evolution_state(evo_state)

            return {
                "success": True,
                "message": f"已回退到版本 {commit_hash[:8]}",
                "current_persona": persona.personality_base.model_dump(),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"回退失败: {str(e)}",
            }

    def evaluate_trial_result(
        self, sessions_after: list[SessionMemory],
        sessions_before: list[SessionMemory]
    ) -> str:
        """评估进化试探结果

        Returns: "pass" / "negative" / "neutral"
        """
        if not sessions_after:
            return "neutral"

        # 比较互动频率
        after_count = len(sessions_after)
        before_count = len(sessions_before)

        # 比较情绪
        def avg_emotion_score(sessions: list[SessionMemory]) -> float:
            positive_kw = {"开心", "高兴", "快乐", "满意", "兴奋", "轻松"}
            negative_kw = {"焦虑", "难过", "压力", "担心", "沮丧", "疲惫", "烦躁"}
            scores = []
            for s in sessions:
                emo = s.emotion_summary
                if any(k in emo for k in positive_kw):
                    scores.append(1)
                elif any(k in emo for k in negative_kw):
                    scores.append(-1)
                else:
                    scores.append(0)
            return sum(scores) / max(len(scores), 1)

        before_score = avg_emotion_score(sessions_before)
        after_score = avg_emotion_score(sessions_after)

        # 判断逻辑
        if after_count < before_count * 0.5:
            # 互动明显减少
            return "negative"
        if after_score < before_score - 0.5:
            # 情绪明显变差
            return "negative"
        if after_score > before_score + 0.3 or after_count > before_count:
            # 情绪变好或互动增加
            return "pass"
        return "neutral"
