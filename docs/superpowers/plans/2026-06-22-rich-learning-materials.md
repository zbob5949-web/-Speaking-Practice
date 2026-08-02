# Rich Learning Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make plan generation, lesson-pack generation, and practice conversation use richer teaching materials instead of only thin topic/scenario/objective text.

**Architecture:** Extend the existing SQLite-backed `learning_plan` rows with nullable rich material columns, then upgrade agents to generate and consume structured lesson data while preserving old-plan compatibility. The frontend renders the richer `practice_brief` progressively: full material before the first user turn and compact coaching material during practice.

**Tech Stack:** FastAPI, SQLite, Python, Pytest, React, TypeScript, Vitest

---

## File Structure

- `app/backend/app/db.py`: Add nullable rich plan columns and seed richer default prompts.
- `app/backend/app/repositories.py`: Save and return rich plan fields.
- `app/backend/app/agents.py`: Upgrade `GoalAgent`, `ScenarioDesignAgent`, and `ConversationAgent` to generate/use richer material.
- `app/backend/app/main.py`: Pass practice brief into conversation replies and use brief fields in session opening.
- `app/backend/tests/test_agents.py`: Cover rich plan, rich brief, and conversation brief injection.
- `app/backend/tests/test_api.py`: Cover onboarding returning rich plan and session returning rich brief.
- `app/frontend/src/types.ts`: Extend `PlanDay` and `PracticeBrief` types.
- `app/frontend/src/components/PracticeRoom.tsx`: Render lesson-pack fields.
- `app/frontend/src/App.test.tsx`: Cover material rendering.

---

### Task 1: Persist Rich Plan Fields

**Files:**
- Modify: `app/backend/app/db.py`
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing test**

Add to `app/backend/tests/test_repositories.py`:

```python
def test_save_plan_persists_rich_learning_material_fields(tmp_path):
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

    saved = repo.save_plan(
        profile["id"],
        [
            {
                "day_index": 1,
                "topic": "Airport delay",
                "scenario": "Explain a delayed flight at the hotel desk.",
                "objective": "Explain what happened and ask for late check-in.",
                "skill_focus": "Past-tense storytelling",
                "communicative_task": "Explain a travel problem and request help.",
                "target_functions": ["explain what happened", "ask for help"],
                "success_criteria": ["Use past tense", "Make a clear request"],
                "brief_seed": "Generate a hotel check-in role-play after a delayed flight.",
            }
        ],
    )

    assert saved[0]["skill_focus"] == "Past-tense storytelling"
    assert saved[0]["communicative_task"] == "Explain a travel problem and request help."
    assert saved[0]["target_functions"] == ["explain what happened", "ask for help"]
    assert saved[0]["success_criteria"] == ["Use past tense", "Make a clear request"]
    assert saved[0]["brief_seed"] == "Generate a hotel check-in role-play after a delayed flight."
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_save_plan_persists_rich_learning_material_fields -v
```

Expected: FAIL because `learning_plan` does not persist the rich fields.

- [ ] **Step 3: Implement persistence**

In `app/backend/app/db.py`, add nullable columns to `learning_plan`:

```sql
skill_focus TEXT,
communicative_task TEXT,
target_functions_json TEXT,
success_criteria_json TEXT,
brief_seed TEXT,
```

Also add migration attempts in `init_db`:

```python
        for statement in [
            "ALTER TABLE learning_plan ADD COLUMN skill_focus TEXT",
            "ALTER TABLE learning_plan ADD COLUMN communicative_task TEXT",
            "ALTER TABLE learning_plan ADD COLUMN target_functions_json TEXT",
            "ALTER TABLE learning_plan ADD COLUMN success_criteria_json TEXT",
            "ALTER TABLE learning_plan ADD COLUMN brief_seed TEXT",
        ]:
            try:
                connection.execute(statement)
                connection.commit()
            except sqlite3.OperationalError:
                pass
```

In `app/backend/app/repositories.py`, update `row_to_dict`:

```python
def row_to_dict(row: Any) -> dict[str, Any]:
    import json
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
```

Update `save_plan` insert columns:

