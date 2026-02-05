"""
Configuration Module
====================
Centralized configuration using Pydantic Settings.
Loads from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # API Configuration
    api_base_url: str = "http://localhost:8000"
    oauth_client_id: str = "energy_trading_client"
    oauth_client_secret: str = "super_secret_key_2024"
    
    # Token refresh settings
    token_refresh_margin_seconds: int = 300  # Refresh 5 min before expiry
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "energy_user"
    postgres_password: str = "energy_secret_2024"
    postgres_db: str = "energy_trading"
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # ETL Configuration
    etl_poll_interval_seconds: int = 300  # 5 minutes
    etl_max_retries: int = 3
    etl_retry_delay_seconds: int = 5
    
    # Logging
    log_level: str = "INFO"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
