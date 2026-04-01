from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, ValidationInfo
from typing import List, Union, Literal
from pathlib import Path

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: Literal["development", "pre", "production"] = "development"

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
            raise ValueError(
                f"SEGURIDAD: {info.field_name} no está configurado. "
                "Genera uno con: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        if len(v) < 32:
            raise ValueError(
                f"SEGURIDAD: {info.field_name} tiene menos de 32 caracteres. "
                "Se recomienda usar: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return v

    @field_validator('ENCRYPTION_MASTER_KEY')
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Valida la clave maestra de encriptación"""
        if not v:
            raise ValueError(
                "SEGURIDAD: ENCRYPTION_MASTER_KEY no está configurado. "
                "Genera uno con: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                "SEGURIDAD: ENCRYPTION_MASTER_KEY tiene menos de 32 caracteres. "
                "Se recomienda usar: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOGS_DIR: str = "../logsBackend"  # Relativo a /app en Docker, será /logsBackend
    LOG_ROTATION_SIZE_MB: int = 10
    LOG_BACKUP_COUNT: int = 5
    
    # Database
    DATABASE_URL_LOCALHOST: str = ""
    DATABASE_URL_PRE: str = ""  # For PRE environment (can be same as DEV or separate)
    DATABASE_URL_PROD: str = ""
    DB_POOL_SIZE: int = 5
    DB_POOL_OVERFLOW: int = 10
    
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
    CORS_MAX_AGE: int = 3600  # Cache de CORS en segundos
    
    # Environment-specific URLs
    FRONTEND_URL: str = "http://localhost:4200"  # URL del frontend según entorno
    BACKEND_URL: str = "http://localhost:8000"  # URL del backend según entorno
    ALLOWED_HOSTS: Union[str, List[str]] = "localhost,127.0.0.1"  # Hosts permitidos para TrustedHostMiddleware
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Login-specific rate limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 15

    # Gemini API Quota (per user per day)
    GEMINI_DAILY_LIMIT_PER_USER: int = 20

    @property
    def DATABASE_URL(self) -> str:
        """Selecciona la URL de base de datos según el entorno"""
        if self.ENVIRONMENT == "production":
            return self.DATABASE_URL_PROD
        elif self.ENVIRONMENT == "pre":
            return self.DATABASE_URL_PRE
        return self.DATABASE_URL_LOCALHOST
    
    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Valida que el entorno sea válido"""
        valid_environments = ["development", "pre", "production"]
        if v not in valid_environments:
            raise ValueError(
                f"ENVIRONMENT debe ser uno de: {', '.join(valid_environments)}. "
                f"Valor recibido: {v}"
            )
        return v
    
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
    
    @field_validator('ALLOWED_HOSTS')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from comma-separated string to list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()