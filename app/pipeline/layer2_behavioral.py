"""
Layer 2 — NLP & Behavioral Extraction

Detects social-engineering intent:
- Urgency
- Fear / Threat
- Authority Impersonation
- Greed / Reward bait

Extracts and returns EXACT character token spans (span_start, span_end)
in the original text so the frontend can highlight them inline within Evidence Cards.
"""

import re
from typing import Any, Dict, List, Tuple
from app.models.scan import EvidenceItem, Severity
from app.pipeline.layer0_normalization import NormalizedData

# Intent definitions with keyword/regex patterns, human labels, and severities
INTENT_PATTERNS: Dict[str, Dict[str, Any]] = {
    "urgency": {
        "label": "Artificial Urgency & Time Pressure",
        "severity": Severity.MEDIUM,
        "patterns": [
            r"\bimmediate(?:ly)? action (?:is )?required\b",
            r"\bwithin (?:12|24|48) hours\b",
            r"\baccount (?:will be|has been) (?:suspended|terminated|deactivated)\b",
            r"\bexpire[sd]? (?:today|tonight|immediately|soon)\b",
            r"\burgent(?:ly)?\b",
            r"\bact immediately\b",
            r"\btime(?:-| )sensitive\b",
            r"\brespond immediately\b",
            r"\bfinal notice\b",
            r"\blast reminder\b",
            r"\bdo not ignore\b",
        ],
    },
    "fear": {
        "label": "Fear, Intimidation & Threat Inducement",
        "severity": Severity.HIGH,
        "patterns": [
            r"\bunauthorized (?:access|login|transaction|activity)\b",
            r"\bsuspicious (?:activity|sign-in|activity detected)\b",
            r"\blegal action (?:will be taken|has been initiated)\b",
            r"\baccount (?:is )?(?:compromised|locked|restricted)\b",
            r"\bsecurity (?:breach|alert|warning)\b",
            r"\blaw enforcement\b",
            r"\bfraudulent (?:charge|activity|attempt)\b",
            r"\bfailed payment (?:threat|consequence)\b",
            r"\bidentity theft\b",
        ],
    },
    "authority": {
        "label": "Authority / Enterprise Brand Impersonation",
        "severity": Severity.HIGH,
        "patterns": [
            r"\b(?:it|technical|global) support (?:team|desk|department)\b",
            r"\bsecurity (?:operations|team|center|division)\b",
            r"\bcustomer (?:support|service|relations|care) (?:team|desk)\b",
            r"\b(?:internal revenue service|irs|hmrc|tax authority)\b",
            r"\bfederal (?:bureau|trade commission|reserve|court)\b",
            r"\b(?:system|network|domain) administrator\b",
            r"\boffice of the (?:ceo|director|president)\b",
            r"\bhelp desk\b",
            r"\bbilling department\b",
            r"\bcompliance department\b",
        ],
    },
    "greed": {
        "label": "Financial Incentive / Reward Bait",
        "severity": Severity.MEDIUM,
        "patterns": [
            r"\bclaim your (?:refund|reward|prize|voucher|gift card|bonus)\b",
            r"\b(?:lottery|sweepstakes) winner\b",
            r"\bunclaimed (?:funds|money|asset|inheritance)\b",
            r"\b(?:crypto|bitcoin|ethereum) (?:giveaway|airdrop|reward)\b",
            r"\bwire transfer (?:pending|approved|waiting)\b",
            r"\bfree (?:gift card|voucher|subscription|access)\b",
            r"\byou have won\b",
            r"\bcongratulations,?\s+you\b",
            r"\bexclusive payout\b",
        ],
    },
}

# Precompile all regex patterns for performance
COMPILED_PATTERNS: Dict[str, List[Tuple[re.Pattern, str, Severity]]] = {}
for category, data in INTENT_PATTERNS.items():
    COMPILED_PATTERNS[category] = [
        (re.compile(pat, re.IGNORECASE), data["label"], data["severity"])
        for pat in data["patterns"]
    ]


def evaluate_layer2(normalized: NormalizedData) -> List[EvidenceItem]:
    """
    Run behavioral NLP extraction over normalized text.
    Finds social engineering intent patterns and captures exact character spans.
    """
    evidence: List[EvidenceItem] = []
    text_to_search = normalized.cleaned_text

    if not text_to_search:
        return evidence

    # Track matches to avoid duplicate overlapping spans of the same category
    seen_spans = set()

    for category, pattern_tuples in COMPILED_PATTERNS.items():
        for pattern, label, severity in pattern_tuples:
            for match in pattern.finditer(text_to_search):
                start, end = match.span()
                span_key = (category, start, end)

                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)

                matched_str = match.group(0)

                evidence.append(
                    EvidenceItem(
                        layer=2,
                        type=category,
                        severity=severity,
                        human_label=label,
                        raw_match=matched_str,
                        span_start=start,
                        span_end=end,
                        metadata={
                            "category": category,
                            "matched_text": matched_str,
                        },
                    )
                )

    return evidence
