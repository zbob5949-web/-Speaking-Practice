# Daily Task Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a soft daily task completion loop so SpeakMate Agent can suggest ending today’s practice, let users manually end it, persist completion state, and show a Today Summary.

**Architecture:** Reuse existing `daily_sessions.ended_at/summary/overall_score` and `learning_plan.status` instead of adding tables. Add a small backend completion service that evaluates soft completion signals and generates fallback summaries, expose completion in session start and turn responses, then add front-end controls and completion cards in `PracticeRoom`.

**Tech Stack:** FastAPI, SQLite, Pydantic, pytest, React, TypeScript, Vitest, Testing Library.

---

## File Structure

- Create: `app/backend/app/completion.py`
  - Owns `SessionCompletionEvaluator`, `build_completion_status`, and fallback summary generation.
- Modify: `app/backend/app/models.py`
  - Add completion request/response-oriented Pydantic models.
- Modify: `app/backend/app/repositories.py`
  - Add methods for completing sessions, reading completed summaries, and returning updated plan days.
- Modify: `app/backend/app/main.py`
  - Add completion status to `/api/sessions/start`, `/api/sessions/turn`, `/api/sessions/turn/stream`.
  - Add `POST /api/sessions/{session_id}/complete`.
- Modify: `app/frontend/src/types.ts`
  - Add `SessionCompletion`, `CompletionSummary`, and `CompleteSessionResponse`.
- Modify: `app/frontend/src/api.ts`
  - Add `completion` to `startSession` and `sendUserTurnStream`.
  - Add `completeSession()`.
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
  - Add manual end button, soft suggestion card, completed summary state, and completed UI.
- Test: `app/backend/tests/test_completion.py`
  - Unit-test evaluator and fallback summary.
- Test: `app/backend/tests/test_api.py`
  - API tests for start, turn, complete, idempotency, and validation.
- Test: `app/frontend/src/App.test.tsx`
  - UI tests for manual ending, suggestion card, and completed state.

---

### Task 1: Backend Completion Contracts And Evaluator

**Files:**
- Create: `app/backend/app/completion.py`
- Modify: `app/backend/app/models.py`
- Test: `app/backend/tests/test_completion.py`

- [ ] **Step 1: Write failing evaluator tests**

Create `app/backend/tests/test_completion.py`:

```python
from app.completion import SessionCompletionEvaluator, build_completion_summary


def user_turn(turn_index: int, text: str) -> dict:
    return {
        "id": turn_index,
        "session_id": 1,
        "turn_index": turn_index,
        "speaker": "user",
        "text": text,
    }


def assistant_turn(turn_index: int, text: str) -> dict:
    return {
        "id": turn_index,
        "session_id": 1,
        "turn_index": turn_index,
        "speaker": "assistant",
        "text": text,
    }


def test_completion_evaluator_does_not_suggest_before_three_user_turns():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I want to book a room."),
            assistant_turn(3, "For what date?"),
            user_turn(4, "Tomorrow night."),
        ],
        feedback=[],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "in_progress"
    assert result["can_suggest_completion"] is False


def test_completion_evaluator_suggests_after_three_user_turns_without_major_blockers():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I want to book a room."),
            assistant_turn(3, "For what date?"),
            user_turn(4, "Tomorrow night for two people."),
            assistant_turn(5, "What room type?"),
            user_turn(6, "A non-smoking double room, please."),
        ],
        feedback=[{"feedback_type": "guidance", "severity": None}],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "completion_suggested"
    assert result["can_suggest_completion"] is True
    assert "核心目标" in result["suggestion_reason_zh"]


def test_completion_evaluator_returns_completed_when_session_has_ended_at():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": "2026-07-26 10:00:00", "summary": '{"summary_zh":"完成"}'},
        turns=[user_turn(1, "Hello.")],
        feedback=[],
        practice_brief={},
    )

    assert result["status"] == "completed"
    assert result["can_suggest_completion"] is False
    assert result["completed_summary"]["summary_zh"] == "完成"


def test_build_completion_summary_short_practice_mentions_short_duration():
    summary = build_completion_summary(
        completion_type="manual",
        turns=[assistant_turn(1, "Welcome."), user_turn(2, "I want a room.")],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert summary["status"] == "completed"
    assert summary["completion_type"] == "manual"
    assert "练习时间较短" in summary["next_focus_zh"]
    assert summary["reusable_sentences"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend
python -m pytest tests/test_completion.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.completion'`.

- [ ] **Step 3: Add completion models**

In `app/backend/app/models.py`, add:

```python
from typing import Literal
```

