"""
Layer 3 — Risk Aggregator & Pure Deterministic Scorer

Deterministic weighted-sum scorer over all Layer 1 + Layer 2 evidence -> composite score 0–100.
Severity bands:
  - LOW: 0–39
  - MEDIUM: 40–69
  - HIGH: 70–100

Pure, side-effect free, unit-testable calculation. No LLM involvement.
"""

from typing import Dict, List, Tuple
from app.models.scan import EvidenceItem, Severity

# Weights assigned per evidence type
WEIGHT_TABLE: Dict[str, int] = {
    # Layer 1: Technical Indicators
    "typosquatting": 40,
    "subdomain_spoofing": 35,
    "idn_homograph": 40,
    "bare_ip_hostname": 30,
    "hidden_html_obfuscation": 25,
    "open_redirect": 20,
    "high_risk_tld": 15,
    # Layer 2: Behavioral / Social Engineering Indicators
    "authority": 20,
    "fear": 20,
    "urgency": 15,
    "greed": 15,
}

# Maximum contribution caps for repetitive categories
CATEGORY_CAPS: Dict[str, int] = {
    "urgency": 30,
    "fear": 30,
    "authority": 30,
    "greed": 25,
    "high_risk_tld": 20,
    "open_redirect": 25,
}


def compute_risk_score(evidence_list: List[EvidenceItem]) -> Tuple[int, Severity, str]:
    """
    Calculate deterministic composite risk score from 0 to 100,
    assign the severity band, and formulate the rule-based recommended action.
    """
    if not evidence_list:
        return 0, Severity.LOW, "No immediate threat indicators detected. Standard email hygiene applies."

    raw_score = 0
    category_acc: Dict[str, int] = {}
    has_layer1 = False
    has_layer2 = False

    for item in evidence_list:
        ev_type = item.type
        weight = WEIGHT_TABLE.get(ev_type, 10)

        if item.layer == 1:
            has_layer1 = True
        elif item.layer == 2:
            has_layer2 = True

        current_total = category_acc.get(ev_type, 0)
        cap = CATEGORY_CAPS.get(ev_type, 100)

        if current_total < cap:
            addition = min(weight, cap - current_total)
            category_acc[ev_type] = current_total + addition
            raw_score += addition

    # Cross-layer synergy bonus: Real phishing combines technical lures with psychological pressure
    if has_layer1 and has_layer2:
        raw_score += 10

    # Normalize within 0 to 100 bounds
    composite_score = max(0, min(100, raw_score))

    # Determine severity band
    if composite_score >= 70:
        severity = Severity.HIGH
        recommended_action = (
            "CRITICAL THREAT: DO NOT CLICK links or interact with content. "
            "Quarantine message immediately, block sender and associated domains at network boundary, "
            "and submit formal incident report to SOC / CERT."
        )
    elif composite_score >= 40:
        severity = Severity.MEDIUM
        recommended_action = (
            "SUSPICIOUS CONTENT: Exercise caution. Verify the sender's identity through an official, "
            "independent channel (e.g. bookmarks or phone directory) before clicking any links or providing data."
        )
    else:
        severity = Severity.LOW
        recommended_action = (
            "LOW RISK: No active malicious indicators detected. "
            "Continue standard security vigilance."
        )

    return composite_score, severity, recommended_action
