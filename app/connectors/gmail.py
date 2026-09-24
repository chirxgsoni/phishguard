"""
Gmail Connector Implementation.

Implements Google OAuth2 authorization code flow with read-only Gmail scope (gmail.readonly).
Extracts recent messages and maps them to standard ConnectedMessage models for the
Layer 0 ingestion pipeline.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.connectors.base import BaseConnector, ConnectedMessage

logger = logging.getLogger("nexus.gmail_connector")

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GmailConnector(BaseConnector):
    """Google OAuth2 and Gmail API Connector."""

    @property
    def provider_name(self) -> str:
        return "gmail"

    def get_authorization_url(self, state: str) -> str:
        """Construct Google OAuth2 authorization consent screen URL."""
        client_id = settings.GOOGLE_CLIENT_ID or "mock-google-client-id"
        redirect_uri = settings.GOOGLE_REDIRECT_URI

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",  # Request refresh_token
            "prompt": "consent",
            "state": state,
        }
        return f"{GMAIL_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for OAuth access and refresh tokens."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            # Fallback mock credentials for dev/demonstration environments
            logger.warning("GOOGLE_CLIENT_ID not configured; using mock token exchange.")
            return {
                "access_token": f"mock_access_token_{code[:8]}",
                "refresh_token": "mock_refresh_token_nexus",
                "token_type": "Bearer",
                "expires_in": 3600,
                "email": "user@gmail.com",
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GMAIL_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                raise ValueError(f"Failed to exchange code for tokens: {resp.text}")

            token_data = resp.json()

            # Retrieve connected email address
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if userinfo_resp.status_code == 200:
                token_data["email"] = userinfo_resp.json().get("email", "")

            return token_data

    async def fetch_recent_messages(
        self, tokens: Dict[str, Any], limit: int = 10
    ) -> List[ConnectedMessage]:
        """Fetch latest messages from user inbox."""
        access_token = tokens.get("access_token")
        if not access_token or access_token.startswith("mock_"):
            # Return high-fidelity realistic demo scenarios for demonstration
            return [
                ConnectedMessage(
                    message_id="msg-demo-001",
                    sender="security-alert@update-wellsfargo.com.update.xyz",
                    subject="URGENT: Unauthorized access detected on your account",
                    body=(
                        "Dear Customer,\n\n"
                        "We detected suspicious activity on your account. Immediate action is required within 24 hours "
                        "to prevent account deactivation.\n\n"
                        "Please verify your credentials at: https://wellsfargo.com.update.xyz/auth?next=https://paypal.com\n\n"
                        "Sincerely,\nWells Fargo Global Security Operations"
                    ),
                    received_at=datetime.now(timezone.utc).isoformat(),
                    metadata={"provider": "gmail", "folder": "INBOX"},
                ),
                ConnectedMessage(
                    message_id="msg-demo-002",
                    sender="newsletter@acme-corp.com",
                    subject="Your weekly engineering update",
                    body=(
                        "Hi team,\n\n"
                        "Here is the digest of release notes for sprint 42. No action required.\n\n"
                        "Best,\nEngineering Management"
                    ),
                    received_at=datetime.now(timezone.utc).isoformat(),
                    metadata={"provider": "gmail", "folder": "INBOX"},
                ),
            ]

        # Live Gmail API integration
        messages: List[ConnectedMessage] = []
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                f"{GMAIL_API_BASE}/messages?maxResults={limit}&q=label:INBOX",
                headers=headers,
            )
            if list_resp.status_code != 200:
                logger.error(f"Gmail API list messages failed: {list_resp.text}")
                return messages

            msg_ids = [m["id"] for m in list_resp.json().get("messages", [])]

            for mid in msg_ids:
                get_resp = await client.get(f"{GMAIL_API_BASE}/messages/{mid}", headers=headers)
                if get_resp.status_code != 200:
                    continue
                data = get_resp.json()

                # Extract headers
                headers_list = data.get("payload", {}).get("headers", [])
                hdr_map = {h["name"].lower(): h["value"] for h in headers_list}

                sender = hdr_map.get("from", "")
                subject = hdr_map.get("subject", "")
                date_str = hdr_map.get("date", "")

                # Extract body
                body = ""
                payload = data.get("payload", {})
                parts = payload.get("parts", [])
                if "body" in payload and "data" in payload["body"]:
                    raw_b64 = payload["body"]["data"]
                    body = base64.urlsafe_b64decode(raw_b64.encode()).decode("utf-8", errors="ignore")
                elif parts:
                    for part in parts:
                        if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                            raw_b64 = part["body"]["data"]
                            body = base64.urlsafe_b64decode(raw_b64.encode()).decode("utf-8", errors="ignore")
                            break

                messages.append(
                    ConnectedMessage(
                        message_id=mid,
                        sender=sender,
                        subject=subject,
                        body=body,
                        received_at=date_str,
                        metadata={"provider": "gmail", "thread_id": data.get("threadId")},
                    )
                )

        return messages


gmail_connector = GmailConnector()
