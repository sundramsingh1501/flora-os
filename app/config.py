"""
Flora OS — Central Configuration
All settings loaded from environment variables via pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    app_base_url: str = "http://localhost:8501"
    app_name: str = "Flora OS"
    app_version: str = "1.0.0"

    # Database
    database_url: str = "sqlite:///./flora_os.db"

    # Encryption
    encryption_key: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8501"

    @property
    def google_redirect_uri_clean(self) -> str:
        """Always strip trailing slash to ensure exact match with Google Cloud Console."""
        return self.google_redirect_uri.rstrip("/")

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8501"

    # AI
    gemini_api_key: str = ""

    # News
    news_api_key: str = ""

    # Weather
    openweather_api_key: str = ""

    # Jobs
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Market
    alpha_vantage_key: str = ""

    # SMTP (for daily email brief delivery)
    smtp_email: str = ""       # sender Gmail address
    smtp_password: str = ""    # Gmail App Password (not your real password)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587

    # Session
    session_cookie_max_age: int = 2592000  # 30 days

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
