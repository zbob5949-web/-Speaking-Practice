import json
import re
from typing import Any

from app.scenarios import tier_for_level


def user_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [turn for turn in turns if turn.get("speaker") == "user"]


def completion_turn_threshold(user_level: str | None) -> int:
    """不同水平建议收束对话的回合数：小白 3 轮、中级 6 轮、大神 8 轮。

    避免「大神级别的对话刚进行几轮就被询问是否结束」的问题：
    水平越高，需要完成的目标信息越多，对话应持续更久。
    """
    tier = tier_for_level(user_level or "")
    if tier == "advanced":
        return 8
    if tier == "intermediate":
        return 6
    return 3


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


# 告别句语义检测：对话双方任一方说出 goodbye 类告别语时，提示本轮结束并总结
FAREWELL_PATTERNS: tuple[str, ...] = (
    r"\bgoodbye\b",
    r"\bgood bye\b",
    r"\bbye[- ]bye\b",
    r"\bbye\b",
    r"\bfarewell\b",
    r"\bsee you (soon|later|tomorrow|tonight|around|next week)\b",
    r"\bsee you\b",
    r"\bsee ya\b",
    r"\bsee u\b",
    r"\btake care\b",
    r"\bgood ?night\b",
    r"\bhave a (good|nice|great|wonderful) day\b",
    r"\btalk to you later\b",
    r"\bcatch you later\b",
    r"\buntil next time\b",
)
FAREWELL_RE = re.compile("|".join(FAREWELL_PATTERNS), re.IGNORECASE)
FAREWELL_SCAN_TURNS = 4


def has_farewell(turns: list[dict[str, Any]]) -> bool:
    """检测最近几轮对话（用户/助手任一方）是否出现告别句。"""
    recent = [str(turn.get("text") or "") for turn in turns[-FAREWELL_SCAN_TURNS:]]
    return any(FAREWELL_RE.search(text) for text in recent)


def is_early_farewell(turns: list[dict[str, Any]]) -> bool:
    """前 3 轮内（用户回合数 ≤ 3）用户主动说出告别语：视为提前道别结束。

    一轮 = 用户一句 + AI 一句；只统计用户回合，AI 告别不算。
    用于：本次结束不计入练习（计划不推进）、无得分、不生成复盘。
    """
    user_texts = [str(turn.get("text") or "") for turn in user_turns(turns)]
    if len(user_texts) > 3:
        return False
    return any(FAREWELL_RE.search(text) for text in user_texts)


# 分数结算：100 分制，每处表达/单词错误适当扣分，major 扣 3、其余扣 2，最低 60 分
MAX_SCORE = 100
MIN_SCORE = 60
MAJOR_ERROR_DEDUCTION = 3
MINOR_ERROR_DEDUCTION = 2


def count_correction_errors(feedback: list[dict[str, Any]] | None) -> int:
    """统计纠错类（correction）错误条数，guidance / language_help 不算错误。"""
    if not feedback:
        return 0
    return sum(1 for item in feedback if item.get("feedback_type") == "correction")


def calculate_score(feedback: list[dict[str, Any]] | None) -> int:
    """按纠错数量结算 100 分制分数：major 扣 3 分、其余错误扣 2 分，最低 60 分。"""
    deduction = 0
    for item in feedback or []:
        if item.get("feedback_type") != "correction":
            continue
        deduction += MAJOR_ERROR_DEDUCTION if item.get("severity") == "major" else MINOR_ERROR_DEDUCTION
    return max(MIN_SCORE, MAX_SCORE - deduction)


def build_completion_summary(
    completion_type: str,
    turns: list[dict[str, Any]],
    practice_brief: dict[str, Any] | None = None,
    feedback: list[dict[str, Any]] | None = None,
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

    error_count = count_correction_errors(feedback)
    score = calculate_score(feedback)
    score_detail_zh = (
        f"本轮共发现 {error_count} 处表达或单词错误，扣除 {MAX_SCORE - score} 分。"
        if error_count > 0
        else "本轮表达清晰，未发现明显错误。"
    )

    return {
        "status": "completed",
        "completion_type": completion_type,
        "summary_zh": f"今天你完成了围绕「{goal}」的口语练习。",
        "strength_zh": "你完成了真实对话中的多轮回应，并保持了练习推进。",
        "next_focus_zh": next_focus,
        "reusable_sentences": reusable,
        "confidence": 0.6 if user_count < 3 else 0.75,
        "score": score,
        "score_detail_zh": score_detail_zh,
    }


def build_completion_status(
    session: dict[str, Any],
    turns: list[dict[str, Any]],
    feedback: list[dict[str, Any]] | None = None,
    practice_brief: dict[str, Any] | None = None,
    user_level: str | None = None,
) -> dict[str, Any]:
    return SessionCompletionEvaluator().evaluate(session, turns, feedback or [], practice_brief or {}, user_level or "A2")


class SessionCompletionEvaluator:
    def evaluate(
        self,
        session: dict[str, Any],
        turns: list[dict[str, Any]],
        feedback: list[dict[str, Any]],
        practice_brief: dict[str, Any],
        user_level: str = "A2",
    ) -> dict[str, Any]:
        if session.get("ended_at"):
            return {
                "status": "completed",
                "can_suggest_completion": False,
                "suggestion_reason_zh": "",
                "completed_summary": decode_completed_summary(session),
            }
        if session.get("scenario_id") == "free_talk":
            # 自由对话：无回合数限制，永不建议收束/生成总结，聊到用户主动结束为止
            return {
                "status": "in_progress",
                "can_suggest_completion": False,
                "suggestion_reason_zh": "",
                "completed_summary": None,
            }
        if has_farewell(turns):
            # 告别句语义检测：对话双方任一方说出 goodbye 类告别语，提示本轮结束并总结
            return {
                "status": "completion_suggested",
                "can_suggest_completion": True,
                "suggestion_reason_zh": "你们已经互相道别，本轮对话可以结束并生成总结。",
                "completed_summary": None,
            }
        if len(user_turns(turns)) < completion_turn_threshold(user_level) or has_major_blocker(feedback):
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
