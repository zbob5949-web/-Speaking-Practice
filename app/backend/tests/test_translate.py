import pytest
from fastapi import HTTPException
from app.services import translate
from app.llm import FakeLLMProvider, OpenRouterProvider


def test_translation_uses_provider_and_timeout(monkeypatch):
    calls = []
    def post(url, headers, body, timeout):
        calls.append((body, timeout))
        return {"choices": [{"message": {"content": "你好。"}}]}
    provider = OpenRouterProvider("test", "https://example.test", "test", post_json=post)
    monkeypatch.setattr(translate.deps, "create_llm_provider", lambda **kwargs: provider)
    assert translate.translate("Hello.")["translation_zh"] == "你好。"
    assert calls[0][1] == 10.0
    assert calls[0][0]["messages"][1]["content"] == "Hello."


def test_translation_failure_is_explicit_and_retried(monkeypatch):
    class Unavailable:
        calls = 0
        def complete(self, **kwargs):
            self.calls += 1
            raise TimeoutError()
    provider = Unavailable()
    monkeypatch.setattr(translate.deps, "create_llm_provider", lambda **kwargs: provider)
    with pytest.raises(HTTPException) as error:
        translate.translate("Hello.")
    assert error.value.status_code == 503
    assert provider.calls == 2


def test_offline_mode_does_not_return_an_unrelated_english_reply(monkeypatch):
    monkeypatch.setattr(translate.deps, "create_llm_provider", lambda **kwargs: FakeLLMProvider())
    with pytest.raises(HTTPException) as error:
        translate.translate("Hello.")
    assert error.value.status_code == 503
