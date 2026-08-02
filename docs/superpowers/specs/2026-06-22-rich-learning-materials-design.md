# Rich Learning Materials Design

## Goal

Upgrade the product from a thin practice-flow prototype into a more realistic learning system that generates richer plans, lesson materials, and conversation guidance.

## Problem

The current flow is technically connected but pedagogically shallow:

- The onboarding profile only feeds a `GoalAgent` that generates `topic`, `scenario`, and `objective`.
- The daily plan does not store skill focus, communicative functions, success criteria, or material-generation hints.
- The `ScenarioDesignAgent` creates a lightweight brief with mostly string fields.
- The first assistant message and ongoing conversation are still driven mainly by `topic` and `objective`, not by a full lesson pack.
- The frontend only shows a small part of the generated brief, so users do not receive enough explicit learning material.

## Approved Approach

Use方案 C: enhance Plan, Practice Brief, and Conversation together.

This keeps the system compatible with all learning goals while giving the model a structured way to produce domain-specific materials for work, travel, exams, interviews, daily conversation, and other contexts.

## Plan Schema

Each plan day keeps the existing fields:

- `day_index`
- `topic`
- `scenario`
- `objective`
- `status`

Each plan day may also include richer instructional fields:

- `skill_focus`: the main speaking skill for the day, such as clarification, storytelling, negotiation, summarizing, or asking follow-up questions.
- `communicative_task`: the concrete user task that must be completed in the conversation.
- `target_functions`: 3-5 communicative functions, such as asking for clarification, explaining constraints, giving reasons, comparing options.
- `success_criteria`: 3-5 user-visible criteria for a successful practice.
- `brief_seed`: a compact instruction for `ScenarioDesignAgent` describing what kind of lesson pack should be generated.

Backward compatibility:

- Existing plan rows without rich fields still work.
- If rich fields are missing, agents fall back to `topic`, `scenario`, and `objective`.
- The SQLite table can store rich fields as nullable columns to avoid breaking old data.

## Practice Brief Schema

The practice brief becomes a lesson pack. It keeps existing fields:

- `title`
- `user_visible_goal`
- `npc_role`
- `scenario_setup`
- `conversation_objective`
- `target_expressions`
- `avoid_patterns`
- `difficulty`
- `coach_notes`

It may add these rich fields:

- `lesson_focus`: one short teaching focus for the session.
- `task_steps`: 3 ordered steps that guide the learner through the role-play.
- `target_expressions`: either strings or objects with `expression`, `meaning_zh`, `example`, and `when_to_use`.
- `sentence_frames`: 3-5 reusable sentence patterns with examples.
- `model_dialogue`: 4-8 turns showing a realistic sample conversation between NPC and learner.
- `common_mistakes`: 3-5 mistakes the learner should avoid, each with a better expression.
- `rubric`: 3-5 scoring criteria for self-review and agent review.
- `stretch_goal`: one optional challenge for stronger performance.

## Prompt Strategy

The default prompts should be upgraded, not only the fallback code:

- `GoalAgent` must output valid JSON with the richer plan fields.
- `ScenarioDesignAgent` must output a complete lesson pack, with examples adapted to the user's level.
- Prompts remain mostly Chinese for editability, while JSON keys remain English.
- Generated English learning materials must stay in English, with Chinese explanations where helpful.

## Conversation Integration

Conversation should use the lesson pack after session start:

- The first assistant message should reflect `npc_role`, `scenario_setup`, and `task_steps`, instead of only repeating `topic` and `scenario`.
- `ConversationAgent.reply` and `reply_stream` should accept optional `practice_brief`.
- The user prompt to the conversation model should include compact brief context:
  - NPC role
  - conversation objective
  - target expressions
  - avoid patterns
  - task steps
  - rubric
- The NPC must still only speak as the role-play NPC, not as a teacher.

## Frontend Experience

Practice Room should expose the generated material more clearly:

- Before the user sends the first answer, show a lesson pack view with:
  - scenario setup
  - lesson focus
  - task steps
  - expression cards
  - sentence frames
  - model dialogue
  - common mistakes
  - success criteria / rubric
- During practice, keep a compact side panel with:
  - current goal
  - target expressions
  - task steps
  - common mistakes
  - success criteria

## Testing

Implementation should use TDD:

- Agent tests verify rich plan and brief parsing.
- Repository/API tests verify rich plan fields are saved and returned.
- Session tests verify practice brief is returned and conversation receives it.
- Frontend tests verify rich materials render in Practice Room.

## Non-Goals

- Do not require users to fill a long onboarding form in this iteration.
- Do not implement spaced repetition UI in this iteration.
- Do not create a separate content-management database in this iteration.
- Do not remove compatibility with existing three-field plans.

