# Agent Learning Loop Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the three-stage product iteration that turns the English speaking coach into a teacher-like Agent system with visible review, memory, and adaptive planning.

**Architecture:** Keep the existing FastAPI + SQLite + React architecture. Add read APIs and repository methods for Growth data, strengthen memory/adaptation lifecycle rules, then render the learning loop in the frontend. Preserve the current Agent classes, but add schema validation and safer parsing around their structured outputs.

**Tech Stack:** Python, FastAPI, SQLite, pytest, React, TypeScript, Vite, Vitest.

---

## File Structure

- `app/backend/app/repositories.py`: Add Growth query methods, JSON decoding helpers, memory merge/upsert logic, active adjustment filtering, and plan-day status updates.
- `app/backend/app/main.py`: Add Growth summary APIs and connect session completion/review data to frontend-consumable endpoints.
- `app/backend/app/models.py`: Add response models for daily reviews, memory items, plan adjustments, and Growth summary.
- `app/backend/app/agents.py`: Add structured-output normalization helpers for review, memory, adjustment, and scenario outputs.
- `app/backend/app/prompts.py`: Tighten JSON contracts for learning-loop Agents.
- `app/backend/tests/test_repositories.py`: Cover repository JSON decoding, memory merge, adjustment expiry, and plan completion logic.
- `app/backend/tests/test_api.py`: Cover Growth APIs and learning-loop endpoint behavior.
- `app/backend/tests/test_agents.py`: Cover malformed Agent output normalization.
- `app/frontend/src/types.ts`: Add Growth-related TypeScript types.
- `app/frontend/src/api.ts`: Add `getGrowthSummary()`.
- `app/frontend/src/components/GrowthPage.tsx`: Replace placeholder with real review/memory/adjustment UI.
- `app/frontend/src/App.test.tsx`: Cover GrowthPage loading, empty, populated, and error states.
- `app/frontend/src/styles.css`: Add compact Growth cards and timeline styles.

---

## Task 1: Backend Growth Summary API

**Files:**
- Modify: `app/backend/app/models.py`
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_repositories.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing repository tests**

Add tests that prove the repository can return decoded Growth data:

```python
def test_get_growth_summary_decodes_review_memory_and_adjustments(tmp_path):
    from app.db import init_db
    from app.repositories import CoachRepository

    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.create_profile("AI PM interview speaking", 7, 20, "B1")
    plan = repo.save_plan(profile["id"], [{
        "day_index": 1,
        "topic": "Product interview",
        "scenario": "Answering product sense questions",
        "objective": "Explain product tradeoffs clearly",
        "status": "pending",
    }])
    review = repo.save_daily_review(
        profile_id=profile["id"],
        review_date="2026-06-22",
        status="completed",
        user_report={"summary": "You practiced tradeoff explanations.", "next_focus": "Use clearer structure."},
        structured_analysis={"weaknesses": ["unclear structure"], "strengths": ["kept speaking"]},
        source_session_ids=[1],
        raw_agent_output="{}",
    )
    repo.save_memory_item(profile["id"], "weakness", "Often misses structured answers", "Review 1", 0.85, "active", review["id"])
    repo.save_plan_adjustment(plan[0]["id"], review["id"], "focus_shift", "Practice STAR structure", "Weak structure", "Start with context-impact-action", "high")

    summary = repo.get_growth_summary(profile["id"])

    assert summary["latest_review"]["user_report"]["summary"] == "You practiced tradeoff explanations."
    assert summary["latest_review"]["structured_analysis"]["weaknesses"] == ["unclear structure"]
    assert summary["active_memory"][0]["content"] == "Often misses structured answers"
    assert summary["active_adjustments"][0]["title"] == "Practice STAR structure"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_get_growth_summary_decodes_review_memory_and_adjustments -v
```

Expected: FAIL because `get_growth_summary` does not exist.

- [ ] **Step 3: Implement repository methods**

Add helpers and methods in `CoachRepository`:

```python
def _decode_json(value, fallback):
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback

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
        item = dict(row)
        item["user_report"] = _decode_json(item.pop("user_report_json", None), {})
        item["structured_analysis"] = _decode_json(item.pop("structured_analysis_json", None), {})
        item["source_session_ids"] = _decode_json(item.pop("source_session_ids_json", None), [])
        reviews.append(item)
    return reviews

def get_memory_items(self, profile_id: int, status: str = "active") -> list[dict[str, Any]]:
    with connect(self.db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM memory_items
            WHERE profile_id = ? AND status = ?
            ORDER BY confidence DESC, updated_at DESC
            """,
            (profile_id, status),
        ).fetchall()
    return [dict(row) for row in rows]

def get_plan_adjustments_for_profile(self, profile_id: int) -> list[dict[str, Any]]:
    with connect(self.db_path) as connection:
        rows = connection.execute(
            """
            SELECT pa.*
            FROM plan_adjustments pa
            JOIN learning_plan lp ON lp.id = pa.target_plan_day_id
            WHERE lp.profile_id = ? AND pa.status = 'active'
            ORDER BY pa.created_at DESC
            """,
            (profile_id,),
        ).fetchall()
    return [dict(row) for row in rows]

def get_growth_summary(self, profile_id: int) -> dict[str, Any]:
    reviews = self.get_daily_reviews(profile_id, limit=5)
    return {
        "latest_review": reviews[0] if reviews else None,
        "recent_reviews": reviews,
        "active_memory": self.get_memory_items(profile_id),
        "active_adjustments": self.get_plan_adjustments_for_profile(profile_id),
    }
```

- [ ] **Step 4: Add response models**

Add minimal models in `models.py`:

```python
class GrowthSummaryResponse(BaseModel):
    latest_review: dict | None
    recent_reviews: list[dict]
    active_memory: list[dict]
    active_adjustments: list[dict]
```

- [ ] **Step 5: Write failing API test**

```python
def test_growth_summary_api_returns_teacher_memory(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)

    onboard = client.post("/api/onboarding", json={
        "learning_goal": "Practice AI PM interviews",
        "total_days": 3,
        "daily_minutes": 20,
        "current_level": "B1",
    })
    profile_id = onboard.json()["profile"]["id"]

    response = client.get(f"/api/growth/summary?profile_id={profile_id}")

    assert response.status_code == 200
    assert response.json()["latest_review"] is None
    assert response.json()["active_memory"] == []
    assert response.json()["active_adjustments"] == []
```

- [ ] **Step 6: Run API test to verify it fails**

Run:

```bash
python -m pytest app/backend/tests/test_api.py::test_growth_summary_api_returns_teacher_memory -v
```

Expected: FAIL with 404 for `/api/growth/summary`.

- [ ] **Step 7: Implement API route**

Add route in `main.py`:

```python
@app.get("/api/growth/summary", response_model=GrowthSummaryResponse)
def get_growth_summary(profile_id: int | None = None):
    repo = get_repo()
    profile = repo.get_profile(profile_id) if profile_id else repo.get_latest_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")
    return repo.get_growth_summary(profile["id"])
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_get_growth_summary_decodes_review_memory_and_adjustments app/backend/tests/test_api.py::test_growth_summary_api_returns_teacher_memory -v
```

Expected: PASS.

---

## Task 2: Memory Merge And Lifecycle

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_repositories.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing memory merge test**

```python
def test_upsert_memory_item_merges_same_category_content(tmp_path):
    from app.db import init_db
    from app.repositories import CoachRepository

    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.create_profile("PM interview", 7, 20, "B1")

    first = repo.upsert_memory_item(profile["id"], "weakness", "Uses vague product language", "Day 1", 0.6, None)
    second = repo.upsert_memory_item(profile["id"], "weakness", "Uses vague product language", "Day 2", 0.9, None)
    items = repo.get_memory_items(profile["id"])

    assert first["id"] == second["id"]
    assert len(items) == 1
    assert items[0]["confidence"] == 0.9
    assert "Day 2" in items[0]["evidence"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_upsert_memory_item_merges_same_category_content -v
```

