from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration loaded from the process environment and `.env`."""

    supabase_url: str = ""
    supabase_key: str = ""
    openai_api_key: str = ""
    llm_model: str = Field(default="gpt-4o-mini")
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    max_prompt_tokens: int = Field(default=8000, gt=0)
    embedding_model: str = "text-embedding-3-small"
    # Must match semantic_cache.embedding in supabase/migrations.
    embedding_dimensions: int = Field(default=1536, gt=0)
    cache_similarity_threshold: float = Field(default=0.85, gt=0, lt=1)
    public_base_url: str = "http://127.0.0.1:8000"
    admin_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_key.strip())

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
