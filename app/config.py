from __future__ import annotations

import os
import math
from dataclasses import dataclass


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(0, value)


@dataclass(frozen=True)
class Settings:
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip() or "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = _env_float("LLM_TIMEOUT_SECONDS", 12.0)
    llm_max_retries: int = _env_int("LLM_MAX_RETRIES", 1)


settings = Settings()
