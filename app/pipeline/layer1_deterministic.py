"""
Layer 1 — Deterministic Security Engine

Pure Python & regex rule evaluation (no ML).
- Levenshtein distance against high-profile brand domains for typosquatting (paypa1.com, micros0ft.com).
- High-risk TLD inspection (.xyz, .top, .info, .biz, .icu, etc.).
- Subdomain spoofing detection (e.g. wellsfargo.com.update.xyz -> real domain is update.xyz).
- Open-redirect and suspicious query string detection (?redirect=, ?next=, ?url=).
- Bare IP address hostnames (e.g. http://192.0.2.1/login).
- IDN homograph and Punycode spoofing detection.
- Evasive / hidden HTML content markers.

Output: List of discrete EvidenceItem objects with layer=1.
"""

import ipaddress
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from app.models.scan import EvidenceItem, Severity
from app.pipeline.layer0_normalization import DomainInfo, NormalizedData

# High-profile brand domains mapped to human-readable brand name
BRAND_DOMAINS: Dict[str, str] = {
    "paypal.com": "PayPal",
    "microsoft.com": "Microsoft",
    "google.com": "Google",
    "apple.com": "Apple",
    "amazon.com": "Amazon",
    "netflix.com": "Netflix",
    "chase.com": "Chase Bank",
    "wellsfargo.com": "Wells Fargo",
    "bankofamerica.com": "Bank of America",
    "citigroup.com": "Citigroup",
    "citi.com": "Citigroup",
    "barclays.com": "Barclays",
    "hsbc.com": "HSBC",
    "dropbox.com": "Dropbox",
    "docusign.com": "DocuSign",
    "dhl.com": "DHL Express",
    "fedex.com": "FedEx",
    "ups.com": "UPS",
    "usps.com": "USPS",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "whatsapp.com": "WhatsApp",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter / X",
    "coinbase.com": "Coinbase",
    "binance.com": "Binance",
    "stripe.com": "Stripe",
    "intuit.com": "Intuit",
    "irs.gov": "Internal Revenue Service",
}

# High-risk TLDs commonly abused by automated phishing kits
HIGH_RISK_TLDS = {
    "xyz", "top", "info", "biz", "buzz", "club", "work", "icu",
    "tk", "ml", "ga", "cf", "gq", "zip", "mov", "rest", "fit",
    "surf", "click", "cam", "link", "online", "live", "site",
}

# Suspicious redirection query parameters
SUSPICIOUS_REDIRECT_PARAMS = {
    "redirect", "redirect_url", "redirect_to", "next", "url",
    "return", "return_to", "dest", "destination", "target", "r", "goto",
}


def compute_levenshtein(s1: str, s2: str) -> int:
    """
    Compute Levenshtein edit distance with pure Python dynamic programming,
    using rapidfuzz if available for fast acceleration.
    """
    try:
        from rapidfuzz.distance import Levenshtein
        return Levenshtein.distance(s1, s2)
    except Exception:
        pass

    # Pure Python DP fallback
    if len(s1) < len(s2):
        return compute_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def check_typosquatting(domain_info: DomainInfo) -> List[EvidenceItem]:
    """
    Check if the registered domain is a typosquatted variant of a known brand.
    e.g. paypa1.com vs paypal.com, micros0ft.com vs microsoft.com.
    """
    evidence: List[EvidenceItem] = []
    reg_domain = domain_info.registered_domain.lower()
    clean_domain_name = domain_info.domain.lower()

    for brand_domain, brand_name in BRAND_DOMAINS.items():
        brand_clean = brand_domain.split(".")[0]

        # Skip exact legitimate match
        if reg_domain == brand_domain:
            continue

        # Check Levenshtein distance on domain SLD
        dist = compute_levenshtein(clean_domain_name, brand_clean)

        # Catch character substitutions (0 -> o, 1 -> l, etc.) and 1-2 edit distance
        is_typo = (
            (dist == 1 and len(clean_domain_name) >= 4)
            or (dist == 2 and len(clean_domain_name) >= 6)
        )

        if is_typo:
            evidence.append(
                EvidenceItem(
                    layer=1,
                    type="typosquatting",
                    severity=Severity.HIGH,
                    human_label=f"Potential typosquatting of {brand_name} ({brand_domain})",
                    raw_match=domain_info.raw_host,
                    metadata={
                        "target_brand": brand_name,
                        "legitimate_domain": brand_domain,
                        "detected_domain": reg_domain,
                        "edit_distance": dist,
                    },
                )
            )
            break  # Found primary spoofed brand

    return evidence


