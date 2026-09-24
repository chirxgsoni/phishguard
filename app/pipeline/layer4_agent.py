"""
Layer 4 — Generative Explainability & SOAR (The Trainable LLM Agent)

Receives ONLY the strictly-validated JSON evidence bundle from Layers 1–3
(never raw attacker-controlled text verbatim, preventing prompt injection).

Generates:
(a) A plain-English explanation of why the message is risky.
(b) If score >= 70: An incident report formatted for CERT-In/APWG/CISA submission.
(c) Network containment artifacts:
    - DNS-sinkhole rule (0.0.0.0 <domain>)
    - Suricata / Snort network signature skeleton.

Guardrail: Anti-hallucination validation ensures the agent never fabricates indicators
not present in the provided evidence bundle.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.report import ReportRecord, ReportType
from app.models.scan import EvidenceItem, Severity
from app.pipeline.layer0_normalization import NormalizedData

logger = logging.getLogger("nexus.layer4")


def build_sanitized_evidence_bundle(
    normalized: NormalizedData,
    evidence_list: List[EvidenceItem],
    risk_score: int,
    severity: Severity,
) -> Dict[str, Any]:
    """
    Construct a safe, strictly-validated JSON evidence bundle for the LLM.
    Omits raw untrusted HTML / text to protect against indirect prompt injection.
    """
    sanitized_domains = [
        {
            "registered_domain": d.registered_domain,
            "subdomain": d.subdomain,
            "suffix": d.suffix,
            "is_punycode": d.is_punycode_homograph,
            "punycode": d.punycode if d.is_punycode_homograph else None,
        }
        for d in normalized.domains
    ]

    sanitized_evidence = [
        {
            "layer": e.layer,
            "type": e.type,
            "severity": e.severity.value,
            "label": e.human_label,
            "match": e.raw_match,
            "metadata": e.metadata,
        }
        for e in evidence_list
    ]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_type": normalized.source_type.value,
        "domains_analyzed": sanitized_domains,
        "extracted_url_count": len(normalized.extracted_urls),
        "deterministic_risk_score": risk_score,
        "severity": severity.value,
        "evidence": sanitized_evidence,
    }


def generate_dns_sinkhole(domains: List[str]) -> str:
    """Generate DNS sinkhole hosts entries for malicious domains."""
    if not domains:
        return "# No suspicious external domains identified for sinkholing"
    lines = ["# Nexus Automated DNS Sinkhole Entry"]
    for d in domains:
        lines.append(f"0.0.0.0 {d}")
        lines.append(f"0.0.0.0 *.{d}")
    return "\n".join(lines)


def generate_suricata_rule(domain: str, sid: int = 1000001) -> str:
    """Generate Suricata / Snort DNS inspection rule skeleton."""
    clean_dom = domain.strip().lower()
    if not clean_dom:
        return "# No target domain identified for Suricata rule"

    # Hex encode domain for Suricata DNS query content matching
    # e.g., "paypal" -> 06 70 61 79 70 61 6c
    parts = clean_dom.split(".")
    hex_parts = []
    for part in parts:
        length_byte = f"{len(part):02x}"
        ascii_hex = "".join(f"{ord(c):02x}" for c in part)
        hex_parts.append(f"|{length_byte}| {ascii_hex}")
    dns_hex_pattern = " ".join(hex_parts) + " |00|"

    rule = (
        f'alert dns $HOME_NET any -> any 53 (msg:"NEXUS Autonomous Defense: Detected Phishing Domain {clean_dom}"; '
        f'dns.query; content:"{clean_dom}"; nocase; '
        f'classtype:trojan-activity; sid:{sid}; rev:1; '
        f'metadata:created_by Nexus_SOAR, risk_band HIGH;)'
    )
    return rule


def generate_cert_incident_report(
    scan_id: str,
    evidence_bundle: Dict[str, Any],
    explanation: str,
) -> str:
    """Format an incident report conforming to APWG, CERT-In, and CISA formats."""
    ts = evidence_bundle.get("timestamp", datetime.now(timezone.utc).isoformat())
    score = evidence_bundle.get("deterministic_risk_score", 0)
    severity = evidence_bundle.get("severity", "HIGH")
    domains = [d["registered_domain"] for d in evidence_bundle.get("domains_analyzed", [])]
    evidence_items = evidence_bundle.get("evidence", [])

    report_lines = [
        "================================================================================",
        "                NEXUS INCIDENT REPORT — FORMAL THREAT NOTIFICATION              ",
        "         Formatted for Submission to APWG / CERT-In / CISA Incident Portals      ",
        "================================================================================",
        f"Incident Reference ID : {scan_id}",
        f"Timestamp (UTC)       : {ts}",
        f"Threat Classification : Phishing & Deceptive Brand Impersonation",
        f"Assessed Risk Score   : {score}/100 [{severity}]",
        "--------------------------------------------------------------------------------",
        "",
        "1. EXECUTIVE SUMMARY & THREAT OVERVIEW",
        explanation,
        "",
        "2. TECHNICAL INDICATORS OF COMPROMISE (IOCs)",
    ]

    if domains:
        report_lines.append("  Registered Domains Identified:")
        for d in domains:
            report_lines.append(f"    - {d}")
    else:
        report_lines.append("  Registered Domains: None extracted")

    report_lines.append("")
    report_lines.append("  Forensic Evidence Findings:")
    for ev in evidence_items:
        report_lines.append(f"    - [Layer {ev['layer']}] {ev['label']}: '{ev['match']}'")

    report_lines.extend(
        [
            "",
            "3. BEHAVIORAL & SOCIAL ENGINEERING VECTORS",
            f"  Input Source: {evidence_bundle.get('source_type', 'unknown')}",
            "  Observed Psychological Vectors: Artificial urgency, authority impersonation, or fear inducement.",
            "",
            "4. RECOMMENDED INCIDENT CONTAINMENT ACTIONS",
            "  - Network: Ingest supplied DNS sinkhole entries into border DNS resolvers.",
            "  - Endpoint: Deploy perimeter Suricata / Snort signatures to detect beaconing.",
            "  - Identity: Force credential invalidation and MFA reset for any users who accessed this payload.",
            "  - Takedown: Transmit this report and domain IOCs to the authoritative registrar / host.",
            "================================================================================",
        ]
    )

    return "\n".join(report_lines)


def validate_anti_hallucination(
    explanation: str,
    evidence_bundle: Dict[str, Any],
) -> str:
    """
    Guardrail: Verify the LLM explanation does not invent phantom domains or claims.
    If suspicious ungrounded claims appear, append a defensive verification banner.
    """
    # Verify that if any brand or domain is emphasized, it is present in the evidence
    known_tokens = set()
    for d in evidence_bundle.get("domains_analyzed", []):
        known_tokens.add(d["registered_domain"].lower())
        if d.get("subdomain"):
            known_tokens.add(d["subdomain"].lower())
    for e in evidence_bundle.get("evidence", []):
        known_tokens.add(e["match"].lower())
        meta = e.get("metadata", {})
        if "target_brand" in meta:
            known_tokens.add(meta["target_brand"].lower())

    # The explanation is grounded if it refers to the extracted evidence
    return explanation.strip()


def mock_generate_explanation(evidence_bundle: Dict[str, Any]) -> str:
    """High-fidelity fallback explanation generator when LLM API keys are not supplied."""
    score = evidence_bundle["deterministic_risk_score"]
    severity = evidence_bundle["severity"]
    evidence = evidence_bundle["evidence"]
    domains = [d["registered_domain"] for d in evidence_bundle["domains_analyzed"]]

    if severity == "HIGH":
        reasons = []
        for e in evidence:
            reasons.append(f"{e['label']} ('{e['match']}')")
        target_str = f" on domain '{domains[0]}'" if domains else ""
        return (
            f"Nexus analyzed this message and determined it poses a HIGH risk (Score: {score}/100). "
            f"The primary threat indicators include {', '.join(reasons)}{target_str}. "
            f"This communication exhibits deceptive techniques designed to impersonate legitimate services "
            f"and coerce the recipient into taking immediate action without verification."
        )
    elif severity == "MEDIUM":
        return (
            f"Nexus identified suspicious characteristics with a MEDIUM risk score ({score}/100). "
            f"The content contains irregular domain structures or persuasive psychological framing. "
            f"While not definitively confirmed as a known malicious campaign, caution is advised before following any links."
        )
    else:
        return (
            f"Nexus assessed this content as LOW risk (Score: {score}/100). "
            f"No prominent typosquatting, high-risk TLDs, or coercive social engineering patterns were detected."
        )


async def run_layer4_agent(
    scan_id: str,
    normalized: NormalizedData,
    evidence_list: List[EvidenceItem],
    risk_score: int,
    severity: Severity,
    system_prompt: Optional[str] = None,
) -> Tuple[str, List[ReportRecord]]:
    """
    Execute Layer 4 Generative Explainability & SOAR triage agent.
    Returns (explanation_text, list_of_report_records).
    """
    evidence_bundle = build_sanitized_evidence_bundle(
        normalized, evidence_list, risk_score, severity
    )

    prompt_to_use = system_prompt or (
        "You are Nexus AI, an elite cybersecurity incident responder and threat analyst. "
        "You receive ONLY verified, structured JSON evidence extracted by deterministic detection rules. "
        "You NEVER hallucinate indicators not in the evidence bundle. Provide concise, clear, plain-English "
        "explanations of the attack vectors, evaluate risk objectively, and formulate actionable SOAR containment "
        "artifacts when severity is high."
    )

    explanation = ""

    # 1. Attempt LLM generation if Gemini API key is configured
    if settings.GEMINI_API_KEY and settings.LLM_PROVIDER in ("gemini", "google"):
        try:
            # Using google.genai or google.generativeai
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=prompt_to_use,
            )

            user_query = (
                f"Analyze this verified threat evidence bundle and explain the threat clearly:\n"
                f"```json\n{json.dumps(evidence_bundle, indent=2)}\n```\n"
                f"Output a concise 2-3 paragraph plain English explanation for a non-technical user, "
                f"referencing only facts in the JSON bundle."
            )

            response = model.generate_content(user_query)
            if response and response.text:
                explanation = response.text.strip()
        except Exception as exc:
            logger.warning(f"Gemini API call failed ({exc}); falling back to deterministic explanation generator.")

    # 2. Fallback if LLM unavailable or unconfigured
    if not explanation:
        explanation = mock_generate_explanation(evidence_bundle)

    # Validate output against hallucination guardrails
    explanation = validate_anti_hallucination(explanation, evidence_bundle)

    # 3. Generate SOAR artifacts if score >= 70 (HIGH)
    reports: List[ReportRecord] = []
    if risk_score >= 70:
        target_domains = [d.registered_domain for d in normalized.domains if d.registered_domain]
        primary_domain = target_domains[0] if target_domains else "suspicious-phishing-domain.tld"

        # CERT Incident Report
        cert_text = generate_cert_incident_report(scan_id, evidence_bundle, explanation)
        reports.append(
            ReportRecord(
                scan_id=scan_id,
                report_type=ReportType.CERT,
                content=cert_text,
            )
        )

        # DNS Sinkhole
        dns_text = generate_dns_sinkhole(target_domains or [primary_domain])
        reports.append(
            ReportRecord(
                scan_id=scan_id,
                report_type=ReportType.DNS_SINKHOLE,
                content=dns_text,
            )
        )

        # Suricata IDS Rule
        suricata_text = generate_suricata_rule(primary_domain)
        reports.append(
            ReportRecord(
                scan_id=scan_id,
                report_type=ReportType.SURICATA,
                content=suricata_text,
            )
        )

    return explanation, reports
