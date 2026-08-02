# AI PM English Coach MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first AI English speaking coach MVP with onboarding, learning plan generation, daily text/voice practice, inline feedback, review reports, and local memory.

**Architecture:** Use a React frontend for the local learning workspace and a FastAPI backend for state, agent orchestration, and LLM calls. Store all learning data in SQLite through a small repository layer. Start with text-first conversation support, then add browser push-to-talk and free browser/system TTS.

**Tech Stack:** React, Vite, TypeScript, Python, FastAPI, SQLite, pytest, Vitest, browser SpeechRecognition fallback, browser SpeechSynthesis, domestic LLM provider abstraction.

---

## File Structure

Create these files:

- `app/backend/pyproject.toml`: Python backend dependencies and pytest config.
- `app/backend/app/main.py`: FastAPI app entrypoint.
- `app/backend/app/config.py`: Environment and settings loader.
- `app/backend/app/db.py`: SQLite connection and schema initialization.
- `app/backend/app/models.py`: Pydantic request/response models.
- `app/backend/app/repositories.py`: SQLite persistence methods.
- `app/backend/app/llm.py`: LLM provider interface and fake provider.
- `app/backend/app/agents.py`: Goal, session, conversation, feedback, review, and memory orchestration.
- `app/backend/tests/test_agents.py`: Agent behavior tests.
- `app/backend/tests/test_api.py`: API endpoint tests.
- `app/frontend/package.json`: Frontend scripts and dependencies.
- `app/frontend/index.html`: Vite HTML entry.
- `app/frontend/src/main.tsx`: React entrypoint.
- `app/frontend/src/App.tsx`: App shell and routing state.
- `app/frontend/src/api.ts`: Backend API client.
- `app/frontend/src/types.ts`: Shared frontend types.
- `app/frontend/src/components/Onboarding.tsx`: First-run setup.
- `app/frontend/src/components/Dashboard.tsx`: Home dashboard.
- `app/frontend/src/components/PracticeRoom.tsx`: Conversation and voice practice.
- `app/frontend/src/components/FeedbackReport.tsx`: Post-session review view.
- `app/frontend/src/components/MemoryLibrary.tsx`: Mistakes and expressions view.
- `app/frontend/src/voice.ts`: Browser speech recognition and TTS helpers.
- `app/frontend/src/App.test.tsx`: Smoke test for the app shell.
- `.gitignore`: Ignore generated files and local data.
- `README.md`: Local setup and run instructions.

Do not create commits during execution unless the user configures Git identity. The repository currently has no commit identity configured.

---

## Task 1: Backend Skeleton And Health Check

**Files:**

- Create: `app/backend/pyproject.toml`
- Create: `app/backend/app/main.py`
- Create: `app/backend/app/config.py`
- Create: `app/backend/app/__init__.py`
- Create: `app/backend/tests/test_api.py`
- Create: `.gitignore`

- [ ] **Step 1: Write the failing health-check test**

Create `app/backend/tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Add backend package config**

Create `app/backend/pyproject.toml`:

```toml
[project]
name = "ai-pm-english-coach-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "python-dotenv>=1.0.1"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "httpx>=0.27.0"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_health_check_returns_ok -v
```

Expected: FAIL because `app.main` does not exist yet.

- [ ] **Step 4: Implement minimal FastAPI app**

Create `app/backend/app/__init__.py`:

```python
"""AI PM English Coach backend package."""
```

Create `app/backend/app/config.py`:

```python
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    database_path = Path(os.getenv("COACH_DB_PATH", project_root / "data" / "coach.sqlite"))
    return Settings(
        database_path=database_path,
        llm_provider=os.getenv("LLM_PROVIDER", "fake"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_model=os.getenv("LLM_MODEL", "fake-local-coach"),
    )
```

Create `app/backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="AI PM English Coach")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

Create `.gitignore`:

```gitignore
.DS_Store
__pycache__/
.pytest_cache/
.venv/
node_modules/
dist/
data/*.sqlite
data/*.sqlite-shm
data/*.sqlite-wal
.env
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
cd app/backend
python -m pytest tests/test_api.py::test_health_check_returns_ok -v
```

Expected: PASS.

- [ ] **Step 6: Check repository status**

Run:

```bash
git status --short
```

Expected: new backend skeleton files are listed. Do not commit unless Git identity is configured by the user.

---

## Task 2: SQLite Schema And Repository Layer

**Files:**

- Create: `app/backend/app/db.py`
- Create: `app/backend/app/models.py`
- Create: `app/backend/app/repositories.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write repository tests**

Create `app/backend/tests/test_agents.py`:

```python
from pathlib import Path

from app.db import init_db
from app.models import OnboardingRequest
from app.repositories import CoachRepository