Then add below `LanguageSupportRequest`:

```python
class CompleteSessionRequest(BaseModel):
    completion_type: Literal["manual", "agent_suggested"] = "manual"


class CompletionSummary(BaseModel):
    status: str = "completed"
    completion_type: str
    summary_zh: str
    strength_zh: str
    next_focus_zh: str
    reusable_sentences: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class SessionCompletionStatus(BaseModel):
    status: Literal["in_progress", "completion_suggested", "completed"]
    can_suggest_completion: bool = False
    suggestion_reason_zh: str = ""
    completed_summary: dict | None = None
```

- [ ] **Step 4: Add completion evaluator**

Create `app/backend/app/completion.py`:

```python
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
    recent_feedback = feedback[-3:]
    return any(item.get("severity") == "major" for item in recent_feedback)


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
```

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
cd app/backend
python -m pytest tests/test_completion.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/models.py app/backend/app/completion.py app/backend/tests/test_completion.py
git commit -m "feat: add session completion evaluator"
```

---

### Task 2: Persist Completed Sessions

**Files:**
- Modify: `app/backend/app/repositories.py`
- Test: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write failing repository tests**

Append to `app/backend/tests/test_repositories.py`:

```python
def test_repository_completes_session_and_plan_day(tmp_path):
    import json
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(learning_goal="Travel English", total_days=1, daily_minutes=15, current_level="A2")
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Hotel", "scenario": "Check in", "objective": "Book a room"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Hotel")
    summary = {"status": "completed", "summary_zh": "今天完成了酒店入住练习。", "confidence": 0.7}

    completed = repo.complete_session(session["id"], summary, overall_score=4)

    assert completed["ended_at"]
    assert json.loads(completed["summary"])["summary_zh"] == "今天完成了酒店入住练习。"
    assert completed["overall_score"] == 4
    assert repo.get_plan_day_by_id(plan[0]["id"])["status"] == "completed"


def test_repository_complete_session_is_idempotent(tmp_path):
    import json
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(learning_goal="Travel English", total_days=1, daily_minutes=15, current_level="A2")
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Hotel", "scenario": "Check in", "objective": "Book a room"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Hotel")
    first = repo.complete_session(session["id"], {"summary_zh": "第一次"}, overall_score=4)
    second = repo.complete_session(session["id"], {"summary_zh": "第二次"}, overall_score=2)

    assert first["ended_at"] == second["ended_at"]
    assert json.loads(second["summary"])["summary_zh"] == "第一次"
    assert second["overall_score"] == 4
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend
python -m pytest tests/test_repositories.py -k "complete_session" -v
```

Expected: FAIL with `AttributeError: 'CoachRepository' object has no attribute 'complete_session'`.

- [ ] **Step 3: Implement repository method**

In `app/backend/app/repositories.py`, add inside `CoachRepository` after `get_session`:

```python
    def complete_session(self, session_id: int, summary: dict[str, Any], overall_score: int = 3) -> dict[str, Any] | None:
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
            if session["plan_day_id"]:
                connection.execute(
                    "UPDATE learning_plan SET status = ? WHERE id = ?",
                    ("completed", session["plan_day_id"]),
                )
            connection.commit()
            completed = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (session_id,)).fetchone()
            return row_to_dict(completed)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
cd app/backend
python -m pytest tests/test_repositories.py -k "complete_session" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "feat: persist completed practice sessions"
```

---

### Task 3: Complete Session API

**Files:**
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Append to `app/backend/tests/test_api.py`:

```python
def test_complete_session_marks_plan_day_completed(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})

    response = client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    assert response.status_code == 200
    body = response.json()
    assert body["completion"]["status"] == "completed"
    assert body["completion"]["completed_summary"]["completion_type"] == "manual"
    assert body["plan_day"]["status"] == "completed"


def test_complete_session_rejects_session_without_user_turn(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]

    response = client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    assert response.status_code == 400
    assert "至少完成一轮练习" in response.json()["detail"]


def test_start_session_returns_completed_status_after_completion(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})
    client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    resumed = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert resumed.status_code == 200
    assert resumed.json()["completion"]["status"] == "completed"
    assert resumed.json()["completion"]["completed_summary"]["status"] == "completed"
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py -k "complete_session or completed_status" -v
```

Expected: FAIL with 404 for `/api/sessions/{session_id}/complete` or missing `completion`.

- [ ] **Step 3: Implement API route and start response completion**

In `app/backend/app/main.py`, update imports:

```python
from app.completion import build_completion_status, build_completion_summary
from app.models import CompleteSessionRequest, GrowthSummaryResponse, LanguageSupportRequest, OnboardingRequest, StartSessionRequest, TodayStrategyResponse, UserTurnRequest, TTSRequest
```

In `start_session`, before return:

```python
    completion = build_completion_status(session, turns, feedback_history, brief)
