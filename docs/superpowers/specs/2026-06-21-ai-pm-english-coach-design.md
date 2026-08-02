# AI PM English Coach Design

## 1. Background

This project is a local-first English learning agent for personal use. The user is an AI product manager with an IELTS level around 6.5 and weaker speaking ability around 6. The goal is to improve international professional communication for future AI-related roles in foreign companies.

The project is not intended to become a commercial product in the first phase. It should optimize for daily personal use, fast iteration, low cost, and useful long-term learning memory.

## 2. Product Goal

Build a local AI English coach that supports:

- Open-ended learning goal setup.
- Flexible learning duration setup.
- Push-to-talk English conversation practice.
- AI spoken replies during conversation.
- Lightweight inline text feedback during conversation.
- Post-session review reports.
- Local long-term memory for mistakes, useful expressions, learning progress, and future session planning.

The first version should focus on a complete learning loop rather than perfect voice quality.

## 3. Target User

Primary user:

- Chinese-native AI product manager.
- English level around IELTS 6.5.
- Speaking level around IELTS 6.
- Wants to improve AI professional communication, foreign-company interview performance, cross-functional meeting communication, and reading-to-speaking ability.

The system should remain configurable enough to support other learning goals later, but the default template is "AI product manager internationalization".

## 4. Core Design Principles

- Local first: all learning data is stored locally.
- Low cost first: use free browser or system TTS in the first version.
- Practical speaking first: optimize for daily speaking practice, not exhaustive English teaching.
- Long-term memory: convert daily conversations into reusable learning assets.
- Lightweight feedback: give inline feedback without interrupting conversation flow.
- Open configuration: allow the user to choose learning goal and duration.
- Simple implementation: avoid RTC, full-duplex interruption, cloud sync, user accounts, and paid voice services in the MVP.

## 5. MVP Scope

### Must Have

- Onboarding page for learning goal, total duration, daily duration, and current level.
- Plan generation based on the selected goal and duration.
- Daily practice page with push-to-talk input.
- AI English conversation replies.
- AI reply playback through browser or system TTS.
- Inline text feedback during conversation.
- End-session review report.
- Local storage of sessions, turns, feedback, mistakes, expressions, and memory snapshots.
- Daily review of previous mistakes and expressions.

### Nice To Have

- Replay AI voice response.
- Manual favorite for useful expressions.
- Manual editing of learning goal.
- Export session report to Markdown.

### Out Of Scope

- Account system.
- Cloud sync.
- Mobile app.
- Knowledge base.
- Real-time full-duplex voice.
- RTC integration.
- Paid ASR or TTS service.
- Multi-user support.
- Complex placement tests.
- Commercial product features.

## 6. First-Run Onboarding

The first-run flow collects four fields:

- Learning goal: open text input plus templates.
- Total learning duration: 7 days, 14 days, or 30 days.
- Daily practice duration: 10 minutes, 15 minutes, or 20 minutes.
- Current level: simple text or preset option.

Default settings:

- Learning goal: AI product manager internationalization.
- Total duration: 14 days.
- Daily duration: 15 minutes.
- Current level: IELTS 6.5, speaking 6.

Recommended goal templates:

- AI product manager internationalization.
- Foreign-company interview.
- Business meeting communication.
- AI technical discussion.
- English reading retelling.
- Custom goal.

## 7. Main User Flow

1. User opens the local app.
2. If no profile exists, the app shows onboarding.
3. The system generates a learning plan.
4. The dashboard shows today's session, previous review items, and progress.
5. User enters the practice room.
6. Session Agent starts the session with a short English introduction.
7. User speaks through push-to-talk.
8. ASR converts speech to text.
9. Conversation Agent replies in English.
10. TTS plays the AI reply.
11. Inline Feedback Agent generates short text feedback.
12. User continues the conversation until time runs out or clicks end.
13. Review Agent generates a Chinese post-session report.
14. Memory Agent updates mistakes, expressions, learning state, and future review items.
15. User returns the next day and reviews selected previous items before practice.

## 8. Page Design

### Dashboard

Shows:

- Current learning goal.
- Current day and total plan duration.
- Today's topic.
- Suggested warm-up items.
- Recent ability snapshot.
- Start Practice button.
- Links to Plan, Memory Library, and Reports.

### Practice Room

Shows:

- Today's scenario and objective.
- Conversation history.
- Push-to-talk button.
- End Session button.
- Replay AI Response button.
- Inline feedback panel.

The inline feedback panel shows:

- More natural expression.
- Grammar reminder.
- Professional expression replacement.
- Follow-up suggestion.

