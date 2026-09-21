"""Supabase Client provider and database abstraction layer.

The backend uses the Supabase SERVICE ROLE KEY which bypasses Row Level Security.
This is intentional — the pipeline needs to write evidence, update scans, and
generate reports on behalf of the user. The frontend uses the ANON key + Supabase
Auth (JWT) which is subject to RLS.

When SUPABASE_URL/SUPABASE_KEY are not configured (dev/demo mode), falls back to
an in-memory store so the app boots without external dependencies.
"""

import logging
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("phishguard.supabase")


# ══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY FALLBACK (Dev / Demo mode only)
# ══════════════════════════════════════════════════════════════════════════════

class InMemoryFallbackStore:
    """In-memory data store used when Supabase credentials are not configured."""

    def __init__(self):
        self.scans: Dict[str, Dict[str, Any]] = {}
        self.evidence: Dict[str, List[Dict[str, Any]]] = {}
        self.reports: Dict[str, List[Dict[str, Any]]] = {}
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.agent_profiles: Dict[str, Dict[str, Any]] = {
            "00000000-0000-0000-0000-000000000001": {
                "id": "00000000-0000-0000-0000-000000000001",
                "user_id": None,
                "name": "Standard Security Analyst (Default)",
                "system_prompt": (
                    "You are PhishGuard AI, an elite cybersecurity incident responder and threat analyst. "
                    "You receive ONLY verified, structured JSON evidence extracted by deterministic detection rules. "
                    "You NEVER hallucinate indicators not in the evidence bundle. Provide concise, clear, plain-English "
                    "explanations of the attack vectors, evaluate risk objectively, and formulate actionable SOAR containment "
                    "artifacts when severity is high."
                ),
                "is_default": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }


fallback_store = InMemoryFallbackStore()


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class DatabaseService:
    """Encapsulates all Supabase Postgres operations.
    
    Uses the service role key (bypasses RLS) for server-side pipeline writes.
    Falls back to in-memory when Supabase is not configured.
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._is_live: bool = False
        self._initialize_client()

    def _initialize_client(self):
        try:
            if (
                settings.SUPABASE_URL
                and "your-project" not in settings.SUPABASE_URL
                and settings.SUPABASE_KEY
                and "your-service-role-key" not in settings.SUPABASE_KEY
            ):
                self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                self._is_live = True
                logger.info("✓ Supabase client initialized — connected to live database.")
            else:
                logger.warning(
                    "⚠ Supabase credentials not configured. "
                    "Running in-memory fallback mode (data will not persist). "
                    "Set SUPABASE_URL and SUPABASE_KEY in .env to connect."
                )
                self._is_live = False
        except Exception as exc:
            logger.error(f"✗ Failed to connect to Supabase: {exc}. Using fallback in-memory store.")
            self._is_live = False

    @property
    def is_live(self) -> bool:
        """True when connected to a real Supabase Postgres instance."""
        return self._is_live

    @property
    def raw_client(self) -> Optional[Client]:
        """Direct Supabase client access (for edge cases)."""
        return self._client

    # ──────────────────────────────────────────────────────────────────────────
    # SCANS
    # ──────────────────────────────────────────────────────────────────────────
    async def create_scan(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new scan record into the scans table."""
        if not scan_data.get("id"):
            scan_data["id"] = str(uuid.uuid4())
        scan_data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        scan_data.setdefault("updated_at", datetime.now(timezone.utc).isoformat())

        if self._is_live and self._client:
            try:
                res = self._client.table("scans").insert(scan_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error inserting scan into Supabase: {e}")

        # Fallback
        fallback_store.scans[scan_data["id"]] = scan_data
        return scan_data

    async def update_scan(self, scan_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing scan (risk_score, severity, status, explanation, etc.)."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self._is_live and self._client:
            try:
                res = self._client.table("scans").update(updates).eq("id", scan_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error updating scan in Supabase: {e}")

        # Fallback
        if scan_id in fallback_store.scans:
            fallback_store.scans[scan_id].update(updates)
            return fallback_store.scans[scan_id]
        return updates

    async def get_scan(self, scan_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single scan by ID. Optionally filter by user_id."""
        if self._is_live and self._client:
            try:
                query = self._client.table("scans").select("*").eq("id", scan_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                logger.error(f"Error fetching scan from Supabase: {e}")

        # Fallback
        scan = fallback_store.scans.get(scan_id)
        if scan and (user_id is None or scan.get("user_id") == user_id):
            return scan
        return None

    async def list_scans(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """Paginated scan history for a user, ordered by created_at DESC."""
        offset = (page - 1) * page_size

        if self._is_live and self._client:
            try:
                query = (
                    self._client.table("scans")
                    .select("*", count="exact")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .range(offset, offset + page_size - 1)
                )
                res = query.execute()
                return {"items": res.data or [], "total": res.count or len(res.data or [])}
            except Exception as e:
                logger.error(f"Error listing scans from Supabase: {e}")

        # Fallback
        user_scans = [
            s for s in fallback_store.scans.values() if s.get("user_id") == user_id
        ]
        user_scans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(user_scans)
        items = user_scans[offset : offset + page_size]
        return {"items": items, "total": total}

    # ──────────────────────────────────────────────────────────────────────────
    # EVIDENCE
    # ──────────────────────────────────────────────────────────────────────────
    async def insert_evidence_batch(self, evidence_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch-insert evidence items from Layer 1 + Layer 2."""
        if not evidence_items:
            return []

        for item in evidence_items:
            if not item.get("id"):
                item["id"] = str(uuid.uuid4())
            item.setdefault("created_at", datetime.now(timezone.utc).isoformat())

        if self._is_live and self._client:
            try:
                res = self._client.table("evidence").insert(evidence_items).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error inserting evidence into Supabase: {e}")

        # Fallback
        for item in evidence_items:
            scan_id = item["scan_id"]
            if scan_id not in fallback_store.evidence:
                fallback_store.evidence[scan_id] = []
            fallback_store.evidence[scan_id].append(item)
        return evidence_items

    async def get_scan_evidence(self, scan_id: str) -> List[Dict[str, Any]]:
        """Retrieve all evidence items for a scan, ordered by layer."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("evidence")
                    .select("*")
                    .eq("scan_id", scan_id)
                    .order("layer")
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.error(f"Error getting evidence from Supabase: {e}")

        # Fallback
        return fallback_store.evidence.get(scan_id, [])

    # ──────────────────────────────────────────────────────────────────────────
    # REPORTS (SOAR Artifacts)
    # ──────────────────────────────────────────────────────────────────────────
    async def insert_reports(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert SOAR containment artifacts (CERT, DNS sinkhole, Suricata rules)."""
        if not reports:
            return []

        for r in reports:
            if not r.get("id"):
                r["id"] = str(uuid.uuid4())
            r.setdefault("created_at", datetime.now(timezone.utc).isoformat())

        if self._is_live and self._client:
            try:
                res = self._client.table("reports").insert(reports).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error inserting reports into Supabase: {e}")

        # Fallback
        for r in reports:
            scan_id = r["scan_id"]
            if scan_id not in fallback_store.reports:
                fallback_store.reports[scan_id] = []
            fallback_store.reports[scan_id].append(r)
        return reports

    async def get_scan_reports(self, scan_id: str) -> List[Dict[str, Any]]:
        """Retrieve all SOAR artifacts for a scan."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("reports")
                    .select("*")
                    .eq("scan_id", scan_id)
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.error(f"Error getting reports from Supabase: {e}")

        # Fallback
        return fallback_store.reports.get(scan_id, [])

    # ──────────────────────────────────────────────────────────────────────────
    # AGENT PROFILES
    # ──────────────────────────────────────────────────────────────────────────
    async def get_agent_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all agent profiles visible to a user (own + global defaults)."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("agent_profiles")
                    .select("*")
                    .or_(f"user_id.is.null,user_id.eq.{user_id}")
                    .order("created_at", desc=False)
                    .execute()
                )
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Error getting agent profiles from Supabase: {e}")

        # Fallback
        profiles = [
            p for p in fallback_store.agent_profiles.values()
            if p.get("user_id") is None or p.get("user_id") == user_id
        ]
        return profiles

    async def get_agent_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a single agent profile by ID."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("agent_profiles")
                    .select("*")
                    .eq("id", profile_id)
                    .execute()
                )
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error getting profile {profile_id}: {e}")

        return fallback_store.agent_profiles.get(profile_id)

    async def save_agent_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an agent profile (upsert)."""
        if not profile_data.get("id"):
            profile_data["id"] = str(uuid.uuid4())
        profile_data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        profile_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self._is_live and self._client:
            try:
                res = self._client.table("agent_profiles").upsert(profile_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error saving agent profile in Supabase: {e}")

        fallback_store.agent_profiles[profile_data["id"]] = profile_data
        return profile_data

    # ──────────────────────────────────────────────────────────────────────────
    # CONNECTIONS (OAuth Integrations)
    # ──────────────────────────────────────────────────────────────────────────
    async def list_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all connections for a user (excludes encrypted_tokens)."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("connections")
                    .select("id, user_id, provider, status, metadata, last_synced_at, created_at")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.error(f"Error listing connections from Supabase: {e}")

        return [
            {k: v for k, v in c.items() if k != "encrypted_tokens"}
            for c in fallback_store.connections.values()
            if c.get("user_id") == user_id
        ]

    async def get_connection(self, connection_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single connection (including encrypted_tokens for sync operations)."""
        if self._is_live and self._client:
            try:
                res = (
                    self._client.table("connections")
                    .select("*")
                    .eq("id", connection_id)
                    .eq("user_id", user_id)
                    .execute()
                )
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error getting connection from Supabase: {e}")

        conn = fallback_store.connections.get(connection_id)
        if conn and conn.get("user_id") == user_id:
            return conn
        return None

    async def save_connection(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a connection record (upsert)."""
        if not connection_data.get("id"):
            connection_data["id"] = str(uuid.uuid4())
        connection_data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        connection_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self._is_live and self._client:
            try:
                res = self._client.table("connections").upsert(connection_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error(f"Error saving connection in Supabase: {e}")

        fallback_store.connections[connection_data["id"]] = connection_data
        return connection_data

    async def delete_connection(self, connection_id: str, user_id: str) -> bool:
        """Revoke and delete a connection."""
        if self._is_live and self._client:
            try:
                self._client.table("connections").delete().eq("id", connection_id).eq("user_id", user_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error deleting connection from Supabase: {e}")

        if connection_id in fallback_store.connections:
            if fallback_store.connections[connection_id].get("user_id") == user_id:
                del fallback_store.connections[connection_id]
                return True
        return False


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════
db_service = DatabaseService()
