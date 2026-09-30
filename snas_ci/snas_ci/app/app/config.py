"""Configuration centrale du projet SNAS-CI."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SNAS-CI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Base de données
    DATABASE_URL: str = "sqlite:///./snas_ci.db"

    # Sécurité
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Règles métier
    SEUIL_ASSIDUITE: float = 85.0
    DELAI_JUSTIFICATIF_HEURES: int = 72
    DELAI_REMPLACEMENT_HEURES: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instance unique utilisable partout dans le projet
settings = Settings()
