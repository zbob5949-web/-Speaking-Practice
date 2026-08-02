# Learning Loop Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `/api/daily-review/run-due` into a working daily learning-loop pipeline that reviews due sessions, saves long-term memory, stores plan adjustments, and prepares the next practice brief.

**Architecture:** Keep the first production slice small and deterministic. Repository helpers identify reviewable session dates, aggregate sessions and turns, read active memory/adjustments, and enforce idempotency. The FastAPI endpoint orchestrates existing agents in this order: DailyReviewAgent -> MemoryAgent -> PlanAdaptationAgent -> ScenarioDesignAgent.

**Tech Stack:** FastAPI, SQLite, Python, Pytest

---

## File Structure

- `app/backend/app/repositories.py`: Add query helpers for due dates, session aggregation, active memory, latest review, active adjustments, next pending plan day, and idempotent brief replacement.
- `app/backend/app/main.py`: Replace the current `/api/daily-review/run-due` stub with the end-to-end orchestration.
- `app/backend/tests/test_repositories.py`: Add focused repository tests for due-date detection and aggregation helpers.
- `app/backend/tests/test_api.py`: Add endpoint tests for full pipeline execution and idempotency.

## Pipeline Rules

- Only review dates earlier than today.
- Only review dates that have at least one user turn.
- Do not create duplicate `daily_reviews` for the same `profile_id + review_date`.
- Save memory items only from `MemoryAgent.extract_memory(...)[\"upserts\"]`.
- Save plan adjustments only when an adjustment can be matched to an upcoming plan day.
- Generate or replace the next pending day's `practice_brief` after saving adjustments.
- Return `processed_days` as the number of new completed daily reviews created.

---

### Task 1: Repository Query Helpers

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `app/backend/tests/test_repositories.py`:

```python
from app.db import connect, init_db
from app.models import OnboardingRequest
from app.repositories import CoachRepository


def test_repository_finds_unreviewed_session_dates(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=2,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"},
            {"day_index": 2, "topic": "Hotel", "scenario": "Check in", "objective": "Ask for room"},
        ],
    )
    session = repo.create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "assistant", "Welcome.")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))

    dates = repo.get_unreviewed_session_dates(profile["id"], today="2026-06-22")

    assert dates == ["2026-06-20"]


def test_repository_skips_already_reviewed_session_dates(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=1,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"}],
    )
    session = repo.create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))
    repo.save_daily_review(profile["id"], "2026-06-20", "completed", {"summary": "Done"}, {}, [session["id"]], "")

    dates = repo.get_unreviewed_session_dates(profile["id"], today="2026-06-22")

    assert dates == []


def test_repository_aggregates_review_sessions_with_turns(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=1,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"}],
    )
    session = repo.create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "assistant", "Welcome.")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))

    sessions = repo.get_review_sessions_for_date(profile["id"], "2026-06-20")

    assert sessions[0]["id"] == session["id"]
    assert sessions[0]["topic"] == "Airport"
    assert sessions[0]["turns"][1]["speaker"] == "user"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest app/backend/tests/test_repositories.py::test_repository_finds_unreviewed_session_dates app/backend/tests/test_repositories.py::test_repository_skips_already_reviewed_session_dates app/backend/tests/test_repositories.py::test_repository_aggregates_review_sessions_with_turns -v
```

Expected: FAIL with missing repository methods.

- [ ] **Step 3: Implement minimal repository helpers**

Add these methods to `CoachRepository` in `app/backend/app/repositories.py`:

```python
    def get_daily_review(self, profile_id: int, review_date: str) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM daily_reviews WHERE profile_id = ? AND review_date = ? ORDER BY id DESC LIMIT 1",
                (profile_id, review_date),
            ).fetchone()
            return row_to_dict(row) if row else None

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
                  AND DATE(ds.started_at) < DATE(?)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest app/backend/tests/test_repositories.py::test_repository_finds_unreviewed_session_dates app/backend/tests/test_repositories.py::test_repository_skips_already_reviewed_session_dates app/backend/tests/test_repositories.py::test_repository_aggregates_review_sessions_with_turns -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "feat: add learning loop repository queries"
```

