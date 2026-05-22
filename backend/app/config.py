from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Remote Job Hunter"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./data/jobs.db"

    scrape_interval_hours: int = 5
    scrape_enabled: bool = True
    request_delay_seconds: float = 1.5
    request_timeout_seconds: int = 30

    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    alert_email_to: str = ""

    # JWT Settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    
    slack_webhook_url: str = ""
    alerts_enabled: bool = True

    linkedin_api_key: str = ""
    linkedin_search_urls: str = ""
    greenhouse_board_tokens: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins

    @property
    def cors_allow_any_origin(self) -> bool:
        origins = self.cors_origin_list
        return len(origins) == 1 and origins[0] == "*"

    @property
    def greenhouse_tokens_list(self) -> List[str]:
        return [t.strip() for t in self.greenhouse_board_tokens.split(",") if t.strip()]

    @property
    def linkedin_url_list(self) -> List[str]:
        return [u.strip() for u in self.linkedin_search_urls.split(",") if u.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
