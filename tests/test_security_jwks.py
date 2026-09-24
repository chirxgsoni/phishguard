"""Tests for JWKS and asymmetric JWT verification in SecurityService."""

import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from app.core.security import SecurityService
from app.config import settings


def test_verify_supabase_jwt_with_jwks(monkeypatch):
    """Verify that SecurityService successfully verifies an ES256 token using JWKS."""
    # Generate an EC private key and create matching JWK
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    from jwt.algorithms import ECAlgorithm
    import json
    jwk_dict = json.loads(ECAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = "test-ec-kid-1"
    jwk_dict["alg"] = "ES256"
    jwks_json = json.dumps({"keys": [jwk_dict]})

    monkeypatch.setattr(settings, "SUPABASE_JWKS", jwks_json)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", None)

    service = SecurityService()

    # Sign a token
    token = jwt.encode(
        {
            "sub": "user-uuid-12345",
            "email": "analyst@phishguard.security",
            "role": "authenticated",
            "aud": "authenticated",
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-ec-kid-1", "alg": "ES256"},
    )

    user = service.verify_supabase_jwt(token)
    assert user["id"] == "user-uuid-12345"
    assert user["email"] == "analyst@phishguard.security"
    assert user["role"] == "authenticated"


def test_verify_supabase_jwt_invalid_kid(monkeypatch):
    """Verify that a token with unknown kid raises ValueError."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    
    from jwt.algorithms import ECAlgorithm
    import json
    jwk_dict = json.loads(ECAlgorithm.to_jwk(private_key.public_key()))
    jwk_dict["kid"] = "known-kid"
    jwk_dict["alg"] = "ES256"
    jwks_json = json.dumps({"keys": [jwk_dict]})

    monkeypatch.setattr(settings, "SUPABASE_JWKS", jwks_json)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", None)
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://your-project.supabase.co")

    service = SecurityService()

    token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated"},
        private_key,
        algorithm="ES256",
        headers={"kid": "unknown-kid", "alg": "ES256"},
    )

    with pytest.raises(ValueError, match="Invalid or expired JWT token"):
        service.verify_supabase_jwt(token)
