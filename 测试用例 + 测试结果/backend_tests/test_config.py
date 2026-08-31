from app.config import load_settings


def test_load_settings_reads_dotenv_file(tmp_path, monkeypatch):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=openrouter",
                "LLM_API_KEY=test-key",
                "LLM_BASE_URL=https://openrouter.ai/api/v1",
                "PLANNER_MODEL=deepseek/deepseek-v4-pro",
                "CHAT_MODEL=deepseek/deepseek-v4-flash",
            ]
        )
    )
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("PLANNER_MODEL", raising=False)
    monkeypatch.delenv("CHAT_MODEL", raising=False)

    settings = load_settings(dotenv_path=dotenv_path)

    assert settings.llm_provider == "openrouter"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_base_url == "https://openrouter.ai/api/v1"
    assert settings.planner_model == "deepseek/deepseek-v4-pro"
    assert settings.chat_model == "deepseek/deepseek-v4-flash"

def test_load_dual_models(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL", "deepseek/deepseek-v4-pro")
    monkeypatch.setenv("CHAT_MODEL", "deepseek/deepseek-v4-flash")
    
    settings = load_settings()
    assert settings.planner_model == "deepseek/deepseek-v4-pro"
    assert settings.chat_model == "deepseek/deepseek-v4-flash"
