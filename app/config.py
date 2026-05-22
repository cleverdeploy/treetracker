from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    session_secret: str
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_url: str = "http://localhost:8000/auth/callback"
    anthropic_api_key: str = ""
    admin_emails: str = ""
    photos_dir: str = "./data/photos"
    base_url: str = "http://localhost:8000"

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
