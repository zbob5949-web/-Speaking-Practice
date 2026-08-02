# Developer Studio Minimal Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing Developer Studio with Prompt editing and product flowchart through the main app navigation.

**Architecture:** Reuse the existing React `DeveloperStudio` component and FastAPI Prompt endpoints. Add the missing sidebar entry, harden Prompt update behavior, improve Studio UI states/styles, and cover the integration with focused tests.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library, FastAPI, SQLite, pytest, Mermaid.

---

## File Structure

- Modify `app/frontend/src/components/AppShell.tsx`: add `Studio` to sidebar navigation.
- Modify `app/frontend/src/components/DeveloperStudio.tsx`: improve loading, empty, dirty-state, save feedback, and flowchart copy.
- Modify `app/frontend/src/styles.css`: add Studio tab, Prompt list/editor, status, and Mermaid container styles.
- Modify `app/frontend/src/App.test.tsx`: mock Prompt API calls and test Studio navigation.
- Modify `app/backend/app/repositories.py`: make `update_prompt` report whether a row changed.
- Modify `app/backend/app/main.py`: return 404 when updating an unknown Prompt.
- Modify `app/backend/tests/test_api.py`: test Prompt listing, update, and unknown Prompt behavior.

## Tasks

### Task 1: Backend Prompt API Hardening

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Test: `app/backend/tests/test_api.py`

- [ ] **Step 1: Add failing backend tests**

Add tests that query seeded prompts, update one Prompt, and verify updating an unknown Prompt returns 404.

Run: `cd app/backend && pytest tests/test_api.py -k prompt -v`

Expected: tests fail before implementation for unknown Prompt behavior.

- [ ] **Step 2: Implement repository return value**

Change `CoachRepository.update_prompt` to return `True` when SQLite updates one or more rows and `False` otherwise.

- [ ] **Step 3: Implement API 404**

Change `PUT /api/prompts/{name}` to raise `HTTPException(status_code=404, detail="Prompt not found")` when `repo.update_prompt(...)` returns `False`.

- [ ] **Step 4: Verify backend tests**

Run: `cd app/backend && pytest tests/test_api.py -k prompt -v`

Expected: Prompt API tests pass.

### Task 2: Frontend Studio Entry And UI States

**Files:**
- Modify: `app/frontend/src/components/AppShell.tsx`
- Modify: `app/frontend/src/components/DeveloperStudio.tsx`
- Modify: `app/frontend/src/styles.css`
- Test: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing frontend test**

Mock `getPrompts` and `updatePrompt`, then assert the sidebar exposes `Studio` and clicking it shows `Prompt Management` and `Product Flowchart`.

Run: `cd app/frontend && npm test -- --run App.test.tsx`

Expected: test fails because `Studio` is not currently in `AppShell` navigation and API mocks are incomplete.

- [ ] **Step 2: Add sidebar entry**

Add `{ view: "studio", label: "Studio" }` to `navItems` in `AppShell.tsx`.

- [ ] **Step 3: Improve Studio component**

Add explicit `isLoading`, `errorMessage`, `successMessage`, and dirty-state copy. Keep the existing Prompt list/editor and Mermaid rendering.

- [ ] **Step 4: Add Studio styles**

Add CSS for `.studio-tabs`, `.studio-tab`, `.studio-prompts-layout`, `.prompts-list`, `.prompt-nav-item`, `.prompt-editor`, `.prompt-textarea`, `.studio-status`, and `.mermaid-container`.

- [ ] **Step 5: Verify frontend tests**

Run: `cd app/frontend && npm test -- --run App.test.tsx`

Expected: frontend tests pass.

### Task 3: Focused Full Verification

**Files:**
- No additional files expected.

- [ ] **Step 1: Run backend focused tests**

Run: `cd app/backend && pytest tests/test_api.py tests/test_repositories.py -v`

Expected: pass.

- [ ] **Step 2: Run frontend tests**

Run: `cd app/frontend && npm test -- --run`

Expected: pass.

- [ ] **Step 3: Manual smoke check**

Start the app if needed, open the UI, click `Studio`, confirm both sub tabs render, edit a Prompt, save it, and confirm the save status appears.

## Self-Review

- Spec coverage: navigation, Prompt management, immediate runtime effect, flowchart, styles, error handling, and tests are covered.
- Placeholder scan: no task depends on unspecified future work.
- Type consistency: frontend API functions already expose `getPrompts` and `updatePrompt`; backend route names match existing FastAPI endpoints.
