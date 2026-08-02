from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_path: Path
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str | None
    planner_model: str
    chat_model: str
    jwt_secret: str
    jwt_expire_hours: int = 24
    refresh_token_expire_days: int = 7
    guest_token_expire_hours: int = 12
    tts_voice: str = "en-US-JennyNeural"
    tts_rate: str = "+0%"


def load_settings(dotenv_path: Path | None = None) -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path or project_root / ".env", override=False)
    database_path = Path(os.getenv("COACH_DB_PATH", project_root / "data" / "coach.sqlite"))

    # Fallback to LLM_MODEL if specific models aren't set for backward compatibility
    legacy_model = os.getenv("LLM_MODEL", "fake-local-coach")

    return Settings(
        database_path=database_path,
        llm_provider=os.getenv("LLM_PROVIDER", "fake"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        planner_model=os.getenv("PLANNER_MODEL", legacy_model),
        chat_model=os.getenv("CHAT_MODEL", legacy_model),
        jwt_secret=os.getenv("JWT_SECRET", "speakmate-jwt-secret-change-me"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "24")),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        guest_token_expire_hours=int(os.getenv("GUEST_TOKEN_EXPIRE_HOURS", "12")),
        tts_voice=os.getenv("TTS_VOICE", "en-US-JennyNeural"),
        tts_rate=os.getenv("TTS_RATE", "+0%"),
    )
