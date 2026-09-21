"""
Base Connector Interface for External Communication Platforms.

Architected so that new providers (Gmail, Slack, Teams, WhatsApp Business API)
can be added by implementing this single interface:
  fetch messages -> normalize -> hand to Layer 0
without touching the 5-layer detection pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConnectedMessage:
    """Standardized representation of a message ingested from a connected account."""

    message_id: str
    sender: str
    subject: str
    body: str
    received_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_scan_content(self) -> str:
        """Format message into plain text representation for the Layer 0 ingestion pipeline."""
        parts = []
        if self.sender:
            parts.append(f"From: {self.sender}")
        if self.subject:
            parts.append(f"Subject: {self.subject}")
        if self.received_at:
            parts.append(f"Date: {self.received_at}")
        parts.append("\n" + self.body)
        return "\n".join(parts)


class BaseConnector(ABC):
    """Abstract provider connector interface."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the platform provider (e.g. 'gmail', 'slack')."""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for credentials/tokens."""
        pass

    @abstractmethod
    async def fetch_recent_messages(
        self, tokens: Dict[str, Any], limit: int = 10
    ) -> List[ConnectedMessage]:
        """Fetch unread or recent messages from the provider."""
        pass
