# Practice Lesson Simplification Design

## Goal

Simplify the pre-practice lesson page so it shows one clear path to start speaking, without repeating the same goal, scenario, and training rationale across multiple cards.

## Problem

The current Learn page in `PracticeRoom` shows overlapping information in three places:

- Header: title plus `user_visible_goal` / `conversation_objective`
- Today Strategy card: focus, reason, and AI coach preparation
- Roleplay Setup card: role, scenario, and repeated `conversation_objective`

This makes the page feel heavy and creates duplicated meaning: the user sees similar practice objectives multiple times before they can start.

## Chosen Approach

Use the lightweight "simplify first screen" approach:

- Keep the header with title, one primary goal sentence, and `Start guided practice`.
- Remove the visible Today Strategy card from this page. Training strategy remains available in data and backend behavior, but it is not shown in the pre-practice UI.
- Keep Roleplay Setup, but only show role and scenario. Do not repeat the objective there.
- Merge `lesson_focus` and `task_steps` into one compact `How to practice` card.
- Keep `Target Expressions` as `Useful phrases`, but show only the first six phrases to reduce visual weight.
- Hide secondary learning material (`model_dialogue`, `common_mistakes`, `rubric`, `stretch_goal`, `avoid_patterns`, `sentence_frames`) from this first screen for now.

## UI Shape

The Learn page should contain:

- Hero: title, one goal sentence, start button
- Roleplay: NPC role and scenario
- How to practice: lesson focus plus task steps
- Useful phrases: up to six target expressions

## Non-Goals

- Do not change backend lesson-pack generation.
- Do not remove fields from `PracticeBrief`.
- Do not redesign the practice chat page.
- Do not add collapsible secondary sections in this pass.

## Testing

- Update existing React tests that assert old repeated strategy sections.
- Assert that core Learn page information still renders.
- Assert that `conversation_objective` does not render twice when it is already used as the header goal.
- Keep the transition to practice chat covered.
