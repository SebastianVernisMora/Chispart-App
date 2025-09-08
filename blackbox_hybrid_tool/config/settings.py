"""
Pydantic-based configuration management for Chispart AI - Blackbox Hybrid Tool.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class AppSettings(BaseSettings):
    environment: str = Field("development", env="CHISPART_ENV")
    jwt_secret_key: str = Field("supersecretkey", env="CHISPART_JWT_SECRET")
    rate_limit_requests: int = Field(100, env="CHISPART_RATE_LIMIT")
    redis_url: Optional[str] = Field(None, env="CHISPART_REDIS_URL")
    models_config_path: str = Field("blackbox_hybrid_tool/config/models.json", env="CHISPART_MODELS_CONFIG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env file


settings = AppSettings()


def load_json_config(path: str) -> dict:
    """
    Load JSON config from the specified path, fallback to empty dict if not found.
    """
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


MODELS_CONFIG = load_json_config(settings.models_config_path)

"""
Usage:
    from blackbox_hybrid_tool.config.settings import settings, MODELS_CONFIG

    # Access environment-based config
    print(settings.environment)

    # Access loaded JSON config
    print(MODELS_CONFIG)
"""