### Task 2: Repository Loop State Helpers

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing tests**

Add this test to `app/backend/tests/test_repositories.py`:

```python
def test_repository_reads_loop_state_for_next_practice(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=2,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass", "status": "completed"},
            {"day_index": 2, "topic": "Hotel", "scenario": "Check in", "objective": "Ask for room", "status": "pending"},
        ],
    )
    review = repo.save_daily_review(profile["id"], "2026-06-20", "completed", {"summary": "Done"}, {"issue": "grammar"}, [], "")
    memory = repo.save_memory_item(profile["id"], "weakness", "grammar", "daily review", 0.8, "active", review["id"])
    adjustment = repo.save_plan_adjustment(plan[1]["id"], review["id"], "focus", "Grammar focus", "Repeated issue", "Practice past tense", "high", "active", 3)

    assert repo.get_active_memory_items(profile["id"])[0]["id"] == memory["id"]
    assert repo.get_next_pending_plan_day(profile["id"])["id"] == plan[1]["id"]
    assert repo.get_active_plan_adjustments(plan[1]["id"])[0]["id"] == adjustment["id"]
    assert repo.get_latest_completed_daily_review(profile["id"])["id"] == review["id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest app/backend/tests/test_repositories.py::test_repository_reads_loop_state_for_next_practice -v
```

Expected: FAIL with missing repository methods.

- [ ] **Step 3: Implement minimal repository helpers**

Add these methods to `CoachRepository`:

```python
    def get_active_memory_items(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM memory_items WHERE profile_id = ? AND status = 'active' ORDER BY id ASC",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_next_pending_plan_day(self, profile_id: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM learning_plan
                WHERE profile_id = ? AND status = 'pending'
                ORDER BY day_index ASC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
            return row_to_dict(row) if row else None

    def get_active_plan_adjustments(self, plan_day_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM plan_adjustments WHERE target_plan_day_id = ? AND status = 'active' ORDER BY id ASC",
                (plan_day_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest app/backend/tests/test_repositories.py::test_repository_reads_loop_state_for_next_practice -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "feat: add learning loop state queries"
```

### Task 3: End-to-End Run-Due Pipeline

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write the failing API test**

Replace `test_run_due_reviews` in `app/backend/tests/test_api.py` with this test:

```python
def test_run_due_reviews_executes_learning_loop_pipeline(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "每日学习复盘" in system_prompt:
                assert "Airport" in user_prompt
                return '{"user_report": {"summary": "You practiced airport English."}, "structured_analysis": {"signals": "grammar"}}'
            if "记忆提取" in system_prompt:
                return '{"upserts": [{"category": "weakness", "content": "past tense accuracy", "evidence": "review", "confidence": 0.8, "status": "active"}]}'
            if "计划微调" in system_prompt:
                return '{"adjustments": [{"target_day_index": 2, "adjustment_type": "focus", "title": "Past tense focus", "rationale": "Repeated issue", "instruction": "Ask user to narrate completed actions.", "priority": "high", "status": "active", "expires_after_days": 3}]}'
            if "场景设计" in system_prompt:
                return '{"title": "Hotel follow-up", "user_visible_goal": "Practice completed actions", "npc_role": "Hotel receptionist", "scenario_setup": "The user checks in after a delayed flight.", "conversation_objective": "Explain what happened earlier.", "target_expressions": ["I arrived late because..."], "avoid_patterns": ["I am arrive"], "difficulty": "normal", "coach_notes": "Push past tense."}'
            return "{}"

    monkeypatch.setattr(main_module, "create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 2,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan = onboarding.json()["plan"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan[0]["id"]})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I arrived yesterday."})
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session_id))

    response = client.post("/api/daily-review/run-due")

    assert response.status_code == 200
    assert response.json()["processed_days"] == 1
    with connect(db_path) as connection:
        daily_review = connection.execute("SELECT * FROM daily_reviews").fetchone()
        memory = connection.execute("SELECT * FROM memory_items").fetchone()
        adjustment = connection.execute("SELECT * FROM plan_adjustments").fetchone()
        brief = connection.execute("SELECT * FROM practice_briefs WHERE plan_day_id = ?", (plan[1]["id"],)).fetchone()
    assert daily_review["status"] == "completed"
    assert "airport English" in daily_review["user_report_json"]
    assert memory["content"] == "past tense accuracy"
    assert adjustment["title"] == "Past tense focus"
    assert "Hotel follow-up" in brief["brief_json"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest app/backend/tests/test_api.py::test_run_due_reviews_executes_learning_loop_pipeline -v
```

