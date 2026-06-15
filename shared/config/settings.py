from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str = "mock_token"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    tavily_api_key: str = ""
    database_url: str = "postgresql://user:pass@postgres:5432/content_db"
    redis_url: str = "redis://redis:6379"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()\n