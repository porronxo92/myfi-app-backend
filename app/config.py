from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, ValidationInfo
from typing import List, Union
from pathlib import Path
import warnings

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"  # "development" or "production"

    # Security & JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Refresh Tokens
    REFRESH_TOKEN_SECRET_KEY: str = ""
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Encryption - PSD2 Compliance
    ENCRYPTION_MASTER_KEY: str = ""
    ENCRYPTION_KEY_VERSION: int = 1
    
    # ============================================
    # VALIDACIÓN DE SECRETS (Seguridad)
    # ============================================
    
    @field_validator('JWT_SECRET_KEY', 'REFRESH_TOKEN_SECRET_KEY')
    @classmethod
    def validate_jwt_secrets(cls, v: str, info: ValidationInfo) -> str:
        """Valida que los secrets de JWT sean suficientemente seguros"""
        if not v:
            warnings.warn(
                f"⚠️ SEGURIDAD: {info.field_name} no está configurado. "
                "La aplicación no funcionará correctamente.",
                UserWarning
            )
            return v
        
        if len(v) < 32:
            warnings.warn(
                f"⚠️ SEGURIDAD: {info.field_name} tiene menos de 32 caracteres. "
                "Se recomienda usar: python -c 'import secrets; print(secrets.token_urlsafe(48))'",
                UserWarning
            )
        
        return v
    
    @field_validator('ENCRYPTION_MASTER_KEY')
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Valida la clave maestra de encriptación"""
        if v and len(v) < 32:
            warnings.warn(
                "⚠️ SEGURIDAD: ENCRYPTION_MASTER_KEY tiene menos de 32 caracteres. "
                "Se recomienda usar: python -c 'import secrets; print(secrets.token_urlsafe(32))'",
                UserWarning
            )
        return v
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOGS_DIR: str = "../logsBackend"  # Relativo a /app en Docker, será /logsBackend
    LOG_ROTATION_SIZE_MB: int = 10
    LOG_BACKUP_COUNT: int = 5
    
    # Database
    DATABASE_URL_LOCALHOST: str = ""
    DATABASE_URL_PROD: str = ""
    
    # LLM Configuration
    GEMINI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.0-flash"
    
    # Stock Market APIs
    # Finnhub API (Prioridad 1 - 60 llamadas/minuto)
    FINNHUB_API_KEY: str = ""
    FINNHUB_MAX_CALLS_PER_MINUTE: int = 60
    
    # Alpha Vantage API (Fallback - 25 llamadas/día)
    ALPHA_VANTAGE_API_KEY: str = ""
    ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co/query"
    ALPHA_VANTAGE_MAX_CALLS_PER_DAY: int = 25
    
    # Brandfetch API (Stock Logos)
    BRANDFETCH_CLIENT_ID: str = ""
    
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