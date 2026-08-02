# AI PM English Coach UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the frontend into a usable learning workspace with separated settings, structured navigation, and a polished practice experience.

**Architecture:** Keep the current React/Vite app and API surface. Add a lightweight local design system with plain CSS and focused layout components, then refactor page components around `today`, `plan`, `practice`, `review`, `memory`, and `settings` views.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, plain CSS.

---

## File Structure

- Modify: `app/frontend/src/App.test.tsx`
  - Owns high-level user-flow coverage for onboarding, Today, Settings, and Practice.
- Modify: `app/frontend/src/App.tsx`
  - Owns app-level state and view routing.
- Create: `app/frontend/src/styles.css`
  - Owns the shared visual system and page layout styles.
- Modify: `app/frontend/src/main.tsx`
  - Imports global styles.
- Create: `app/frontend/src/components/AppShell.tsx`
  - Owns persistent left navigation and app frame.
- Create: `app/frontend/src/components/ui.tsx`
  - Owns small reusable presentational components.
- Modify: `app/frontend/src/components/Onboarding.tsx`
  - Converts first-run setup into a guided card layout.
- Modify: `app/frontend/src/components/Dashboard.tsx`
  - Converts Dashboard into Today workspace.
- Create: `app/frontend/src/components/PlanPage.tsx`
  - Owns full learning plan browsing.
- Create: `app/frontend/src/components/SettingsPage.tsx`
  - Owns isolated learning and local configuration display.
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
  - Converts practice into conversation + feedback + fixed input layout.
- Modify: `app/frontend/src/components/FeedbackReport.tsx`
  - Converts review into card-based report.
- Modify: `app/frontend/src/components/MemoryLibrary.tsx`
  - Fits memory into the new shell.

## Task 1: Test The New App Structure

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing tests for Today and Settings**

Replace `app/frontend/src/App.test.tsx` with:

```tsx
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi, type Mock } from "vitest";
import { createOnboarding, startSession } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  createOnboarding: vi.fn(),
  startSession: vi.fn(),
  sendUserTurn: vi.fn(),
  endSession: vi.fn()
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const onboardingResult = {
  profile: {
    id: 1,
    learning_goal: "AI product manager internationalization",
    total_days: 14,
    daily_minutes: 15,
    current_level: "IELTS 6.5, speaking 6"
  },
  plan: [
    {
      id: 1,
      day_index: 1,
      topic: "AI PM self-introduction",
      scenario: "Introduce your background to an international AI team.",
      objective: "Give a concise introduction with product impact.",
      status: "pending"
    },
    {
      id: 2,
      day_index: 2,
      topic: "Product discovery",
      scenario: "Clarify user needs with a cross-functional team.",
      objective: "Ask focused product discovery questions.",
      status: "pending"
    }
  ]
};

test("renders guided onboarding form first", () => {
  render(<App />);

  expect(screen.getByText("AI PM English Coach")).toBeTruthy();
  expect(screen.getByText("Set up your local English coaching plan")).toBeTruthy();
  expect(screen.getByLabelText("onboarding form")).toBeTruthy();
});

test("lands on the today workspace after onboarding", async () => {
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);

  render(<App />);
  fireEvent.click(screen.getByText("Generate Plan"));

  expect(await screen.findByText("Today")).toBeTruthy();
  expect(screen.getByText("AI PM self-introduction")).toBeTruthy();
  expect(screen.getByText("Start Practice")).toBeTruthy();
});

test("opens settings from navigation after onboarding", async () => {
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);

  render(<App />);
  fireEvent.click(screen.getByText("Generate Plan"));
  await screen.findByText("Today");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));

  expect(screen.getByText("Settings")).toBeTruthy();
  expect(screen.getByText("Learning Configuration")).toBeTruthy();
  expect(screen.getByDisplayValue("AI product manager internationalization")).toBeTruthy();
});

test("starts practice from the today workspace", async () => {
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "AI PM self-introduction" },
    assistant_turn: {
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }
  });

  render(<App />);
  fireEvent.click(screen.getByText("Generate Plan"));
  await screen.findByText("Today");
  fireEvent.click(screen.getByText("Start Practice"));

  await waitFor(() => {
    expect(screen.getByText("Practice Room")).toBeTruthy();
  });
  expect(screen.getByText("Today we will practice your self-introduction.")).toBeTruthy();
  expect(screen.getByText("Real-time Feedback")).toBeTruthy();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd app/frontend
npm test -- App.test.tsx
```

Expected: tests fail because `Today`, `Settings`, `Set up your local English coaching plan`, and `Practice Room` do not exist yet.

- [ ] **Step 3: Commit the failing-test milestone after implementation passes**

Do not commit while tests are red. Commit after Task 4 passes with:

```bash
git add app/frontend/src/App.test.tsx
git commit -m "test: cover redesigned app navigation"
```

## Task 2: Add The Visual System And App Shell

**Files:**
- Create: `app/frontend/src/styles.css`
- Modify: `app/frontend/src/main.tsx`
- Create: `app/frontend/src/components/AppShell.tsx`
- Create: `app/frontend/src/components/ui.tsx`

- [ ] **Step 1: Create global styles**

Create `app/frontend/src/styles.css` with a clean app shell, card, form, button, navigation, conversation, and responsive layout styles.

