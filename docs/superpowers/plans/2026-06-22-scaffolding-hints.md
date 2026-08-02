# Scaffolding and Hints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the AI into a "director" that provides structured scenario choices and hints, handles Chinglish gracefully, and lowers the cognitive load for speaking practice.

**Architecture:** 
1. The `ConversationAgent` prompt is updated to output JSON containing `reply` and `hints` arrays.
2. The `/api/sessions/turn` backend endpoint extracts the `reply` string for the database and passes `hints` to the frontend.
3. The `InlineFeedbackAgent` prompt is updated to explicitly provide full English translations for Chinglish inputs.
4. The frontend UI introduces a new "Hints" rendering area above the chat composer to display actionable ideas.

**Tech Stack:** Python, FastAPI, React, TypeScript, CSS

---

### Task 1: Update `ConversationAgent` Prompt and Output Parsing

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_conversation_agent.py`

- [ ] **Step 1: Update the failing test for `ConversationAgent`**

Modify `app/backend/tests/test_conversation_agent.py` to expect a dict return value:

```python
from app.agents import ConversationAgent
from app.llm import FakeLLMProvider
import json

class MockJSONConversationProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps({
            "reply": "Mock reply.",
            "hints": ["Hint 1", "Hint 2"]
        })

def test_conversation_agent_returns_dict():
    agent = ConversationAgent(MockJSONConversationProvider())
    result = agent.reply("Topic", "Obj", "Level", "Goal", [])
    assert isinstance(result, dict)
    assert result["reply"] == "Mock reply."
    assert len(result["hints"]) == 2
    assert result["hints"][0] == "Hint 1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: FAIL (returns string instead of dict)

- [ ] **Step 3: Write minimal implementation in `ConversationAgent.reply`**

In `app/backend/app/agents.py`, update `ConversationAgent.reply`:

```python
    def reply(self, topic: str, objective: str, user_level: str, learning_goal: str, conversation: list[dict[str, str]]) -> dict[str, object]:
        recent_turns = conversation[-20:] if len(conversation) > 20 else conversation
        user_prompt_turns = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in recent_turns)
        
        system_prompt = (
            "You are an expert English speaking coach acting as a roleplay director. "
            f"The user's current level is: '{user_level}'. Their ultimate goal is: '{learning_goal}'. "
            "Instructions:\n"
            "1. Adapt your vocabulary and sentence complexity based on the user's level.\n"
            "2. DO NOT ask open-ended questions like 'What do you want to practice next?'. Instead, drive the plot forward by introducing a specific scenario obstacle or giving the user a clear binary choice (e.g., 'Your bag is overweight. Do you want to pay the fee or take something out?').\n"
            "3. If the user speaks in a mix of Chinese and English (Chinglish), understand their intent and respond naturally in English.\n"
            "4. Output ONLY a valid JSON object with no markdown formatting. It must contain exactly two keys: "
            "'reply' (your spoken response as the coach/roleplay character) and "
            "'hints' (an array of 2-3 short strings in the user's native language providing ideas for what they could say next, e.g., ['💡 询问超重费用', '💡 表示拿几件衣服出来']).\n"
        )
        
        user_prompt = (
            f"Today's Topic: {topic}\n"
            f"Today's Objective: {objective}\n"
            "--- Conversation History ---\n"
            f"{user_prompt_turns}\n"
            "--- End History ---\n"
            "Provide your next JSON reply:"
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            import json
            data = json.loads(cleaned_response)
            return {
                "reply": data.get("reply", "Let's continue."),
                "hints": data.get("hints", [])
            }
        except json.JSONDecodeError:
            return {
                "reply": cleaned_response,
                "hints": []
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_conversation_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_conversation_agent.py
git commit -m "feat: conversation agent outputs JSON with hints and specific roleplay prompt"
```

---

### Task 2: Update `InlineFeedbackAgent` Prompt

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write the failing test**

In `app/backend/tests/test_agents.py`, add a test for Chinglish input:

```python
class MockChinglishFeedbackProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        assert "mix of Chinese and English" in system_prompt
        return json.dumps([
            {
                "feedback_type": "expression",
                "feedback_text": "Here is the full English expression."
            }
        ])

def test_inline_feedback_agent_handles_chinglish():
    agent = InlineFeedbackAgent(MockChinglishFeedbackProvider())
    feedback = agent.generate("I want to 靠窗的 seat.")
    assert len(feedback) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_agents.py::test_inline_feedback_agent_handles_chinglish -v`
Expected: FAIL (assertion error on system prompt contents)

- [ ] **Step 3: Write minimal implementation**

In `app/backend/app/agents.py`, update `InlineFeedbackAgent.generate`:

```python
    def generate(self, user_text: str) -> list[dict[str, str]]:
        system_prompt = (
            "You are an expert English speaking coach providing instant feedback. "
            "Analyze the user's input and provide corrections or better expressions. "
            "IMPORTANT: If the user's input contains Chinese or a mix of Chinese and English (Chinglish), "
            "you MUST provide the full, natural English expression for their intended meaning, categorized as an 'expression' feedback. "
            "Output ONLY a valid JSON array of objects, with no markdown formatting or extra text. "
            "Each object must have exactly these keys: 'feedback_type' (e.g. 'grammar', 'expression', 'pronunciation') "
            "and 'feedback_text' (the feedback message in the user's native language or English). "
            "If the user's input is perfect English and needs no feedback, return an empty array []."
        )
        user_prompt = f"User's input: '{user_text}'"
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            import json
            feedback = json.loads(cleaned_response)
            if not isinstance(feedback, list):
                return []
            return feedback
        except json.JSONDecodeError:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_agents.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: inline feedback agent explicitly handles chinglish"
```

