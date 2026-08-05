"""Application configuration via pydantic-settings.

All tunable analytics constants live here as named values (never inlined
magic numbers in the service layer) so they are easy to find, tune, and
reference from unit tests.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Connectivity ---
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "quiz_app"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Quiz-taking ---
    DEFAULT_QUIZ_LENGTH: int = 10
    ATTEMPT_FRESHNESS_MINUTES: int = 30

    # --- Learning Velocity Index weights ---
    LVI_WEIGHT_ACCURACY: float = 0.5
    LVI_WEIGHT_SPEED: float = 0.3
    LVI_WEIGHT_CONSISTENCY: float = 0.2

    # --- Question Difficulty Index weights ---
    QDI_WEIGHT_ACCURACY: float = 0.7
    QDI_WEIGHT_TIME: float = 0.3

    # --- Shrinkage ---
    SHRINKAGE_K: int = 10

    # --- Chapter/Subject Mastery weights ---
    MASTERY_WEIGHT_ACCURACY: float = 0.7
    MASTERY_WEIGHT_SPEED: float = 0.3

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
