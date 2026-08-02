# AI PM English Coach UI Redesign

## Background

The current frontend is functionally usable but visually and structurally too primitive. The first screen exposes raw configuration controls inline, which makes the product feel like a test form rather than a daily learning tool. The redesign focuses on usability first: users should immediately understand what to do today, where to start practice, and where configuration lives.

## Goals

- Turn the default experience into a learning workspace instead of a setup form.
- Separate daily learning actions from configuration and model settings.
- Make the practice experience easier to use during real speaking sessions.
- Establish a simple reusable visual system for cards, buttons, layout, forms, and page shells.
- Keep the MVP local-first and avoid adding backend complexity unless needed.

## Non-Goals

- Do not redesign the backend data model in this iteration.
- Do not add login, cloud sync, billing, sharing, or multi-user support.
- Do not implement a full brand system with illustrations, animations, or complex themes.
- Do not expose the real API key in the frontend.

## Information Architecture

The app will use a persistent shell with left navigation and a main content area.

Primary sections:

- Today: the default workspace for the current day's learning task.
- Plan: the 14-day learning plan and day-level status.
- Practice: the active conversation session.
- Review: the latest post-session report.
- Memory: mistakes, expressions, and learning notes.
- Settings: learning goal, duration, level, model status, and voice preferences.

The first-run experience still needs onboarding, but it should look like a guided setup card rather than a single raw horizontal form. After onboarding, routine use should start from Today.

## Page Designs

### Today Workspace

The Today page is the default landing page after setup.

It should show:

- Current day number and topic.
- Today's scenario and objective.
- A primary Start Practice action.
- A compact progress summary.
- A preview of the next few plan days.
- Recent feedback or a useful empty state if no feedback exists.

The page should not contain model provider settings or raw API configuration.

### Practice Room

The Practice page should support live use during a speaking session.

Layout:

- Main area: conversation transcript with assistant and user turns.
- Right panel: real-time text feedback, including correction, suggestion, and rationale.
- Bottom input area: typed response, Send button, Push-to-Talk button, and End Session button.
- Top context area: topic, scenario, and objective for the current day.

The user should always know:

- What scenario they are practicing.
- Whether the session has started.
- Where to speak or type.
- Where to find feedback.
- How to end the session.

### Settings Page

Settings should be isolated from the daily learning flow.

Settings sections:

- Learning: learning goal, total days, daily minutes, current level.
- Model: provider name and model name as read-only local configuration for now.
- Voice: browser speech recognition and browser TTS status.
- Data: local-only storage note plus disabled reset/export entries labeled as future work.

For this iteration, settings can update frontend state and regenerate onboarding if needed. Direct editing of `.env` from the browser is out of scope.

### Plan Page

The Plan page should show all generated plan days in a readable card grid or list.

Each day card should show:

- Day index.
- Topic.
- Scenario.
- Objective.
- Status.
- Start Practice action for pending days.

### Review And Memory

Review should become visually readable rather than a plain report.

It should show:

- Summary.
- Mistakes.
- Better expressions.
- Next-step suggestions.

Memory can remain lightweight in this iteration, but it should visually fit the new shell and show useful guidance even before real memory browsing is expanded.

## Visual System

Use a clean productivity-app style:

- Light background with elevated white cards.
- Dark left navigation.
- Blue primary action color.
- Consistent spacing with generous page padding.
- Rounded cards and buttons.
- Clear hierarchy with section labels, titles, and helper text.

Initial implementation can use plain CSS without introducing a component library.

Core reusable components:

- `AppShell`
- `Sidebar`
- `PageHeader`
- `Card`
- `PrimaryButton`
- `SecondaryButton`
- `FormField`
- `StatusPill`

## State And Data Flow

The existing React state machine can remain the source of truth for the MVP.

Recommended view states:

- `onboarding`
- `today`
- `plan`
- `practice`
- `review`
- `memory`
- `settings`

Existing API calls remain:

- `createOnboarding`
- `startSession`
- `sendUserTurn`
- `endSession`

No new backend endpoint is required for the first UI redesign pass.

## Error Handling

Frontend API errors should be visible to the user instead of failing silently.

Minimum error states:

- Onboarding failure: show a message near the Generate Plan action.
- Session start failure: show a retryable error on the Today or Practice page.
- Turn send failure: keep the typed text and show a retryable message.
- End session failure: keep the session visible and allow retry.

## Accessibility And Usability

- Buttons should have clear labels.
- Form controls should be vertically arranged and readable.
- Keyboard input should remain usable for text-based testing.
- The visual hierarchy should work on a laptop screen width around 1440px.
- The app should still be usable if browser speech recognition is unavailable.

## Testing Plan

Update frontend tests to cover:

- First-run onboarding still renders.
- Successful onboarding lands on the Today workspace.
- Settings page is reachable from navigation and contains learning configuration.
- Practice can start from Today.
- Practice renders conversation context and assistant turn.

Manual verification:

- Open the app at `http://127.0.0.1:5173/`.
- Generate a plan.
- Navigate between Today, Plan, Memory, and Settings.
- Start a practice session.
- Send one typed turn and confirm assistant response and feedback render.
- End the session and confirm review appears.

## Acceptance Criteria

- The default post-onboarding page looks like a learning workspace, not a raw form.
- Configuration is isolated under Settings.
- The practice page has separate conversation, feedback, and input areas.
- The UI uses a consistent visual system across pages.
- Existing backend tests still pass.
- Existing frontend tests are updated and pass.
- Frontend build passes.
