from pydantic import BaseSettings, Field, SecretStr, AnyHttpUrl


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: AnyHttpUrl = Field(..., description="Supabase project URL")
    SUPABASE_KEY: SecretStr = Field(..., description="Supabase anon/service key")

    # Telegram
    TELEGRAM_BOT_TOKEN: SecretStr = Field(..., description="Telegram bot token")
    TELEGRAM_CHAT_ID: str = Field(..., description="Telegram chat id")

    # Gupy
    GUPY_COOKIE: SecretStr = Field(
        ...,
        description="JWT do cookie candidate_secure_token da Gupy",
    )

    # App
    LOG_LEVEL: str = Field("INFO", description="Logging level")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
