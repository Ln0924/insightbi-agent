from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "InsightBI Agent"
    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: str = "development-only-secret"
    database_url: str = "sqlite:///./insightbi.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: Literal["deterministic", "openai_compatible"] = "deterministic"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    llm_small_model: str = "qwen-plus"
    llm_large_model: str = "qwen-max"
    sql_timeout_seconds: int = Field(8, ge=1, le=60)
    sql_max_rows: int = Field(1000, ge=1, le=10000)
    sql_cost_limit: int = Field(100000, ge=1)
    rate_limit_per_minute: int = Field(60, ge=1)
    max_agent_steps: int = Field(12, ge=3, le=30)
    max_sql_retries: int = Field(2, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()

