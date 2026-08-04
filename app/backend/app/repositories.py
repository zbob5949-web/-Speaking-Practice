import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from app.db import connect
from app.models import OnboardingRequest


def row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    for db_key, api_key in [
        ("target_functions_json", "target_functions"),
        ("success_criteria_json", "success_criteria"),
    ]:
        if db_key in data:
            raw_value = data.pop(db_key)
            if raw_value:
                try:
                    data[api_key] = json.loads(raw_value)
                except json.JSONDecodeError:
                    data[api_key] = []
            else:
                data[api_key] = []
    return data


def decode_json(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def decode_agent_run(row: Any) -> dict[str, Any]:
    data = row_to_dict(row)
    data["input"] = decode_json(data.pop("input_json", None), {})
    data["tool_calls"] = decode_json(data.pop("tool_calls_json", None), [])
    data["output"] = decode_json(data.pop("output_json", None), {})
    return data


class CoachRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def save_profile(self, request: OnboardingRequest) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO user_profile (learning_goal, total_days, daily_minutes, current_level)
                VALUES (?, ?, ?, ?)
                """,
                (request.learning_goal, request.total_days, request.daily_minutes, request.current_level),
            )
            profile_id = cursor.lastrowid
            row = connection.execute("SELECT * FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
            return row_to_dict(row)

    def get_latest_profile(self) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1").fetchone()
            return row_to_dict(row) if row else None

    def get_all_profiles(self) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM user_profile ORDER BY id DESC").fetchall()
            return [row_to_dict(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
            return row_to_dict(row) if row else None

    def delete_profile(self, profile_id: int) -> None:
        with connect(self.db_path) as connection:
            connection.execute("DELETE FROM learning_plan WHERE profile_id = ?", (profile_id,))
            connection.execute("DELETE FROM user_profile WHERE id = ?", (profile_id,))
            connection.commit()

    def save_plan(self, profile_id: int, days: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            connection.execute("DELETE FROM learning_plan WHERE profile_id = ?", (profile_id,))
            for day in days:
                connection.execute(
                    """
                    INSERT INTO learning_plan (
                        profile_id, day_index, topic, scenario, objective, status,
                        skill_focus, communicative_task, target_functions_json, success_criteria_json, brief_seed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile_id,
                        day["day_index"],
                        day["topic"],
                        day["scenario"],
                        day["objective"],
                        day.get("status", "pending"),
                        day.get("skill_focus") if not isinstance(day.get("skill_focus"), list) else json.dumps(day.get("skill_focus"), ensure_ascii=False),
                        day.get("communicative_task") if not isinstance(day.get("communicative_task"), list) else json.dumps(day.get("communicative_task"), ensure_ascii=False),
                        json.dumps(day.get("target_functions", []), ensure_ascii=False) if isinstance(day.get("target_functions", []), list) else str(day.get("target_functions", [])),
                        json.dumps(day.get("success_criteria", []), ensure_ascii=False) if isinstance(day.get("success_criteria", []), list) else str(day.get("success_criteria", [])),
                        day.get("brief_seed"),
                    ),
                )
            rows = connection.execute(
                "SELECT * FROM learning_plan WHERE profile_id = ? ORDER BY day_index",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_plan(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM learning_plan WHERE profile_id = ? ORDER BY day_index",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_plan_day_by_id(self, plan_day_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM learning_plan WHERE id = ?",
                (plan_day_id,),
            ).fetchone()
            return row_to_dict(row) if row else None

    def mark_plan_day_status(self, plan_day_id: int, status: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "UPDATE learning_plan SET status = ? WHERE id = ?",
                (status, plan_day_id),
            )
            connection.commit()

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (session_id,)).fetchone()
            return row_to_dict(row) if row else None

    def complete_session(self, session_id: int, summary: dict[str, Any], overall_score: int = 3, mark_plan_completed: bool = True) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            session = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (session_id,)).fetchone()
            if not session:
                return None
            if session["ended_at"]:
                return row_to_dict(session)
            connection.execute(
                """
                UPDATE daily_sessions
                SET ended_at = CURRENT_TIMESTAMP, summary = ?, overall_score = ?
                WHERE id = ?
                """,
                (json.dumps(summary, ensure_ascii=False), overall_score, session_id),
            )
            if session["plan_day_id"] and mark_plan_completed:
                connection.execute(
                    "UPDATE learning_plan SET status = ? WHERE id = ?",
                    ("completed", session["plan_day_id"]),
                )
            connection.commit()
            completed = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (session_id,)).fetchone()
            return row_to_dict(completed)

    def create_session(
        self,
        plan_day_id: int | None,
        day_index: int,
        topic: str,
        scenario_id: str | None = None,
        profile_id: int | None = None,
    ) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO daily_sessions (plan_day_id, scenario_id, profile_id, day_index, topic)
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan_day_id, scenario_id, profile_id, day_index, topic),
            )
            row = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def get_or_create_session(
        self,
        plan_day_id: int | None,
        day_index: int,
        topic: str,
        scenario_id: str | None = None,
        profile_id: int | None = None,
    ) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            if plan_day_id is not None:
                # Query by plan_day_id instead of day_index to prevent cross-profile session resume
                row = connection.execute(
                    "SELECT * FROM daily_sessions WHERE plan_day_id = ? ORDER BY id DESC LIMIT 1",
                    (plan_day_id,)
                ).fetchone()
            elif scenario_id is not None:
                # Reuse the latest open session for the same scenario
                row = connection.execute(
                    """
                    SELECT * FROM daily_sessions
                    WHERE scenario_id = ? AND plan_day_id IS NULL
                      AND (ended_at IS NULL OR ended_at = '')
                    ORDER BY id DESC LIMIT 1
                    """,
                    (scenario_id,),
                ).fetchone()
            else:
                row = None
            if row:
                return row_to_dict(row)
            cursor = connection.execute(
                """
                INSERT INTO daily_sessions (plan_day_id, scenario_id, profile_id, day_index, topic)
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan_day_id, scenario_id, profile_id, day_index, topic),
            )
            saved = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(saved)

    def delete_open_scenario_sessions(self, profile_id: int | None, keep_scenario_id: str | None = None) -> int:
        """删除某画像下所有未结束的其他场景会话（连同回合与纠错记录）。

        用于「选择新场景后自动清掉上次场景的对话」：切换到新场景时调用，
        让每个场景始终以全新状态开始，避免再次进入时还残留上次对话。
        未传 profile_id 时不做删除（避免误删全局会话）。
        """
        if profile_id is None:
            return 0
        with connect(self.db_path) as connection:
            clauses = [
                "plan_day_id IS NULL",
                "scenario_id IS NOT NULL",
                "scenario_id != ''",
                "(ended_at IS NULL OR ended_at = '')",
                "(profile_id = ? OR profile_id IS NULL)",
            ]
            params: list[Any] = [profile_id]
            if keep_scenario_id is not None:
                clauses.append("scenario_id != ?")
                params.append(keep_scenario_id)
            rows = connection.execute(
                f"SELECT id FROM daily_sessions WHERE {' AND '.join(clauses)}",
                params,
            ).fetchall()
            ids = [row["id"] for row in rows]
            for session_id in ids:
                connection.execute(
                    "DELETE FROM inline_feedback WHERE session_id = ?", (session_id,)
                )
                connection.execute(
                    "DELETE FROM conversation_turns WHERE session_id = ?", (session_id,)
                )
                connection.execute(
                    "DELETE FROM daily_sessions WHERE id = ?", (session_id,)
                )
            connection.commit()
            return len(ids)


    def get_sessions(self, profile_id: int | None = None, limit: int = 60) -> list[dict[str, Any]]:
        """历史对话场景列表：优先按会话 profile_id 过滤，旧会话回退到 plan_day 归属。"""
        with connect(self.db_path) as connection:
            if profile_id is not None:
                rows = connection.execute(
                    """
                    SELECT ds.*, lp.profile_id AS plan_profile_id
                    FROM daily_sessions ds
                    LEFT JOIN learning_plan lp ON lp.id = ds.plan_day_id
                    WHERE ds.profile_id = ? OR lp.profile_id = ?
                    ORDER BY ds.id DESC
                    LIMIT ?
                    """,
                    (profile_id, profile_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT ds.*, lp.profile_id AS plan_profile_id FROM daily_sessions ds "
                    "LEFT JOIN learning_plan lp ON lp.id = ds.plan_day_id ORDER BY ds.id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            sessions = []
            for row in rows:
                session = row_to_dict(row)
                turn_count = connection.execute(
                    "SELECT COUNT(*) AS n FROM conversation_turns WHERE session_id = ?",
                    (session["id"],),
                ).fetchone()["n"]
                session["turn_count"] = int(turn_count)
                sessions.append(session)
            return sessions

    def add_favorite(self, profile_id: int, scenario_id: str) -> bool:
        with connect(self.db_path) as connection:
            try:
                connection.execute(
                    "INSERT INTO favorites (profile_id, scenario_id) VALUES (?, ?)",
                    (profile_id, scenario_id),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_favorite(self, profile_id: int, scenario_id: str) -> bool:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "DELETE FROM favorites WHERE profile_id = ? AND scenario_id = ?",
                (profile_id, scenario_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def list_favorites(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM favorites WHERE profile_id = ? ORDER BY id DESC",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def is_favorite(self, profile_id: int, scenario_id: str) -> bool:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT 1 AS one FROM favorites WHERE profile_id = ? AND scenario_id = ?",
                (profile_id, scenario_id),
            ).fetchone()
            return row is not None

    def add_turn(self, session_id: int, speaker: str, text: str) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(turn_index), 0) AS max_index FROM conversation_turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            turn_index = int(row["max_index"]) + 1
            cursor = connection.execute(
                "INSERT INTO conversation_turns (session_id, turn_index, speaker, text) VALUES (?, ?, ?, ?)",
                (session_id, turn_index, speaker, text),
            )
            saved = connection.execute("SELECT * FROM conversation_turns WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(saved)

    def get_turns(self, session_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM conversation_turns WHERE session_id = ? ORDER BY turn_index",
                (session_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def delete_turn_pair(self, session_id: int, user_turn_id: int) -> bool:
        with connect(self.db_path) as connection:
            user_turn = connection.execute(
                """
                SELECT * FROM conversation_turns
                WHERE id = ? AND session_id = ? AND speaker = 'user'
                """,
                (user_turn_id, session_id),
            ).fetchone()
            if not user_turn:
                return False

            assistant_turn = connection.execute(
                """
                SELECT * FROM conversation_turns
                WHERE session_id = ? AND turn_index = ? AND speaker = 'assistant'
                LIMIT 1
                """,
                (session_id, user_turn["turn_index"] + 1),
            ).fetchone()

            turn_ids = [user_turn_id]
            if assistant_turn:
                turn_ids.append(assistant_turn["id"])

            placeholders = ",".join("?" for _ in turn_ids)
            connection.execute("DELETE FROM inline_feedback WHERE turn_id = ?", (user_turn_id,))
            connection.execute(
                f"DELETE FROM conversation_turns WHERE id IN ({placeholders})",
                turn_ids,
            )
            connection.commit()
            return True

    def clear_session_history(self, session_id: int) -> bool:
        with connect(self.db_path) as connection:
            session = connection.execute(
                "SELECT * FROM daily_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not session:
                return False

            connection.execute("DELETE FROM inline_feedback WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,))
            connection.execute(
                """
                UPDATE daily_sessions
                SET ended_at = NULL, summary = NULL, overall_score = NULL
                WHERE id = ?
                """,
                (session_id,),
            )
            if session["plan_day_id"]:
                connection.execute(
                    "UPDATE learning_plan SET status = 'in_progress' WHERE id = ?",
                    (session["plan_day_id"],),
                )
            connection.commit()
            return True
    def save_inline_feedback(self, session_id: int, turn_id: int, feedback_list: list[dict[str, Any]]) -> list[dict[str, object]]:
        with connect(self.db_path) as connection:
            saved = []
            for item in feedback_list:
                cursor = connection.execute(
                    """
                    INSERT INTO inline_feedback
                    (session_id, turn_id, feedback_type, feedback_text, original_fragment, better_expression, reason_zh, example_sentence, severity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        turn_id,
                        item.get("feedback_type", "general"),
                        item.get("feedback_text", ""),
                        item.get("original_fragment"),
                        item.get("better_expression"),
                        item.get("reason_zh"),
                        item.get("example_sentence"),
                        item.get("severity"),
                    ),
                )
                saved.append(
                    {
                        "id": cursor.lastrowid,
                        "session_id": session_id,
                        "turn_id": turn_id,
                        "feedback_type": item.get("feedback_type", "general"),
                        "feedback_text": item.get("feedback_text", ""),
                        "original_fragment": item.get("original_fragment"),
                        "better_expression": item.get("better_expression"),
                        "reason_zh": item.get("reason_zh"),
                        "example_sentence": item.get("example_sentence"),
                        "severity": item.get("severity"),
                    }
                )
            connection.commit()
            return saved

    def get_prompt(self, name: str) -> str | None:
        from app.prompts import DEFAULT_PROMPTS
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT content FROM prompts WHERE name = ?", (name,)).fetchone()
            if row:
                return row["content"]
        return DEFAULT_PROMPTS.get(name)

    def update_prompt(self, name: str, content: str) -> bool:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO prompts (name, content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, content),
            )
            connection.commit()
            return True

    def get_all_prompts(self) -> list[dict[str, str]]:
        from app.prompts import DEFAULT_PROMPTS
        with connect(self.db_path) as connection:
            rows = connection.execute("SELECT name, content, updated_at FROM prompts").fetchall()
            db_prompts = {row["name"]: dict(row) for row in rows}
            
            result = []
            for name, content in DEFAULT_PROMPTS.items():
                if name in db_prompts:
                    result.append(db_prompts[name])
                else:
                    result.append({"name": name, "content": content, "updated_at": ""})
            return result

    def get_inline_feedback_for_session(self, session_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM inline_feedback WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def save_daily_review(self, profile_id: int, review_date: str, status: str, user_report: dict, structured_analysis: dict, source_session_ids: list[int], raw_agent_output: str) -> dict[str, Any]:
        import json
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO daily_reviews (profile_id, review_date, status, user_report_json, structured_analysis_json, source_session_ids_json, raw_agent_output)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, review_date, status, json.dumps(user_report), json.dumps(structured_analysis), json.dumps(source_session_ids), raw_agent_output)
            )
            row = connection.execute("SELECT * FROM daily_reviews WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def get_daily_review(self, profile_id: int, review_date: str) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM daily_reviews WHERE profile_id = ? AND review_date = ? ORDER BY id DESC LIMIT 1",
                (profile_id, review_date),
            ).fetchone()
            return row_to_dict(row) if row else None

    def get_daily_reviews(self, profile_id: int, limit: int = 5) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM daily_reviews
                WHERE profile_id = ?
                ORDER BY review_date DESC, id DESC
                LIMIT ?
                """,
                (profile_id, limit),
            ).fetchall()
        reviews = []
        for row in rows:
            review = row_to_dict(row)
            review["user_report"] = decode_json(review.pop("user_report_json", None), {})
            review["structured_analysis"] = decode_json(review.pop("structured_analysis_json", None), {})
            review["source_session_ids"] = decode_json(review.pop("source_session_ids_json", None), [])
            reviews.append(review)
        return reviews

    def get_unreviewed_session_dates(self, profile_id: int, today: str) -> list[str]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT DATE(ds.started_at) AS review_date
                FROM daily_sessions ds
                JOIN learning_plan lp ON lp.id = ds.plan_day_id
                JOIN conversation_turns ct ON ct.session_id = ds.id AND ct.speaker = 'user'
                LEFT JOIN daily_reviews dr
                  ON dr.profile_id = lp.profile_id
                 AND dr.review_date = DATE(ds.started_at)
                WHERE lp.profile_id = ?
                  AND DATE(ds.started_at) <= DATE(?)
                  AND dr.id IS NULL
                ORDER BY review_date ASC
                """,
                (profile_id, today),
            ).fetchall()
            return [row["review_date"] for row in rows]

    def get_review_sessions_for_date(self, profile_id: int, review_date: str) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT ds.*
                FROM daily_sessions ds
                JOIN learning_plan lp ON lp.id = ds.plan_day_id
                WHERE lp.profile_id = ?
                  AND DATE(ds.started_at) = DATE(?)
                ORDER BY ds.id ASC
                """,
                (profile_id, review_date),
            ).fetchall()
            sessions = []
            for row in rows:
                session = row_to_dict(row)
                turn_rows = connection.execute(
                    "SELECT * FROM conversation_turns WHERE session_id = ? ORDER BY turn_index",
                    (session["id"],),
                ).fetchall()
                session["turns"] = [row_to_dict(turn_row) for turn_row in turn_rows]
                sessions.append(session)
            return sessions

    def save_memory_item(self, profile_id: int, category: str, content: str, evidence: str, confidence: float, status: str, source_review_id: int) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO memory_items (profile_id, category, content, evidence, confidence, status, source_review_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, category, content, evidence, confidence, status, source_review_id)
            )
            row = connection.execute("SELECT * FROM memory_items WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def upsert_memory_item(
        self,
        profile_id: int,
        category: str,
        content: str,
        evidence: str,
        confidence: float,
        source_review_id: int | None,
    ) -> dict[str, Any]:
        normalized_content = " ".join(content.strip().lower().split())
        with connect(self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT * FROM memory_items
                WHERE profile_id = ?
                  AND category = ?
                  AND lower(content) = ?
                  AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
                (profile_id, category, normalized_content),
            ).fetchone()
            if existing:
                existing_evidence = existing["evidence"] or ""
                merged_evidence = (
                    existing_evidence
                    if evidence in existing_evidence
                    else "\n".join(part for part in [existing_evidence, evidence] if part)
                )
                connection.execute(
                    """
                    UPDATE memory_items
                    SET evidence = ?,
                        confidence = ?,
                        source_review_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        merged_evidence,
                        max(float(existing["confidence"]), confidence),
                        source_review_id,
                        existing["id"],
                    ),
                )
                connection.commit()
                row = connection.execute(
                    "SELECT * FROM memory_items WHERE id = ?",
                    (existing["id"],),
                ).fetchone()
                return row_to_dict(row)

            cursor = connection.execute(
                """
                INSERT INTO memory_items (profile_id, category, content, evidence, confidence, status, source_review_id)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (profile_id, category, content, evidence, confidence, source_review_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM memory_items WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def save_plan_adjustment(self, target_plan_day_id: int, source_review_id: int, adjustment_type: str, title: str, rationale: str, instruction: str, priority: str, status: str, expires_after_days: int) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO plan_adjustments (target_plan_day_id, source_review_id, adjustment_type, title, rationale, instruction, priority, status, expires_after_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (target_plan_day_id, source_review_id, adjustment_type, title, rationale, instruction, priority, status, expires_after_days)
            )
            row = connection.execute("SELECT * FROM plan_adjustments WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def get_active_memory_items(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM memory_items WHERE profile_id = ? AND status = 'active' ORDER BY id ASC",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_memory_items(self, profile_id: int, status: str = "active") -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM memory_items
                WHERE profile_id = ? AND status = ?
                ORDER BY confidence DESC, updated_at DESC, id DESC
                """,
                (profile_id, status),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_active_plan_adjustments(self, plan_day_id: int, today: str | None = None) -> list[dict[str, Any]]:
        current_date = today or date.today().isoformat()
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM plan_adjustments
                WHERE target_plan_day_id = ?
                  AND status = 'active'
                  AND DATE(created_at, '+' || expires_after_days || ' day') >= DATE(?)
                ORDER BY id ASC
                """,
                (plan_day_id, current_date),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_plan_adjustments_for_profile(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT pa.*
                FROM plan_adjustments pa
                JOIN learning_plan lp ON lp.id = pa.target_plan_day_id
                WHERE lp.profile_id = ? AND pa.status = 'active'
                ORDER BY pa.created_at DESC, pa.id DESC
                """,
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_growth_summary(self, profile_id: int) -> dict[str, Any]:
        reviews = self.get_daily_reviews(profile_id, limit=5)
        return {
            "latest_review": reviews[0] if reviews else None,
            "recent_reviews": reviews,
            "active_memory": self.get_memory_items(profile_id),
            "active_adjustments": self.get_plan_adjustments_for_profile(profile_id),
        }

    def get_latest_completed_daily_review(self, profile_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM daily_reviews
                WHERE profile_id = ? AND status = 'completed'
                ORDER BY review_date DESC, id DESC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
            return row_to_dict(row) if row else None

    def save_practice_brief(self, plan_day_id: int, brief: dict) -> dict[str, Any]:
        import json
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO practice_briefs (plan_day_id, brief_json) VALUES (?, ?)",
                (plan_day_id, json.dumps(brief))
            )
            row = connection.execute("SELECT * FROM practice_briefs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

    def get_practice_brief(self, plan_day_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM practice_briefs WHERE plan_day_id = ? ORDER BY id DESC LIMIT 1",
                (plan_day_id,)
            ).fetchone()
            return row_to_dict(row) if row else None

    def save_agent_run(
        self,
        profile_id: int | None,
        plan_day_id: int | None,
        session_id: int | None,
        agent_name: str,
        trigger_source: str,
        input_data: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        output_data: dict[str, Any],
        validation_status: str,
        error_message: str | None,
    ) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_runs (
                  profile_id, plan_day_id, session_id, agent_name, trigger_source,
                  input_json, tool_calls_json, output_json, validation_status, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    plan_day_id,
                    session_id,
                    agent_name,
                    trigger_source,
                    json.dumps(input_data, ensure_ascii=False),
                    json.dumps(tool_calls, ensure_ascii=False),
                    json.dumps(output_data, ensure_ascii=False),
                    validation_status,
                    error_message,
                ),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM agent_runs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return decode_agent_run(row)

    def get_agent_runs(self, profile_id: int, limit: int = 10) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM agent_runs
                WHERE profile_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (profile_id, limit),
            ).fetchall()
            return [decode_agent_run(row) for row in rows]