Each turn should generate at most 1-2 short feedback items.

### Feedback Report

Shows:

- Overall performance summary in Chinese.
- Clarity of communication.
- Naturalness.
- Professional vocabulary.
- Structured answering.
- Grammar and wording issues.
- Corrected sentences.
- Better alternatives.
- 3-5 high-value expressions.
- 1-3 suggestions for the next session.

### Memory Library

Shows:

- Mistake bank.
- Expression bank.
- Session history.
- Memory snapshots.
- Review items.

### Plan View

Shows:

- Generated plan by day.
- Session status.
- Topic.
- Learning objective.
- Completion status.

## 9. Agent Design

### Goal Agent

Responsibilities:

- Convert user goal, duration, daily time, and level into a learning plan.
- Produce daily topics, scenario descriptions, and learning objectives.
- Keep the plan simple and focused.

Inputs:

- User profile.
- Learning goal.
- Duration.
- Daily duration.
- Current level.

Outputs:

- Learning plan.

### Session Agent

Responsibilities:

- Prepare the daily session.
- Read today's topic and previous memory.
- Create a short session instruction for Conversation Agent.
- Decide which previous mistakes or expressions should be reviewed.

Inputs:

- User profile.
- Today's plan item.
- Recent mistakes.
- Recent expressions.
- Memory snapshot.

Outputs:

- Session brief.
- Warm-up review items.

### Conversation Agent

Responsibilities:

- Conduct the English speaking session.
- Reply in short spoken English.
- Role-play as interviewer, colleague, business stakeholder, engineer, or coach.
- Ask follow-up questions.
- Keep the conversation active and practical.

Rules:

- Speak in English.
- Keep each reply to 1-3 sentences.
- Avoid over-correcting in spoken replies.
- Encourage the user to speak more.
- Use AI product manager scenarios when relevant.

### Inline Feedback Agent

Responsibilities:

- Generate lightweight text feedback during conversation.
- Avoid interrupting the spoken conversation.
- Focus on immediate improvements.

Rules:

- Output in Chinese.
- At most 1-2 feedback items per user turn.
- Prefer short, actionable suggestions.
- Do not generate long explanations.

### Review Agent

Responsibilities:

- Generate full post-session review.
- Score the session against the user's learning goal.
- Extract corrected sentences and useful expressions.

Outputs:

- Review report.
- Mistake candidates.
- Expression candidates.
- Next-session suggestions.

### Memory Agent

Responsibilities:

- Update local long-term memory.
- Save mistakes and expressions.
- Update learning state.
- Create compact memory snapshots.
- Select future review items.

Rules:

- Store learning-useful summaries instead of raw context dumps.
- Keep review load manageable.
- Prefer recurring issues over one-off minor mistakes.

## 10. Memory Model

### User Profile

Stores:

- Learning goal.
- Duration.
- Daily practice duration.
- Current level.
- User preferences.
- Default target scenario.

### Learning Plan

Stores:

- Day index.
- Topic.
- Scenario.
- Objective.
- Status.
- Generated instructions.

### Session History

Stores:

- Session ID.
- Date.
- Day index.
- Topic.
- Start time.
- End time.
- Duration.
- Overall score.
- Summary.

### Conversation Turns

Stores:

- Session ID.
- Turn index.
- Speaker.
- Text.
- Timestamp.
- Optional ASR confidence.

### Inline Feedback

Stores:

- Session ID.
- Turn ID.
- Feedback type.
- Feedback text.

### Error Bank

Stores:

- Original sentence.
- Corrected sentence.
- Better expression.
- Error type.
- Explanation.
- Source session.
- Review count.
- Last reviewed time.

### Expression Bank

Stores:

- Expression.
- Meaning.
- Usage context.
- Example sentence.
- Source session.
- Review count.
- Last reviewed time.

### Memory Snapshot

Stores:

- Date.
- Current strengths.
- Current weaknesses.
- Frequent mistakes.
- Useful expressions learned.
- Recommended next focus.

## 11. Default 14-Day Plan Template

This template is used when the user selects the default AI product manager internationalization goal.

1. AI product manager self-introduction.
2. Explain the user value of an AI product.
3. Explain LLM, Agent, RAG, and fine-tuning.
4. Discuss latency, cost, accuracy, and launch risk with engineers.
5. Present an AI product roadmap to an overseas stakeholder.
6. Discuss AI product metrics such as activation, retention, task success, latency, and cost.
7. Review common issues from the first six days.
8. Foreign-company AI PM behavioral interview.
9. Product sense interview for designing an AI assistant.
10. Technical tradeoff discussion: RAG, fine-tuning, and prompt engineering.
11. Cross-functional meeting with design, engineering, legal, and safety.
12. Read an AI article excerpt and summarize it verbally.
13. Pressure Q&A: clarification, structured response, and disagreement.
14. Full mock interview and next-stage learning plan.

