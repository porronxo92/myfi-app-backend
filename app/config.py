from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
from pathlib import Path

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "production"  # "development" or "production"

    # Security & JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Refresh Tokens
    REFRESH_TOKEN_SECRET_KEY: str = ""
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOGS_DIR: Path = Path("../logsBackend")
    LOG_ROTATION_SIZE_MB: int = 10
    LOG_BACKUP_COUNT: int = 5
    
    # Database
    DATABASE_URL_LOCALHOST: str = ""
    DATABASE_URL_PROD: str = ""
    
    # LLM Configuration
    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.0-flash"
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: Union[str, List[str]] = "pdf,xlsx,csv,txt"
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:4200,http://localhost:3000"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Login-specific rate limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 15

    @property
    def DATABASE_URL(self) -> str:
        if self.ENVIRONMENT == "production":
            return self.DATABASE_URL_PROD
        return self.DATABASE_URL_LOCALHOST
    
    @field_validator('ALLOWED_EXTENSIONS')
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(',')]
        return v
    
    @field_validator('CORS_ORIGINS')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()