def check_subdomain_spoofing(domain_info: DomainInfo) -> List[EvidenceItem]:
    """
    Detects brand names situated in the subdomain rather than the true registrable domain.
    e.g. wellsfargo.com.update.xyz -> real domain is update.xyz.
    """
    evidence: List[EvidenceItem] = []
    subdomain = domain_info.subdomain.lower()
    reg_domain = domain_info.registered_domain.lower()

    if not subdomain:
        return evidence

    for brand_domain, brand_name in BRAND_DOMAINS.items():
        brand_sld = brand_domain.split(".")[0]

        # If brand name or brand domain is embedded inside the subdomain
        if (brand_sld in subdomain or brand_domain in subdomain) and reg_domain != brand_domain:
            evidence.append(
                EvidenceItem(
                    layer=1,
                    type="subdomain_spoofing",
                    severity=Severity.HIGH,
                    human_label=(
                        f"Subdomain brand impersonation: '{brand_name}' appears in subdomain, "
                        f"but actual registered domain is '{reg_domain}'"
                    ),
                    raw_match=domain_info.raw_host,
                    metadata={
                        "target_brand": brand_name,
                        "subdomain": domain_info.subdomain,
                        "actual_registered_domain": reg_domain,
                    },
                )
            )
            break

    return evidence


def check_high_risk_tld(domain_info: DomainInfo) -> List[EvidenceItem]:
    """Flag domains utilizing high-risk or commonly abused TLDs."""
    evidence: List[EvidenceItem] = []
    suffix = domain_info.suffix.lower()

    if suffix in HIGH_RISK_TLDS:
        evidence.append(
            EvidenceItem(
                layer=1,
                type="high_risk_tld",
                severity=Severity.MEDIUM,
                human_label=f"Suspicious / high-risk Top-Level Domain (.{suffix})",
                raw_match=f".{suffix}",
                metadata={"tld": suffix, "domain": domain_info.registered_domain},
            )
        )

    return evidence


def check_bare_ip_hostname(domain_info: DomainInfo) -> List[EvidenceItem]:
    """Flag URLs that use bare IP addresses instead of standard domain names."""
    evidence: List[EvidenceItem] = []
    host = domain_info.raw_host.strip("[]")
    try:
        ipaddress.ip_address(host)
        evidence.append(
            EvidenceItem(
                layer=1,
                type="bare_ip_hostname",
                severity=Severity.HIGH,
                human_label="URL uses bare numerical IP address instead of registered domain",
                raw_match=domain_info.raw_host,
                metadata={"ip": host},
            )
        )
    except ValueError:
        pass
    return evidence


def check_open_redirects_and_params(urls: List[str]) -> List[EvidenceItem]:
    """Detect open redirect parameters or deceptive query strings."""
    evidence: List[EvidenceItem] = []

    for u in urls:
        try:
            parsed = urlparse(u)
            params = parse_qs(parsed.query)

            for p_name, p_vals in params.items():
                if p_name.lower() in SUSPICIOUS_REDIRECT_PARAMS:
                    for val in p_vals:
                        if val.startswith(("http://", "https://", "//")):
                            evidence.append(
                                EvidenceItem(
                                    layer=1,
                                    type="open_redirect",
                                    severity=Severity.MEDIUM,
                                    human_label=f"Suspicious open-redirect query parameter (?{p_name}={val[:30]}...)",
                                    raw_match=f"{p_name}={val}",
                                    metadata={"url": u, "param": p_name, "target": val},
                                )
                            )
                            break
        except Exception:
            continue

    return evidence


def evaluate_layer1(normalized: NormalizedData) -> List[EvidenceItem]:
    """
    Run all Layer 1 deterministic security rules over normalized data.
    Pure, side-effect free evaluation returning discrete Evidence items.
    """
    evidence: List[EvidenceItem] = []

    # 1. Analyze all resolved domains
    for d in normalized.domains:
        # Typosquatting
        evidence.extend(check_typosquatting(d))

        # Subdomain spoofing
        evidence.extend(check_subdomain_spoofing(d))

        # High-risk TLD
        evidence.extend(check_high_risk_tld(d))

        # Bare IP hostnames
        evidence.extend(check_bare_ip_hostname(d))

        # Punycode / IDN Homograph attack
        if d.is_punycode_homograph:
            evidence.append(
                EvidenceItem(
                    layer=1,
                    type="idn_homograph",
                    severity=Severity.HIGH,
                    human_label=f"IDN Homograph / Punycode spoofing detected ({d.punycode})",
                    raw_match=d.raw_host,
                    metadata={"punycode": d.punycode, "mixed_scripts": d.has_mixed_scripts},
                )
            )

    # 2. Check for open-redirect query parameters across extracted and redirected URLs
    all_urls = list(normalized.extracted_urls)
    for chain in normalized.final_unshortened_urls.values():
        all_urls.extend(chain)

    evidence.extend(check_open_redirects_and_params(all_urls))

    # 3. Check for obfuscated/hidden HTML text
    if normalized.has_obfuscated_html:
        evidence.append(
            EvidenceItem(
                layer=1,
                type="hidden_html_obfuscation",
                severity=Severity.HIGH,
                human_label="Detected hidden / evasive HTML elements (display:none, font-size:0, or zero-width text)",
                raw_match="<hidden text elements>",
                metadata={"hidden_snippets": normalized.hidden_text[:3]},
            )
        )

    return evidence