```python
INSERT INTO learning_plan (
  profile_id, day_index, topic, scenario, objective, status,
  skill_focus, communicative_task, target_functions_json, success_criteria_json, brief_seed
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

Use:

```python
import json
...
json.dumps(day.get("target_functions", []), ensure_ascii=False),
json.dumps(day.get("success_criteria", []), ensure_ascii=False),
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_save_plan_persists_rich_learning_material_fields -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/db.py app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "feat: persist rich learning plan fields"
```

### Task 2: Generate Rich Plan Days

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `app/backend/tests/test_agents.py`:

```python
def test_goal_agent_generates_rich_plan_fields():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "skill_focus" in system_prompt
            return """
            [
              {
                "topic": "Airport delay",
                "scenario": "Explain a delayed flight at a hotel desk.",
                "objective": "Ask for late check-in.",
                "skill_focus": "Past-tense storytelling",
                "communicative_task": "Explain the delay and request help.",
                "target_functions": ["explain what happened", "make a request"],
                "success_criteria": ["Use past tense", "Ask one clear question"],
                "brief_seed": "Create a hotel receptionist role-play after a delayed flight."
              }
            ]
            """

    plan = GoalAgent(MockLLM()).generate_plan(
        learning_goal="Travel English",
        total_days=1,
        daily_minutes=15,
        current_level="A2",
    )

    assert plan[0]["skill_focus"] == "Past-tense storytelling"
    assert plan[0]["target_functions"] == ["explain what happened", "make a request"]
    assert plan[0]["success_criteria"] == ["Use past tense", "Ask one clear question"]
    assert plan[0]["brief_seed"].startswith("Create a hotel receptionist")
```

Add to `app/backend/tests/test_api.py`:

```python
def test_onboarding_returns_rich_plan_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)

    response = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )

    assert response.status_code == 200
    day = response.json()["plan"][0]
    assert "skill_focus" in day
    assert "communicative_task" in day
    assert "target_functions" in day
    assert "success_criteria" in day
    assert "brief_seed" in day
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_goal_agent_generates_rich_plan_fields app/backend/tests/test_api.py::test_onboarding_returns_rich_plan_fields -v
```

Expected: FAIL because `GoalAgent` and fake onboarding do not return rich fields yet.

- [ ] **Step 3: Implement rich plan generation**

In `GoalAgent.generate_plan`, update the fallback system prompt so it requires these JSON keys:

```python
"每个对象必须包含英文键：topic, scenario, objective, skill_focus, communicative_task, target_functions, success_criteria, brief_seed。\n"
"target_functions 和 success_criteria 必须是数组，每个数组 3-5 项。\n"
```

When appending each plan item, include:

```python
"skill_focus": item.get("skill_focus", "Functional speaking"),
"communicative_task": item.get("communicative_task", item.get("objective", "Complete the speaking task")),
"target_functions": item.get("target_functions", []),
"success_criteria": item.get("success_criteria", []),
"brief_seed": item.get("brief_seed", item.get("scenario", "Generate a practical role-play lesson pack")),
```

Update fake LLM plan output in `app/backend/app/llm.py` if needed so fake provider returns the rich fields.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_goal_agent_generates_rich_plan_fields app/backend/tests/test_api.py::test_onboarding_returns_rich_plan_fields -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/llm.py app/backend/tests/test_agents.py app/backend/tests/test_api.py
git commit -m "feat: generate rich learning plan days"
```

### Task 3: Generate Rich Practice Briefs

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `app/backend/tests/test_agents.py`:

```python
def test_scenario_design_agent_generates_rich_lesson_pack():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "lesson pack" in system_prompt.lower() or "材料包" in system_prompt
            assert "brief_seed" in user_prompt
            return """
            {
              "title": "Hotel delay check-in",
              "user_visible_goal": "Explain a delayed flight and request late check-in.",
              "npc_role": "Hotel receptionist",
              "scenario_setup": "You arrived late because your flight was delayed.",
              "conversation_objective": "Explain the problem and ask whether your room is still available.",
              "lesson_focus": "Past-tense storytelling plus polite requests",
              "task_steps": ["Explain what happened", "Ask about the room", "Confirm the next step"],
              "target_expressions": [
                {"expression": "My flight was delayed.", "meaning_zh": "我的航班延误了。", "example": "My flight was delayed by two hours.", "when_to_use": "explaining the reason you arrived late"}
              ],
              "sentence_frames": ["I arrived late because...", "Could you still...?"],
              "model_dialogue": ["NPC: Good evening. How can I help?", "Learner: My flight was delayed by two hours."],
              "common_mistakes": [{"mistake": "I am arrive late.", "better": "I arrived late.", "reason_zh": "arrive 要用过去式 arrived。"}],
              "rubric": ["Clear reason", "Polite request"],
              "stretch_goal": "Add one detail about the delay."
            }
            """

    agent = ScenarioDesignAgent(MockLLM(), lambda name: None)
    brief = agent.generate_brief(
        {"topic": "Hotel", "brief_seed": "Generate a hotel delay lesson pack."},
        [],
        [],
        {},
    )

    assert brief["lesson_focus"] == "Past-tense storytelling plus polite requests"
    assert brief["task_steps"][0] == "Explain what happened"
    assert brief["target_expressions"][0]["meaning_zh"] == "我的航班延误了。"
    assert brief["common_mistakes"][0]["better"] == "I arrived late."
```

