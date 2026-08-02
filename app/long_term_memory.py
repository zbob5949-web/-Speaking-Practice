"""Turn grammar evidence into durable weakness memory and targeted drills."""

from collections import Counter
from typing import Any


def build_error_memory(feedback: list[dict[str, object]], limit: int = 5) -> dict[str, object]:
    counts = Counter(str(item.get("error_type") or item.get("rule_id") or "general") for item in feedback)
    frequent = counts.most_common(limit)
    weaknesses = [
        {
            "error_type": error_type,
            "frequency": frequency,
            "content": f"常犯语法错误：{error_type}",
            "evidence": f"最近练习中出现 {frequency} 次。",
            "confidence": min(0.95, 0.55 + frequency * 0.08),
        }
        for error_type, frequency in frequent
    ]
    exercises = [
        {
            "error_type": item["error_type"],
            "instruction": f"请在新的对话场景中完成 3 句练习，重点避免{item['error_type']}。",
            "prompt": f"用与 {item['error_type']} 相关的句型回答 NPC 的一个追问。",
        }
        for item in weaknesses
    ]
    return {"weaknesses": weaknesses, "targeted_exercises": exercises}
