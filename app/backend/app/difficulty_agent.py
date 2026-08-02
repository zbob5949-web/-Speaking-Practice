"""Deterministic dynamic-difficulty sub-agent.

It uses recent turn accuracy as the first signal. A model can later explain the
decision, but the level transition remains bounded and reproducible.
"""

from dataclasses import dataclass

from app.scenarios import LEVEL_ORDER, normalize_level


@dataclass(frozen=True)
class DifficultyDecision:
    current_level: str
    next_level: str
    accuracy_rate: float
    adjustment: str
    vocabulary_action: str
    sentence_action: str
    reason_zh: str

    def to_dict(self) -> dict[str, object]:
        return {
            "current_level": self.current_level,
            "next_level": self.next_level,
            "accuracy_rate": self.accuracy_rate,
            "adjustment": self.adjustment,
            "vocabulary_action": self.vocabulary_action,
            "sentence_action": self.sentence_action,
            "reason_zh": self.reason_zh,
        }


class DifficultyAdjustmentAgent:
    def decide(self, current_level: str, turn_reports: list[dict[str, object]]) -> dict[str, object]:
        level = normalize_level(current_level)
        if not turn_reports:
            return DifficultyDecision(level, level, 0.0, "same", "保持当前词汇范围", "保持当前句型复杂度", "暂无足够练习数据，先保持当前难度。").to_dict()
        correct_turns = sum(1 for report in turn_reports if not report.get("has_errors"))
        accuracy = round(correct_turns / len(turn_reports), 2)
        index = LEVEL_ORDER[level]
        if accuracy >= 0.8 and index < len(LEVEL_ORDER) - 1:
            next_level = list(LEVEL_ORDER)[index + 1]
            return DifficultyDecision(level, next_level, accuracy, "increase", "增加 10%-15% 新词汇并加入同义表达", "加入一个从句或追问", "最近正确率较高，逐步增加词汇和句型挑战。 ").to_dict()
        if accuracy < 0.6 and index > 0:
            next_level = list(LEVEL_ORDER)[index - 1]
            return DifficultyDecision(level, next_level, accuracy, "decrease", "优先复用高频词并减少生词", "拆成短句并提供句型支架", "最近错误较集中，先降低负荷并巩固薄弱点。 ").to_dict()
        return DifficultyDecision(level, level, accuracy, "same", "保持当前词汇范围", "保持当前句型复杂度", "当前正确率处于稳定区间，继续练习并观察趋势。 ").to_dict()
