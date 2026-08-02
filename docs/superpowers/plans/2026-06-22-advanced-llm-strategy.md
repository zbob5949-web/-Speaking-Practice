# Project Management and Advanced LLM Strategies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the local MVP to support multi-project (goal) management, implement dual-model architecture (Planner vs Chat), replace hardcoded plans with dynamic LLM generation, and build a flexible multi-dimensional memory mechanism for daily conversations.

**Architecture:** 
1. **Multi-project Management:** Update the database to support fetching/creating specific profiles. Expose a project switcher and a "Create New Project" button in the frontend sidebar/settings.
2. **Dual-Model Configuration:** Expand `Settings` in `app/backend/app/config.py` to support `PLANNER_MODEL` (e.g., deepseek/deepseek-v4-pro) and `CHAT_MODEL` (e.g., deepseek/deepseek-v4-flash).
3. **Agent LLM Rewrite:** Rewrite `GoalAgent` to call the Planner model and parse JSON output. Rewrite `ConversationAgent` to use the Chat model with dynamic prompts based on user level, goal, and task.
4. **Session Persistence:** Update the `sessions/start` API to check for an existing session for the current day. If it exists, resume it (return existing turns) instead of creating a new one. Update Conversation memory retrieval to use a balanced context strategy rather than a hardcoded 6-turn limit.

**Tech Stack:** React, FastAPI, SQLite, Python `dotenv`, OpenRouter API.

---

### Task 1: Update Configuration for Dual Models

**Files:**
- Modify: `app/backend/app/config.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/app/agents.py`
- Modify: `.env.example`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from app.config import load_settings
from pathlib import Path

