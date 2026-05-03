"""Environment-backed configuration for Silicon Agents."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    app_name: str = "Silicon Agents"
    app_version: str = "0.1.0"
    log_level: str = Field(default_factory=lambda: os.getenv("SA_LOG_LEVEL", "INFO"))
    host: str = Field(default_factory=lambda: os.getenv("SA_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("SA_PORT", "8000")))
    api_key: str = Field(default_factory=lambda: os.getenv("SA_API_KEY", "local-dev-key"))
    pilot_access_token: str = Field(default_factory=lambda: os.getenv("PILOT_ACCESS_TOKEN", ""))
    pilot_cookie_name: str = Field(default_factory=lambda: os.getenv("SA_PILOT_COOKIE_NAME", "sa_pilot_access"))
    llm_primary: str = Field(default_factory=lambda: os.getenv("SA_LLM_PRIMARY", "gemini"))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))
    gemini_fallback_model: str = Field(default_factory=lambda: os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash"))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    db_path: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", os.getenv("SA_DB_PATH", "./silicon_agents.db")))
    max_report_chars: int = Field(default_factory=lambda: int(os.getenv("SA_MAX_REPORT_CHARS", "50000")))
    max_csv_chars: int = Field(default_factory=lambda: int(os.getenv("SA_MAX_CSV_CHARS", "100000")))
    max_decisions: int = Field(default_factory=lambda: int(os.getenv("SA_MAX_DECISIONS", "20")))
    stream_timeout_s: int = Field(default_factory=lambda: int(os.getenv("SA_STREAM_TIMEOUT_S", "120")))
    bin1_min_freq_ghz: float = Field(default_factory=lambda: float(os.getenv("SA_BIN1_MIN_FREQ_GHZ", "3.75")))
    bin1_max_leakage_ua: float = Field(default_factory=lambda: float(os.getenv("SA_BIN1_MAX_LEAKAGE_UA", "200")))
    bin2_min_freq_ghz: float = Field(default_factory=lambda: float(os.getenv("SA_BIN2_MIN_FREQ_GHZ", "3.0")))
    bin3_min_freq_ghz: float = Field(default_factory=lambda: float(os.getenv("SA_BIN3_MIN_FREQ_GHZ", "2.0")))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
