from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    PROJECT_NAME: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str
    DB_ECHO: bool = False
    MAIL_USERNAME : str
    MAIL_PASSWORD : str
    MAIL_FROM : str
    MAIL_SERVER : str
    MAIL_PORT : int 
    # Güvenli varsayılanlar; yerel .env dosyası geliştirme değerlerini geçersiz kılabilir.
    MAIL_USE_CREDENTIALS: bool = True
    MAIL_VALIDATE_CERTS: bool = True
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    FRONTEND_BASE_URL: str
    REFRESH_COOKIE_SECURE: bool = True
    REFRESH_COOKIE_SAMESITE: Literal['lax', 'strict', 'none'] = "lax"
    REFRESH_COOKIE_DOMAIN: str | None = None
    PASSWORD_RESET_EXPIRE_MINUTES : int = 15

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings() # type: ignore
