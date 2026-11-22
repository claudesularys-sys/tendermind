from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://tendermind:tendermind123@localhost:5432/tendermind"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Auth
    jwt_secret_key: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # Telegram
    telegram_bot_token: str = ""

    # App
    debug: bool = False

    # Crawler
    match_vector_threshold: float = 0.72
    crawler_interval_minutes: int = 30

    # SAM.gov
    sam_gov_api_key: str = ""

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
