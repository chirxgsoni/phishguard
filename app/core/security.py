"""Cryptographic and Authentication helpers for PhishGuard."""

import json
import os
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
import jwt
from app.config import settings


class SecurityService:
    """Handles symmetric token encryption and Supabase JWT verification."""

    def __init__(self):
        key = settings.get_token_encryption_key()
        self._fernet = Fernet(key)
        self._jwks_client: Optional[jwt.PyJWKClient] = None
        self._local_jwk_set: Optional[jwt.PyJWKSet] = None
        self._init_jwks()

    def _init_jwks(self):
        """Initialize local JWKS and remote JWKS client if configured."""
        raw_jwks = getattr(settings, "SUPABASE_JWKS", None) or ""
        # Handle case where user pasted JWKS JSON into SUPABASE_JWT_SECRET
        if not raw_jwks and getattr(settings, "SUPABASE_JWT_SECRET", None) and settings.SUPABASE_JWT_SECRET.strip().startswith("{"):
            raw_jwks = settings.SUPABASE_JWT_SECRET

        if not raw_jwks and os.path.exists("jwt.json"):
            try:
                with open("jwt.json", "r", encoding="utf-8") as f:
                    raw_jwks = f.read()
            except Exception:
                pass

        if raw_jwks:
            try:
                if os.path.exists(raw_jwks):
                    with open(raw_jwks, "r", encoding="utf-8") as f:
                        raw_jwks = f.read()
                self._local_jwk_set = jwt.PyJWKSet.from_json(raw_jwks)
            except Exception:
                pass

        # Remote JWKS endpoint from Supabase URL
        if getattr(settings, "SUPABASE_URL", None) and not settings.SUPABASE_URL.startswith("https://your-project"):
            jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
            try:
                self._jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)
            except Exception:
                pass

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
            unverified_header = jwt.get_unverified_header(token)
            alg = unverified_header.get("alg", "HS256")
            kid = unverified_header.get("kid")

            payload = None

            # 1. Asymmetric verification (ES256, RS256, etc.)
            if alg in ["ES256", "RS256", "ES384", "ES512"]:
                signing_key = None
                if self._local_jwk_set:
                    try:
                        if kid:
                            signing_key = self._local_jwk_set[kid]
                        elif len(self._local_jwk_set.keys) > 0:
                            signing_key = self._local_jwk_set.keys[0]
                    except KeyError:
                        pass

                if signing_key is None and self._jwks_client:
                    try:
                        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                    except Exception:
                        pass

                if signing_key:
                    payload = jwt.decode(
                        token,
                        signing_key.key,
                        algorithms=[alg],
                        audience="authenticated",
                    )
                else:
                    raise ValueError(f"No matching verification key found for kid='{kid}'")

            # 2. Symmetric verification (HS256)
            elif settings.SUPABASE_JWT_SECRET and not settings.SUPABASE_JWT_SECRET.strip().startswith("{"):
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                )

            # 3. Development/test fallback mode without configured keys
            else:
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
