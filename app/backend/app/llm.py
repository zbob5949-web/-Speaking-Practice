from typing import Any, Callable, Protocol, Iterator
import json

import httpx

from app.context import current_user_id


class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        ...


class FakeLLMProvider:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        prompt_lower = system_prompt.lower()
        asks_for_json_array = "json array" in prompt_lower or "json 数组" in prompt_lower
        asks_for_feedback = "feedback_type" in prompt_lower or "correction" in prompt_lower
        asks_for_plan = all(key in prompt_lower for key in ("topic", "scenario", "objective"))
        asks_for_reply = "reply" in prompt_lower and "hints" in prompt_lower
        asks_for_lesson_pack = "lesson pack" in prompt_lower or "材料包" in system_prompt

        if asks_for_json_array and asks_for_feedback:
            return '[{"feedback_type": "correction", "feedback_text": "show me -> could you show me -> 用疑问句请求更自然。"}, {"feedback_type": "guidance", "feedback_text": "下一句练习询问价格、库存或对比选项。"}]'
        elif asks_for_json_array and asks_for_plan:
            return (
                '[{"topic": "Mock Topic", "scenario": "Mock Scenario", "objective": "Mock Obj", '
                '"skill_focus": "Functional speaking", '
                '"communicative_task": "Complete a practical speaking task.", '
                '"target_functions": ["explain the situation", "ask a follow-up question", "confirm the next step"], '
                '"success_criteria": ["Use clear sentences", "Ask one relevant question", "Respond to the NPC"], '
                '"brief_seed": "Create a practical role-play lesson pack for this speaking scenario."}]'
            )
        elif asks_for_lesson_pack:
            return (
                '{"title": "Mock Topic", '
                '"user_visible_goal": "Practice a practical speaking task.", '
                '"npc_role": "NPC", '
                '"scenario_setup": "Mock Scenario", '
                '"conversation_objective": "Mock Obj", '
                '"lesson_focus": "Functional speaking", '
                '"task_steps": ["Explain the situation", "Ask one follow-up question"], '
                '"target_expressions": ['
                '{"expression": "Could you help me with this?", "meaning_zh": "你能帮我处理这个吗？", '
                '"example": "Could you help me with this booking?", "when_to_use": "asking for help politely"}'
                '], '
                '"sentence_frames": ["I need help with...", "Could you please...?"], '
                '"model_dialogue": ["NPC: How can I help?", "Learner: Could you help me with this?"], '
                '"common_mistakes": ['
                '{"mistake": "Help me this.", "better": "Could you help me with this?", "reason_zh": "help 后需要 with this 表达处理某事。"}'
                '], '
                '"rubric": ["Use a clear request", "Respond to the NPC"], '
                '"stretch_goal": "Add one extra detail."}'
            )
        elif asks_for_reply:
            return '{"reply": "Could you describe the user problem?", "hints": ["Describe pain points", "Mention impact"]}'
        return "Could you describe the user problem and the product impact in more detail?"

    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        yield '{\n  "hints": ["Use \\"reply\\""],\n  "reply": "Could you describe the user problem?"\n}'


PostJson = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]
PostJsonStream = Callable[[str, dict[str, str], dict[str, Any], float], Iterator[dict[str, Any]]]


def default_post_json(url: str, headers: dict[str, str], json: dict[str, Any], timeout: float) -> dict[str, Any]:
    response = httpx.post(url, headers=headers, json=json, timeout=timeout)
    response.raise_for_status()
    return response.json()


def default_post_json_stream(url: str, headers: dict[str, str], json_data: dict[str, Any], timeout: float) -> Iterator[dict[str, Any]]:
    with httpx.stream("POST", url, headers=headers, json=json_data, timeout=timeout) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue


class OpenRouterProvider:
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

    def complete(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> str:
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "thinking": {"type": "disabled"},
        }
        uid = current_user_id.get()
        if uid:
            request_body["user_id"] = uid
        prompt_lower = system_prompt.lower()
        asks_json_object = "json object" in prompt_lower or "json 对象" in prompt_lower
        asks_json_array = "json array" in prompt_lower or "json 数组" in prompt_lower
        if asks_json_object and not asks_json_array:
            request_body["response_format"] = {"type": "json_object"}

        data = self.post_json(
            f"{self.base_url}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "SpeakMate Agent",
            },
            request_body,
            timeout,
        )
        return data["choices"][0]["message"]["content"].strip()

    def stream_complete(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "stream": True,
            "max_tokens": 800,
            "thinking": {"type": "disabled"},
        }
        uid = current_user_id.get()
        if uid:
            request_body["user_id"] = uid
        stream = self.post_json_stream(
            f"{self.base_url}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "SpeakMate Agent",
            },
            request_body,
            30.0,
        )
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content


def create_llm_provider(
    provider_name: str,
    api_key: str | None,
    base_url: str | None,
    model: str,
) -> LLMProvider:
    if provider_name in ("openrouter", "deepseek") and api_key:
        return OpenRouterProvider(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
            model=model,
        )
    return FakeLLMProvider()
