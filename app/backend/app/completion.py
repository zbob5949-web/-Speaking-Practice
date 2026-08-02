import json
from typing import Any


def user_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [turn for turn in turns if turn.get("speaker") == "user"]


def decode_completed_summary(session: dict[str, Any]) -> dict[str, Any] | None:
    raw_summary = session.get("summary")
    if not raw_summary:
        return None
    if isinstance(raw_summary, dict):
        return raw_summary
    try:
        return json.loads(raw_summary)
    except (TypeError, json.JSONDecodeError):
        return {"summary_zh": str(raw_summary)}


def has_major_blocker(feedback: list[dict[str, Any]]) -> bool:
    return any(item.get("severity") == "major" for item in feedback[-3:])


def build_completion_summary(
    completion_type: str,
    turns: list[dict[str, Any]],
    practice_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    brief = practice_brief or {}
    goal = brief.get("user_visible_goal") or brief.get("conversation_objective") or "今天的口语练习"
    user_count = len(user_turns(turns))
    next_focus = "下次可以继续围绕同一目标，补充更多关键信息。"
    if user_count < 3:
        next_focus = "今天练习时间较短，建议下次继续加强同一目标。"

    reusable = [
        "Could you help me with this?",
        "Let me explain the details.",
    ]
    target_expressions = brief.get("target_expressions") or []
    if target_expressions:
        first = target_expressions[0]
        reusable[0] = first.get("expression") if isinstance(first, dict) else str(first)

    return {
        "status": "completed",
        "completion_type": completion_type,
        "summary_zh": f"今天你完成了围绕「{goal}」的口语练习。",
        "strength_zh": "你完成了真实对话中的多轮回应，并保持了练习推进。",
        "next_focus_zh": next_focus,
        "reusable_sentences": reusable,
        "confidence": 0.6 if user_count < 3 else 0.75,
    }


def build_completion_status(
    session: dict[str, Any],
    turns: list[dict[str, Any]],
    feedback: list[dict[str, Any]] | None = None,
    practice_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return SessionCompletionEvaluator().evaluate(session, turns, feedback or [], practice_brief or {})


class SessionCompletionEvaluator:
    def evaluate(
        self,
        session: dict[str, Any],
        turns: list[dict[str, Any]],
        feedback: list[dict[str, Any]],
        practice_brief: dict[str, Any],
    ) -> dict[str, Any]:
        if session.get("ended_at"):
            return {
                "status": "completed",
                "can_suggest_completion": False,
                "suggestion_reason_zh": "",
                "completed_summary": decode_completed_summary(session),
            }
        if len(user_turns(turns)) < 3 or has_major_blocker(feedback):
            return {
                "status": "in_progress",
                "can_suggest_completion": False,
                "suggestion_reason_zh": "",
                "completed_summary": None,
            }
        return {
            "status": "completion_suggested",
            "can_suggest_completion": True,
            "suggestion_reason_zh": "今天的核心目标已经基本练到了，可以收束并生成今日总结。",
            "completed_summary": None,
        }