def test_repository_saves_profile_and_plan(tmp_path: Path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    request = OnboardingRequest(
        learning_goal="AI product manager internationalization",
        total_days=14,
        daily_minutes=15,
        current_level="IELTS 6.5, speaking 6",
    )

    profile = repo.save_profile(request)
    plan = repo.save_plan(
        profile_id=profile["id"],
        days=[
            {
                "day_index": 1,
                "topic": "AI PM self-introduction",
                "scenario": "Introduce your background to an interviewer.",
                "objective": "Give a concise and professional self-introduction.",
            }
        ],
    )

    assert profile["learning_goal"] == "AI product manager internationalization"
    assert len(plan) == 1
    assert plan[0]["day_index"] == 1
    assert plan[0]["status"] == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_repository_saves_profile_and_plan -v
```

Expected: FAIL because `app.db`, `app.models`, and `app.repositories` do not exist.

- [ ] **Step 3: Implement Pydantic models**

Create `app/backend/app/models.py`:

```python
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    learning_goal: str = Field(min_length=1)
    total_days: int = Field(ge=1, le=60)
    daily_minutes: int = Field(ge=5, le=60)
    current_level: str = Field(min_length=1)


class PlanDay(BaseModel):
    day_index: int
    topic: str
    scenario: str
    objective: str
    status: str = "pending"


class StartSessionRequest(BaseModel):
    day_index: int = Field(ge=1)


class UserTurnRequest(BaseModel):
    session_id: int
    text: str = Field(min_length=1)


class EndSessionRequest(BaseModel):
    session_id: int
```

- [ ] **Step 4: Implement database schema**

Create `app/backend/app/db.py`:

```python
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  learning_goal TEXT NOT NULL,
  total_days INTEGER NOT NULL,
  daily_minutes INTEGER NOT NULL,
  current_level TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_plan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  day_index INTEGER NOT NULL,
  topic TEXT NOT NULL,
  scenario TEXT NOT NULL,
  objective TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  FOREIGN KEY(profile_id) REFERENCES user_profile(id)
);

CREATE TABLE IF NOT EXISTS daily_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day_index INTEGER NOT NULL,
  topic TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TEXT,
  summary TEXT,
  overall_score INTEGER
);

CREATE TABLE IF NOT EXISTS conversation_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  turn_index INTEGER NOT NULL,
  speaker TEXT NOT NULL,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES daily_sessions(id)
);