- [ ] **Step 2: Import global styles**

Modify `app/frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 3: Create shell component**

Create `app/frontend/src/components/AppShell.tsx` with:

```tsx
import type { ReactNode } from "react";

export type AppView = "today" | "plan" | "practice" | "review" | "memory" | "settings";

type Props = {
  activeView: AppView;
  goal: string;
  children: ReactNode;
  onNavigate: (view: AppView) => void;
};

const navItems: Array<{ view: AppView; label: string }> = [
  { view: "today", label: "Today" },
  { view: "plan", label: "Plan" },
  { view: "review", label: "Review" },
  { view: "memory", label: "Memory" },
  { view: "settings", label: "Settings" }
];

export function AppShell({ activeView, goal, children, onNavigate }: Props) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <div className="brand-title">AI PM Coach</div>
            <div className="brand-subtitle">Local English Agent</div>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.view}
              className={item.view === activeView ? "nav-item nav-item-active" : "nav-item"}
              onClick={() => onNavigate(item.view)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="goal-card">
          <span>Current goal</span>
          <strong>{goal}</strong>
        </div>
      </aside>
      <div className="app-main">{children}</div>
    </div>
  );
}
```

- [ ] **Step 4: Create reusable UI components**

Create `app/frontend/src/components/ui.tsx` with `Card`, `PageHeader`, `PrimaryButton`, `SecondaryButton`, `StatusPill`, and `FormField` components.

- [ ] **Step 5: Run tests**

Run:

```bash
cd app/frontend
npm test -- App.test.tsx
```

Expected: tests still fail until pages are refactored in Task 3.

## Task 3: Refactor Pages Around The New Structure

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/components/Onboarding.tsx`
- Modify: `app/frontend/src/components/Dashboard.tsx`
- Create: `app/frontend/src/components/PlanPage.tsx`
- Create: `app/frontend/src/components/SettingsPage.tsx`
- Modify: `app/frontend/src/components/MemoryLibrary.tsx`
- Modify: `app/frontend/src/components/FeedbackReport.tsx`

- [ ] **Step 1: Update app view routing**

Modify `app/frontend/src/App.tsx` so the view type is:

```tsx
type View = "onboarding" | "today" | "plan" | "practice" | "review" | "memory" | "settings";
```

After onboarding, call `setView("today")`. Wrap post-onboarding views in `AppShell`.

- [ ] **Step 2: Refactor onboarding**

Modify `Onboarding` into a centered guided setup page that contains the existing controls, keeps `aria-label="onboarding form"`, and includes the text `Set up your local English coaching plan`.

- [ ] **Step 3: Refactor Dashboard into Today workspace**

Modify `Dashboard` to render `Today`, current day details, progress cards, plan preview, recent-feedback card, and `Start Practice`.

- [ ] **Step 4: Add Plan page**

Create `PlanPage` to show all `PlanDay` cards and allow starting a selected day.

- [ ] **Step 5: Add Settings page**

Create `SettingsPage` to render `Settings`, `Learning Configuration`, editable local inputs for profile values, read-only model and voice sections, and a local-only data notice.

- [ ] **Step 6: Fit Review and Memory into cards**

Modify `FeedbackReport` and `MemoryLibrary` to use page headers and cards.

- [ ] **Step 7: Run tests**

Run:

```bash
cd app/frontend
npm test -- App.test.tsx
```

Expected: onboarding, Today, and Settings tests pass. Practice test may still fail until Task 4.

## Task 4: Refactor Practice Room And Verify End-To-End

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Refactor practice layout**

Modify `PracticeRoom` to render:

- `Practice Room` as the main title.
- Topic, scenario, and objective context.
- `aria-label="conversation"` transcript area.
- `Real-time Feedback` side panel.
- A fixed or visually distinct input composer with typed input, `Push to Talk`, `Send`, and `End Session`.
- Visible retryable error messages for session start, send, and end failures.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd app/frontend
npm test
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd app/frontend
npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Run backend tests**

Run:

```bash
cd app/backend
python -m pytest
```

Expected: backend tests still pass because no backend behavior changed.

- [ ] **Step 5: Manual browser verification**

Open:

```text
http://127.0.0.1:5173/
```

Verify:

- Onboarding looks like a setup page.
- `Generate Plan` lands on `Today`.
- Sidebar opens `Plan`, `Memory`, and `Settings`.
- `Settings` contains learning configuration and local model/voice information.
- `Start Practice` opens `Practice Room`.
- Typed turn returns assistant response and feedback.
- `End Session` opens the review report.

- [ ] **Step 6: Commit implementation**

Run:

```bash
git add app/frontend/src
git commit -m "feat: redesign frontend workspace"
```

## Self-Review

Spec coverage:

- Today workspace: Task 3.
- Settings isolation: Task 3.
- Practice conversation and feedback layout: Task 4.
- Visual system: Task 2.
- Tests and build verification: Tasks 1 and 4.

Red-flag scan:

- No unresolved markers or unspecified implementation steps remain.

Type consistency:

- `AppView` excludes `onboarding` because `AppShell` only wraps post-onboarding app views.
- `View` includes `onboarding` because `App.tsx` owns first-run routing.
