"""增强回合：规则+LLM 语法纠错、RAG 出处、错误报告、记忆与难度信号。

从 enhanced_main_v2 抽取，供增强入口与语音闭环共用。
"""
import json

from fastapi import HTTPException

from app.agents import ConversationAgent
from app import dependencies as deps
from app.completion import build_completion_status
from app.db import connect
from app.difficulty_agent import DifficultyAdjustmentAgent
from app.error_aggregation import aggregate_errors
from app.grammar_service import GrammarAnalysisService
from app.long_term_memory import build_error_memory


def _turn_reports(turns: list[dict[str, object]], feedback: list[dict[str, object]]) -> list[dict[str, object]]:
    reports = []
    for turn in [item for item in turns if item.get("speaker") == "user"]:
        report = aggregate_errors([item for item in feedback if item.get("turn_id") == turn.get("id")])
        report["turn_id"] = turn.get("id")
        reports.append(report)
    return reports


def _save_round_report(db_path, session_id: int, report: dict[str, object]) -> dict[str, object]:
    with connect(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO session_feedback (session_id, report) VALUES (?, ?)",
            (session_id, json.dumps(report, ensure_ascii=False)),
        )
        connection.commit()
        return {"id": cursor.lastrowid, "session_id": session_id, "report": report}


def _get_round_reports(db_path, session_id: int) -> list[dict[str, object]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, session_id, report, created_at FROM session_feedback WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [
        {"id": row["id"], "session_id": row["session_id"], "report": json.loads(row["report"]), "created_at": row["created_at"]}
        for row in rows
    ]


def _learning_signals(repo, profile: dict[str, object] | None, session_id: int, feedback: list[dict[str, object]]) -> dict[str, object]:
    memory = build_error_memory(feedback)
    if profile:
        for weakness in memory["weaknesses"]:
            repo.upsert_memory_item(
                int(profile["id"]),
                "weakness",
                str(weakness["content"]),
                str(weakness["evidence"]),
                float(weakness["confidence"]),
                None,
            )
    reports = _turn_reports(repo.get_turns(session_id), feedback)
    level = str(profile.get("current_level", "A2")) if profile else "A2"
    return {"memory": memory, "difficulty": DifficultyAdjustmentAgent().decide(level, reports), "turn_reports": reports}


def enhanced_user_turn(repo, session_id: int, text: str) -> dict[str, object]:
    """增强回合：保存用户回合 → 语法分析 → AI 回复 → 错误报告 → 记忆/难度信号。"""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_turn = repo.add_turn(session_id, "user", text)
    turns = repo.get_turns(session_id)
    profile = repo.get_latest_profile()
    plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else None
    objective = plan_day["objective"] if plan_day else "Practice speaking"
    level = profile["current_level"] if profile else "A2"
    goal = profile["learning_goal"] if profile else "Improve English"
    brief = None
    if plan_day:
        brief_row = repo.get_practice_brief(plan_day["id"])
        if brief_row:
            brief = json.loads(brief_row["brief_json"])

    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    grammar_feedback = GrammarAnalysisService().analyze(text, level, llm, f"topic={session['topic']}; objective={objective}")
    agent_response = ConversationAgent(llm, repo.get_prompt).reply(
        topic=session["topic"],
        objective=objective,
        user_level=level,
        learning_goal=goal,
        conversation=turns,
        practice_brief=brief,
    )
    assistant_turn = repo.add_turn(session_id, "assistant", agent_response["reply"])
    saved_feedback = repo.save_inline_feedback(session_id, user_turn["id"], grammar_feedback)

    round_report = aggregate_errors(saved_feedback)
    round_report["turn_id"] = user_turn["id"]
    _save_round_report(settings.database_path, session_id, round_report)

    all_feedback = repo.get_inline_feedback_for_session(session_id)
    signals = _learning_signals(repo, profile, session_id, all_feedback)
    completion = build_completion_status(
        repo.get_session(session_id) or session,
        repo.get_turns(session_id),
        all_feedback,
        brief or {},
    )

    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
        "round_error_report": round_report,
        "session_error_report": aggregate_errors(all_feedback),
        "learning_signals": signals,
        "hints": agent_response["hints"],
        "completion": completion,
    }
