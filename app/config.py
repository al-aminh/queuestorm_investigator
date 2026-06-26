from dataclasses import dataclass
import os


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "production")
    use_llm: bool = _to_bool(os.getenv("USE_LLM", "false"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))


def get_settings() -> Settings:
    return Settings()