Expected: FAIL because `upsert_memory_item` does not exist.

- [ ] **Step 3: Implement `upsert_memory_item`**

Add method:

```python
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
            WHERE profile_id = ? AND category = ? AND lower(content) = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (profile_id, category, normalized_content),
        ).fetchone()
        if existing:
            merged_evidence = f"{existing['evidence']}\n{evidence}" if evidence not in existing["evidence"] else existing["evidence"]
            connection.execute(
                """
                UPDATE memory_items
                SET evidence = ?, confidence = ?, source_review_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (merged_evidence, max(float(existing["confidence"]), confidence), source_review_id, existing["id"]),
            )
            connection.commit()
            return dict(connection.execute("SELECT * FROM memory_items WHERE id = ?", (existing["id"],)).fetchone())
        cursor = connection.execute(
            """
            INSERT INTO memory_items (profile_id, category, content, evidence, confidence, status, source_review_id)
            VALUES (?, ?, ?, ?, ?, 'active', ?)
            """,
            (profile_id, category, content, evidence, confidence, source_review_id),
        )
        connection.commit()
        return dict(connection.execute("SELECT * FROM memory_items WHERE id = ?", (cursor.lastrowid,)).fetchone())
```

- [ ] **Step 4: Replace memory writes in review pipeline**

In `run_due_reviews`, replace `save_memory_item(...)` calls with `upsert_memory_item(...)`.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_upsert_memory_item_merges_same_category_content app/backend/tests/test_api.py::test_run_due_reviews_is_idempotent -v
```

Expected: PASS.

---

## Task 3: Plan Adjustment Expiry And Real Influence

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_repositories.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing active-adjustment filtering test**

```python
def test_active_plan_adjustments_exclude_expired_items(tmp_path):
    from app.db import init_db
    from app.repositories import CoachRepository

    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.create_profile("PM interview", 7, 20, "B1")
    plan = repo.save_plan(profile["id"], [{"day_index": 1, "topic": "A", "scenario": "B", "objective": "C"}])
    review = repo.save_daily_review(profile["id"], "2026-06-01", "completed", {}, {}, [], "{}")
    repo.save_plan_adjustment(plan[0]["id"], review["id"], "focus_shift", "Old adjustment", "Old", "Old", "low", expires_after_days=1)

    active = repo.get_active_plan_adjustments(plan[0]["id"], today="2026-06-23")

    assert active == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py::test_active_plan_adjustments_exclude_expired_items -v
