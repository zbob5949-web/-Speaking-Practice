from app.llm import OpenRouterProvider, create_llm_provider


def test_openrouter_provider_sends_chat_completion_request():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": "Could you explain the product impact more clearly?"
                    }
                }
            ]
        }

    provider = OpenRouterProvider(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324:free",
        post_json=fake_post,
    )

    reply = provider.complete("system prompt", "user prompt")

    assert reply == "Could you explain the product impact more clearly?"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "deepseek/deepseek-chat-v3-0324:free"
    assert captured["json"]["messages"][0] == {"role": "system", "content": "system prompt"}
    assert captured["json"]["messages"][1] == {"role": "user", "content": "user prompt"}


def test_openrouter_provider_requests_json_object_response_for_object_prompts():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    provider = OpenRouterProvider(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v4-flash",
        post_json=fake_post,
    )

    provider.complete("必须输出合法 JSON 对象，不要 markdown。", "user prompt")

    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_openrouter_provider_does_not_force_json_object_for_array_prompts():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return {"choices": [{"message": {"content": "[]"}}]}

    provider = OpenRouterProvider(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v4-flash",
        post_json=fake_post,
    )

    provider.complete("只输出一个合法的 JSON 数组。", "user prompt")

    assert "response_format" not in captured["json"]


def fake_post_json_stream(url, headers, json_data, timeout):
    yield {"choices": [{"delta": {"content": "Hello"}}]}
    yield {"choices": [{"delta": {"content": " world!"}}]}

def test_openrouter_stream_complete():
    provider = OpenRouterProvider("fake_key", "http://fake.com", "fake_model", post_json_stream=fake_post_json_stream)
    chunks = list(provider.stream_complete("system", "user"))
    assert chunks == ["Hello", " world!"]

def test_create_llm_provider_defaults_to_fake_without_api_key():
    provider = create_llm_provider(
        provider_name="openrouter",
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat-v3-0324:free",
    )

    assert provider.complete("system", "user").startswith("Could you")
