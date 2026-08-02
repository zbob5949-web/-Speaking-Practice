# Practice Lesson Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the pre-practice lesson page by removing repeated objective/strategy information while keeping the key roleplay setup and useful phrases.

**Architecture:** This is a focused presentation-layer change in `PracticeRoom`. The backend lesson-pack data remains unchanged; the component chooses a smaller subset of existing fields for the Learn page.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

## File Structure

- Modify: `app/frontend/src/components/PracticeRoom.tsx`
  - Remove the Learn page Today Strategy card.
  - Stop repeating `conversation_objective` inside Roleplay Setup.
  - Merge `lesson_focus` and `task_steps` into one compact section.
  - Limit target expressions to six visible phrases.
- Modify: `app/frontend/src/App.test.tsx`
  - Update Learn page assertions to match the simplified UI.
  - Add a regression assertion that duplicated objective text appears only once.

---

### Task 1: Update Tests For Simplified Learn Page

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Replace old strategy assertions**

In `starts a new lesson in Learn mode before opening the chat`, remove assertions for:

```ts
expect(await screen.findByText("今日练习依据")).toBeTruthy();
expect(await screen.findByText("今天怎么练")).toBeTruthy();
expect(screen.getByText("为什么这样练")).toBeTruthy();
expect(screen.getByText("AI 教练准备")).toBeTruthy();
expect(screen.getByText("这是最近重复出现的细节遗漏问题。")).toBeTruthy();
```

Add assertions for the retained simple structure:

```ts
expect(await screen.findByText("Speak about travel plans")).toBeTruthy();
expect(screen.getByText("Hotel receptionist")).toBeTruthy();
expect(screen.getByText("You are checking in at a hotel after a long trip.")).toBeTruthy();
expect(screen.getByText("Useful phrases")).toBeTruthy();
expect(screen.getByText("I'm here to check in.")).toBeTruthy();
```

- [ ] **Step 2: Add a duplicate-objective regression assertion**

Inside the same test, after the page renders, assert that the header goal is only rendered once:

```ts
expect(screen.getAllByText("Use one clear travel-plan sentence before the roleplay ends.")).toHaveLength(1);
```

- [ ] **Step 3: Update rich material test expectations**

In `renders rich lesson pack materials in practice room`, keep assertions for:

```ts
expect(await screen.findByText("Past-tense storytelling plus polite requests")).toBeTruthy();
expect(screen.getByText("Explain what happened")).toBeTruthy();
expect(screen.getByText("My flight was delayed.")).toBeTruthy();
expect(screen.getByText("我的航班延误了。")).toBeTruthy();
```

Remove assertions for hidden secondary materials:

```ts
expect(screen.getByText("I arrived late because...")).toBeTruthy();
expect(screen.getByText("NPC: Good evening. How can I help?")).toBeTruthy();
expect(screen.getByText("I am arrive late.")).toBeTruthy();
expect(screen.getByText("Clear reason")).toBeTruthy();
```

- [ ] **Step 4: Run focused tests and verify failure**

Run:

```bash
cd app/frontend
PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx
```

Expected before implementation: tests fail because the UI still renders the old structure.

---

### Task 2: Simplify PracticeRoom Learn Page

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Remove unused Learn-page collections**

In the `lessonPhase === "learn"` block, remove local variables for hidden secondary materials:

```ts
const avoidPatterns = practiceBrief.avoid_patterns || [];
const sentenceFrames = practiceBrief.sentence_frames || [];
const modelDialogue = practiceBrief.model_dialogue || [];
const commonMistakes = practiceBrief.common_mistakes || [];
const rubric = practiceBrief.rubric || [];
```

Keep:

```ts
const targetExpressions = practiceBrief.target_expressions || [];
const taskSteps = practiceBrief.task_steps || [];
const visibleExpressions = targetExpressions.slice(0, 6);
```

- [ ] **Step 2: Delete the visible Today Strategy card**

Remove the JSX block:

```tsx
{todayStrategy ? (
  <section className="lesson-brief-card lesson-strategy-card" aria-label="Today strategy">
    ...
  </section>
) : null}
```

- [ ] **Step 3: Stop repeating objective in Roleplay Setup**

Change the Roleplay Setup card from:

```tsx
<p>{practiceBrief.scenario_setup || day.scenario}</p>
<p className="muted">{practiceBrief.conversation_objective || day.objective}</p>
```

to:

```tsx
<p>{practiceBrief.scenario_setup || day.scenario}</p>
```

- [ ] **Step 4: Merge lesson focus and task steps**

Replace separate `Lesson Focus` and `Task Steps` cards with one card:

```tsx
{practiceBrief.lesson_focus || taskSteps.length > 0 ? (
  <section className="lesson-brief-card">
    <p className="section-label">How to practice</p>
    {practiceBrief.lesson_focus ? <p>{practiceBrief.lesson_focus}</p> : null}
    {taskSteps.length > 0 ? (
      <ol className="lesson-watch-list">
        {taskSteps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    ) : null}
  </section>
) : null}
```

- [ ] **Step 5: Rename and limit expressions**

Change the target expression card label and map source:

```tsx
<p className="section-label">Useful phrases</p>
{visibleExpressions.length > 0 ? (
  <ul className="lesson-expression-list">
    {visibleExpressions.map((expression) => (
      <ExpressionCard expression={expression} key={expressionLabel(expression)} />
    ))}
  </ul>
) : (
  <p className="muted">Use the scenario goal to shape your first response.</p>
)}
```

- [ ] **Step 6: Remove hidden secondary cards**

Delete JSX blocks for:

```tsx
Sentence Frames
Model Dialogue
Common Mistakes
Success Rubric
Stretch Goal
Watch For
```

---

### Task 3: Verify

**Files:**
- Test: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
cd app/frontend
PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx
```

Expected: all tests pass.

- [ ] **Step 2: Check git diff**

Run:

```bash
git diff -- app/frontend/src/components/PracticeRoom.tsx app/frontend/src/App.test.tsx
```

Expected: diff only changes Learn page presentation and matching tests.

- [ ] **Step 3: Commit focused changes**

Run:

```bash
git add docs/superpowers/specs/2026-07-26-practice-lesson-simplification-design.md docs/superpowers/plans/2026-07-26-practice-lesson-simplification.md app/frontend/src/components/PracticeRoom.tsx app/frontend/src/App.test.tsx
git commit -m "feat: simplify practice lesson brief"
```

Expected: commit succeeds with only relevant files staged.

---

## Self-Review

- Spec coverage: The plan removes Today Strategy, avoids duplicated objective text, merges lesson focus with task steps, limits expressions, and updates tests.
- Placeholder scan: No placeholders remain.
- Type consistency: All referenced fields already exist on `PracticeBrief` and current tests.