```

Expected: FAIL because expiry is ignored or `today` is unsupported.

- [ ] **Step 3: Implement expiry-aware filtering**

Update `get_active_plan_adjustments`:

```python
def get_active_plan_adjustments(self, plan_day_id: int, today: str | None = None) -> list[dict[str, Any]]:
    current_date = today or date.today().isoformat()
    with connect(self.db_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM plan_adjustments
            WHERE target_plan_day_id = ?
              AND status = 'active'
              AND (
                expires_after_days IS NULL
                OR DATE(created_at, '+' || expires_after_days || ' day') >= DATE(?)
              )
            ORDER BY priority DESC, created_at DESC
            """,
            (plan_day_id, current_date),
        ).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Add plan-day completion behavior**

Write failing test:

```python
def test_session_turn_marks_plan_day_in_progress(tmp_path):
    from app.db import init_db
    from app.repositories import CoachRepository

    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.create_profile("PM interview", 7, 20, "B1")
    plan = repo.save_plan(profile["id"], [{"day_index": 1, "topic": "A", "scenario": "B", "objective": "C"}])
    repo.mark_plan_day_status(plan[0]["id"], "in_progress")
    current = repo.get_current_learning_state(profile["id"])["plan"][0]

    assert current["status"] == "in_progress"
```

Implement:

```python
def mark_plan_day_status(self, plan_day_id: int, status: str) -> None:
    with connect(self.db_path) as connection:
        connection.execute("UPDATE learning_plan SET status = ? WHERE id = ?", (status, plan_day_id))
        connection.commit()
```

- [ ] **Step 5: Use status updates in session flow**

In `start_session`, mark the plan day as `in_progress` when a session starts. In future completion flow, mark completed after review generation or explicit end-session API.

- [ ] **Step 6: Run backend tests**

Run:

```bash
python -m pytest app/backend/tests/test_repositories.py app/backend/tests/test_api.py -v
```

Expected: PASS.

---

## Task 4: GrowthPage Productization

**Files:**
- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/components/GrowthPage.tsx`
- Modify: `app/frontend/src/styles.css`
- Test: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend test**

Add test:

```tsx
it("shows growth summary from teacher memory", async () => {
  vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/daily-review/run-due")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", processed_days: 0 }), { status: 200 }));
    }
    if (url.includes("/api/growth/summary")) {
      return Promise.resolve(new Response(JSON.stringify({
        latest_review: {
          review_date: "2026-06-22",
          user_report: { summary: "You practiced product tradeoffs.", next_focus: "Use a clearer structure." },
          structured_analysis: { weaknesses: ["unclear structure"], strengths: ["kept speaking"] }
        },
        recent_reviews: [],
        active_memory: [
          { id: 1, category: "weakness", content: "Often gives vague product answers", confidence: 0.88 }
        ],
        active_adjustments: [
          { id: 1, title: "Practice structured answers", rationale: "Recent answers lack clear framing", instruction: "Start with context, tradeoff, decision." }
        ]
      }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({ profiles: [] }), { status: 200 }));
  });

  render(<App />);
  await userEvent.click(screen.getByText("Growth"));

  expect(await screen.findByText("You practiced product tradeoffs.")).toBeTruthy();
  expect(screen.getByText("Often gives vague product answers")).toBeTruthy();
  expect(screen.getByText("Practice structured answers")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: FAIL because GrowthPage does not fetch summary.

- [ ] **Step 3: Add frontend types**

```ts
export type DailyReview = {
  id?: number;
  review_date?: string;
  user_report?: {
    summary?: string;
    next_focus?: string;
  };
  structured_analysis?: {
    strengths?: string[];
    weaknesses?: string[];
  };
};

export type MemoryItem = {
  id: number;
  category: string;
  content: string;
  evidence?: string;
  confidence?: number;
};

export type PlanAdjustment = {
  id: number;
  title: string;
  rationale: string;
  instruction: string;
  priority?: string;
};

export type GrowthSummary = {
  latest_review: DailyReview | null;
  recent_reviews: DailyReview[];
  active_memory: MemoryItem[];
  active_adjustments: PlanAdjustment[];
};
```

- [ ] **Step 4: Add frontend API**

```ts
export async function getGrowthSummary(profileId?: number): Promise<GrowthSummary> {
  const url = profileId ? `${API_BASE}/api/growth/summary?profile_id=${profileId}` : `${API_BASE}/api/growth/summary`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to get growth summary");
  }
  return response.json();
}
```

- [ ] **Step 5: Implement GrowthPage**

Use `useEffect` and `useState` to load `getGrowthSummary()`. Render four compact sections:

```tsx
<section className="growth-card">
  <p className="section-label">Latest Review</p>
  <h2>{summary.latest_review?.user_report?.summary ?? "No review yet"}</h2>
  <p>{summary.latest_review?.user_report?.next_focus ?? "Finish a practice session to unlock your first review."}</p>
</section>
```

Render memory and adjustments as lists, with empty states:

```tsx
{summary.active_memory.length === 0 ? (
  <p className="muted">No long-term teacher memory yet.</p>
) : summary.active_memory.map((item) => (
  <article className="growth-mini-card" key={item.id}>
    <strong>{item.category}</strong>
    <p>{item.content}</p>
  </article>
))}
```

- [ ] **Step 6: Add compact styles**

Add styles for:

```css
.growth-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.growth-card { border: 1px solid var(--border); border-radius: 16px; padding: 16px; background: var(--surface); }
.growth-mini-card { border: 1px solid var(--border); border-radius: 12px; padding: 12px; background: rgba(255,255,255,0.04); }
```

- [ ] **Step 7: Run frontend test**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: PASS.

---

## Task 5: Structured Agent Output Validation

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/prompts.py`
- Test: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write failing normalization tests**

```python
def test_memory_agent_normalizes_missing_upserts_to_empty_list():
    from app.agents import MemoryAgent

    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"bad": "shape"}'

    agent = MemoryAgent(MockLLM())
    result = agent.extract_memory({"summary": "x"}, [])

    assert result == {"upserts": []}
```

```python
def test_plan_adaptation_agent_normalizes_missing_adjustments_to_empty_list():
    from app.agents import PlanAdaptationAgent

    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"adjustments": "wrong"}'

    agent = PlanAdaptationAgent(MockLLM())
    result = agent.propose_adjustments({}, [], [])

    assert result == {"adjustments": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py::test_memory_agent_normalizes_missing_upserts_to_empty_list app/backend/tests/test_agents.py::test_plan_adaptation_agent_normalizes_missing_adjustments_to_empty_list -v
```

Expected: FAIL because malformed outputs are returned directly or not normalized.

- [ ] **Step 3: Add JSON object helper**

Add helper:

```python
def parse_json_object(text: str, fallback: dict[str, object]) -> dict[str, object]:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback
    return parsed if isinstance(parsed, dict) else fallback
```

- [ ] **Step 4: Normalize Agent outputs**

Use:

```python
data = parse_json_object(response, {"upserts": []})
if not isinstance(data.get("upserts"), list):
    data["upserts"] = []
return data
```

For plan adaptation:

```python
data = parse_json_object(response, {"adjustments": []})
if not isinstance(data.get("adjustments"), list):
    data["adjustments"] = []
return data
```

For scenario design, ensure returned data is a dict and includes default arrays:

```python
data = parse_json_object(response, {})
for key in ("task_steps", "target_expressions", "common_mistakes", "rubric", "avoid_patterns"):
    if not isinstance(data.get(key), list):
        data[key] = []
return data
```

- [ ] **Step 5: Tighten prompts**

In `prompts.py`, update learning-loop Agent prompts to include explicit top-level keys and “return empty array when no item is useful”:

```python
"MemoryAgent output must be a JSON object with exactly one top-level key: upserts. upserts must be an array. If there is no durable memory, return {\"upserts\": []}."
```

```python
"PlanAdaptationAgent output must be a JSON object with exactly one top-level key: adjustments. adjustments must be an array. If no adjustment is needed, return {\"adjustments\": []}."
```

- [ ] **Step 6: Run backend Agent tests**

Run:

```bash
python -m pytest app/backend/tests/test_agents.py -v
```

Expected: PASS.

---

## Task 6: End-To-End Verification

**Files:**
- Verify all touched files.

- [ ] **Step 1: Run backend test suite**

Run:

```bash
python -m pytest app/backend/tests/ -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend test suite**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Manually verify product flow**

Run backend and frontend, then verify:

```bash
uvicorn app.main:app --reload
cd app/frontend && npm run dev
```

Expected behavior:
- Onboarding creates a plan.
- Starting a session marks today as in progress.
- Practice creates turns and inline feedback.
- Running review generates review, memory, adjustment, and next practice brief.
- Growth page shows latest review, teacher memory, and adaptive focus.

- [ ] **Step 4: Commit**

```bash
git add app/backend/app app/backend/tests app/frontend/src docs/superpowers/plans/2026-06-23-agent-learning-loop-completion.md
git commit -m "feat: complete agent learning loop"
```

---

## Self-Review

- Spec coverage: The plan covers Stage 1 loop completion through Growth APIs, memory merge, adjustment expiry, and plan-day status. It covers Stage 2 user visibility through GrowthPage. It covers Stage 3 output quality through Agent normalization and prompt tightening.
- Placeholder scan: No task relies on undefined “TBD” work; every task has a concrete file, test, command, and expected result.
- Type consistency: Backend response keys match frontend `GrowthSummary`: `latest_review`, `recent_reviews`, `active_memory`, `active_adjustments`.
