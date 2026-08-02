# Learning Loop Agent System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Daily Review, Memory, Plan Adaptation, and Scenario Design agents with a daily trigger mechanism to create a continuous learning loop.

**Architecture:** We will add JSON-backed tables to SQLite to store reviews, memory items, plan adjustments, and practice briefs. We will implement four new LLM-based agents. We will add a `/api/daily-review/run-due` endpoint to process pending reviews on app load. Finally, we will refactor the frontend to merge Review and Memory into a "Growth" page and update the Studio.

**Tech Stack:** FastAPI, SQLite, Pydantic, React.

---

### Task 1: Update Database Schema

**Files:**
- Modify: `app/backend/app/db.py`
- Modify: `app/backend/tests/test_db.py` (or create it if it doesn't exist)

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_db.py
from app.db import init_db, connect
import sqlite3

def test_new_tables_exist(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with connect(db_path) as conn:
        tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "daily_reviews" in tables
        assert "memory_items" in tables
        assert "plan_adjustments" in tables
        assert "practice_briefs" in tables
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with assertion error for `daily_reviews`

- [ ] **Step 3: Write minimal implementation**

Update `SCHEMA` in `app/backend/app/db.py` to include:

```sql
CREATE TABLE IF NOT EXISTS daily_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  review_date TEXT NOT NULL,
  status TEXT NOT NULL,
  user_report_json TEXT,
  structured_analysis_json TEXT,
  source_session_ids_json TEXT,
  raw_agent_output TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  evidence TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  source_review_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_plan_day_id INTEGER NOT NULL,
  source_review_id INTEGER NOT NULL,
  adjustment_type TEXT NOT NULL,
  title TEXT NOT NULL,
  rationale TEXT NOT NULL,
  instruction TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  expires_after_days INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS practice_briefs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_day_id INTEGER NOT NULL,
  brief_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/tests/test_db.py app/backend/app/db.py
git commit -m "feat: add schema for learning loop tables"
```

### Task 2: Implement Repository Methods

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_repositories.py (append)
import json

def test_learning_loop_repo_methods(setup_db):
    repo = CoachRepository(setup_db)
    
    # daily_review
    review = repo.save_daily_review(1, "2026-06-22", "completed", {"summary": "good"}, {"signals": "good"}, [1, 2], "raw")
    assert review["id"] is not None
    assert json.loads(review["user_report_json"])["summary"] == "good"
    
    # memory
    mem = repo.save_memory_item(1, "weakness", "bad grammar", "said X", 0.8, "active", review["id"])
    assert mem["id"] is not None
    assert mem["category"] == "weakness"
    
    # plan adjustment
    adj = repo.save_plan_adjustment(1, review["id"], "focus", "Title", "Reason", "Instruction", "high", "active", 3)
    assert adj["id"] is not None
    
    # brief
    brief = repo.save_practice_brief(1, {"role": "NPC"})
    assert brief["id"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repositories.py::test_learning_loop_repo_methods -v`
Expected: FAIL with AttributeError (methods don't exist)

- [ ] **Step 3: Write minimal implementation**

Add to `CoachRepository` in `app/backend/app/repositories.py`:

```python
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

    def save_practice_brief(self, plan_day_id: int, brief: dict) -> dict[str, Any]:
        import json
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO practice_briefs (plan_day_id, brief_json) VALUES (?, ?)",
                (plan_day_id, json.dumps(brief))
            )
            row = connection.execute("SELECT * FROM practice_briefs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repositories.py::test_learning_loop_repo_methods -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/tests/test_repositories.py app/backend/app/repositories.py
git commit -m "feat: add repository methods for learning loop data"
```

### Task 3: Seed Prompts for New Agents

**Files:**
- Modify: `app/backend/app/db.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_db.py (append)
def test_new_prompts_seeded(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with connect(db_path) as conn:
        prompts = [row["name"] for row in conn.execute("SELECT name FROM prompts").fetchall()]
        assert "daily_review_agent_system" in prompts
        assert "memory_agent_system" in prompts
        assert "plan_adaptation_agent_system" in prompts
        assert "scenario_design_agent_system" in prompts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py::test_new_prompts_seeded -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Add to `default_prompts` in `app/backend/app/db.py`:

```python
            "daily_review_agent_system": (
                "你是一个每日学习复盘 Agent。你的任务是分析当天的所有练习记录，生成结构化的日报。\n"
                "必须输出合法的 JSON 对象，包含两个顶级键：'user_report' 和 'structured_analysis'。"
            ),
            "memory_agent_system": (
                "你是一个记忆提取 Agent。从日报中提取稳定的、需要长期记住的用户特征。\n"
                "必须输出合法的 JSON 对象，包含 'upserts' 数组。"
            ),
            "plan_adaptation_agent_system": (
                "你是一个计划微调 Agent。基于日报和记忆，对未来1-3天的练习计划提出微调建议。\n"
                "必须输出合法的 JSON 对象，包含 'adjustments' 数组。"
            ),
            "scenario_design_agent_system": (
                "你是一个场景设计 Agent。根据学习计划和近期的微调建议，生成下一次练习的具体场景任务单。\n"
                "必须输出合法的 JSON 对象，包含 'title', 'npc_role', 'target_expressions' 等键。"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py::test_new_prompts_seeded -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/db.py app/backend/tests/test_db.py
git commit -m "feat: seed default prompts for learning loop agents"
```

### Task 4: Implement DailyReviewAgent and MemoryAgent Mocks (For wiring)

**Files:**
- Modify: `app/backend/app/agents.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_agents.py (append)
from app.agents import DailyReviewAgent, MemoryAgent

def test_daily_review_agent_mock():
    agent = DailyReviewAgent(None, lambda x: None)
    res = agent.generate_review({}, [], {})
    assert "user_report" in res
    assert "structured_analysis" in res

def test_memory_agent_mock():
    agent = MemoryAgent(None, lambda x: None)
    res = agent.extract_memory({}, [])
    assert "upserts" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents.py::test_daily_review_agent_mock -v`
Expected: FAIL (classes don't exist)

- [ ] **Step 3: Write minimal implementation**

Add to `app/backend/app/agents.py`:

```python
class DailyReviewAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def generate_review(self, profile: dict, sessions: list, plan_context: dict) -> dict:
        # Mock implementation for now to establish wiring
        return {
            "user_report": {"title": "Today's Review", "summary": "Good job", "achievements": [], "key_issues": [], "suggested_focus": [], "encouragement": "Keep it up"},
            "structured_analysis": {"performance_signals": {}, "recurring_issues": [], "memory_candidates": [], "plan_adaptation_signals": []}
        }

class MemoryAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def extract_memory(self, review: dict, active_memory: list) -> dict:
        # Mock implementation
        return {"upserts": [], "updates": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents.py::test_daily_review_agent_mock tests/test_agents.py::test_memory_agent_mock -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: add DailyReviewAgent and MemoryAgent mocks"
```

### Task 5: Implement PlanAdaptationAgent and ScenarioDesignAgent Mocks

**Files:**
- Modify: `app/backend/app/agents.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_agents.py (append)
from app.agents import PlanAdaptationAgent, ScenarioDesignAgent

def test_plan_adaptation_agent_mock():
    agent = PlanAdaptationAgent(None, lambda x: None)
    res = agent.propose_adjustments({}, [], [])
    assert "adjustments" in res

def test_scenario_design_agent_mock():
    agent = ScenarioDesignAgent(None, lambda x: None)
    res = agent.generate_brief({}, [], [], {})
    assert "title" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents.py::test_plan_adaptation_agent_mock -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Add to `app/backend/app/agents.py`:

```python
class PlanAdaptationAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def propose_adjustments(self, review: dict, active_memory: list, upcoming_days: list) -> dict:
        return {"adjustments": []}

class ScenarioDesignAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def generate_brief(self, plan_day: dict, adjustments: list, memory: list, review: dict) -> dict:
        return {
            "title": plan_day.get("topic", "Practice"),
            "user_visible_goal": "Practice speaking",
            "npc_role": "NPC",
            "scenario_setup": plan_day.get("scenario", "Setup"),
            "conversation_objective": plan_day.get("objective", "Objective"),
            "target_expressions": [],
            "avoid_patterns": [],
            "difficulty": "normal",
            "coach_notes": ""
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents.py::test_plan_adaptation_agent_mock tests/test_agents.py::test_scenario_design_agent_mock -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: add PlanAdaptationAgent and ScenarioDesignAgent mocks"
```

### Task 6: Implement /api/daily-review/run-due API

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_api.py (append)
def test_run_due_reviews(client, mock_repo):
    # Setup mock repo to return a profile and mock sessions
    mock_repo.get_latest_profile.return_value = {"id": 1, "learning_goal": "x", "current_level": "y", "daily_minutes": 10}
    mock_repo.save_daily_review.return_value = {"id": 1}
    
    response = client.post("/api/daily-review/run-due")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "processed_days": 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_run_due_reviews -v`
Expected: FAIL (404 not found)

- [ ] **Step 3: Write minimal implementation**

Add to `app/backend/app/main.py`:

```python
@app.post("/api/daily-review/run-due")
def run_due_reviews() -> dict[str, object]:
    # Very simplified version for the wiring task.
    # A complete implementation would fetch un-reviewed days, aggregate sessions, call DailyReviewAgent, MemoryAgent, PlanAdaptationAgent, and ScenarioDesignAgent.
    repo = get_repository()
    profile = repo.get_latest_profile()
    if not profile:
        return {"status": "success", "processed_days": 0}
        
    # TODO: Implement the actual logic to find missed days and run the agents
    
    return {"status": "success", "processed_days": 0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_run_due_reviews -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: add /api/daily-review/run-due endpoint stub"
```

### Task 7: Update Session Start to Use Practice Brief

**Files:**
- Modify: `app/backend/app/main.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_api.py (update test_start_session)
# Assert that the response contains a 'practice_brief' key.
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation**

Modify `start_session` in `app/backend/app/main.py` to fetch or generate a practice brief using the `ScenarioDesignAgent` if one doesn't exist.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

### Task 8: Frontend API Updates and Startup Trigger

**Files:**
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Write the failing test**

Update `App.test.tsx` to mock `runDueReviews` and assert it is called on mount.

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation**

Add `runDueReviews` to `api.ts`.
Call it in `App.tsx` inside `loadCurrentState`.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

### Task 9: Frontend UI Restructuring (Growth Page)

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/AppShell.tsx`
- Create: `app/frontend/src/components/GrowthPage.tsx`
- Delete: `MemoryLibrary.tsx`, `FeedbackReport.tsx` (or merge logic)

- [ ] **Step 1: Write the failing test**

Update `App.test.tsx` to look for "Growth" instead of "Review" and "Memory".

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Write minimal implementation**

Create `GrowthPage.tsx` that fetches and displays the latest Daily Review. Update `AppShell.tsx` navigation.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**
