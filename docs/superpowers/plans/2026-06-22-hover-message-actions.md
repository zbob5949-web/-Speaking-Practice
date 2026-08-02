# Hover Message Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the trash and replay controls feel less clumsy by moving them into subtle hover/focus message actions.

**Architecture:** Keep the existing replay and delete behaviors in `PracticeRoom`, but change their presentation from always-visible row buttons to a grouped action rail attached to each message. Use CSS opacity and transform transitions so actions appear on message hover or keyboard focus.

**Tech Stack:** React, TypeScript, CSS, Vitest, Testing Library.

---

### Task 1: Test Message Action Structure

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Add a focused assertion**

Assert that replay/delete controls render inside `.message-actions` groups rather than as direct row-level icon buttons.

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm test -- App.test.tsx`
Expected: FAIL because the current buttons are direct children of `.message-row`.

### Task 2: Move Buttons Into Hover Actions

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Wrap actions in a message action group**

Place delete and replay buttons inside a `div` with `className="message-actions"` and `aria-label="Message actions"`.

- [ ] **Step 2: Make action buttons visually subtle**

Use CSS to hide action groups by default and reveal them on `.message-row:hover` and `.message-row:focus-within`.

- [ ] **Step 3: Run tests and build**

Run: `npm test -- App.test.tsx` and `npm run build`. Expected: both pass.
