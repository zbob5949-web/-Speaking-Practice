# SpeakMate Agent V2 Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V2 Agent architecture by adding Orchestrator contracts, tool wrappers, agent run tracing, a Today strategy API, and a lightweight frontend explanation block.

**Architecture:** Keep the existing learning loop and session APIs stable. Add focused backend units for contracts, tools, and orchestration, then expose `/api/today/strategy` and pass the returned strategy into `PracticeRoom` for display.

**Tech Stack:** FastAPI, Pydantic, SQLite, pytest, React, TypeScript, Vitest.

---

## File Structure

- Create `app/backend/app/contracts.py`: Pydantic contracts for tool records, orchestration output, and validated agent outputs.
- Create `app/backend/app/tools.py`: tool registry and tool handlers wrapping existing repository/agent capabilities.
- Modify `app/backend/app/db.py`: add `agent_runs` table.
- Modify `app/backend/app/repositories.py`: add `save_agent_run()` and `get_agent_runs()`.
- Modify `app/backend/app/prompts.py`: add Orchestrator prompt and strengthen review/memory/adaptation/scenario prompts.
- Modify `app/backend/app/agents.py`: add `CoachOrchestratorAgent` with validation fallback.
- Modify `app/backend/app/models.py`: add `TodayStrategyResponse`.
- Modify `app/backend/app/main.py`: add `/api/today/strategy`.
- Modify `app/frontend/src/types.ts`: add `TodayStrategy` types.
- Modify `app/frontend/src/api.ts`: add `getTodayStrategy()`.
- Modify `app/frontend/src/App.tsx`: load today strategy when a day is active.
- Modify `app/frontend/src/components/PracticeRoom.tsx`: display `今日练习依据`.
- Modify `app/frontend/src/App.test.tsx`: assert strategy block is shown.
- Add/modify backend tests under `app/backend/tests/`.

## Task 1: Contracts And Agent Run Persistence

**Files:**
- Create: `app/backend/app/contracts.py`
- Modify: `app/backend/app/db.py`
- Modify: `app/backend/app/repositories.py`
- Test: `app/backend/tests/test_db.py`
- Test: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write failing DB test**

```python
def test_agent_runs_table_exists(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'"
        ).fetchone()
    assert row is not None
```

- [ ] **Step 2: Write failing repository test**

```python
def test_save_and_get_agent_runs(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel speaking",
            total_days=3,
            daily_minutes=15,
            current_level="B1",
        )
    )

    saved = repo.save_agent_run(
        profile_id=profile["id"],
        plan_day_id=None,
        session_id=None,
        agent_name="CoachOrchestratorAgent",
        trigger_source="today_entry",
        input_data={"profile_id": profile["id"]},
        tool_calls=[],
        output_data={"coach_explanation_zh": "今天先练酒店入住。"},
        validation_status="passed",
        error_message=None,
    )
    runs = repo.get_agent_runs(profile["id"])

    assert saved["id"] == runs[0]["id"]
    assert runs[0]["agent_name"] == "CoachOrchestratorAgent"
    assert runs[0]["input"]["profile_id"] == profile["id"]
    assert runs[0]["output"]["coach_explanation_zh"] == "今天先练酒店入住。"
```

- [ ] **Step 3: Run RED tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_db.py::test_agent_runs_table_exists tests/test_repositories.py::test_save_and_get_agent_runs -v
```

Expected: fail because `agent_runs` and repository methods do not exist.

- [ ] **Step 4: Implement contracts and persistence**

Add `contracts.py`:

```python
from typing import Literal
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    side_effect: Literal["read_only", "write"]


class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, object]
    output: dict[str, object] | list[dict[str, object]] | None = None
    status: Literal["success", "failed"]
    error_message: str | None = None


class TodayStrategy(BaseModel):
    focus: str
    reason: str
    success_criteria: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    action: Literal[
        "run_due_reviews",
        "generate_practice_brief",
        "use_existing_brief",
        "start_practice",
        "review_lesson_material",
    ]
    rationale: str
    priority: Literal["low", "medium", "high"] = "medium"


class OrchestrationResult(BaseModel):
    today_strategy: TodayStrategy
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    coach_explanation_zh: str
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
```

Add table to `db.py`:

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER,
  plan_day_id INTEGER,
  session_id INTEGER,
  agent_name TEXT NOT NULL,
  trigger_source TEXT NOT NULL,
  input_json TEXT NOT NULL,
  tool_calls_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  validation_status TEXT NOT NULL,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Add repository methods:

```python
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
        return self._decode_agent_run(row)
```

- [ ] **Step 5: Run GREEN tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_db.py::test_agent_runs_table_exists tests/test_repositories.py::test_save_and_get_agent_runs -v
```

