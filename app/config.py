# we use use pydantic-settings to load GITHUB_APP_ID, 
# GITHUB_PRIVATE_KEY_PATH, GITHUB_WEBHOOK_SECRET and REDIS_URL to access them from anywhere.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GITHUB_APP_ID: int
    GITHUB_PRIVATE_KEY_PATH: str
    GITHUB_WEBHOOK_SECRET: str
    REDIS_URL: str
    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()


# access these values from anywhere
# example:

# from config import settings
# from pathlib import Path

# app_id = settings.GITHUB_APP_ID
# private_key = Path(settings.GITHUB_PRIVATE_KEY_PATH).read_text()
# redis_url = settings.REDIS_URL