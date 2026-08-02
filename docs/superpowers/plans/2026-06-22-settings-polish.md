# Settings Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Settings page feel like a polished settings center instead of a rough management list.

**Architecture:** Keep existing profile switching/deletion behavior and `DeveloperTools`. Refactor `SettingsPage` markup into semantic settings sections and move visual treatment into reusable CSS classes in `styles.css`.

**Tech Stack:** React, TypeScript, CSS, Vitest, Testing Library.

---

### Task 1: Add Settings Structure Test

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Add assertions for the new settings center**

Verify that Settings renders `Current Setup`, `Voice`, `Local Data`, `Advanced`, and goal action buttons.

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm test -- App.test.tsx`
Expected: FAIL because the current Settings page does not render the new polished sections.

### Task 2: Refactor Settings Markup

**Files:**
- Modify: `app/frontend/src/components/SettingsPage.tsx`

- [ ] **Step 1: Remove inline styles**

Replace inline list/card/button styles with named CSS classes.

- [ ] **Step 2: Add settings summary sections**

Render `Current Setup`, `Voice`, `Local Data`, and `Advanced` sections around existing profile and developer tooling content.

### Task 3: Add Settings Styles

**Files:**
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Add settings grid and cards**

Create CSS classes for the two-column settings layout, goal cards, summary cards, metadata rows, and danger/ghost buttons.

- [ ] **Step 2: Run verification**

Run: `npm test -- App.test.tsx` and `npm run build`. Expected: both pass.
