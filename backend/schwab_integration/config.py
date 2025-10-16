"""Configuration management for Schwab API integration."""

from pydantic_settings import BaseSettings
from pydantic import Field


class SchwabConfig(BaseSettings):
    """Schwab API configuration."""
    
    app_key: str = Field(..., description="Schwab API application key")
    app_secret: str = Field(..., description="Schwab API application secret")
    callback_url: str = Field(
        default="https://127.0.0.1:8182/",
        description="OAuth callback URL"
    )
    token_path: str = Field(
        default="config/schwab_token.json",
        description="Path to store OAuth tokens"
    )
    account_id: str = Field(default="", description="Schwab account ID")
    base_url: str = Field(
        default="https://api.schwab.com",
        description="Schwab API base URL"
    )
    paper: bool = Field(default=True, description="Use paper trading")
    
    class Config:
        env_file = ".env"
        env_prefix = "SCHWAB_"
        extra = "ignore"  # Ignore extra env variables


class SupabaseConfig(BaseSettings):
    """Supabase configuration."""
    
    url: str = Field(..., description="Supabase project URL")
    service_role_key: str = Field(..., description="Supabase service role key")
    
    class Config:
        env_file = ".env"
        env_prefix = "SUPABASE_"
        extra = "ignore"  # Ignore extra env variables


class AppConfig(BaseSettings):
    """Application configuration."""
    
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Data download settings
    default_ticker: str = Field(default="QQQ", description="Default ticker to download")
    lookback_days: int = Field(default=5, description="Days of historical data to fetch")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env variables

