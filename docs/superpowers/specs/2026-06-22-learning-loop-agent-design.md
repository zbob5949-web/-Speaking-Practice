# English Coach: Learning Loop Agent System Design

## Overview
This spec defines the architecture for upgrading the current English Coach from a "chat tool with a static plan" to a true "adaptive learning agent." It establishes a daily learning loop where practice sessions are summarized into a daily review, which extracts long-term memory, which in turn slightly adapts the upcoming learning plan and drives the scenario design for the next practice session.

## 1. System Architecture

The system consists of five distinct agents that pass structured data between each other in a loop:

1. **Practice Agent (Conversation + Inline Feedback):**
   - Handles the real-time chat with the user.
   - Generates natural NPC dialogue and immediate sentence-level corrections.
   - *Outputs:* `conversation_turns`, `inline_feedback`.

2. **Daily Review Agent:**
   - Triggered daily or via catch-up mechanism.
   - Aggregates all sessions from a given day.
   - *Outputs:* `daily_reviews` (dual-layered: user-readable report + structured analysis).

3. **Memory Agent:**
   - Reads the structured analysis from the Daily Review.
   - Decides what information about the user is stable enough to be kept long-term.
   - *Outputs:* `memory_items` (upserts or updates).

4. **Plan Adaptation Agent:**
   - Reads the Daily Review and active Memory Items.
   - Proposes moderate adjustments (focus, difficulty, scenario) to the next 1-3 days of the existing `learning_plan`.
   - Does NOT overwrite the original plan directly.
   - *Outputs:* `plan_adjustments`.

5. **Scenario Design Agent:**
   - Reads the original plan day, active plan adjustments, and active memory items.
   - Generates a concrete "practice brief" before the next session starts.
   - *Outputs:* `practice_briefs` (target expressions, NPC role, specific objectives).

## 2. Data Models (SQLite)

We will use JSON fields in the MVP for complex outputs to speed up implementation, moving to normalized tables later if needed.

### `daily_reviews`
- `id` INTEGER PK
- `profile_id` INTEGER
- `review_date` TEXT (YYYY-MM-DD)
- `status` TEXT ('completed', 'failed', 'skipped')
- `user_report_json` TEXT (The natural language summary, achievements, key issues)
- `structured_analysis_json` TEXT (The signals for downstream agents: performance, recurring issues)
- `source_session_ids_json` TEXT (Array of session IDs included)
- `created_at` TEXT

### `memory_items`
- `id` INTEGER PK
- `profile_id` INTEGER
- `category` TEXT ('weakness', 'strength', 'preference', 'learning_goal', 'expression_focus', 'user_profile')
- `content` TEXT
- `evidence` TEXT
- `confidence` REAL
- `status` TEXT ('active', 'archived')
- `source_review_id` INTEGER
- `created_at` TEXT
- `updated_at` TEXT

### `plan_adjustments`
- `id` INTEGER PK
- `target_plan_day_id` INTEGER
- `source_review_id` INTEGER
- `adjustment_type` TEXT ('focus', 'difficulty', 'scenario', 'repeat', 'skip')
- `instruction` TEXT (The prompt instructions for the Scenario Design Agent)
- `rationale` TEXT (Why this adjustment was made)
- `status` TEXT ('active', 'applied', 'expired')
- `expires_after_days` INTEGER
- `created_at` TEXT

### `practice_briefs`
- `id` INTEGER PK
- `session_id` INTEGER
- `plan_day_id` INTEGER
- `brief_json` TEXT (NPC role, setup, target expressions, avoid patterns, coach notes)
- `created_at` TEXT

## 3. Trigger Mechanism: "Daily + Catch-up"

To balance the need for a daily cadence with the realities of a local desktop app:

1. **Backend Endpoint:** `POST /api/daily-review/run-due`
   - Checks the last reviewed date for the active profile.
   - For every day between the last reviewed date and "yesterday", runs the Daily Review Agent.
   - If a day has no sessions, it inserts a `status: 'skipped'` record.
2. **Frontend Trigger:** 
   - The React app calls `POST /api/daily-review/run-due` once during its initial mount/load sequence.
   - This ensures that when the user opens the app the next day, the previous day's review is generated before they start a new session.
3. **Future Extension:** The `run-due` logic can later be wired to a local cron job or launchd service.

## 4. UI / UX Restructuring

1. **Growth Page (Replaces standalone Review and Memory):**
   - User-facing dashboard.
   - Shows the latest `DailyReview.user_report`.
   - Shows a simplified view of active `memory_items` (e.g., "Your known weaknesses").
2. **Plan Page Update:**
   - Shows the original plan.
   - Highlights days that have active `plan_adjustments` (e.g., "Adjusted: Focus on polite requests").
3. **Developer Studio Extension:**
   - Adds a "Memory Debugger" tab.
   - Allows raw JSON viewing of Daily Reviews and Plan Adjustments.
   - Allows manual archiving/editing of `memory_items`.

## 5. Agent Prompts Strategy

All new agents will follow the existing pattern in `agents.py` and `db.py`:
- System prompts are seeded in the database.
- They enforce strict JSON output.
- The prompts will be written in Chinese, with strict instructions to keep English examples/target expressions in English.

## 6. Implementation Scope (MVP)

1. **Database:** Add the 4 new tables.
2. **Agents:** Implement `DailyReviewAgent`, `MemoryAgent`, `PlanAdaptationAgent`, and `ScenarioDesignAgent`.
3. **API:** 
   - Add `/api/daily-review/run-due` (which will also pre-generate the `practice_brief` for the next pending plan day).
   - Modify `/api/sessions/start` to fetch the pre-generated `practice_brief`.
   - Modify `/api/sessions/turn` to pass the `practice_brief` to the `ConversationAgent`.
4. **Frontend:** 
   - Add the startup trigger.
   - Build the `Growth` page.
   - Update `Plan` and `Studio` pages.