def test_load_dual_models(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL", "deepseek/deepseek-v4-pro")
    monkeypatch.setenv("CHAT_MODEL", "deepseek/deepseek-v4-flash")
    
    settings = load_settings()
    assert settings.planner_model == "deepseek/deepseek-v4-pro"
    assert settings.chat_model == "deepseek/deepseek-v4-flash"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL due to missing attributes in `Settings`.

- [ ] **Step 3: Write minimal implementation**

Modify `app/backend/app/config.py`:
```python
@dataclass(frozen=True)
class Settings:
    database_path: Path
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str | None
    planner_model: str
    chat_model: str

def load_settings(dotenv_path: Path | None = None) -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path or project_root / ".env", override=False)
    database_path = Path(os.getenv("COACH_DB_PATH", project_root / "data" / "coach.sqlite"))
    
    # Fallback to LLM_MODEL if specific models aren't set for backward compatibility
    legacy_model = os.getenv("LLM_MODEL", "fake-local-coach")
    
    return Settings(
        database_path=database_path,
        llm_provider=os.getenv("LLM_PROVIDER", "fake"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        planner_model=os.getenv("PLANNER_MODEL", legacy_model),
        chat_model=os.getenv("CHAT_MODEL", legacy_model),
    )
```

Modify `.env.example` to show `PLANNER_MODEL` and `CHAT_MODEL` instead of `LLM_MODEL`.

Modify `app/backend/app/main.py` in `add_user_turn` to use `settings.chat_model`:
```python
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/backend/app/config.py app/backend/app/main.py .env.example tests/test_config.py
git commit -m "feat: support dual models for planner and chat"
```

---

### Task 2: Implement Multi-Project Database Queries

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/app/models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repositories.py
from app.repositories import CoachRepository
from app.db import init_db, connect

def test_get_all_profiles(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    p1 = repo.save_profile("Goal 1", 7, 15, "Level 1")
    p2 = repo.save_profile("Goal 2", 14, 20, "Level 2")
    
    profiles = repo.get_all_profiles()
    assert len(profiles) == 2
    assert profiles[0]["learning_goal"] == "Goal 2" # Newest first
    assert profiles[1]["learning_goal"] == "Goal 1"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_repositories.py -v`
Expected: FAIL due to `get_all_profiles` not defined.

- [ ] **Step 3: Write minimal implementation**

In `app/backend/app/repositories.py`, add:
```python
    def get_all_profiles(self) -> list[dict[str, object]]:
        with connect(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM user_profile ORDER BY id DESC").fetchall()
            return [row_to_dict(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict[str, object] | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM user_profile WHERE id = ?", (profile_id,)).fetchone()
            return row_to_dict(row) if row else None
```

In `app/backend/app/models.py`, add:
```python
class SwitchProfileRequest(BaseModel):
    profile_id: int
```

In `app/backend/app/main.py`, update `get_current_learning_state` to optionally take `profile_id`, and add a route to get all profiles:
```python
from typing import Optional

@app.get("/api/profiles")
def get_all_profiles() -> dict[str, object]:
    repo = get_repository()
    return {"profiles": repo.get_all_profiles()}

@app.get("/api/current")
def get_current_learning_state(profile_id: Optional[int] = None) -> dict[str, object]:
    repo = get_repository()
    profile = repo.get_profile(profile_id) if profile_id else repo.get_latest_profile()
    if profile is None:
        raise HTTPException(status_code=404, detail="No learning plan found")
    plan = clean_plan(repo.get_plan(profile_id=profile["id"]))
    return {"profile": profile, "plan": plan}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_repositories.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/backend/app/repositories.py app/backend/app/main.py app/backend/app/models.py tests/test_repositories.py
git commit -m "feat: support fetching multiple profiles for project switching"
```

---

### Task 3: Replace Hardcoded Plan with LLM Generation

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# app/backend/tests/test_agents.py
from app.agents import GoalAgent
from app.llm import FakeLLMProvider

class MockPlannerProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return '''
        [
            {"topic": "Mock Topic", "scenario": "Mock Scenario", "objective": "Mock Obj"}
        ]
        '''

def test_goal_agent_uses_llm():
    agent = GoalAgent(MockPlannerProvider())
    plan = agent.generate_plan("Test Goal", 1, 15, "Level 1")
    assert len(plan) == 1
    assert plan[0]["topic"] == "Mock Topic"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_agents.py -v`
Expected: FAIL because `GoalAgent` currently uses hardcoded `DEFAULT_AI_PM_PLAN`.

- [ ] **Step 3: Write minimal implementation**

Modify `app/backend/app/agents.py`:
```python
import json

class GoalAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def generate_plan(
        self,
        learning_goal: str,
        total_days: int,
        daily_minutes: int,
        current_level: str,
    ) -> list[dict[str, str | int]]:
        system_prompt = (
            "You are an expert English learning planner. "
            "Output ONLY a valid JSON array of objects, with no markdown formatting or extra text. "
            "Each object must have exactly these keys: 'topic', 'scenario', 'objective'."
        )
        user_prompt = (
            f"Create a {total_days}-day speaking practice plan for a user at level: '{current_level}'. "
            f"The goal is: '{learning_goal}'. Daily practice time: {daily_minutes} minutes. "
            "Each day should build upon the previous ones."
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Clean potential markdown fences
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            generated_items = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Fallback for catastrophic failure
            generated_items = [{"topic": "General Practice", "scenario": "Practice English", "objective": "Speak fluently"}] * total_days

        plan: list[dict[str, str | int]] = []
        for index in range(total_days):
            item = generated_items[index] if index < len(generated_items) else generated_items[-1]
            plan.append(
                {
                    "day_index": index + 1,
                    "topic": item.get("topic", "Practice"),
                    "scenario": item.get("scenario", "Daily practice"),
                    "objective": item.get("objective", "Improve fluency"),
                    "status": "pending",
                }
            )
        return plan
```

Update `app/backend/app/main.py` in `create_onboarding`:
```python
@app.post("/api/onboarding")
def create_onboarding(request: OnboardingRequest) -> dict[str, object]:
    repo = get_repository()
    settings = load_settings()
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.planner_model,
    )
    profile = repo.save_profile(
        learning_goal=request.learning_goal,
        total_days=request.total_days,
        daily_minutes=request.daily_minutes,
        current_level=request.current_level,
    )
    plan_data = GoalAgent(llm).generate_plan(
        learning_goal=request.learning_goal,
        total_days=request.total_days,
        daily_minutes=request.daily_minutes,
        current_level=request.current_level,
    )
    for day in plan_data:
        repo.save_plan(
            profile_id=profile["id"],
            day_index=int(day["day_index"]),
            topic=str(day["topic"]),
            scenario=str(day["scenario"]),
            objective=str(day["objective"]),
        )
    plan = clean_plan(repo.get_plan(profile_id=profile["id"]))
    return {"profile": profile, "plan": plan}
```

Fix `app/backend/tests/test_api.py` to handle the new `GoalAgent` initialization (since it now requires `llm`).

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_agents.py tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/backend/app/agents.py app/backend/app/main.py tests/test_agents.py tests/test_api.py
git commit -m "feat: replace hardcoded plan with real LLM planner agent"
```

---

### Task 4: Dynamic Conversation Prompt and Memory Balance

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/main.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_conversation_agent.py
from app.agents import ConversationAgent
from app.llm import FakeLLMProvider

class MockChatProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system = system_prompt
        self.last_user = user_prompt
        return "Reply"

def test_dynamic_conversation_prompt():
    llm = MockChatProvider()
    agent = ConversationAgent(llm)
    
    # We pass 10 turns. We expect it not to strictly hard-truncate at 6 inside the agent blindly, 
    # or at least use the context properly.
    turns = [{"speaker": "user", "text": f"T{i}"} for i in range(10)]
    
    agent.reply(
        topic="Interviews", 
        objective="Practice answering.",
        user_level="Beginner",
        learning_goal="Job hunt",
        conversation=turns
    )
    
    assert "Beginner" in llm.last_system
    assert "Job hunt" in llm.last_system
    assert "Interviews" in llm.last_user
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_conversation_agent.py -v`
Expected: FAIL because `reply` signature changed and prompt is currently static.

- [ ] **Step 3: Write minimal implementation**

Modify `ConversationAgent.reply` in `app/backend/app/agents.py`:
```python
class ConversationAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def reply(self, topic: str, objective: str, user_level: str, learning_goal: str, conversation: list[dict[str, str]]) -> str:
        # Multi-dimensional memory: 
        # We pass the full history to the model, but let the LLM handle it, or we truncate to last 20 if extremely long.
        recent_turns = conversation[-20:] if len(conversation) > 20 else conversation
        user_prompt_turns = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in recent_turns)
        
        system_prompt = (
            "You are an expert English speaking coach. "
            f"The user's current level is: '{user_level}'. Their ultimate goal is: '{learning_goal}'. "
            "Instructions:\n"
            "1. Adapt your vocabulary, sentence complexity, and response length dynamically based on the user's level and their latest response.\n"
            "2. Keep the conversation natural and engaging.\n"
            "3. Usually ask a relevant follow-up question to keep the flow going, unless it's a natural endpoint.\n"
            "4. Do NOT explicitly mention their level or goal, just act accordingly."
        )
        
        user_prompt = (
            f"Today's Topic: {topic}\n"
            f"Today's Objective: {objective}\n"
            "--- Conversation History ---\n"
            f"{user_prompt_turns}\n"
            "--- End History ---\n"
            "Provide your next reply:"
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        return response.strip()
```

Update `app/backend/app/main.py` inside `add_user_turn`:
```python
    profile = repo.get_profile(turns[0].get("profile_id")) if False else repo.get_latest_profile() # We need profile data
    # Actually, turns belong to a session, session belongs to a day. 
    # Let's get the active profile.
    profile = repo.get_latest_profile() 
    plan_day = repo.get_plan_day(turns[0]["day_index"] if turns else 1) if False else None
    # Wait, we need to get the session to know the day_index.
    session = connection.execute("SELECT day_index FROM daily_sessions WHERE id = ?", (request.session_id,)).fetchone() # Pseudo code
```
*Correction for `main.py` `add_user_turn`:*
```python
@app.post("/api/sessions/turn")
def add_user_turn(request: UserTurnRequest) -> dict[str, object]:
    repo = get_repository()
    
    # 1. Save user turn
    user_turn = repo.add_turn(request.session_id, "user", request.text)
    turns = repo.get_turns(request.session_id)
    
    # 2. Fetch context
    with connect(repo.db_path) as conn:
        session = dict(conn.execute("SELECT day_index, topic FROM daily_sessions WHERE id = ?", (request.session_id,)).fetchone())
        # We need the profile for level/goal. For now, fetch latest.
        profile = repo.get_latest_profile()
        plan_day = repo.get_plan_day(session["day_index"])
        
    objective = plan_day["objective"] if plan_day else "Practice speaking"
    user_level = profile["current_level"] if profile else "Intermediate"
    learning_goal = profile["learning_goal"] if profile else "Improve English"

    # 3. Call LLM
    settings = load_settings()
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    
    assistant_text = ConversationAgent(llm).reply(
        topic=session["topic"],
        objective=objective,
        user_level=user_level,
        learning_goal=learning_goal,
        conversation=turns
    )
    
    assistant_turn = repo.add_turn(request.session_id, "assistant", assistant_text)
    
    # 4. Feedback
    feedback = InlineFeedbackAgent().generate(request.text)
    saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
    
    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
    }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_conversation_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/backend/app/agents.py app/backend/app/main.py tests/test_conversation_agent.py
git commit -m "feat: implement dynamic conversation prompt and expand memory context"
```

---

### Task 5: Daily Session Resumption (Same-day Memory)

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session_resume.py
from app.repositories import CoachRepository
from app.db import init_db

def test_get_or_create_session_resumes_same_day(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    s1 = repo.get_or_create_session(1, "Topic 1")
    repo.add_turn(s1["id"], "user", "Hello")
    
    s2 = repo.get_or_create_session(1, "Topic 1")
    assert s1["id"] == s2["id"]
    
    turns = repo.get_turns(s2["id"])
    assert len(turns) == 1
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_session_resume.py -v`
Expected: FAIL due to `get_or_create_session` not existing.

- [ ] **Step 3: Write minimal implementation**

Modify `app/backend/app/repositories.py`:
```python
    def get_or_create_session(self, day_index: int, topic: str) -> dict[str, Any]:
        with connect(self.db_path) as connection:
            # Look for an active session today (we can approximate by day_index and no ended_at, or just latest by day_index)
            row = connection.execute(
                "SELECT * FROM daily_sessions WHERE day_index = ? ORDER BY id DESC LIMIT 1",
                (day_index,)
            ).fetchone()
            
            if row:
                return row_to_dict(row)
                
            cursor = connection.execute(
                "INSERT INTO daily_sessions (day_index, topic) VALUES (?, ?)",
                (day_index, topic),
            )
            saved = connection.execute("SELECT * FROM daily_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return row_to_dict(saved)
```

Modify `app/backend/app/main.py` `start_session`:
```python
@app.post("/api/sessions/start")
def start_session(request: StartSessionRequest) -> dict[str, object]:
    repo = get_repository()
    plan_day = repo.get_plan_day(request.day_index)
    if plan_day is None:
        raise HTTPException(status_code=404, detail="Plan day not found")
    plan_day = clean_plan_day(plan_day)
    
    session = repo.get_or_create_session(day_index=request.day_index, topic=plan_day["topic"])
    turns = repo.get_turns(session["id"])
    
    if not turns:
        assistant_text = (
            f"Today we will practice: {plan_day['topic']}. "
            f"{plan_day['scenario']} Let's start with your first answer."
        )
        assistant_turn = repo.add_turn(session["id"], "assistant", assistant_text)
        turns = [assistant_turn]
        
    return {"session": session, "turns": turns, "plan_day": plan_day}
```

Modify `app/frontend/src/api.ts` to type `turns` instead of `assistant_turn`:
```typescript
export async function startSession(dayIndex: number): Promise<{
  session: PracticeSession;
  turns: ConversationTurn[];
  plan_day: PlanDay;
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
```

Modify `app/frontend/src/components/PracticeRoom.tsx`:
```typescript
        const result = await startSession(day.day_index);
        setSession(result.session);
        setTurns(result.turns);
        
        // Only play opening TTS if it's a fresh session (1 turn)
        if (result.turns.length === 1) {
            playTTS(result.turns[0].text).catch(() => {
              console.warn("Failed to play opening TTS audio automatically.");
            });
        }
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_session_resume.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/backend/app/repositories.py app/backend/app/main.py app/frontend/src/api.ts app/frontend/src/components/PracticeRoom.tsx tests/test_session_resume.py
git commit -m "feat: resume existing daily session instead of creating new ones"
```

---

### Task 6: Frontend Multi-Project Switching

**Files:**
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/components/SettingsPage.tsx`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Update API Client**
Modify `app/frontend/src/api.ts` to support fetching profiles and loading specific ones:
```typescript
export async function getProfiles(): Promise<{ profiles: Profile[] }> {
  const response = await fetch(`${API_BASE}/api/profiles`);
  return response.json();
}

export async function getCurrentLearningState(profileId?: number): Promise<OnboardingResponse> {
  const url = profileId ? `${API_BASE}/api/current?profile_id=${profileId}` : `${API_BASE}/api/current`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("No current learning state");
  }
  return response.json();
}
```

- [ ] **Step 2: Update Settings UI**
Modify `app/frontend/src/components/SettingsPage.tsx` to list profiles and add a "Create New Goal" button. (Mock implementation for brevity, actual code will use standard React state to fetch `getProfiles` and map over them, providing a `onSwitchProfile(id)` and `onCreateNew()` callback).

- [ ] **Step 3: Update App.tsx State**
Modify `app/frontend/src/App.tsx` to handle `profileId` state. Pass `onCreateNew={() => { setProfile(null); setView("onboarding"); }}` to Settings.

- [ ] **Step 4: Run test to verify it passes**
Run: `npm test`
Expected: PASS (fix minor typescript errors if any).

- [ ] **Step 5: Commit**
```bash
git add app/frontend/src/api.ts app/frontend/src/components/SettingsPage.tsx app/frontend/src/App.tsx
git commit -m "feat: add multi-project switching and creation in settings"
```
