"""Unit tests for Layer 3: Risk Aggregator & Pure Deterministic Scorer."""

from app.models.scan import EvidenceItem, Severity
from app.pipeline.layer3_scorer import compute_risk_score


def test_empty_evidence_low_score():
    """Verify zero evidence yields 0 risk score and LOW severity."""
    score, severity, action = compute_risk_score([])
    assert score == 0
    assert severity == Severity.LOW
    assert "No immediate threat" in action


def test_single_typosquatting_medium_score():
    """Verify a single typosquatting indicator lands in MEDIUM band."""
    ev = [
        EvidenceItem(
            layer=1,
            type="typosquatting",
            severity=Severity.HIGH,
            human_label="Typosquatting of PayPal",
            raw_match="paypa1.com",
        )
    ]
    score, severity, action = compute_risk_score(ev)
    assert score == 40
    assert severity == Severity.MEDIUM


def test_combined_indicators_high_severity():
    """Verify combined technical + behavioral indicators trigger HIGH severity band."""
    ev = [
        EvidenceItem(
            layer=1,
            type="typosquatting",
            severity=Severity.HIGH,
            human_label="Typosquatting of PayPal",
            raw_match="paypa1.com",
        ),
        EvidenceItem(
            layer=1,
            type="subdomain_spoofing",
            severity=Severity.HIGH,
            human_label="Subdomain spoofing",
            raw_match="paypal.update.xyz",
        ),
        EvidenceItem(
            layer=2,
            type="urgency",
            severity=Severity.MEDIUM,
            human_label="Urgency",
            raw_match="within 24 hours",
        ),
    ]
    score, severity, action = compute_risk_score(ev)
    # 40 (typosquatting) + 35 (subdomain) + 15 (urgency) + 10 (cross-layer synergy) = 100
    assert score >= 70
    assert severity == Severity.HIGH
    assert "CRITICAL THREAT" in action


def test_determinism_consistency():
    """Verify the scorer is 100% deterministic and pure across repeated executions."""
    ev = [
        EvidenceItem(
            layer=1,
            type="high_risk_tld",
            severity=Severity.MEDIUM,
            human_label="High risk TLD",
            raw_match=".xyz",
        ),
        EvidenceItem(
            layer=2,
            type="fear",
            severity=Severity.HIGH,
            human_label="Fear",
            raw_match="unauthorized access",
        ),
    ]
    results = [compute_risk_score(ev) for _ in range(50)]
    assert all(r == results[0] for r in results)