For 7-day or 30-day plans, the Goal Agent should compress or expand this structure according to the user's selected duration.

## 12. Voice Interaction Design

The MVP uses push-to-talk instead of full-duplex real-time voice.

Flow:

1. User presses or clicks the talk button.
2. Browser captures speech.
3. ASR converts speech to text.
4. User text is sent to backend.
5. Conversation Agent generates reply.
6. Reply text appears in chat.
7. Browser or system TTS plays the reply.
8. Inline feedback appears in text-only panel.

MVP voice constraints:

- No real-time interruption.
- No echo cancellation tuning.
- No paid voice synthesis.
- No RTC.
- AI voice quality only needs to be usable.

## 13. Technical Architecture

Recommended stack:

- Frontend: React + Vite.
- Backend: Python FastAPI.
- Database: SQLite.
- LLM: domestic model API preferred, such as DeepSeek, Qwen, or Doubao, selected by availability and cost.
- ASR: browser speech recognition first; local ASR can be added later.
- TTS: browser SpeechSynthesis or macOS system voice.

Architecture:

```text
React Frontend
  -> Push-to-talk speech input
  -> ASR transcript
  -> FastAPI Backend
  -> Agent Orchestrator
  -> LLM Provider
  -> SQLite Memory Store
  -> Response + Inline Feedback
  -> Browser/System TTS
```

## 14. Suggested Project Structure

```text
english-ai-coach/
  app/
    frontend/
    backend/
  data/
    coach.sqlite
    transcripts/
    reports/
  prompts/
    goal_agent.md
    session_agent.md
    conversation_agent.md
    inline_feedback_agent.md
    review_agent.md
    memory_agent.md
  docs/
    superpowers/
      specs/
        2026-06-21-ai-pm-english-coach-design.md
```

## 15. Acceptance Criteria

The MVP is successful when:

- The user can complete onboarding locally.
- The app can generate a learning plan from goal and duration.
- The user can start a daily practice session.
- The user can speak through push-to-talk.
- The system can convert or accept the spoken input as text.
- The AI can reply in English.
- The AI reply can be played through free TTS.
- The app can show inline text feedback during conversation.
- The app can generate a post-session Chinese review.
- The app can save mistakes and expressions locally.
- The next session can review previous items.

## 16. Implementation Phasing

### Phase 1: Text Loop

- Create local app skeleton.
- Implement onboarding.
- Generate learning plan.
- Implement text-based practice.
- Save sessions and turns.

### Phase 2: Agent Memory

- Add review report generation.
- Add error bank and expression bank.
- Add memory snapshots.
- Add next-session review items.

### Phase 3: Voice Basics

- Add push-to-talk input.
- Add browser or system TTS.
- Add replay response.

### Phase 4: Inline Feedback

- Add inline feedback generation.
- Store feedback per turn.
- Tune feedback brevity.

### Phase 5: Experience Polish

- Improve dashboard.
- Add Markdown export.
- Improve plan editing.
- Add local settings for LLM provider.

## 17. Risks And Mitigations

### Browser ASR Availability

Risk: Browser speech recognition may be inconsistent depending on browser and system.

Mitigation: Provide text input fallback in the practice room. Add local ASR later if needed.

### TTS Quality

Risk: Free browser or system TTS may sound mechanical.

Mitigation: Accept this in the MVP. Keep AI replies short. Add paid or better TTS only if needed.

### LLM Cost

Risk: Long conversations and review reports may consume tokens.

Mitigation: Keep each AI reply short. Summarize sessions. Store compact memory snapshots.

### Feedback Overload

Risk: Too much feedback may interrupt speaking confidence.

Mitigation: Limit inline feedback to 1-2 short items per turn and keep full feedback for post-session review.

### Memory Pollution

Risk: Saving too many low-value mistakes can make review overwhelming.

Mitigation: Memory Agent should prioritize recurring or high-impact mistakes.

## 18. Open Decisions

All major MVP decisions are currently resolved:

- Use push-to-talk instead of full-duplex voice.
- Use text-only inline feedback.
- Use voice only for AI conversation replies.
- Avoid paid TTS in the first version.
- Support open learning goal and learning duration.
- Keep all data local.

Future decisions:

- Which domestic LLM provider should be used first.
- Whether browser ASR is acceptable after a real-device test.
- Whether to add local ASR if browser ASR is unstable.