Expected: pass.

## Task 2: Tools Registry

**Files:**
- Create: `app/backend/app/tools.py`
- Test: `app/backend/tests/test_tools.py`

- [ ] **Step 1: Write failing tool tests**

```python
def test_learning_tools_read_profile_memory_and_review(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(OnboardingRequest(
        learning_goal="Travel speaking",
        total_days=3,
        daily_minutes=15,
        current_level="B1",
    ))

    tools = LearningToolRegistry(repo)

    profile_result = tools.call("get_profile", {"profile_id": profile["id"]})
    memory_result = tools.call("get_active_memory", {"profile_id": profile["id"]})

    assert profile_result.status == "success"
    assert profile_result.output["learning_goal"] == "Travel speaking"
    assert memory_result.status == "success"
    assert memory_result.output == []
```

- [ ] **Step 2: Run RED test**

Run:

```bash
cd app/backend
python -m pytest tests/test_tools.py -v
```

Expected: fail because `LearningToolRegistry` does not exist.

- [ ] **Step 3: Implement minimal registry**

Create `tools.py`:

```python
from app.contracts import ToolCallRecord, ToolDefinition
from app.repositories import CoachRepository


class LearningToolRegistry:
    def __init__(self, repo: CoachRepository):
        self.repo = repo
        self.definitions = {
            "get_profile": ToolDefinition(
                name="get_profile",
                description="Read a learner profile.",
                input_schema={"profile_id": "int | null"},
                output_schema={"profile": "dict | null"},
                side_effect="read_only",
            ),
            "get_active_memory": ToolDefinition(
                name="get_active_memory",
                description="Read active long-term memory items for a learner.",
                input_schema={"profile_id": "int"},
                output_schema={"memory": "list"},
                side_effect="read_only",
            ),
        }

    def call(self, name: str, input_data: dict[str, object]) -> ToolCallRecord:
        try:
            output = self._call(name, input_data)
            return ToolCallRecord(tool_name=name, input=input_data, output=output, status="success")
        except Exception as exc:
            return ToolCallRecord(tool_name=name, input=input_data, output=None, status="failed", error_message=str(exc))

    def _call(self, name: str, input_data: dict[str, object]):
        if name == "get_profile":
            profile_id = input_data.get("profile_id")
            return self.repo.get_profile(int(profile_id)) if profile_id else self.repo.get_latest_profile()
        if name == "get_active_memory":
            return self.repo.get_active_memory_items(int(input_data["profile_id"]))
        raise ValueError(f"Unknown tool: {name}")
```

- [ ] **Step 4: Extend tools for plan/review/adjustments/brief**

Add tool names: `get_current_plan_day`, `get_latest_review`, `get_active_adjustments`, `get_or_create_practice_brief`.

- [ ] **Step 5: Run GREEN tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_tools.py -v
```

Expected: pass.

## Task 3: CoachOrchestratorAgent And Prompt Contracts

**Files:**
- Modify: `app/backend/app/prompts.py`
- Modify: `app/backend/app/agents.py`
- Test: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write failing tests**

```python
def test_orchestrator_agent_returns_valid_strategy():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "学习教练总控" in system_prompt
            return json.dumps({
                "today_strategy": {
                    "focus": "Practice hotel check-in details.",
                    "reason": "Recent memory says the learner gives vague travel details.",
                    "success_criteria": ["State reservation name", "Ask one room question"]
                },
                "recommended_actions": [
                    {"action": "use_existing_brief", "rationale": "The brief matches today's focus.", "priority": "medium"}
                ],
                "coach_explanation_zh": "今天重点练酒店入住细节，因为你最近容易遗漏关键信息。",
                "risk_flags": [],
                "confidence": 0.82
            })

    result = CoachOrchestratorAgent(MockLLM()).plan_today(
        profile={"learning_goal": "Travel speaking"},
        plan_day={"topic": "Hotel check-in", "objective": "Ask room questions"},
        latest_review={},
        active_memory=[{"content": "Often gives vague travel details"}],
        active_adjustments=[],
        practice_brief={"title": "Hotel check-in"},
        session_state={"has_session": False},
    )

    assert result["validation_status"] == "passed"
    assert result["output"]["today_strategy"]["focus"] == "Practice hotel check-in details."
```

```python
def test_orchestrator_agent_falls_back_on_bad_json():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return "not-json"

    result = CoachOrchestratorAgent(MockLLM()).plan_today(
        profile={"learning_goal": "Travel speaking"},
        plan_day={"topic": "Hotel check-in", "objective": "Ask room questions"},
        latest_review={},
        active_memory=[],
        active_adjustments=[],
        practice_brief={},
        session_state={},
    )

    assert result["validation_status"] == "failed"
    assert result["output"]["today_strategy"]["focus"]
