"""
Configuration management for the Curacel Claims QA Service.
Handles environment variables, API keys, and application settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # App settings
    app_name: str = "Curacel Claims QA Service"
    version: str = "1.0.0"
    debug: bool = False
    
    # API settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Gemini Vision API (you'll need to set this)
    gemini_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
