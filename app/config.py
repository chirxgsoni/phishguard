"""Configuration module for PhishGuard backend using pydantic-settings."""

import os
from typing import Optional
from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Supabase credentials
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_KEY: str = "your-service-role-key"  # Service role key ONLY, never public anon
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Encryption key for storing OAuth credentials securely (AES/Fernet)
    # Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: str = ""

    # LLM Settings (for Layer 4 Explainability & SOAR Agent)
    LLM_PROVIDER: str = "gemini"  # "gemini", "litellm", or "mock"
    GEMINI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-1.5-flash"

    # Google OAuth (for Gmail ingestion)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/connections/callback"

    # Safety limits
    MAX_REDIRECT_HOPS: int = 5
    URL_FETCH_TIMEOUT_SECONDS: float = 5.0
    MAX_UPLOAD_SIZE_MB: int = 10

    def get_token_encryption_key(self) -> bytes:
        """Return the Fernet key, falling back to a deterministic development key if empty."""
        if self.TOKEN_ENCRYPTION_KEY:
            return self.TOKEN_ENCRYPTION_KEY.encode()
        # Fallback for dev/testing so app boots smoothly even before .env is populated
        dev_key = b"A_DEV_SECRET_KEY_FOR_PHISHGUARD_32B="
        # Ensure 32 url-safe base64 bytes:
        import base64
        padded = base64.urlsafe_b64encode(b"phishguard_default_dev_secret_!"[:32].ljust(32, b"0"))
        return padded


# Global singleton settings instance
settings = Settings()