```

Return:

```python
    return {
        "session": session,
        "turns": turns,
        "plan_day": plan_day,
        "feedback_history": feedback_history,
        "practice_brief": brief,
        "completion": completion,
    }
```

Add after `start_session`:

```python
@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int, request: CompleteSessionRequest) -> dict[str, object]:
    repo = get_repository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = repo.get_turns(session_id)
    if not any(turn["speaker"] == "user" for turn in turns):
        raise HTTPException(status_code=400, detail="至少完成一轮练习后再结束今天的任务。")
    plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else None
    brief = {}
    if plan_day:
        brief_row = repo.get_practice_brief(plan_day["id"])
        if brief_row:
            brief = json.loads(brief_row["brief_json"])
    existing_completion = build_completion_status(session, turns, repo.get_inline_feedback_for_session(session_id), brief)
    if existing_completion["status"] == "completed":
        completed_plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else plan_day
        return {"session": session, "plan_day": completed_plan_day or {}, "completion": existing_completion}
    summary = build_completion_summary(request.completion_type, turns, brief)
    completed_session = repo.complete_session(session_id, summary, overall_score=4)
    if not completed_session:
        raise HTTPException(status_code=404, detail="Session not found")
    completed_plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else plan_day
    completion = build_completion_status(completed_session, turns, repo.get_inline_feedback_for_session(session_id), brief)
    return {"session": completed_session, "plan_day": completed_plan_day or {}, "completion": completion}
```

- [ ] **Step 4: Run API tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py -k "complete_session or completed_status" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: add complete session api"
```

---

### Task 4: Turn Completion Suggestions

**Files:**
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing turn suggestion test**

Append to `app/backend/tests/test_api.py`:

```python
def test_user_turn_returns_completion_suggestion_after_three_turns(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "Tomorrow night for two people."})

    response = client.post("/api/sessions/turn", json={"session_id": session_id, "text": "A double room please."})

    assert response.status_code == 200
    assert response.json()["completion"]["status"] == "completion_suggested"
    assert response.json()["completion"]["can_suggest_completion"] is True
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_user_turn_returns_completion_suggestion_after_three_turns -v
```

Expected: FAIL with missing `completion`.

- [ ] **Step 3: Add completion to non-stream turn response**

In `add_user_turn`, after saving feedback:

```python
    completion = build_completion_status(
        repo.get_session(request.session_id) or session,
        repo.get_turns(request.session_id),
        repo.get_inline_feedback_for_session(request.session_id),
        brief or {},
    )
```

Return:

```python
    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
        "hints": hints,
        "completion": completion,
    }
```

- [ ] **Step 4: Add completion to stream meta**

In `add_user_turn_stream.event_generator`, after `saved_feedback`:

```python
            completion = build_completion_status(
                repo.get_session(request.session_id) or session,
                repo.get_turns(request.session_id),
                repo.get_inline_feedback_for_session(request.session_id),
                brief or {},
            )
```

Add to `meta`:

```python
                "completion": completion,
```

- [ ] **Step 5: Run focused API test**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_user_turn_returns_completion_suggestion_after_three_turns -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: suggest completion after practice progress"
```

---

### Task 5: Frontend API And Types

**Files:**
- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/api.ts`
- Test: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Add TypeScript types**

In `app/frontend/src/types.ts`, add after `PracticeSession`:

```ts
export type CompletionSummary = {
  status: string;
  completion_type: "manual" | "agent_suggested";
  summary_zh: string;
  strength_zh: string;
  next_focus_zh: string;
  reusable_sentences: string[];
  confidence: number;
};

export type SessionCompletion = {
  status: "in_progress" | "completion_suggested" | "completed";
  can_suggest_completion: boolean;
  suggestion_reason_zh: string;
  completed_summary: CompletionSummary | null;
};
```

- [ ] **Step 2: Update API return types and completeSession**

In `app/frontend/src/api.ts`, update imports to include `SessionCompletion`.

Update `startSession` return type:

```ts
  completion?: SessionCompletion;
```

Update `sendUserTurnStream` return type:

```ts
  completion?: SessionCompletion;
```

Add after `deleteTurnPair`:

```ts
export async function completeSession(
  sessionId: number,
  completionType: "manual" | "agent_suggested" = "manual"
): Promise<{
  session: PracticeSession;
  plan_day: PlanDay;
  completion: SessionCompletion;
}> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ completion_type: completionType })
  });
  if (!response.ok) {
    throw new Error("Failed to complete session");
  }
  return response.json();
}
```

- [ ] **Step 3: Run frontend type build**

Run:

```bash
cd app/frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/types.ts app/frontend/src/api.ts
git commit -m "feat: add frontend completion api types"
```

---

### Task 6: Frontend Manual Completion UI

**Files:**
- Modify: `app/frontend/src/App.test.tsx`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Write failing manual completion test**

Update the API mock import in `app/frontend/src/App.test.tsx` to include `completeSession`, add it to `vi.mock`, and add default mock in `beforeEach`:

```ts
(completeSession as Mock).mockResolvedValue({
  session: { id: 1, day_index: 1, topic: "Self-introduction" },
  plan_day: { ...onboardingResult.plan[0], status: "completed" },
  completion: {
    status: "completed",
    can_suggest_completion: false,
    suggestion_reason_zh: "",
    completed_summary: {
      status: "completed",
      completion_type: "manual",
      summary_zh: "今天你完成了酒店入住练习。",
      strength_zh: "你能保持对话推进。",
      next_focus_zh: "下次继续补充时间和对象。",
      reusable_sentences: ["I'd like to book a room."],
      confidence: 0.75
    }
  }
});
```

Add test:

```ts
test("lets the user manually complete today's practice and shows summary", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    turns: [
      ...startedSession.turns,
      { id: 2, session_id: 1, turn_index: 2, speaker: "user", text: "I want to book a room." }
    ],
    completion: {
      status: "in_progress",
      can_suggest_completion: false,
      suggestion_reason_zh: "",
      completed_summary: null
    }
  });

  render(<App />);

  expect(await screen.findByText("I want to book a room.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "结束今日练习" }));

  expect(await screen.findByText("今日已完成")).toBeTruthy();
  expect(screen.getByText("今天你完成了酒店入住练习。")).toBeTruthy();
  expect(screen.getByText("I'd like to book a room.")).toBeTruthy();
  expect(completeSession).toHaveBeenCalledWith(1, "manual");
});
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx -t "lets the user manually complete today's practice"
```

Expected: FAIL because `completeSession` and button/UI do not exist.

- [ ] **Step 3: Implement manual completion UI**

In `PracticeRoom.tsx`:

Update imports:

```ts
import { completeSession, deleteTurnPair, requestLanguageSupport, sendUserTurnStream, startSession, playTTS } from "../api";
import type { ConversationTurn, InlineFeedback, LanguageSupportMode, LanguageSupportResult, PlanDay, PracticeBrief, PracticeSession, SessionCompletion, TargetExpression } from "../types";
```

Add state:

```ts
const [completion, setCompletion] = useState<SessionCompletion | null>(null);
const [isCompletingSession, setIsCompletingSession] = useState(false);
```

After `setPracticeBrief` in boot:

```ts
setCompletion(result.completion || null);
```

Add helper:

```ts
const hasUserTurn = turns.some((turn) => turn.speaker === "user");
const isCompleted = completion?.status === "completed";

async function handleCompleteSession(completionType: "manual" | "agent_suggested" = "manual") {
  if (!session || isCompletingSession) return;
  if (!window.confirm("确定结束今天的练习吗？系统会生成今日总结，并把这一天标记为已完成。")) return;
  setIsCompletingSession(true);
  setApiError("");
  try {
    const result = await completeSession(session.id, completionType);
    setSession(result.session);
    setCompletion(result.completion);
  } catch {
    setApiError("Failed to complete today's practice. Please try again.");
  } finally {
    setIsCompletingSession(false);
  }
}
```

In topic strip actions before session dot:

```tsx
{hasUserTurn && !isCompleted ? (
  <SecondaryButton type="button" onClick={() => handleCompleteSession("manual")} disabled={isCompletingSession}>
    {isCompletingSession ? "生成总结中..." : "结束今日练习"}
  </SecondaryButton>
) : null}
{isCompleted ? <span className="session-dot session-dot-active">今日已完成</span> : null}
```

Render summary above composer:

```tsx
{completion?.status === "completed" && completion.completed_summary ? (
  <section className="feedback-card feedback-card-guidance" aria-label="Today summary">
    <p className="feedback-card-label">今日已完成</p>
    <p>{completion.completed_summary.summary_zh}</p>
    <p className="feedback-reason"><span>做得好的点：</span>{completion.completed_summary.strength_zh}</p>
    <p className="feedback-reason"><span>下次重点：</span>{completion.completed_summary.next_focus_zh}</p>
    {completion.completed_summary.reusable_sentences.length > 0 ? (
      <p className="feedback-example">{completion.completed_summary.reusable_sentences[0]}</p>
    ) : null}
  </section>
) : null}
```

