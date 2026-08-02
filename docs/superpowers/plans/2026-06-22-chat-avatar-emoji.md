# Chat Avatar Emoji Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `C` and `Y` chat avatars with a bear avatar for the AI assistant and a dragon avatar for the user.

**Architecture:** Keep the change local to the existing `PracticeRoom` message rendering and shared avatar CSS. Do not change API payloads, session state, TTS, streaming, or feedback behavior.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, CSS.

---

### Task 1: Add Avatar Rendering Test

**Files:**
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Add a focused assertion to the existing practice workspace test**

Add assertions that the assistant avatar renders `🐻` and the user avatar renders `🐉`.

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm test -- App.test.tsx`
Expected: FAIL because the UI still renders `C` and `Y`.

### Task 2: Replace Avatar Content And Tune Styling

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Replace hard-coded avatar text**

Use `🐻` for assistant turns, including the streaming assistant turn. Use `🐉` for user turns.

- [ ] **Step 2: Adjust avatar CSS**

Slightly increase avatar font size and use soft backgrounds that fit emoji avatars.

- [ ] **Step 3: Run the test and verify it passes**

Run: `npm test -- App.test.tsx`
Expected: PASS.

- [ ] **Step 4: Build the frontend**

Run: `npm run build`
Expected: PASS.
