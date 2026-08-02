# AI PM English Coach Compact UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the redesigned UI so the Today page fits one laptop screen, avoids repeated setup information, and uses lighter typography.

**Architecture:** Keep the existing React structure and API calls. Refactor only the shell, Today workspace, tests, and global CSS so configuration remains isolated in Settings and the daily page stays focused.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, plain CSS.

---

## File Structure

- Modify: `app/frontend/src/App.test.tsx`
  - Adds a regression test proving Today no longer repeats setup/configuration modules.
- Modify: `app/frontend/src/components/AppShell.tsx`
  - Removes the sidebar goal card to avoid repeating the user's initial configuration.
- Modify: `app/frontend/src/App.tsx`
  - Stops passing the learning goal into the shell.
- Modify: `app/frontend/src/components/Dashboard.tsx`
  - Collapses Today into one focused hero plus a compact next-step hint.
- Modify: `app/frontend/src/styles.css`
  - Reduces font weight, shadow, spacing, sidebar width, card radius, and hero height.

## Task 1: Add A Regression Test For Simplicity

- [ ] **Step 1: Write failing test**

Add a test to `app/frontend/src/App.test.tsx` after the Today workspace test:

```tsx
test("keeps the today workspace focused without repeated setup details", async () => {
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);

  render(<App />);
  fireEvent.click(screen.getByText("Generate Plan"));
  await screen.findByText("Today");

  expect(screen.queryByText("Current goal")).toBeNull();
  expect(screen.queryByText("Practice Setup")).toBeNull();
  expect(screen.queryByText("Recent Feedback")).toBeNull();
  expect(screen.queryByText("IELTS 6.5, speaking 6")).toBeNull();
  expect(screen.queryByText("Next practice blocks")).toBeNull();
});
```

- [ ] **Step 2: Verify test fails**

Run:

```bash
cd app/frontend
npm test -- App.test.tsx
```

Expected: the new test fails because Today still renders `Current goal`, `Practice Setup`, `Recent Feedback`, current level, and `Next practice blocks`.

## Task 2: Remove Redundant Today Information

- [ ] **Step 1: Simplify shell**

Remove `goal` from `AppShell` props and delete the `.goal-card` rendering from `app/frontend/src/components/AppShell.tsx`.

- [ ] **Step 2: Update app shell call**

In `app/frontend/src/App.tsx`, call:

```tsx
<AppShell activeView={view} onNavigate={setView}>
  {content}
</AppShell>
```

- [ ] **Step 3: Simplify Today**

In `app/frontend/src/components/Dashboard.tsx`, remove the duplicated objective card, practice setup card, plan preview card, and feedback placeholder. Keep only current day, scenario, objective, start button, and a short next-day hint.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
cd app/frontend
npm test -- App.test.tsx
```

Expected: all App tests pass.

## Task 3: Lighten The Visual System

- [ ] **Step 1: Update CSS**

In `app/frontend/src/styles.css`, reduce visual weight:

- Sidebar width from `252px` to around `208px`.
- App padding from `32px` to around `22px`.
- Card padding from `22px` to around `18px`.
- Large heading weights from `800/900` to `600/700`.
- Main hero heading from `2.7rem` to around `2rem`.
- Shadows and border radii to quieter values.
- Today page gap so the first screen remains compact.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd app/frontend
npm test
npm run build
```

Expected: tests and build pass.

- [ ] **Step 3: Commit**

Run:

```bash
git add app/frontend/src docs/superpowers/plans/2026-06-21-ai-pm-english-coach-compact-ui.md
git commit -m "fix: simplify frontend workspace"
```

## Self-Review

Spec coverage:

- Removes repeated personal setup information from daily workspace.
- Keeps configuration in Settings only.
- Reduces page length and visual heaviness.
- Maintains existing app navigation and practice flow.

Red-flag scan:

- No unresolved markers or unspecified implementation steps remain.

Type consistency:

- `AppShell` no longer accepts `goal`, and `App.tsx` stops passing it.