---

### Task 3: Update `/api/sessions/turn` API Endpoint

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`
- Modify: `app/backend/app/llm.py` (Update FakeLLMProvider)

- [ ] **Step 1: Update `FakeLLMProvider` in `app/backend/app/llm.py`**

Modify `FakeLLMProvider.complete` to return a JSON string when acting as a ConversationAgent (so tests don't break):

```python
class FakeLLMProvider:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if "JSON array" in system_prompt and "feedback" in system_prompt.lower():
            return '[{"feedback_type": "grammar", "feedback_text": "Mock feedback."}]'
        elif "JSON array" in system_prompt:
            return '[{"topic": "Mock Topic", "scenario": "Mock Scenario", "objective": "Mock Obj"}]'
        elif "JSON object" in system_prompt and "hints" in system_prompt:
            return '{"reply": "Could you describe the user problem?", "hints": ["💡 Describe pain points", "💡 Mention impact"]}'
        return "Could you describe the user problem and the product impact in more detail?"
```

- [ ] **Step 2: Update the failing test in `test_api.py`**

In `app/backend/tests/test_api.py` (inside `test_session_turn_and_review_flow`), add an assertion for hints:

```python
        # ... existing test code ...
        assert turn.status_code == 200
        assert "assistant_turn" in turn.json()
        assert "hints" in turn.json()
        assert len(turn.json()["hints"]) > 0
        assert turn.json()["hints"][0] == "💡 Describe pain points"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest app/backend/tests/test_api.py -v`
Expected: FAIL (API returns string `assistant_text` or `hints` is missing)

- [ ] **Step 4: Write minimal implementation in `main.py`**

In `app/backend/app/main.py`, inside `add_user_turn`:

```python
    # 3. Call LLM
    settings = load_settings()
    llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    
    agent_response = ConversationAgent(llm).reply(
        topic=session["topic"],
        objective=objective,
        user_level=user_level,
        learning_goal=learning_goal,
        conversation=turns
    )
    
    assistant_text = agent_response["reply"]
    hints = agent_response["hints"]
    
    assistant_turn = repo.add_turn(request.session_id, "assistant", assistant_text)
    
    # 4. Feedback
    feedback = InlineFeedbackAgent(llm).generate(request.text)
    saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
    
    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
        "hints": hints,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest app/backend/tests/test_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/main.py app/backend/app/llm.py app/backend/tests/test_api.py
git commit -m "feat: turn api returns structured hints and extracts reply"
```

---

### Task 4: Frontend API Types

**Files:**
- Modify: `app/frontend/src/api.ts`

- [ ] **Step 1: Update API return types**

In `app/frontend/src/api.ts`, update `sendUserTurn` signature to include hints:

```typescript
export async function sendUserTurn(
  sessionId: number,
  text: string
): Promise<{
  user_turn: ConversationTurn;
  assistant_turn: ConversationTurn;
  inline_feedback: InlineFeedback[];
  hints: string[];
}> {
  const response = await fetch(`${API_BASE}/sessions/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  if (!response.ok) {
    throw new Error("Failed to send turn");
  }
  return response.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/api.ts
git commit -m "feat: frontend api supports hints return type"
```

---

### Task 5: Frontend UI (PracticeRoom Hints)

**Files:**
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/styles.css`

- [ ] **Step 1: Add CSS for hints**

In `app/frontend/src/styles.css`:

```css
.hints-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hint-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #155eef;
  font-size: 0.85rem;
  font-weight: 500;
  border: 1px solid #d1e0ff;
  cursor: default;
  transition: all 0.2s ease;
}

.hint-pill:hover {
  background: #d1e0ff;
}
```

- [ ] **Step 2: Add hints to `PracticeRoom.tsx` state and render**

In `app/frontend/src/components/PracticeRoom.tsx`:

Add `hints` state:
```tsx
  const [feedback, setFeedback] = useState<InlineFeedback[]>([]);
  const [hints, setHints] = useState<string[]>([]);
  const [typedText, setTypedText] = useState("");
```

Clear hints on initial boot and clear them when starting submission (optional, but good UX):
```tsx
    // in boot()
    setSession(result.session);
    setTurns(result.turns);
    setHints([]); // reset hints on load
```

Update `submitTurn`:
```tsx
      setTurns((current) => [...current, result.user_turn, result.assistant_turn]);
      setFeedback(result.inline_feedback);
      setHints(result.hints || []);
      setTypedText("");
```

Render hints above the `textarea` in `.chat-composer`:
```tsx
            <div className="chat-composer" aria-label="Chat composer">
              {hints.length > 0 && (
                <div className="hints-container">
                  {hints.map((hint, idx) => (
                    <span key={idx} className="hint-pill">{hint}</span>
                  ))}
                </div>
              )}
              <textarea
```

- [ ] **Step 3: Verify build**

Run: `cd app/frontend && npm run build`
Expected: Successful build

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/PracticeRoom.tsx app/frontend/src/styles.css
git commit -m "feat: render hints above chat composer in practice room"
```