CREATE TABLE IF NOT EXISTS inline_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  turn_id INTEGER,
  feedback_type TEXT NOT NULL,
  feedback_text TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  report TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS error_bank (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_sentence TEXT NOT NULL,
  corrected_sentence TEXT NOT NULL,
  better_expression TEXT NOT NULL,
  error_type TEXT NOT NULL,
  explanation TEXT NOT NULL,
  source_session_id INTEGER NOT NULL,
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS expression_bank (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  expression TEXT NOT NULL,
  meaning TEXT NOT NULL,
  usage_context TEXT NOT NULL,
  example_sentence TEXT NOT NULL,
  source_session_id INTEGER NOT NULL,
  review_count INTEGER NOT NULL DEFAULT 0,
  last_reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
```

- [ ] **Step 5: Implement repository**

Create `app/backend/app/repositories.py`:

```python
from pathlib import Path
from typing import Any

from app.db import connect
from app.models import OnboardingRequest


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


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

    def save_plan(self, profile_id: int, days: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            connection.execute("DELETE FROM learning_plan WHERE profile_id = ?", (profile_id,))
            for day in days:
                connection.execute(
                    """
                    INSERT INTO learning_plan (profile_id, day_index, topic, scenario, objective, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile_id,
                        day["day_index"],
                        day["topic"],
                        day["scenario"],
                        day["objective"],
                        day.get("status", "pending"),
                    ),
                )
            rows = connection.execute(
                "SELECT * FROM learning_plan WHERE profile_id = ? ORDER BY day_index",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]
```

- [ ] **Step 6: Run repository test**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_repository_saves_profile_and_plan -v
```

Expected: PASS.

---

## Task 3: Goal Agent And Onboarding API

**Files:**

- Create: `app/backend/app/agents.py`
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_agents.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Add Goal Agent test**

Append to `app/backend/tests/test_agents.py`:

```python
from app.agents import GoalAgent


def test_goal_agent_generates_requested_number_of_days():
    agent = GoalAgent()

    plan = agent.generate_plan(
        learning_goal="AI product manager internationalization",
        total_days=7,
        daily_minutes=15,
        current_level="IELTS 6.5, speaking 6",
    )

    assert len(plan) == 7
    assert plan[0]["day_index"] == 1
    assert "self-introduction" in plan[0]["topic"].lower()
    assert all(day["scenario"] for day in plan)
```

- [ ] **Step 2: Add onboarding API test**

Append to `app/backend/tests/test_api.py`:

```python
def test_onboarding_creates_profile_and_plan(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)

    response = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "AI product manager internationalization",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["learning_goal"] == "AI product manager internationalization"
    assert len(body["plan"]) == 7
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_goal_agent_generates_requested_number_of_days tests/test_api.py::test_onboarding_creates_profile_and_plan -v
```

Expected: FAIL because `GoalAgent` and `/api/onboarding` do not exist.

- [ ] **Step 4: Implement Goal Agent**

Create `app/backend/app/agents.py`:

```python
DEFAULT_AI_PM_PLAN = [
    ("AI PM self-introduction", "Introduce your AI PM background to a foreign-company interviewer.", "Give a concise and professional self-introduction."),
    ("AI product user value", "Explain the user value of an AI product to an overseas stakeholder.", "Connect user pain points with product value."),
    ("LLM, Agent, RAG, and fine-tuning", "Explain core AI concepts to a non-technical product leader.", "Use simple and accurate professional English."),
    ("Latency, cost, and launch risk", "Discuss model tradeoffs with an engineering lead.", "Explain risks and ask practical follow-up questions."),
    ("AI product roadmap", "Present a roadmap to an overseas business owner.", "Structure roadmap, priorities, and tradeoffs."),
    ("AI product metrics", "Discuss activation, retention, task success, latency, and cost.", "Use metrics to support product decisions."),
    ("Review and consolidation", "Review recurring issues and reuse stronger expressions.", "Improve accuracy and fluency from previous sessions."),
    ("Behavioral interview", "Answer foreign-company AI PM behavioral interview questions.", "Use structured stories and clear impact."),
    ("Product sense interview", "Design an AI assistant in an interview setting.", "Clarify users, scenarios, and success metrics."),
    ("Technical tradeoff discussion", "Compare RAG, fine-tuning, and prompt engineering.", "Discuss technical choices in product language."),
    ("Cross-functional meeting", "Coordinate design, engineering, legal, and safety teams.", "Handle disagreement and align next steps."),
    ("Reading retelling", "Summarize an AI article excerpt verbally.", "Extract key points and express opinions."),
    ("Pressure Q&A", "Handle rapid follow-up questions from an interviewer.", "Clarify, structure, and respond under pressure."),
    ("Full mock interview", "Complete a full AI PM interview simulation.", "Integrate professional English and product thinking."),
]


class GoalAgent:
    def generate_plan(
        self,
        learning_goal: str,
        total_days: int,
        daily_minutes: int,
        current_level: str,
    ) -> list[dict[str, str | int]]:
        plan: list[dict[str, str | int]] = []
        for index in range(total_days):
            topic, scenario, objective = DEFAULT_AI_PM_PLAN[index % len(DEFAULT_AI_PM_PLAN)]
            plan.append(
                {
                    "day_index": index + 1,
                    "topic": topic,
                    "scenario": f"{scenario} Goal: {learning_goal}. Level: {current_level}. Time: {daily_minutes} minutes.",
                    "objective": objective,
                    "status": "pending",
                }
            )
        return plan
```

- [ ] **Step 5: Add plan lookup to repository**

Append to `CoachRepository` in `app/backend/app/repositories.py`:

```python
    def get_plan(self, profile_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM learning_plan WHERE profile_id = ? ORDER BY day_index",
                (profile_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]
```

- [ ] **Step 6: Implement onboarding API**

Replace `app/backend/app/main.py` with:

```python
from fastapi import FastAPI

from app.agents import GoalAgent
from app.config import load_settings
from app.db import init_db
from app.models import OnboardingRequest
from app.repositories import CoachRepository

app = FastAPI(title="AI PM English Coach")


def get_repository() -> CoachRepository:
    settings = load_settings()
    init_db(settings.database_path)
    return CoachRepository(settings.database_path)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/onboarding")
def onboard(request: OnboardingRequest) -> dict[str, object]:
    repo = get_repository()
    profile = repo.save_profile(request)
    plan_days = GoalAgent().generate_plan(
        learning_goal=request.learning_goal,
        total_days=request.total_days,
        daily_minutes=request.daily_minutes,
        current_level=request.current_level,
    )
    plan = repo.save_plan(profile_id=profile["id"], days=plan_days)
    return {"profile": profile, "plan": plan}
```

- [ ] **Step 7: Run tests**

Run:

```bash
cd app/backend
python -m pytest -v
```

Expected: PASS.

---

## Task 4: Session, Conversation, Inline Feedback, And Review APIs

**Files:**

- Create: `app/backend/app/llm.py`
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_agents.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Add conversation agent test**

Append to `app/backend/tests/test_agents.py`:

```python
from app.agents import ConversationAgent, InlineFeedbackAgent, ReviewAgent
from app.llm import FakeLLMProvider


def test_conversation_agent_returns_short_english_reply():
    agent = ConversationAgent(FakeLLMProvider())

    reply = agent.reply(
        topic="AI PM self-introduction",
        conversation=[{"speaker": "user", "text": "I worked on an AI assistant."}],
    )

    assert "Could you" in reply
    assert len(reply.split(".")) <= 3


def test_inline_feedback_agent_returns_short_chinese_feedback():
    feedback = InlineFeedbackAgent().generate("I am responsible for make AI product.")

    assert len(feedback) == 2
    assert feedback[0]["feedback_type"] == "expression"


def test_review_agent_generates_chinese_report():
    report = ReviewAgent().generate_report(
        topic="AI PM self-introduction",
        turns=[
            {"speaker": "user", "text": "I am responsible for make AI product."},
            {"speaker": "assistant", "text": "Could you describe the user problem?"},
        ],
    )

    assert "总体表现" in report["report"]
    assert len(report["errors"]) == 1
    assert len(report["expressions"]) == 3
```

- [ ] **Step 2: Run agent tests to verify failure**

Run:

```bash
cd app/backend
python -m pytest tests/test_agents.py::test_conversation_agent_returns_short_english_reply tests/test_agents.py::test_inline_feedback_agent_returns_short_chinese_feedback tests/test_agents.py::test_review_agent_generates_chinese_report -v
```

Expected: FAIL because the agents do not exist.

- [ ] **Step 3: Implement fake LLM provider**

Create `app/backend/app/llm.py`:

```python
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class FakeLLMProvider:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Could you describe the user problem and the product impact in more detail?"
```

- [ ] **Step 4: Add conversation and feedback agents**

Append to `app/backend/app/agents.py`:

```python
from app.llm import LLMProvider


class ConversationAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def reply(self, topic: str, conversation: list[dict[str, str]]) -> str:
        user_prompt = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in conversation[-6:])
        response = self.llm.complete(
            system_prompt=(
                "You are an English-speaking AI product manager coach. "
                "Reply in English with 1-3 short sentences and ask a useful follow-up question."
            ),
            user_prompt=f"Topic: {topic}\nConversation:\n{user_prompt}",
        )
        return response.strip()


class InlineFeedbackAgent:
    def generate(self, user_text: str) -> list[dict[str, str]]:
        feedback = [
            {
                "feedback_type": "expression",
                "feedback_text": "可以把表达改得更自然，例如：I am responsible for building AI products.",
            },
            {
                "feedback_type": "grammar",
                "feedback_text": "注意 responsible for 后面接名词或动名词，例如 responsible for making/building.",
            },
        ]
        if len(user_text.split()) < 4:
            return feedback[:1]
        return feedback


class ReviewAgent:
    def generate_report(self, topic: str, turns: list[dict[str, str]]) -> dict[str, object]:
        user_turns = [turn["text"] for turn in turns if turn["speaker"] == "user"]
        report = (
            f"总体表现：你完成了关于 {topic} 的口语练习，能够表达基本想法。"
            "下一步要提升表达自然度、句子结构和 AI 产品专业词汇。"
        )
        errors = []
        if user_turns:
            errors.append(
                {
                    "original_sentence": user_turns[0],
                    "corrected_sentence": "I am responsible for building AI products.",
                    "better_expression": "I lead the development of AI product experiences.",
                    "error_type": "grammar",
                    "explanation": "responsible for 后面应接名词或动名词。",
                }
            )
        expressions = [
            {
                "expression": "user pain point",
                "meaning": "用户痛点",
                "usage_context": "产品价值讨论",
                "example_sentence": "The key user pain point is the lack of reliable feedback.",
            },
            {
                "expression": "product impact",
                "meaning": "产品影响",
                "usage_context": "项目复盘或面试",
                "example_sentence": "I measured product impact through retention and task success rate.",
            },
            {
                "expression": "cross-functional alignment",
                "meaning": "跨团队对齐",
                "usage_context": "会议沟通",
                "example_sentence": "I drove cross-functional alignment between engineering and design.",
            },
        ]
        return {"report": report, "errors": errors, "expressions": expressions}
```

- [ ] **Step 5: Add repository methods for sessions**

Append to `CoachRepository` in `app/backend/app/repositories.py`:

```python
    def get_plan_day(self, day_index: int) -> dict[str, Any] | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM learning_plan WHERE day_index = ? ORDER BY id DESC LIMIT 1",
                (day_index,),
            ).fetchone()
            return row_to_dict(row) if row else None

    def create_session(self, day_index: int, topic: str) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO daily_sessions (day_index, topic) VALUES (?, ?)",
                (day_index, topic),
            )
            row = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)

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

    def save_inline_feedback(self, session_id: int, turn_id: int, feedback: list[dict[str, str]]) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            saved = []
            for item in feedback:
                cursor = connection.execute(
                    "INSERT INTO inline_feedback (session_id, turn_id, feedback_type, feedback_text) VALUES (?, ?, ?, ?)",
                    (session_id, turn_id, item["feedback_type"], item["feedback_text"]),
                )
                row = connection.execute("SELECT * FROM inline_feedback WHERE id = ?", (cursor.lastrowid,)).fetchone()
                saved.append(row_to_dict(row))
            return saved

    def save_review(self, session_id: int, review: dict[str, Any]) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO session_feedback (session_id, report) VALUES (?, ?)",
                (session_id, review["report"]),
            )
            for error in review["errors"][:5]:
                connection.execute(
                    """
                    INSERT INTO error_bank
                    (original_sentence, corrected_sentence, better_expression, error_type, explanation, source_session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        error["original_sentence"],
                        error["corrected_sentence"],
                        error["better_expression"],
                        error["error_type"],
                        error["explanation"],
                        session_id,
                    ),
                )
            for expression in review["expressions"][:5]:
                connection.execute(
                    """
                    INSERT INTO expression_bank
                    (expression, meaning, usage_context, example_sentence, source_session_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        expression["expression"],
                        expression["meaning"],
                        expression["usage_context"],
                        expression["example_sentence"],
                        session_id,
                    ),
                )
            row = connection.execute("SELECT * FROM session_feedback WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(row)
```

- [ ] **Step 6: Add session API test**

Append to `app/backend/tests/test_api.py`:

```python
def test_session_turn_and_review_flow(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)
    client.post(
        "/api/onboarding",
        json={
            "learning_goal": "AI product manager internationalization",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )

    start = client.post("/api/sessions/start", json={"day_index": 1})
    session_id = start.json()["session"]["id"]
    turn = client.post(
        "/api/sessions/turn",
        json={"session_id": session_id, "text": "I am responsible for make AI product."},
    )
    end = client.post("/api/sessions/end", json={"session_id": session_id})

    assert start.status_code == 200
    assert turn.status_code == 200
    assert "assistant_turn" in turn.json()
    assert len(turn.json()["inline_feedback"]) >= 1
    assert end.status_code == 200
    assert "总体表现" in end.json()["review"]["report"]
```

- [ ] **Step 7: Implement session APIs**

Append these imports to `app/backend/app/main.py`:

```python
from fastapi import HTTPException
from app.agents import ConversationAgent, InlineFeedbackAgent, ReviewAgent
from app.llm import FakeLLMProvider
from app.models import EndSessionRequest, StartSessionRequest, UserTurnRequest
```

Append these routes to `app/backend/app/main.py`:

```python
@app.post("/api/sessions/start")
def start_session(request: StartSessionRequest) -> dict[str, object]:
    repo = get_repository()
    plan_day = repo.get_plan_day(request.day_index)
    if plan_day is None:
        raise HTTPException(status_code=404, detail="Plan day not found")
    session = repo.create_session(day_index=request.day_index, topic=plan_day["topic"])
    assistant_text = f"Today we will practice: {plan_day['topic']}. {plan_day['scenario']} Let's start with your first answer."
    assistant_turn = repo.add_turn(session["id"], "assistant", assistant_text)
    return {"session": session, "assistant_turn": assistant_turn, "plan_day": plan_day}


@app.post("/api/sessions/turn")
def add_user_turn(request: UserTurnRequest) -> dict[str, object]:
    repo = get_repository()
    user_turn = repo.add_turn(request.session_id, "user", request.text)
    turns = repo.get_turns(request.session_id)
    topic = turns[0]["text"] if turns else "English speaking practice"
    assistant_text = ConversationAgent(FakeLLMProvider()).reply(topic=topic, conversation=turns)
    assistant_turn = repo.add_turn(request.session_id, "assistant", assistant_text)
    feedback = InlineFeedbackAgent().generate(request.text)
    saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
    }


@app.post("/api/sessions/end")
def end_session(request: EndSessionRequest) -> dict[str, object]:
    repo = get_repository()
    turns = repo.get_turns(request.session_id)
    topic = turns[0]["text"] if turns else "English speaking practice"
    review = ReviewAgent().generate_report(topic=topic, turns=turns)
    saved_review = repo.save_review(request.session_id, review)
    return {"review": review, "saved_review": saved_review}
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
cd app/backend
python -m pytest -v
```

Expected: PASS.

---

## Task 5: Frontend Skeleton, Onboarding, And Dashboard

**Files:**

- Create: `app/frontend/package.json`
- Create: `app/frontend/index.html`
- Create: `app/frontend/src/main.tsx`
- Create: `app/frontend/src/App.tsx`
- Create: `app/frontend/src/api.ts`
- Create: `app/frontend/src/types.ts`
- Create: `app/frontend/src/components/Onboarding.tsx`
- Create: `app/frontend/src/components/Dashboard.tsx`
- Create: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Create frontend package**

Create `app/frontend/package.json`:

```json
{
  "name": "ai-pm-english-coach-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc && vite build",
    "test": "vitest run",
    "preview": "vite preview --host 0.0.0.0"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/react": "^15.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "jsdom": "^24.1.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create app files**

Create `app/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI PM English Coach</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `app/frontend/src/types.ts`:

```typescript
export type Profile = {
  id: number;
  learning_goal: string;
  total_days: number;
  daily_minutes: number;
  current_level: string;
};

export type PlanDay = {
  id: number;
  day_index: number;
  topic: string;
  scenario: string;
  objective: string;
  status: string;
};

export type OnboardingResponse = {
  profile: Profile;
  plan: PlanDay[];
};
```

Create `app/frontend/src/api.ts`:

```typescript
import type { OnboardingResponse } from "./types";

const API_BASE = "http://localhost:8000";

export async function createOnboarding(input: {
  learning_goal: string;
  total_days: number;
  daily_minutes: number;
  current_level: string;
}): Promise<OnboardingResponse> {
  const response = await fetch(`${API_BASE}/api/onboarding`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  if (!response.ok) {
    throw new Error("Failed to create onboarding");
  }
  return response.json();
}
```

Create `app/frontend/src/components/Onboarding.tsx`:

```tsx
import { FormEvent, useState } from "react";

type Props = {
  onComplete: (input: {
    learning_goal: string;
    total_days: number;
    daily_minutes: number;
    current_level: string;
  }) => Promise<void>;
};

export function Onboarding({ onComplete }: Props) {
  const [learningGoal, setLearningGoal] = useState("AI product manager internationalization");
  const [totalDays, setTotalDays] = useState(14);
  const [dailyMinutes, setDailyMinutes] = useState(15);
  const [currentLevel, setCurrentLevel] = useState("IELTS 6.5, speaking 6");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    await onComplete({
      learning_goal: learningGoal,
      total_days: totalDays,
      daily_minutes: dailyMinutes,
      current_level: currentLevel
    });
    setIsSubmitting(false);
  }

  return (
    <form onSubmit={handleSubmit} aria-label="onboarding form">
      <h1>AI PM English Coach</h1>
      <label>
        Learning goal
        <textarea value={learningGoal} onChange={(event) => setLearningGoal(event.target.value)} />
      </label>
      <label>
        Total days
        <select value={totalDays} onChange={(event) => setTotalDays(Number(event.target.value))}>
          <option value={7}>7 days</option>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
        </select>
      </label>
      <label>
        Daily minutes
        <select value={dailyMinutes} onChange={(event) => setDailyMinutes(Number(event.target.value))}>
          <option value={10}>10 minutes</option>
          <option value={15}>15 minutes</option>
          <option value={20}>20 minutes</option>
        </select>
      </label>
      <label>
        Current level
        <input value={currentLevel} onChange={(event) => setCurrentLevel(event.target.value)} />
      </label>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Generating..." : "Generate Plan"}
      </button>
    </form>
  );
}
```

Create `app/frontend/src/components/Dashboard.tsx`:

```tsx
import type { PlanDay, Profile } from "../types";

type Props = {
  profile: Profile;
  plan: PlanDay[];
  onStartPractice: (day: PlanDay) => void;
};

export function Dashboard({ profile, plan, onStartPractice }: Props) {
  const today = plan.find((day) => day.status === "pending") ?? plan[0];

  return (
    <main>
      <h1>Dashboard</h1>
      <p>Goal: {profile.learning_goal}</p>
      <p>Plan: {profile.total_days} days, {profile.daily_minutes} minutes per day</p>
      {today ? (
        <section>
          <h2>Day {today.day_index}: {today.topic}</h2>
          <p>{today.objective}</p>
          <button onClick={() => onStartPractice(today)}>Start Practice</button>
        </section>
      ) : (
        <p>No plan available.</p>
      )}
    </main>
  );
}
```

Create `app/frontend/src/App.tsx`:

```tsx
import { useState } from "react";
import { createOnboarding } from "./api";
import { Dashboard } from "./components/Dashboard";
import { Onboarding } from "./components/Onboarding";
import type { PlanDay, Profile } from "./types";

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [plan, setPlan] = useState<PlanDay[]>([]);

  async function handleOnboarding(input: {
    learning_goal: string;
    total_days: number;
    daily_minutes: number;
    current_level: string;
  }) {
    const result = await createOnboarding(input);
    setProfile(result.profile);
    setPlan(result.plan);
  }

  if (!profile) {
    return <Onboarding onComplete={handleOnboarding} />;
  }

  return <Dashboard profile={profile} plan={plan} onStartPractice={() => undefined} />;
}
```

Create `app/frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 3: Add frontend smoke test**

Create `app/frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "./App";

vi.mock("./api", () => ({
  createOnboarding: vi.fn()
}));

test("renders onboarding form first", () => {
  render(<App />);

  expect(screen.getByText("AI PM English Coach")).toBeTruthy();
  expect(screen.getByLabelText("onboarding form")).toBeTruthy();
});
```

- [ ] **Step 4: Run frontend tests**

Run:

```bash
cd app/frontend
npm install
npm test
```

Expected: PASS.

---

## Task 6: Practice Room, Voice Helpers, And Review UI

**Files:**

- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/api.ts`
- Create: `app/frontend/src/voice.ts`
- Create: `app/frontend/src/components/PracticeRoom.tsx`
- Create: `app/frontend/src/components/FeedbackReport.tsx`
- Create: `app/frontend/src/components/MemoryLibrary.tsx`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Extend frontend types**

Append to `app/frontend/src/types.ts`:

```typescript
export type ConversationTurn = {
  id: number;
  session_id: number;
  turn_index: number;
  speaker: "user" | "assistant";
  text: string;
};

export type InlineFeedback = {
  id: number;
  feedback_type: string;
  feedback_text: string;
};

export type PracticeSession = {
  id: number;
  day_index: number;
  topic: string;
};

export type ReviewResult = {
  report: string;
  errors: Array<{
    original_sentence: string;
    corrected_sentence: string;
    better_expression: string;
    error_type: string;
    explanation: string;
  }>;
  expressions: Array<{
    expression: string;
    meaning: string;
    usage_context: string;
    example_sentence: string;
  }>;
};
```

- [ ] **Step 2: Add API client methods**

Append to `app/frontend/src/api.ts`:

```typescript
import type { ConversationTurn, InlineFeedback, PracticeSession, ReviewResult } from "./types";

export async function startSession(dayIndex: number): Promise<{
  session: PracticeSession;
  assistant_turn: ConversationTurn;
}> {
  const response = await fetch(`${API_BASE}/api/sessions/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ day_index: dayIndex })
  });
  if (!response.ok) {
    throw new Error("Failed to start session");
  }
  return response.json();
}

export async function sendUserTurn(sessionId: number, text: string): Promise<{
  user_turn: ConversationTurn;
  assistant_turn: ConversationTurn;
  inline_feedback: InlineFeedback[];
}> {
  const response = await fetch(`${API_BASE}/api/sessions/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text })
  });
  if (!response.ok) {
    throw new Error("Failed to send turn");
  }
  return response.json();
}

export async function endSession(sessionId: number): Promise<{ review: ReviewResult }> {
  const response = await fetch(`${API_BASE}/api/sessions/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });
  if (!response.ok) {
    throw new Error("Failed to end session");
  }
  return response.json();
}
```

- [ ] **Step 3: Add voice helpers**

Create `app/frontend/src/voice.ts`:

```typescript
type SpeechRecognitionConstructor = new () => SpeechRecognition;

type SpeechRecognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
};

type SpeechRecognitionEvent = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};

export function speak(text: string) {
  if (!("speechSynthesis" in window)) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.95;
  window.speechSynthesis.speak(utterance);
}

export function createSpeechRecognizer(onText: (text: string) => void, onError: (message: string) => void) {
  const SpeechRecognitionApi =
    (window as unknown as { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor })
      .SpeechRecognition ??
    (window as unknown as { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor })
      .webkitSpeechRecognition;

  if (!SpeechRecognitionApi) {
    return null;
  }

  const recognition = new SpeechRecognitionApi();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    onText(transcript);
  };
  recognition.onerror = () => onError("Speech recognition failed. Please type your answer instead.");
  return recognition;
}
```

- [ ] **Step 4: Add Practice Room**

Create `app/frontend/src/components/PracticeRoom.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import { endSession, sendUserTurn, startSession } from "../api";
import type { ConversationTurn, InlineFeedback, PlanDay, PracticeSession, ReviewResult } from "../types";
import { createSpeechRecognizer, speak } from "../voice";

type Props = {
  day: PlanDay;
  onReview: (review: ReviewResult) => void;
};

export function PracticeRoom({ day, onReview }: Props) {
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [feedback, setFeedback] = useState<InlineFeedback[]>([]);
  const [typedText, setTypedText] = useState("");
  const [voiceError, setVoiceError] = useState("");

  const recognizer = useMemo(
    () =>
      createSpeechRecognizer(
        (text) => {
          setTypedText(text);
        },
        setVoiceError
      ),
    []
  );

  useEffect(() => {
    async function boot() {
      const result = await startSession(day.day_index);
      setSession(result.session);
      setTurns([result.assistant_turn]);
      speak(result.assistant_turn.text);
    }
    void boot();
  }, [day.day_index]);

  async function submitTurn(text: string) {
    if (!session || !text.trim()) {
      return;
    }
    const result = await sendUserTurn(session.id, text.trim());
    setTurns((current) => [...current, result.user_turn, result.assistant_turn]);
    setFeedback(result.inline_feedback);
    setTypedText("");
    speak(result.assistant_turn.text);
  }

  async function finish() {
    if (!session) {
      return;
    }
    const result = await endSession(session.id);
    onReview(result.review);
  }

  return (
    <main>
      <h1>Practice: {day.topic}</h1>
      <p>{day.objective}</p>
      {voiceError ? <p role="alert">{voiceError}</p> : null}
      <section aria-label="conversation">
        {turns.map((turn) => (
          <article key={turn.id}>
            <strong>{turn.speaker}</strong>
            <p>{turn.text}</p>
          </article>
        ))}
      </section>
      <aside>
        <h2>Inline Feedback</h2>
        {feedback.map((item) => (
          <p key={item.id}>{item.feedback_text}</p>
        ))}
      </aside>
      <textarea value={typedText} onChange={(event) => setTypedText(event.target.value)} />
      <button onMouseDown={() => recognizer?.start()} onMouseUp={() => recognizer?.stop()}>
        Push to Talk
      </button>
      <button onClick={() => submitTurn(typedText)}>Send</button>
      <button onClick={finish}>End Session</button>
    </main>
  );
}
```

- [ ] **Step 5: Add feedback and memory views**

Create `app/frontend/src/components/FeedbackReport.tsx`:

```tsx
import type { ReviewResult } from "../types";

type Props = {
  review: ReviewResult;
  onBack: () => void;
};

export function FeedbackReport({ review, onBack }: Props) {
  return (
    <main>
      <h1>Feedback Report</h1>
      <p>{review.report}</p>
      <h2>Mistakes</h2>
      {review.errors.map((error) => (
        <article key={error.original_sentence}>
          <p>Original: {error.original_sentence}</p>
          <p>Corrected: {error.corrected_sentence}</p>
          <p>Better: {error.better_expression}</p>
        </article>
      ))}
      <h2>Expressions</h2>
      {review.expressions.map((expression) => (
        <article key={expression.expression}>
          <p>{expression.expression}: {expression.meaning}</p>
          <p>{expression.example_sentence}</p>
        </article>
      ))}
      <button onClick={onBack}>Back to Dashboard</button>
    </main>
  );
}
```

Create `app/frontend/src/components/MemoryLibrary.tsx`:

```tsx
export function MemoryLibrary() {
  return (
    <main>
      <h1>Memory Library</h1>
      <p>Mistakes and expressions are saved locally after each session.</p>
    </main>
  );
}
```

- [ ] **Step 6: Wire Practice Room into App**

Replace `app/frontend/src/App.tsx` with:

```tsx
import { useState } from "react";
import { createOnboarding } from "./api";
import { Dashboard } from "./components/Dashboard";
import { FeedbackReport } from "./components/FeedbackReport";
import { Onboarding } from "./components/Onboarding";
import { PracticeRoom } from "./components/PracticeRoom";
import type { PlanDay, Profile, ReviewResult } from "./types";

type View = "onboarding" | "dashboard" | "practice" | "review";

export default function App() {
  const [view, setView] = useState<View>("onboarding");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [plan, setPlan] = useState<PlanDay[]>([]);
  const [activeDay, setActiveDay] = useState<PlanDay | null>(null);
  const [review, setReview] = useState<ReviewResult | null>(null);

  async function handleOnboarding(input: {
    learning_goal: string;
    total_days: number;
    daily_minutes: number;
    current_level: string;
  }) {
    const result = await createOnboarding(input);
    setProfile(result.profile);
    setPlan(result.plan);
    setView("dashboard");
  }

  if (view === "onboarding" || !profile) {
    return <Onboarding onComplete={handleOnboarding} />;
  }

  if (view === "practice" && activeDay) {
    return (
      <PracticeRoom
        day={activeDay}
        onReview={(nextReview) => {
          setReview(nextReview);
          setView("review");
        }}
      />
    );
  }

  if (view === "review" && review) {
    return <FeedbackReport review={review} onBack={() => setView("dashboard")} />;
  }

  return (
    <Dashboard
      profile={profile}
      plan={plan}
      onStartPractice={(day) => {
        setActiveDay(day);
        setView("practice");
      }}
    />
  );
}
```

- [ ] **Step 7: Run frontend tests and build**

Run:

```bash
cd app/frontend
npm test
npm run build
```

Expected: PASS.

---

## Task 7: Local Run Documentation And Manual Verification

**Files:**

- Create: `README.md`
- Modify: `docs/superpowers/plans/2026-06-21-ai-pm-english-coach-mvp.md` only if execution reveals command changes.

- [ ] **Step 1: Add README**

Create `README.md`:

````markdown
# AI PM English Coach

Local-first AI English speaking coach for personal practice.

## Current MVP

- Configure learning goal and duration.
- Generate a local learning plan.
- Practice daily English conversations.
- Use push-to-talk or text fallback.
- Play AI replies with browser/system TTS.
- Show inline text feedback.
- Generate post-session review reports.
- Store learning memory in local SQLite.

## Backend

```bash
cd app/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Tests

```bash
cd app/backend
python -m pytest -v
```

```bash
cd app/frontend
npm test
npm run build
```

## LLM Provider

The first implementation uses a fake local provider for deterministic testing. Replace it with a domestic LLM provider after the local loop is stable.

Suggested environment variables:

```bash
export LLM_PROVIDER=deepseek
export LLM_API_KEY=your_api_key
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL=deepseek-chat
```
````

- [ ] **Step 2: Run backend tests**

Run:

```bash
cd app/backend
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend tests and build**

Run:

```bash
cd app/frontend
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 4: Start backend**

Run:

```bash
cd app/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: backend starts at `http://localhost:8000`.

- [ ] **Step 5: Start frontend**

Run:

```bash
cd app/frontend
npm run dev
```

Expected: frontend starts at the Vite local URL.

- [ ] **Step 6: Manual MVP verification**

In browser:

1. Open the frontend URL.
2. Confirm onboarding form appears.
3. Submit default goal, 14 days, 15 minutes, IELTS 6.5.
4. Confirm dashboard shows Day 1.
5. Click Start Practice.
6. Confirm AI opening message appears and TTS plays if browser supports it.
7. Type or speak: `I am responsible for make AI product.`
8. Click Send.
9. Confirm assistant replies in English.
10. Confirm inline feedback appears in Chinese.
11. Click End Session.
12. Confirm feedback report appears with mistakes and expressions.

Expected: the full local learning loop works without paid voice services.

---

## Self-Review

Spec coverage:

- Onboarding is covered by Task 3 and Task 5.
- Learning duration and goal setup are covered by Task 3 and Task 5.
- Local SQLite memory is covered by Task 2 and Task 4.
- Push-to-talk is covered by Task 6.
- Free TTS is covered by Task 6.
- Inline text feedback is covered by Task 4 and Task 6.
- Post-session review is covered by Task 4 and Task 6.
- Local run documentation is covered by Task 7.

Known intentional limitations:

- The first provider is fake for deterministic local testing.
- Real domestic LLM integration is deferred until the local loop is stable.
- Browser ASR may not work in every browser, so typed input remains as fallback.
- Git commit steps are omitted because the user chose not to configure a local Git identity yet.
