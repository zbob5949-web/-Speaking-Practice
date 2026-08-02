# Dual Persona, Chunked TTS, and Feedback Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement dual persona (Coach/NPC) parsing in prompts, chunked real-time TTS playback in frontend, append-only feedback history, and silent fallback on metadata errors.

**Architecture:** 
1. **Backend Agent**: Modify `ConversationAgent` system prompt to output `<coach>...</coach>` and/or `<npc>...</npc>` inside `<reply>`.
2. **Frontend UI (Feedback)**: Append feedback instead of overwriting, fetch history on boot, and rename "Instant Feedback" to "Feedback History". Ignore metadata stream errors to prevent UI rollback.
3. **Frontend TTS (Chunking)**: Extract text inside `<npc>` and `<coach>`, split by punctuation (`.`, `?`, `!`, `\n`), queue them, and play sequentially via the backend `/api/tts` endpoint while text is still streaming.

**Tech Stack:** Python, FastAPI, React, TypeScript, CSS

---

### Task 1: Update Conversation Agent Dual Persona Prompt

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_conversation_agent.py`

- [ ] **Step 1: Write the failing test**

In `app/backend/tests/test_conversation_agent.py`, update `MockXMLStreamProvider`:

```python
class MockXMLStreamProvider(FakeLLMProvider):
    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        assert "Dual Persona" in system_prompt
        chunks = ["<rep", "ly><coach>Helpful tip.</coach><npc>Hello</npc></reply>", "<hints>[\"H1", "\"]</hints>"]
        for c in chunks:
            yield c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: FAIL (assertion error on system prompt contents)

- [ ] **Step 3: Write minimal implementation**

In `app/backend/app/agents.py`, update `ConversationAgent.reply_stream` system prompt:

```python
        system_prompt = (
            "You are an expert English speaking coach acting as a roleplay director. "
            f"The user's current level is: '{user_level}'. Their ultimate goal is: '{learning_goal}'. "
            "Instructions:\n"
            "1. Adapt your vocabulary and sentence complexity based on the user's level.\n"
            "2. DO NOT ask open-ended questions like 'What do you want to practice next?'. Instead, drive the plot forward by introducing a specific scenario obstacle or giving the user a clear binary choice.\n"
            "3. If the user speaks in a mix of Chinese and English (Chinglish), understand their intent and respond naturally in English.\n"
            "4. Dual Persona Rules:\n"
            "   - When providing guidance, encouragement, or correcting the user, wrap your text in <coach>...</coach> tags.\n"
            "   - When speaking in-character as the NPC (e.g. receptionist, waiter), wrap your text in <npc>...</npc> tags.\n"
            "   - You can use both if needed (e.g. <coach>Here is the front desk.</coach><npc>Hello!</npc>).\n"
            "5. You MUST format your total output exactly like this:\n"
            "<reply><coach>Optional coach text</coach><npc>Optional NPC text</npc></reply>\n"
            "<hints>[\"💡 询问超重费用\", \"💡 表示拿几件衣服出来\"]</hints>\n"
            "The <hints> tag MUST contain a valid JSON array of 2-3 short strings in the user's native language."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_conversation_agent.py
git commit -m "feat: conversation agent prompt updated for dual persona coach and npc"
```

---

### Task 2: Backend API Support for Feedback History

**Files:**
- Modify: `app/backend/app/repositories.py`
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing test**

In `app/backend/tests/test_repositories.py`:

```python
def test_get_inline_feedback_for_session(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    repo.save_inline_feedback(1, 1, [{"feedback_type": "grammar", "feedback_text": "text1"}])
    repo.save_inline_feedback(1, 2, [{"feedback_type": "expression", "feedback_text": "text2"}])
    
    feedbacks = repo.get_inline_feedback_for_session(1)
    assert len(feedbacks) == 2
    assert feedbacks[0]["feedback_text"] == "text1"
    assert feedbacks[1]["feedback_text"] == "text2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_repositories.py -v`
Expected: FAIL (missing `get_inline_feedback_for_session`)

- [ ] **Step 3: Write minimal implementation in repository**

In `app/backend/app/repositories.py`, add `get_inline_feedback_for_session`:

```python
    def get_inline_feedback_for_session(self, session_id: int) -> list[dict[str, Any]]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM inline_feedback WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]
```

In `app/backend/app/main.py`, update `/api/sessions/start` to return history:
```python
@app.post("/api/sessions/start")
def start_session(request: StartSessionRequest) -> dict[str, object]:
    repo = get_repository()
    # ... existing code ...
    session = repo.get_or_create_session(plan_day_id=plan_day["id"], day_index=plan_day["day_index"], topic=plan_day["topic"])
    turns = repo.get_turns(session["id"])
    feedback_history = repo.get_inline_feedback_for_session(session["id"])
    
    if not turns:
        # ... existing ...
        
    return {"session": session, "turns": turns, "plan_day": plan_day, "feedback_history": feedback_history}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_repositories.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/repositories.py app/backend/app/main.py app/backend/tests/test_repositories.py
git commit -m "feat: backend supports fetching inline feedback history for a session"
```

---

### Task 3: Frontend Dual Persona Styling and Feedback History Resilience

**Files:**
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Update API signature**

In `app/frontend/src/api.ts`, update `startSession` return type:
```typescript
export async function startSession(planDayId: number): Promise<{
  session: PracticeSession;
  turns: ConversationTurn[];
  feedback_history?: InlineFeedback[];
}> {
```