Add to `app/backend/tests/test_api.py`:

```python
def test_start_session_returns_rich_practice_brief(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
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

    response = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert response.status_code == 200
    brief = response.json()["practice_brief"]
    assert "lesson_focus" in brief
    assert "task_steps" in brief
    assert "sentence_frames" in brief
    assert "model_dialogue" in brief
    assert "common_mistakes" in brief
    assert "rubric" in brief
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_scenario_design_agent_generates_rich_lesson_pack app/backend/tests/test_api.py::test_start_session_returns_rich_practice_brief -v
```

Expected: FAIL because brief generation does not guarantee rich fields yet.

- [ ] **Step 3: Implement rich brief generation**

Update `ScenarioDesignAgent.generate_brief` default prompt to require a complete lesson pack with:

```python
"必须输出完整 lesson pack JSON，包含 title, user_visible_goal, npc_role, scenario_setup, conversation_objective, lesson_focus, task_steps, target_expressions, sentence_frames, model_dialogue, common_mistakes, rubric, stretch_goal。\n"
"target_expressions 必须是对象数组，每个对象包含 expression, meaning_zh, example, when_to_use。\n"
```

After JSON parse, normalize missing fields:

```python
defaults = {
    "title": plan_day.get("topic", "Practice"),
    "user_visible_goal": plan_day.get("objective", "Practice speaking"),
    "npc_role": "NPC",
    "scenario_setup": plan_day.get("scenario", "Setup"),
    "conversation_objective": plan_day.get("objective", "Objective"),
    "lesson_focus": plan_day.get("skill_focus", "Functional speaking"),
    "task_steps": [],
    "target_expressions": [],
    "sentence_frames": [],
    "model_dialogue": [],
    "common_mistakes": [],
    "rubric": plan_day.get("success_criteria", []),
    "avoid_patterns": [],
    "difficulty": "normal",
    "coach_notes": "",
    "stretch_goal": "",
}
defaults.update(parsed)
return defaults
```

Update fake LLM scenario output in `app/backend/app/llm.py` if needed so fake provider returns these fields.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_scenario_design_agent_generates_rich_lesson_pack app/backend/tests/test_api.py::test_start_session_returns_rich_practice_brief -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/llm.py app/backend/tests/test_agents.py app/backend/tests/test_api.py
git commit -m "feat: generate rich practice lesson packs"
```

### Task 4: Inject Practice Brief Into Conversation

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_agents.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add to `app/backend/tests/test_agents.py`:

```python
def test_conversation_agent_includes_practice_brief_context():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Hotel receptionist" in user_prompt
            assert "My flight was delayed." in user_prompt
            assert "Explain what happened" in user_prompt
            return '{"reply": "Good evening. Could you tell me what happened with your flight?", "hints": ["说明航班延误"]}'

    agent = ConversationAgent(MockLLM())
    response = agent.reply(
        topic="Hotel delay",
        objective="Explain the problem.",
        user_level="A2",
        learning_goal="Travel English",
        conversation=[{"speaker": "user", "text": "Hello."}],
        practice_brief={
            "npc_role": "Hotel receptionist",
            "task_steps": ["Explain what happened"],
            "target_expressions": [{"expression": "My flight was delayed."}],
            "rubric": ["Clear reason"],
        },
    )

    assert response["reply"].startswith("Good evening")