Expected: FAIL because `/api/daily-review/run-due` still returns `processed_days: 0`.

- [ ] **Step 3: Implement the orchestration**

In `app/backend/app/main.py`, update imports:

```python
import json
from datetime import date
from app.agents import ConversationAgent, DailyReviewAgent, GoalAgent, InlineFeedbackAgent, MemoryAgent, PlanAdaptationAgent, ReviewAgent, ScenarioDesignAgent, clean_plan, clean_plan_day
```

Replace `run_due_reviews()` with:

```python
@app.post("/api/daily-review/run-due")
def run_due_reviews() -> dict[str, object]:
    repo = get_repository()
    profile = repo.get_latest_profile()
    if not profile:
        return {"status": "success", "processed_days": 0}

    settings = load_settings()
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.planner_model,
    )
    today = date.today().isoformat()
    review_dates = repo.get_unreviewed_session_dates(profile["id"], today=today)
    processed_days = 0
    processed = []

    for review_date in review_dates:
        sessions = repo.get_review_sessions_for_date(profile["id"], review_date)
        user_sessions = [
            session
            for session in sessions
            if any(turn["speaker"] == "user" for turn in session.get("turns", []))
        ]
        if not user_sessions or repo.get_daily_review(profile["id"], review_date):
            continue

        plan = clean_plan(repo.get_plan(profile["id"]))
        plan_context = {
            "learning_goal": profile["learning_goal"],
            "current_level": profile["current_level"],
            "review_date": review_date,
            "plan": plan,
        }
        review_result = DailyReviewAgent(llm, repo.get_prompt).generate_review(profile, user_sessions, plan_context)
        user_report = review_result.get("user_report", {})
        structured_analysis = review_result.get("structured_analysis", {})
        source_session_ids = [session["id"] for session in user_sessions]
        daily_review = repo.save_daily_review(
            profile["id"],
            review_date,
            "completed",
            user_report,
            structured_analysis,
            source_session_ids,
            json.dumps(review_result, ensure_ascii=False),
        )

        active_memory = repo.get_active_memory_items(profile["id"])
        memory_result = MemoryAgent(llm, repo.get_prompt).extract_memory(review_result, active_memory)
        for item in memory_result.get("upserts", []):
            repo.save_memory_item(
                profile["id"],
                item.get("category", "general"),
                item.get("content", ""),
                item.get("evidence", ""),
                float(item.get("confidence", 0.5)),
                item.get("status", "active"),
                daily_review["id"],
            )

        upcoming_days = [day for day in plan if day.get("status") == "pending"]
        active_memory = repo.get_active_memory_items(profile["id"])
        adjustment_result = PlanAdaptationAgent(llm, repo.get_prompt).propose_adjustments(
            review_result,
            active_memory,
            upcoming_days,
        )
        saved_adjustments = []
        for item in adjustment_result.get("adjustments", []):
            target_day = next(
                (day for day in upcoming_days if day.get("day_index") == item.get("target_day_index")),
                upcoming_days[0] if upcoming_days else None,
            )
            if not target_day:
                continue
            saved_adjustments.append(
                repo.save_plan_adjustment(
                    target_day["id"],
                    daily_review["id"],
                    item.get("adjustment_type", "focus"),
                    item.get("title", ""),
                    item.get("rationale", ""),
                    item.get("instruction", ""),
                    item.get("priority", "medium"),
                    item.get("status", "active"),
                    int(item.get("expires_after_days", 3)),
                )
            )

        next_day = repo.get_next_pending_plan_day(profile["id"])
        if next_day:
            adjustments = repo.get_active_plan_adjustments(next_day["id"])
            latest_review = repo.get_latest_completed_daily_review(profile["id"]) or daily_review
            brief = ScenarioDesignAgent(llm, repo.get_prompt).generate_brief(
                clean_plan_day(next_day),
                adjustments,
                active_memory,
                latest_review,
            )
            repo.save_practice_brief(next_day["id"], brief)

        processed_days += 1
        processed.append({"review_date": review_date, "review_id": daily_review["id"]})

    return {"status": "success", "processed_days": processed_days, "processed": processed}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest app/backend/tests/test_api.py::test_run_due_reviews_executes_learning_loop_pipeline -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: wire daily review learning loop pipeline"
```

