# Settings Studio Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge Studio into Settings and remove misleading non-functional Settings controls.

**Architecture:** Reuse the existing DeveloperStudio prompt/flowchart logic inside Settings to avoid changing backend APIs. Remove the standalone Studio route and navigation item from App/AppShell. Keep profile-management behavior unchanged.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Mermaid

---

## File Structure

- `app/frontend/src/App.test.tsx`: Update tests to assert Studio is no longer in sidebar and Settings contains developer tools.
- `app/frontend/src/components/AppShell.tsx`: Remove `studio` from `AppView` and sidebar nav.
- `app/frontend/src/App.tsx`: Remove `DeveloperStudio` import, `studio` view type, and route branch.
- `app/frontend/src/components/DeveloperStudio.tsx`: Export reusable `DeveloperTools` content while keeping `DeveloperStudio` as a thin wrapper if still imported elsewhere.
- `app/frontend/src/components/SettingsPage.tsx`: Remove non-functional AI Model/Input/Save Settings UI and render developer tools below learning-goal management.

---

### Task 1: Remove Standalone Studio Navigation

**Files:**
- Modify: `app/frontend/src/App.test.tsx`
- Modify: `app/frontend/src/components/AppShell.tsx`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Write the failing test**

In `app/frontend/src/App.test.tsx`, update `starts the daily practice immediately after onboarding` to include:

```tsx
expect(screen.queryByRole("button", { name: "Studio" })).toBeNull();
```

Replace `test("opens developer studio from navigation and loads prompt tools", ...)` with:

```tsx
test("does not expose standalone studio navigation", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("Today’s topic");
  expect(screen.queryByRole("button", { name: "Studio" })).toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npx vitest run src/App.test.tsx --testNamePattern "does not expose standalone studio navigation|starts the daily practice immediately after onboarding"
```

Expected: FAIL because Studio is still visible in the sidebar.

- [ ] **Step 3: Remove Studio from route and navigation**

In `app/frontend/src/components/AppShell.tsx`, change:

```tsx
export type AppView = "today" | "plan" | "practice" | "growth" | "settings" | "studio";
```

to:

```tsx
export type AppView = "today" | "plan" | "practice" | "growth" | "settings";
```

Remove this nav item:

```tsx
{ view: "studio", label: "Studio" }
```

In `app/frontend/src/App.tsx`, remove:

```tsx
import { DeveloperStudio } from "./components/DeveloperStudio";
```

Change the `View` type from:

```tsx
type View = "loading" | "onboarding" | "today" | "plan" | "practice" | "growth" | "settings" | "studio";
```

to:

```tsx
type View = "loading" | "onboarding" | "today" | "plan" | "practice" | "growth" | "settings";
```

Remove this branch:

```tsx
if (view === "studio") {
  content = <DeveloperStudio />;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
npx vitest run src/App.test.tsx --testNamePattern "does not expose standalone studio navigation|starts the daily practice immediately after onboarding"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/App.tsx app/frontend/src/App.test.tsx app/frontend/src/components/AppShell.tsx
git commit -m "feat: remove standalone studio navigation"
```

### Task 2: Merge Developer Tools Into Settings

**Files:**
- Modify: `app/frontend/src/App.test.tsx`
- Modify: `app/frontend/src/components/DeveloperStudio.tsx`
- Modify: `app/frontend/src/components/SettingsPage.tsx`

- [ ] **Step 1: Write the failing test**

Add this test to `app/frontend/src/App.test.tsx`:

```tsx
test("settings contains prompt tools and removes nonfunctional controls", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (getProfiles as Mock).mockResolvedValue({ profiles: [onboardingResult.profile] });
  (startSession as Mock).mockResolvedValue(startedSession);
  (getPrompts as Mock).mockResolvedValue({
    prompts: [
      {
        name: "conversation_agent_system",
        content: "Conversation prompt",
        updated_at: "2026-06-22 10:00:00"
      }
    ]
  });
  (updatePrompt as Mock).mockResolvedValue(undefined);

  render(<App />);

  await screen.findByText("Today’s topic");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));

  expect(await screen.findByText("Learning Goals")).toBeTruthy();
  expect(screen.queryByText("AI Model")).toBeNull();
  expect(screen.queryByText("Input")).toBeNull();
  expect(screen.queryByRole("button", { name: "Save Settings" })).toBeNull();
  expect(await screen.findByText("Prompt 管理")).toBeTruthy();
  expect(screen.getByText("产品流程图")).toBeTruthy();
  expect(await screen.findByText("conversation_agent_system")).toBeTruthy();
  expect(screen.getByDisplayValue("Conversation prompt")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npx vitest run src/App.test.tsx --testNamePattern "settings contains prompt tools and removes nonfunctional controls"
```

Expected: FAIL because Settings still shows AI Model/Input/Save Settings and does not show prompt tools.

- [ ] **Step 3: Extract reusable developer tools**

In `app/frontend/src/components/DeveloperStudio.tsx`, change:

```tsx
export function DeveloperStudio() {
```

to:

```tsx
export function DeveloperTools() {
```

Change the root markup from:

```tsx
return (
  <div className="page compact-page">
    <header className="page-header">
      <div>
        <h1>开发者工作台</h1>
        <p>调试运行时 Prompt，并查看产品架构与流程。</p>
      </div>
    </header>
```

to:

```tsx
return (
  <section className="settings-developer-tools">
    <header className="settings-section-header">
      <div>
        <p className="section-label">Developer Tools</p>
        <h2>开发调试</h2>
        <p className="muted">调试运行时 Prompt，并查看产品架构与流程。</p>
      </div>
    </header>
```

Change the final closing tag from:

```tsx
</div>
```

to:

```tsx
</section>
```

Add this wrapper at the end of the file:

```tsx
export function DeveloperStudio() {
  return (
    <div className="page compact-page">
      <DeveloperTools />
    </div>
  );
}
```

- [ ] **Step 4: Update SettingsPage**

In `app/frontend/src/components/SettingsPage.tsx`, update imports:

```tsx
import { getProfiles, deleteProfile } from "../api";
import type { Profile } from "../types";
import { Card, PageHeader, PrimaryButton, StatusPill } from "./ui";
import { DeveloperTools } from "./DeveloperStudio";
```

Change the `PageHeader` action from:

```tsx
action={<PrimaryButton type="button">Save Settings</PrimaryButton>}
```

to no `action` prop.

Replace the outer layout body with a single page flow:

```tsx
<section className="settings-layout">
  <Card>
    ...existing Learning Goals content...
  </Card>
  <DeveloperTools />
</section>
```

Remove the AI Model and Input cards entirely.

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
npx vitest run src/App.test.tsx --testNamePattern "settings contains prompt tools and removes nonfunctional controls"
npx vitest run src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/App.test.tsx app/frontend/src/components/DeveloperStudio.tsx app/frontend/src/components/SettingsPage.tsx
git commit -m "feat: merge developer tools into settings"
```