Update `sendUserTurnStream` to NOT throw on missing metadata, but return empty hints/feedback if it fails at the end:
```typescript
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // ... existing buffer logic ...
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "text") {
            onTextChunk(data.content);
          } else if (data.type === "meta") {
            meta = data;
          }
        } catch (e) {
          // ignore incomplete json
        }
      }
    }
  }
  
  if (!meta) {
    // Resilience: If meta is missing (e.g. timeout on feedback generation), don't crash.
    // Return empty arrays so the text response is preserved.
    return {
      user_turn: null as any, // handled by caller if needed
      assistant_turn: null as any,
      inline_feedback: [],
      hints: []
    };
  }
  return meta;
```

- [ ] **Step 2: Update `PracticeRoom.tsx` for History and Persona Rendering**

In `app/frontend/src/components/PracticeRoom.tsx`:

Append feedback instead of overwrite:
```tsx
    // in boot()
    setFeedback(result.feedback_history || []);
    
    // in submitTurn()
      const result = await sendUserTurnStream(...)
      // ... existing turn replace logic ...
      
      if (result.inline_feedback && result.inline_feedback.length > 0) {
        setFeedback(current => [...current, ...result.inline_feedback]);
      }
      setHints(result.hints || []);
```

Change sidebar title:
```tsx
        <aside className="feedback-sidebar" aria-label="Instant feedback">
          <p className="section-label">Feedback History</p>
```

Add a helper function to render dual persona text:
```tsx
  function renderDualPersonaText(text: string) {
    // Very simple replacement for demo purposes. In a robust app, parse XML properly.
    let html = text
      .replace(/<coach>/g, '<span class="persona-coach">💡 ')
      .replace(/<\/coach>/g, '</span>')
      .replace(/<npc>/g, '<span class="persona-npc">')
      .replace(/<\/npc>/g, '</span>');
      
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  }
```

Update message bubble rendering:
```tsx
                      <div className={isUser ? "message-bubble message-bubble-user" : "message-bubble message-bubble-assistant"}>
                        <p>{isUser ? turn.text : renderDualPersonaText(turn.text)}</p>
                      </div>
```
And similarly for `streamingReply`:
```tsx
                      <p>{renderDualPersonaText(streamingReply)}<span className="typing-cursor">▋</span></p>
```

- [ ] **Step 3: Update CSS**

In `app/frontend/src/styles.css`:
```css
.persona-coach {
  display: block;
  color: #667085;
  font-style: italic;
  font-size: 0.9em;
  margin-bottom: 8px;
  background: #f9fafb;
  padding: 8px 12px;
  border-radius: 8px;
}

.persona-npc {
  display: block;
  color: #1d2939;
}
```

- [ ] **Step 4: Verify build and Commit**

Run: `cd app/frontend && npm run build`

```bash
git add app/frontend/src/api.ts app/frontend/src/components/PracticeRoom.tsx app/frontend/src/styles.css
git commit -m "feat: frontend resilience, feedback history append, and dual persona styling"
```

---

### Task 4: Frontend Chunked TTS Playback

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Add TTS Queue Logic**

In `app/frontend/src/components/PracticeRoom.tsx`:

We need to capture chunks during streaming and play them. Remove the `playTTS(result.assistant_turn.text)` from the end of `submitTurn`.

Add state and refs:
```tsx
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingAudioRef = useRef(false);
  const processedTextLenRef = useRef(0);
```

Add queue processor function:
```tsx
  const processAudioQueue = async () => {
    if (isPlayingAudioRef.current || audioQueueRef.current.length === 0) return;
    
    isPlayingAudioRef.current = true;
    const textToPlay = audioQueueRef.current.shift();
    
    if (textToPlay) {
      try {
        await playTTS(textToPlay);
      } catch (e) {
        console.warn("Chunk TTS failed", e);
      }
    }
    
    isPlayingAudioRef.current = false;
    processAudioQueue(); // Process next
  };
```

Update `sendUserTurnStream` callback in `submitTurn`:
```tsx
    processedTextLenRef.current = 0;
    audioQueueRef.current = [];
    
    try {
      const result = await sendUserTurnStream(
        session.id,
        text.trim(),
        (chunk) => {
          setStreamingReply((prev) => {
            const newText = (prev || "") + chunk;
            
            // Check for sentence boundaries in the NEW text portion
            const unprocessed = newText.slice(processedTextLenRef.current);
            const sentenceMatch = unprocessed.match(/([^.!?\n]+[.!?\n]+)/);
            
            if (sentenceMatch) {
              const sentence = sentenceMatch[1];
              processedTextLenRef.current += sentence.length;
              
              // Strip XML tags before sending to TTS
              const cleanSentence = sentence.replace(/<[^>]+>/g, '').trim();
              if (cleanSentence.length > 0) {
                audioQueueRef.current.push(cleanSentence);
                processAudioQueue();
              }
            }
            return newText;
          });
        }
      );
      
      // End of stream, flush remaining text
      setStreamingReply((finalText) => {
        if (finalText) {
          const remaining = finalText.slice(processedTextLenRef.current);
          const cleanRemaining = remaining.replace(/<[^>]+>/g, '').trim();
          if (cleanRemaining.length > 0) {
            audioQueueRef.current.push(cleanRemaining);
            processAudioQueue();
          }
        }
        return null; // clear streaming reply
      });
```

- [ ] **Step 2: Verify build and Commit**

Run: `cd app/frontend && npm run build`

```bash
git add app/frontend/src/components/PracticeRoom.tsx
git commit -m "feat: chunked real-time TTS playback during SSE stream"
```
