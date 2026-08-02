# Streaming SSE & Trailing Meta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Server-Sent Events (SSE) for the conversation API to stream text progressively, sending structural metadata (hints & feedback) as a trailing event at the end.

**Architecture:** 
1. **`LLMProvider`**: Add a `stream_complete` method yielding chunks via `httpx.stream`.
2. **`ConversationAgent`**: Modify prompt to output `<reply>...</reply><hints>[...]</hints>` instead of JSON. Add `reply_stream` method to yield reply text and return parsed hints.
3. **API Endpoint**: Add `/api/sessions/turn/stream` returning a `StreamingResponse`. It streams `type: text` chunks, then processes `InlineFeedbackAgent`, then yields `type: meta` with hints and feedback.
4. **Frontend**: Use `fetch` reading `body.getReader()` to handle the SSE format stream, updating `typedText`/`assistant_text` in real-time, then `hints`/`feedback` at the end.

**Tech Stack:** Python, FastAPI, httpx, React, TypeScript

---

### Task 1: Add Streaming to LLM Providers

**Files:**
- Modify: `app/backend/app/llm.py`
- Modify: `app/backend/tests/test_llm.py`

- [ ] **Step 1: Write the failing test**

In `app/backend/tests/test_llm.py`:

```python
from app.llm import OpenRouterProvider

def fake_post_json_stream(url, headers, json_data, timeout):
    yield {"choices": [{"delta": {"content": "Hello"}}]}
    yield {"choices": [{"delta": {"content": " world!"}}]}

def test_openrouter_stream_complete():
    provider = OpenRouterProvider("fake_key", "http://fake.com", "fake_model", post_json_stream=fake_post_json_stream)
    chunks = list(provider.stream_complete("system", "user"))
    assert chunks == ["Hello", " world!"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_llm.py -v`
Expected: FAIL (missing `post_json_stream` and `stream_complete`)

- [ ] **Step 3: Write minimal implementation in `llm.py`**

In `app/backend/app/llm.py`, update `LLMProvider` protocol:

```python
from typing import Iterator

class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...
    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]: ...
```

Update `FakeLLMProvider`:
```python
    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        yield "<reply>Could you describe</reply><hints>[\"Hint\"]</hints>"
```

Add `PostJsonStream` type and `default_post_json_stream`:
```python
import json

PostJsonStream = Callable[[str, dict[str, str], dict[str, Any], float], Iterator[dict[str, Any]]]

def default_post_json_stream(url: str, headers: dict[str, str], json_data: dict[str, Any], timeout: float) -> Iterator[dict[str, Any]]:
    with httpx.stream("POST", url, headers=headers, json=json_data, timeout=timeout) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
```

Update `OpenRouterProvider`:
```python
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        post_json: PostJson = default_post_json,
        post_json_stream: PostJsonStream = default_post_json_stream,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.post_json = post_json
        self.post_json_stream = post_json_stream

    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        stream = self.post_json_stream(
            f"{self.base_url}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "English Coach",
            },
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "stream": True,
            },
            30.0,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                yield delta["content"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_llm.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/llm.py app/backend/tests/test_llm.py
git commit -m "feat: add stream_complete to llm providers"
```

---

### Task 2: Streaming Output Parser in `ConversationAgent`

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_conversation_agent.py`

- [ ] **Step 1: Write the failing test**

In `app/backend/tests/test_conversation_agent.py`:

```python
from typing import Iterator

class MockXMLStreamProvider(FakeLLMProvider):
    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        chunks = ["<rep", "ly>Hel", "lo</reply>", "<hints>[\"H1", "\"]</hints>"]
        for c in chunks:
            yield c