### Task 4: Pipeline Idempotency and Session Start Context

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `app/backend/tests/test_api.py`:

```python
def test_run_due_reviews_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "每日学习复盘" in system_prompt:
                return '{"user_report": {"summary": "Done"}, "structured_analysis": {}}'
            if "记忆提取" in system_prompt:
                return '{"upserts": []}'
            if "计划微调" in system_prompt:
                return '{"adjustments": []}'
            if "场景设计" in system_prompt:
                return '{"title": "Next brief"}'
            return "{}"

    monkeypatch.setattr(main_module, "create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I arrived yesterday."})
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session_id))

    first = client.post("/api/daily-review/run-due")
    second = client.post("/api/daily-review/run-due")

    assert first.json()["processed_days"] == 1
    assert second.json()["processed_days"] == 0
    with connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM daily_reviews").fetchone()["count"]
    assert count == 1


def test_session_start_uses_learning_loop_context_when_generating_brief(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "场景设计" in system_prompt:
                assert "Past tense focus" in user_prompt
                assert "past tense accuracy" in user_prompt
                return '{"title": "Context-aware hotel scenario", "npc_role": "Hotel receptionist"}'
            return "{}"

    monkeypatch.setattr(main_module, "create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    with connect(db_path) as connection:
        review = connection.execute(
            """
            INSERT INTO daily_reviews (profile_id, review_date, status, user_report_json, structured_analysis_json, source_session_ids_json, raw_agent_output)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-06-20", "completed", "{}", "{}", "[]", "{}"),
        )
        connection.execute(
            "INSERT INTO memory_items (profile_id, category, content, evidence, confidence, status, source_review_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "weakness", "past tense accuracy", "review", 0.8, "active", review.lastrowid),
        )
        connection.execute(
            "INSERT INTO plan_adjustments (target_plan_day_id, source_review_id, adjustment_type, title, rationale, instruction, priority, status, expires_after_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plan_day_id, review.lastrowid, "focus", "Past tense focus", "Repeated issue", "Practice completed actions", "high", "active", 3),
        )

    response = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert response.status_code == 200
    assert response.json()["practice_brief"]["title"] == "Context-aware hotel scenario"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest app/backend/tests/test_api.py::test_run_due_reviews_is_idempotent app/backend/tests/test_api.py::test_session_start_uses_learning_loop_context_when_generating_brief -v
```

Expected: at least the session-start context test fails because `start_session()` still passes empty adjustments, memory, and review into `ScenarioDesignAgent`.

- [ ] **Step 3: Update session start brief generation**

In `start_session()`, replace this call:

```python
brief = ScenarioDesignAgent(llm, repo.get_prompt).generate_brief(plan_day, [], [], {})
```

with:

```python
profile = repo.get_latest_profile()
memory = repo.get_active_memory_items(profile["id"]) if profile else []
adjustments = repo.get_active_plan_adjustments(plan_day["id"])
latest_review = repo.get_latest_completed_daily_review(profile["id"]) if profile else {}
brief = ScenarioDesignAgent(llm, repo.get_prompt).generate_brief(
    plan_day,
    adjustments,
    memory,
    latest_review or {},
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest app/backend/tests/test_api.py::test_run_due_reviews_is_idempotent app/backend/tests/test_api.py::test_session_start_uses_learning_loop_context_when_generating_brief -v
```

Expected: PASS.

- [ ] **Step 5: Run focused backend tests**

Run:

```bash
pytest app/backend/tests/test_repositories.py app/backend/tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: pass learning loop context into practice brief generation"
```

