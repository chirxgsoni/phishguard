"""Cryptographic and Authentication helpers for PhishGuard."""

import json
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
import jwt
from app.config import settings


class SecurityService:
    """Handles symmetric token encryption and Supabase JWT verification."""

    def __init__(self):
        key = settings.get_token_encryption_key()
        self._fernet = Fernet(key)

    def encrypt_json(self, payload: Dict[str, Any]) -> str:
        """Encrypt a Python dictionary into a safe base64 Fernet string."""
        serialized = json.dumps(payload).encode("utf-8")
        encrypted = self._fernet.encrypt(serialized)
        return encrypted.decode("utf-8")

    def decrypt_json(self, token_str: str) -> Dict[str, Any]:
        """Decrypt a Fernet encrypted string back into a Python dictionary."""
        try:
            decrypted = self._fernet.decrypt(token_str.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, Exception) as exc:
            raise ValueError(f"Failed to decrypt credentials: {str(exc)}") from exc

    def verify_supabase_jwt(self, token: str) -> Dict[str, Any]:
        """Validate and decode a Supabase JWT access token."""
        try:
            if settings.SUPABASE_JWT_SECRET:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
            else:
                # In development/test mode without a configured secret, decode payload without signature verification
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},
                )

            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Token missing user ID ('sub') claim")

            return {
                "id": user_id,
                "email": payload.get("email", ""),
                "role": payload.get("role", "authenticated"),
                "app_metadata": payload.get("app_metadata", {}),
                "user_metadata": payload.get("user_metadata", {}),
            }
        except Exception as exc:
            raise ValueError(f"Invalid or expired JWT token: {str(exc)}") from exc


security_service = SecurityService()