Disable textarea and send when completed:

```tsx
disabled={isCompleted}
```

and:

```tsx
<PrimaryButton disabled={isSubmitting || isCompleted} onClick={() => submitTurn(typedText)}>
  {isCompleted ? "今日已完成" : isSubmitting ? "Sending..." : "Send"}
</PrimaryButton>
```

- [ ] **Step 4: Run focused frontend test**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx -t "lets the user manually complete today's practice"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/App.test.tsx app/frontend/src/components/PracticeRoom.tsx
git commit -m "feat: add manual practice completion ui"
```

---

### Task 7: Frontend Agent Suggestion UI

**Files:**
- Modify: `app/frontend/src/App.test.tsx`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Write failing suggestion test**

Add test:

```ts
test("shows agent completion suggestion after a turn and allows continuing", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    completion: {
      status: "in_progress",
      can_suggest_completion: false,
      suggestion_reason_zh: "",
      completed_summary: null
    }
  });
  (sendUserTurnStream as Mock).mockImplementation(async (_sessionId: number, _text: string, onTextChunk: (chunk: string) => void) => {
    onTextChunk("Great, you covered the key details.");
    return {
      ...sentTurnResult,
      inline_feedback: [],
      hints: [],
      completion: {
        status: "completion_suggested",
        can_suggest_completion: true,
        suggestion_reason_zh: "今天的核心目标已经基本练到了。",
        completed_summary: null
      }
    };
  });

  render(<App />);

  expect(await screen.findByLabelText("Practice response")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Practice response"), { target: { value: "I want to book a room." } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByText("今天可以收束了")).toBeTruthy();
  expect(screen.getByText("今天的核心目标已经基本练到了。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "继续练一会儿" }));
  expect(screen.queryByText("今天可以收束了")).toBeNull();
});
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx -t "shows agent completion suggestion"
```

Expected: FAIL because suggestion UI is missing.

- [ ] **Step 3: Implement suggestion UI**

In `PracticeRoom.tsx`, add state:

```ts
const [dismissedCompletionSuggestion, setDismissedCompletionSuggestion] = useState(false);
```

In `submitTurn`, after hints:

```ts
if (result.completion) {
  setCompletion(result.completion);
  if (result.completion.status === "completion_suggested") {
    setDismissedCompletionSuggestion(false);
  }
}
```

Add derived value:

```ts
const showCompletionSuggestion =
  completion?.status === "completion_suggested" &&
  completion.can_suggest_completion &&
  !dismissedCompletionSuggestion &&
  !isCompleted;
```

Render above composer:

```tsx
{showCompletionSuggestion ? (
  <section className="feedback-card feedback-card-guidance" aria-label="Completion suggestion">
    <p className="feedback-card-label">今天可以收束了</p>
    <p>{completion.suggestion_reason_zh || "今天的核心目标已经基本练到了。"}</p>
    <div className="topic-strip-actions">
      <PrimaryButton type="button" onClick={() => handleCompleteSession("agent_suggested")}>
        结束并总结
      </PrimaryButton>
      <SecondaryButton type="button" onClick={() => setDismissedCompletionSuggestion(true)}>
        继续练一会儿
      </SecondaryButton>
    </div>
  </section>
) : null}
```

- [ ] **Step 4: Run focused frontend test**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx -t "shows agent completion suggestion"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/App.test.tsx app/frontend/src/components/PracticeRoom.tsx
git commit -m "feat: show agent completion suggestion"
```

---

### Task 8: Full Regression

**Files:**
- No new files.

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd app/backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx
```

Expected: all App tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd app/frontend
npm run build
```

Expected: build passes. Existing large chunk warning is acceptable.

- [ ] **Step 4: Inspect status and log**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: clean working tree and recent completion commits visible.

---

## Self-Review

- Spec coverage: plan covers manual ending, Agent soft suggestion, summary persistence, completed state, API response changes, front-end UI, and tests.
- Scope control: plan does not add new tables, complex scoring, speech scoring, or a full autonomous tool-calling agent.
- Type consistency: uses `CompletionSummary`, `SessionCompletion`, `completion_type`, `completion_suggested`, and `completed_summary` consistently across backend and frontend.
- Placeholder scan: no placeholder sections or unresolved implementation markers.