```

Add to `app/backend/tests/test_api.py`:

```python
def test_user_turn_uses_practice_brief_context(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "reply" in system_prompt and "hints" in system_prompt:
                assert "Hotel receptionist" in user_prompt
                assert "My flight was delayed." in user_prompt
                return '{"reply": "I see. Could you explain how long the delay was?", "hints": ["说明延误多久"]}'
            if "feedback_type" in system_prompt:
                return "[]"
            return "{}"

    monkeypatch.setattr(main_module, "create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]

    response = client.post("/api/sessions/turn", json={"session_id": session_id, "text": "Hello."})

    assert response.status_code == 200
    assert response.json()["assistant_turn"]["text"].startswith("I see")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_conversation_agent_includes_practice_brief_context app/backend/tests/test_api.py::test_user_turn_uses_practice_brief_context -v
```

Expected: FAIL because `ConversationAgent.reply` does not accept/use `practice_brief`.

- [ ] **Step 3: Implement brief injection**

Update `ConversationAgent.reply` and `reply_stream` signatures:

```python
practice_brief: dict[str, object] | None = None
```

Add helper:

```python
def format_practice_brief_context(practice_brief: dict[str, object] | None) -> str:
    if not practice_brief:
        return ""
    return json.dumps(
        {
            "npc_role": practice_brief.get("npc_role"),
            "conversation_objective": practice_brief.get("conversation_objective"),
            "task_steps": practice_brief.get("task_steps", []),
            "target_expressions": practice_brief.get("target_expressions", []),
            "avoid_patterns": practice_brief.get("avoid_patterns", []),
            "rubric": practice_brief.get("rubric", []),
        },
        ensure_ascii=False,
    )
```

Include in conversation user prompt:

```python
"--- 今日材料包（供 NPC 设计下一句时使用，不要逐字朗读）---\n{practice_brief_context}\n"
```

In `app/backend/app/main.py`, when calling `ConversationAgent.reply` and `reply_stream`, load the stored brief:

```python
brief = None
if plan_day:
    brief_row = repo.get_practice_brief(plan_day["id"])
    if brief_row:
        brief = json.loads(brief_row["brief_json"])
```

Pass `practice_brief=brief`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_conversation_agent_includes_practice_brief_context app/backend/tests/test_api.py::test_user_turn_uses_practice_brief_context -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/main.py app/backend/tests/test_agents.py app/backend/tests/test_api.py
git commit -m "feat: inject lesson pack context into conversation"
```

### Task 5: Render Rich Learning Materials

**Files:**
- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

In `app/frontend/src/App.test.tsx`, add rich brief fields to one `startSession` mock and assert they render:

```tsx
test("renders rich lesson pack materials in practice room", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Hotel delay" },
    turns: [{ id: 1, session_id: 1, turn_index: 1, speaker: "assistant", text: "Good evening." }],
    practice_brief: {
      title: "Hotel delay check-in",
      user_visible_goal: "Explain a delayed flight.",
      npc_role: "Hotel receptionist",
      scenario_setup: "You arrived late because your flight was delayed.",
      conversation_objective: "Explain the problem and ask whether your room is still available.",
      lesson_focus: "Past-tense storytelling plus polite requests",
      task_steps: ["Explain what happened", "Ask about the room"],
      target_expressions: [
        {
          expression: "My flight was delayed.",
          meaning_zh: "我的航班延误了。",
          example: "My flight was delayed by two hours.",
          when_to_use: "explaining why you arrived late"
        }
      ],
      sentence_frames: ["I arrived late because..."],
      model_dialogue: ["NPC: Good evening. How can I help?", "Learner: My flight was delayed."],
      common_mistakes: [{ mistake: "I am arrive late.", better: "I arrived late.", reason_zh: "用过去式 arrived。" }],
      rubric: ["Clear reason", "Polite request"],
      stretch_goal: "Add one detail about the delay.",
      avoid_patterns: ["I am arrive"],
      difficulty: "normal",
      coach_notes: "Push past tense."
    },
  });

  render(<App />);

  expect(await screen.findByText("Past-tense storytelling plus polite requests")).toBeTruthy();
  expect(screen.getByText("Explain what happened")).toBeTruthy();
  expect(screen.getByText("My flight was delayed.")).toBeTruthy();
  expect(screen.getByText("我的航班延误了。")).toBeTruthy();
  expect(screen.getByText("I arrived late because...")).toBeTruthy();
  expect(screen.getByText("NPC: Good evening. How can I help?")).toBeTruthy();
  expect(screen.getByText("I am arrive late.")).toBeTruthy();
  expect(screen.getByText("Clear reason")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx --testNamePattern "renders rich lesson pack materials in practice room"
```

Expected: FAIL because PracticeRoom does not render these fields yet.

- [ ] **Step 3: Extend frontend types and rendering**

In `app/frontend/src/types.ts`, extend `PracticeBrief`:

```ts
export type TargetExpression = string | {
  expression: string;
  meaning_zh?: string;
  example?: string;
  when_to_use?: string;
};

export type CommonMistake = string | {
  mistake: string;
  better: string;
  reason_zh?: string;
};

export type PracticeBrief = {
  title: string;
  user_visible_goal: string;
  npc_role: string;
  scenario_setup: string;
  conversation_objective: string;
  lesson_focus?: string;
  task_steps?: string[];
  target_expressions: TargetExpression[];
  sentence_frames?: string[];
  model_dialogue?: string[];
  common_mistakes?: CommonMistake[];
  rubric?: string[];
  avoid_patterns: string[];
  difficulty: string;
  coach_notes: string;
  stretch_goal?: string;
};
```

In `PracticeRoom.tsx`, render:

- lesson focus
- task steps
- expression cards with meaning/example/when_to_use
- sentence frames
- model dialogue
- common mistakes
- rubric
- stretch goal

Use small helper render functions so string/object arrays both work.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx --testNamePattern "renders rich lesson pack materials in practice room"
PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/types.ts app/frontend/src/components/PracticeRoom.tsx app/frontend/src/App.test.tsx
git commit -m "feat: render rich lesson materials in practice room"
```

