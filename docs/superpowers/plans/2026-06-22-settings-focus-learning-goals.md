# Settings Focus Learning Goals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the Settings page UI by removing non-actionable status cards and focusing the page on learning goals plus advanced tools.

**Architecture:** Keep all backend/API behavior unchanged. Only adjust the Settings page markup, styling, and frontend tests so the page no longer implies unsupported Voice or Local Data configuration.

**Tech Stack:** React, TypeScript, CSS, Vitest, Testing Library.

---

### Task 1: Update Settings UI Test

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Change the Settings structure expectation**

Assert that Settings still renders Learning Goals, Create New Goal, Advanced, and Developer workspace, while `Voice` and `Local Data` are absent.

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm test -- App.test.tsx`
Expected: FAIL because the current Settings page still renders Voice and Local Data cards.

### Task 2: Remove Non-Actionable Settings Cards

**Files:**
- Modify: `app/frontend/src/components/SettingsPage.tsx`
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Remove the right summary column**

Remove `Current Setup`, `Voice`, and `Local Data` cards. Keep a clean learning goals section and advanced tools section.

- [ ] **Step 2: Refine copy around goal changes**

Make it clear that changing goals currently means creating a new goal/plan, without adding edit/regenerate logic.

- [ ] **Step 3: Run verification**

Run: `npm test -- App.test.tsx` and `npm run build`. Expected: both pass.
