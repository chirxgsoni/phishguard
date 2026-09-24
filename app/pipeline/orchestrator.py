"""
Nexus Pipeline Orchestrator

Sequentially executes Layers 0 through 4, streams real-time progress events
over WebSockets, and persists all evidence and SOAR artifacts to Supabase.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.supabase import db_service
from app.core.websocket_manager import ws_manager
from app.models.scan import EvidenceItem, ScanStatus, Severity, SourceType
from app.pipeline.layer0_normalization import normalize_input
from app.pipeline.layer1_deterministic import evaluate_layer1
from app.pipeline.layer2_behavioral import evaluate_layer2
from app.pipeline.layer3_scorer import compute_risk_score
from app.pipeline.layer4_agent import run_layer4_agent

logger = logging.getLogger("nexus.orchestrator")


async def run_pipeline_orchestrator(
    scan_id: str,
    user_id: str,
    source_type: SourceType,
    content: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    agent_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the 5-layer threat detection pipeline.
    Emits granular real-time progress to any listening WebSockets.
    """
    try:
        # Mark scan as processing
        await db_service.update_scan(scan_id, {"status": ScanStatus.PROCESSING.value})

        # Fetch custom agent profile prompt if requested
        system_prompt = None
        if agent_profile_id:
            prof = await db_service.get_agent_profile_by_id(agent_profile_id)
            if prof:
                system_prompt = prof.get("system_prompt")

        # ----------------------------------------------------------------------
        # LAYER 0: Normalization & Ingestion
        # ----------------------------------------------------------------------
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 0,
                "status": "running",
                "message": "Normalizing content, unshortening URLs, and decoding payloads",
            },
        )
        # Small delay for UI smoothness during live demonstration
        await asyncio.sleep(0.3)

        normalized = await normalize_input(source_type, content, file_bytes)

        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 0,
                "status": "complete",
                "extracted_urls": len(normalized.extracted_urls),
                "domains_found": len(normalized.domains),
            },
        )

        # ----------------------------------------------------------------------
        # LAYER 1: Deterministic Engine (Pure Python / Regex)
        # ----------------------------------------------------------------------
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 1,
                "status": "running",
                "message": "Evaluating typosquatting, TLD reputation, and subdomain spoofing",
            },
        )
        await asyncio.sleep(0.3)

        layer1_evidence: List[EvidenceItem] = evaluate_layer1(normalized)
        for ev in layer1_evidence:
            ev.scan_id = scan_id

        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 1,
                "status": "complete",
                "evidence_count": len(layer1_evidence),
            },
        )

        # ----------------------------------------------------------------------
        # LAYER 2: Behavioral & NLP Extraction
        # ----------------------------------------------------------------------
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 2,
                "status": "running",
                "message": "Extracting social engineering triggers and character spans",
            },
        )
        await asyncio.sleep(0.3)

        layer2_evidence: List[EvidenceItem] = evaluate_layer2(normalized)
        for ev in layer2_evidence:
            ev.scan_id = scan_id

        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 2,
                "status": "complete",
                "evidence_count": len(layer2_evidence),
            },
        )

        # Combine all evidence items
        all_evidence: List[EvidenceItem] = layer1_evidence + layer2_evidence

        # ----------------------------------------------------------------------
        # LAYER 3: Risk Aggregator & Scorer
        # ----------------------------------------------------------------------
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 3,
                "status": "running",
                "message": "Aggregating evidence weights and computing deterministic risk score",
            },
        )
        await asyncio.sleep(0.2)

        risk_score, severity, recommended_action = compute_risk_score(all_evidence)

        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 3,
                "status": "complete",
                "risk_score": risk_score,
                "severity": severity.value,
            },
        )

        # ----------------------------------------------------------------------
        # LAYER 4: Generative Explainability & SOAR Agent
        # ----------------------------------------------------------------------
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 4,
                "status": "running",
                "message": "Synthesizing plain-English explanation and containment artifacts",
            },
        )
        await asyncio.sleep(0.3)

        explanation, reports = await run_layer4_agent(
            scan_id=scan_id,
            normalized=normalized,
            evidence_list=all_evidence,
            risk_score=risk_score,
            severity=severity,
            system_prompt=system_prompt,
        )

        # Stream partial/complete explanation event
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 4,
                "status": "streaming",
                "partial_explanation": explanation[:150] + "...",
            },
        )

        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "layer": 4,
                "status": "complete",
                "reports_generated": len(reports),
            },
        )

        # ----------------------------------------------------------------------
        # PERSISTENCE & FINALIZATION
        # ----------------------------------------------------------------------
        # 1. Save evidence items to Supabase
        evidence_dicts = [e.model_dump() for e in all_evidence]
        await db_service.insert_evidence_batch(evidence_dicts)

        # 2. Save SOAR reports if generated
        report_dicts = [r.model_dump() for r in reports]
        await db_service.insert_reports(report_dicts)

        # 3. Update master scan record
        scan_updates = {
            "risk_score": risk_score,
            "severity": severity.value,
            "status": ScanStatus.COMPLETED.value,
            "recommended_action": recommended_action,
            "explanation": explanation,
        }
        updated_scan = await db_service.update_scan(scan_id, scan_updates)

        # Emit terminal completion event
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "status": "complete",
                "risk_score": risk_score,
                "severity": severity.value,
                "recommended_action": recommended_action,
            },
        )

        return updated_scan

    except Exception as exc:
        logger.error(f"Pipeline failure for scan {scan_id}: {exc}", exc_info=True)
        await db_service.update_scan(scan_id, {"status": ScanStatus.FAILED.value})
        await ws_manager.broadcast_step(
            scan_id,
            {
                "scan_id": scan_id,
                "status": "failed",
                "error": str(exc),
            },
        )
        raise