```

- [ ] **Step 2: Run RED tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_orchestrator_agent_returns_valid_strategy tests/test_agents.py::test_orchestrator_agent_falls_back_on_bad_json -v
```

Expected: fail because `CoachOrchestratorAgent` does not exist.

- [ ] **Step 3: Add prompts**

Add `orchestrator_agent_system` and `orchestrator_agent_user_template` to `DEFAULT_PROMPTS`, and strengthen DailyReview, Memory, PlanAdaptation, ScenarioDesign prompt text per spec.

- [ ] **Step 4: Implement agent**

Add `CoachOrchestratorAgent` to `agents.py` using `OrchestrationResult.model_validate()` and fallback output on parse/validation failure.

- [ ] **Step 5: Run GREEN tests**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_orchestrator_agent_returns_valid_strategy tests/test_agents.py::test_orchestrator_agent_falls_back_on_bad_json -v
```

Expected: pass.

## Task 4: Today Strategy API

**Files:**
- Modify: `app/backend/app/models.py`
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing API test**

```python
def test_today_strategy_returns_orchestrated_plan(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post("/api/onboarding", json={
        "learning_goal": "Travel speaking",
        "total_days": 1,
        "daily_minutes": 15,
        "current_level": "B1",
    })

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    body = response.json()
    assert body["today_strategy"]["focus"]
    assert body["coach_explanation_zh"]
    assert body["practice_brief"]
    assert body["agent_run_id"] >= 1
```

- [ ] **Step 2: Run RED test**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_today_strategy_returns_orchestrated_plan -v
```

Expected: 404 because endpoint does not exist.

- [ ] **Step 3: Add response model**

Add `TodayStrategyResponse` to `models.py`:

```python
class TodayStrategyResponse(BaseModel):
    today_strategy: dict
    coach_explanation_zh: str
    recommended_actions: list[dict]
    risk_flags: list[str]
    practice_brief: dict
    agent_run_id: int
```

- [ ] **Step 4: Implement endpoint**

Add `/api/today/strategy` to `main.py`. It should load profile/plan_day, ensure practice brief, call `CoachOrchestratorAgent`, save agent run, and return response.

- [ ] **Step 5: Run GREEN test**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_today_strategy_returns_orchestrated_plan -v
```

Expected: pass.

## Task 5: Frontend Today Strategy Display

**Files:**
- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

In `App.test.tsx`, mock `getTodayStrategy`:

```tsx
(getTodayStrategy as Mock).mockResolvedValue({
  today_strategy: {
    focus: "Practice hotel check-in details.",
    reason: "Recent memory says reservation details are vague.",
    success_criteria: ["State reservation name", "Ask one room question"]
  },
  coach_explanation_zh: "今天重点练酒店入住细节，因为你最近容易遗漏关键信息。",
  recommended_actions: [],
  risk_flags: [],
  practice_brief: practiceBrief,
  agent_run_id: 1
});
```

Add assertion:

```tsx
expect(await screen.findByText("今日练习依据")).toBeTruthy();
expect(screen.getByText("Practice hotel check-in details.")).toBeTruthy();
expect(screen.getByText("今天重点练酒店入住细节，因为你最近容易遗漏关键信息。")).toBeTruthy();
```

- [ ] **Step 2: Run RED test**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx
```

Expected: fail because `getTodayStrategy` and display block do not exist.

- [ ] **Step 3: Add type and API client**

Add `TodayStrategy` type and `getTodayStrategy(profileId?: number)` in `api.ts`.

- [ ] **Step 4: Wire App to PracticeRoom**

Load strategy after current state is loaded and pass `todayStrategy` to `PracticeRoom`.

- [ ] **Step 5: Render strategy block**

In `PracticeRoom` Learn view, render a compact `今日练习依据` card when `todayStrategy` is present.

- [ ] **Step 6: Run GREEN test**

Run:

```bash
cd app/frontend
npm run test -- src/App.test.tsx
```

Expected: pass.

## Task 6: Full Verification

**Files:**
- All modified files.

- [ ] **Step 1: Run backend tests**

```bash
cd app/backend
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

```bash
cd app/frontend
npm run test -- src/App.test.tsx
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

```bash
cd app/frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Search for placeholders and broken names**

```bash
rg "TBD|TODO|placeholder|CoachOrchestratorAgent" app docs/superpowers/specs/2026-07-18-agent-architecture-v2-design.md
```

Expected: no placeholder strings; `CoachOrchestratorAgent` appears only in implemented code, tests, docs, and prompts.