def test_conversation_agent_reply_stream():
    agent = ConversationAgent(MockXMLStreamProvider())
    generator = agent.reply_stream("Topic", "Obj", "Level", "Goal", [])
    
    chunks = []
    for item in generator:
        if isinstance(item, str):
            chunks.append(item)
        elif isinstance(item, list):
            hints = item
            
    assert "".join(chunks) == "Hello"
    assert hints == ["H1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: FAIL (missing `reply_stream`)

- [ ] **Step 3: Write minimal implementation**

In `app/backend/app/agents.py`, update `ConversationAgent`:

```python
    def reply_stream(self, topic: str, objective: str, user_level: str, learning_goal: str, conversation: list[dict[str, str]]) -> Iterator[str | list[str]]:
        recent_turns = conversation[-20:] if len(conversation) > 20 else conversation
        user_prompt_turns = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in recent_turns)
        
        system_prompt = (
            "You are an expert English speaking coach acting as a roleplay director. "
            f"The user's current level is: '{user_level}'. Their ultimate goal is: '{learning_goal}'. "
            "Instructions:\n"
            "1. Adapt your vocabulary and sentence complexity based on the user's level.\n"
            "2. DO NOT ask open-ended questions like 'What do you want to practice next?'. Instead, drive the plot forward by introducing a specific scenario obstacle or giving the user a clear binary choice.\n"
            "3. If the user speaks in a mix of Chinese and English (Chinglish), understand their intent and respond naturally in English.\n"
            "4. You MUST format your output exactly like this:\n"
            "<reply>Your spoken response as the coach/roleplay character here.</reply>\n"
            "<hints>[\"💡 询问超重费用\", \"💡 表示拿几件衣服出来\"]</hints>\n"
            "The <hints> tag MUST contain a valid JSON array of 2-3 short strings in the user's native language."
        )
        
        user_prompt = (
            f"Today's Topic: {topic}\n"
            f"Today's Objective: {objective}\n"
            "--- Conversation History ---\n"
            f"{user_prompt_turns}\n"
            "--- End History ---\n"
            "Provide your response:"
        )
        
        stream = self.llm.stream_complete(system_prompt=system_prompt, user_prompt=user_prompt)
        
        buffer = ""
        in_reply = False
        
        for chunk in stream:
            buffer += chunk
            
            if not in_reply:
                if "<reply>" in buffer:
                    in_reply = True
                    buffer = buffer.split("<reply>")[1]
            
            if in_reply:
                if "</reply>" in buffer:
                    parts = buffer.split("</reply>")
                    yield parts[0]
                    buffer = parts[1]
                    in_reply = False
                else:
                    # yield everything except the last 8 chars (in case they are part of </reply>)
                    if len(buffer) > 8:
                        yield buffer[:-8]
                        buffer = buffer[-8:]
                        
        # Now process the remaining buffer for hints
        hints = []
        if "<hints>" in buffer and "</hints>" in buffer:
            hints_str = buffer.split("<hints>")[1].split("</hints>")[0].strip()
            try:
                import json
                hints = json.loads(hints_str)
            except:
                pass
                
        yield hints
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_conversation_agent.py
git commit -m "feat: conversation agent supports xml streaming output"
```

---

### Task 3: Backend SSE Endpoint

**Files:**
- Modify: `app/backend/app/main.py`

- [ ] **Step 1: Write the streaming endpoint**

In `app/backend/app/main.py`, add the `/api/sessions/turn/stream` endpoint:

```python
import json
from fastapi.responses import StreamingResponse

@app.post("/api/sessions/turn/stream")
def add_user_turn_stream(request: UserTurnRequest) -> StreamingResponse:
    repo = get_repository()
    
    # 1. Save user turn
    user_turn = repo.add_turn(request.session_id, "user", request.text)
    turns = repo.get_turns(request.session_id)
    
    # 2. Fetch context
    session = repo.get_session(request.session_id)
    profile = repo.get_latest_profile()
    plan_day = None
    if session.get("plan_day_id"):
        plan_day = repo.get_plan_day_by_id(session["plan_day_id"])
        
    objective = plan_day["objective"] if plan_day else "Practice speaking"
    user_level = profile["current_level"] if profile else "Intermediate"
    learning_goal = profile["learning_goal"] if profile else "Improve English"

    settings = load_settings()
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    
    def event_generator():
        # 3. Stream LLM reply
        generator = ConversationAgent(llm).reply_stream(
            topic=session["topic"],
            objective=objective,
            user_level=user_level,
            learning_goal=learning_goal,
            conversation=turns
        )
        
        full_reply = ""
        hints = []
        for item in generator:
            if isinstance(item, str):
                full_reply += item
                yield f"data: {json.dumps({'type': 'text', 'content': item})}\n\n"
            elif isinstance(item, list):
                hints = item
                
        # 4. Save assistant turn
        assistant_turn = repo.add_turn(request.session_id, "assistant", full_reply.strip())
        
        # 5. Generate Feedback
        feedback = InlineFeedbackAgent(llm).generate(request.text)
        saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
        
        # 6. Yield final metadata
        meta = {
            "type": "meta",
            "hints": hints,
            "inline_feedback": saved_feedback,
            "user_turn": user_turn,
            "assistant_turn": assistant_turn
        }
        yield f"data: {json.dumps(meta)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: Commit**

```bash
git add app/backend/app/main.py
git commit -m "feat: add SSE streaming endpoint for turns"
```

---

### Task 4: Frontend API and Streaming Client

**Files:**
- Modify: `app/frontend/src/api.ts`

- [ ] **Step 1: Add streaming fetch function**

In `app/frontend/src/api.ts`, add `sendUserTurnStream`:

```typescript
export async function sendUserTurnStream(
  sessionId: number,
  text: string,
  onTextChunk: (chunk: string) => void
): Promise<{
  user_turn: ConversationTurn;
  assistant_turn: ConversationTurn;
  inline_feedback: InlineFeedback[];
  hints: string[];
}> {
  const response = await fetch(`${API_BASE}/sessions/turn/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to send turn");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let meta: any = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || ""; // Keep the last incomplete part in the buffer
    
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
  
  if (!meta) throw new Error("Stream closed without metadata");
  return meta;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/api.ts
git commit -m "feat: add frontend api for sse streaming"
```

---

### Task 5: Frontend UI Real-time Rendering

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`

- [ ] **Step 1: Update `submitTurn` to use stream**

In `app/frontend/src/components/PracticeRoom.tsx`:

```tsx
// 1. Add import
import { startSession, playTTS, sendUserTurnStream } from "../api";

// 2. Update state to include a temporary streaming turn
  const [streamingReply, setStreamingReply] = useState<string | null>(null);

// 3. Update submitTurn
  async function submitTurn(text: string) {
    if (!session || !text.trim() || isSubmittingRef.current) return;
    
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setApiError("");
    setHints([]); // clear old hints
    
    // Add temporary user turn immediately for better UX
    const tempUserTurn: ConversationTurn = {
      id: Date.now(),
      session_id: session.id,
      turn_index: turns.length + 1,
      speaker: "user",
      text: text.trim(),
      created_at: new Date().toISOString()
    };
    setTurns((current) => [...current, tempUserTurn]);
    setTypedText("");
    setStreamingReply(""); // start stream
    
    try {
      const result = await sendUserTurnStream(
        session.id,
        text.trim(),
        (chunk) => setStreamingReply((prev) => (prev || "") + chunk)
      );
      
      // Stream done, replace temp turns with real ones
      setTurns((current) => {
        const withoutTemp = current.filter(t => t.id !== tempUserTurn.id);
        return [...withoutTemp, result.user_turn, result.assistant_turn];
      });
      setStreamingReply(null);
      setFeedback(result.inline_feedback);
      setHints(result.hints || []);
      
      playTTS(result.assistant_turn.text).catch(() => console.warn("TTS failed"));
    } catch {
      setApiError("Failed to send response.");
      setStreamingReply(null);
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }
```

- [ ] **Step 2: Render the streaming reply**

In the `chat-scroll` mapping, right after the `.map` loop:

```tsx
                {streamingReply !== null && (
                  <article className="message-row" key="streaming-turn">
                    <div className="message-avatar message-avatar-assistant" aria-hidden="true">C</div>
                    <div className="message-bubble message-bubble-assistant">
                      <p>{streamingReply}<span className="typing-cursor">▋</span></p>
                    </div>
                  </article>
                )}
```

Add CSS for `.typing-cursor` in `styles.css` (optional, but nice):
```css
.typing-cursor {
  animation: blink 1s step-end infinite;
  margin-left: 2px;
  color: #1f4ed8;
}
@keyframes blink { 50% { opacity: 0; } }
```

- [ ] **Step 3: Verify build and Commit**

Run: `cd app/frontend && npm run build`

```bash
git add app/frontend/src/components/PracticeRoom.tsx app/frontend/src/styles.css
git commit -m "feat: practice room uses streaming api for real-time text rendering"
```
