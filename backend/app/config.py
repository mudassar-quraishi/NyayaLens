"""NyayaLens backend configuration — all settings from environment."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # --- LLM ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")

    # --- Demo mode ---
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")

    # --- Database ---
    database_url: str = Field(
        default="sqlite:///./nyayalens.db", alias="DATABASE_URL"
    )

    # --- Session ---
    session_expiry_hours: int = Field(default=24, alias="SESSION_EXPIRY_HOURS")

    # --- Concurrency ---
    max_concurrent_llm_calls: int = Field(
        default=4, alias="MAX_CONCURRENT_LLM_CALLS"
    )

    # --- Paths ---
    samples_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "samples"
    )
    fixtures_dir: Path = Field(
        default=Path(__file__).resolve().parent / "fixtures"
    )
    jurisdiction_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent / "jurisdiction"
    )

    # --- Embedding model ---
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def llm_provider(self) -> str:
        """Detect which LLM provider to use based on available keys and model name."""
        model = self.llm_model.lower()
        if self.groq_api_key or model.startswith("llama") or model.startswith("groq") or model.startswith("mixtral") or "groq" in model:
            return "groq"
        if model.startswith("claude") or model.startswith("anthropic"):
            return "anthropic"
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "anthropic"
        return "groq" if self.groq_api_key else "gemini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
