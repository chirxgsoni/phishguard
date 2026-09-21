"""Unit tests for Layer 1: Deterministic Engine."""

from app.models.scan import SourceType
from app.pipeline.layer0_normalization import DomainInfo, NormalizedData
from app.pipeline.layer1_deterministic import (
    check_bare_ip_hostname,
    check_high_risk_tld,
    check_open_redirects_and_params,
    check_subdomain_spoofing,
    check_typosquatting,
    compute_levenshtein,
    evaluate_layer1,
)


def test_levenshtein_distance():
    """Verify Levenshtein distance calculations."""
    assert compute_levenshtein("paypal", "paypa1") == 1
    assert compute_levenshtein("microsoft", "micros0ft") == 1
    assert compute_levenshtein("google", "google") == 0


def test_brand_typosquatting_detection():
    """Verify typosquatting flags paypa1.com and ignores paypal.com."""
    fake_domain = DomainInfo(
        raw_host="paypa1.com",
        subdomain="",
        domain="paypa1",
        suffix="com",
        registered_domain="paypa1.com",
        punycode="paypa1.com",
    )
    ev_fake = check_typosquatting(fake_domain)
    assert len(ev_fake) == 1
    assert ev_fake[0].type == "typosquatting"
    assert ev_fake[0].metadata["target_brand"] == "PayPal"

    real_domain = DomainInfo(
        raw_host="paypal.com",
        subdomain="",
        domain="paypal",
        suffix="com",
        registered_domain="paypal.com",
        punycode="paypal.com",
    )
    ev_real = check_typosquatting(real_domain)
    assert len(ev_real) == 0


def test_subdomain_spoofing():
    """Verify wellsfargo.com.update.xyz is flagged as subdomain spoofing."""
    spoofed = DomainInfo(
        raw_host="wellsfargo.com.update.xyz",
        subdomain="wellsfargo.com",
        domain="update",
        suffix="xyz",
        registered_domain="update.xyz",
        punycode="wellsfargo.com.update.xyz",
    )
    ev = check_subdomain_spoofing(spoofed)
    assert len(ev) == 1
    assert ev[0].type == "subdomain_spoofing"
    assert ev[0].metadata["target_brand"] == "Wells Fargo"
    assert ev[0].metadata["actual_registered_domain"] == "update.xyz"


def test_high_risk_tld():
    """Verify suspicious TLDs are flagged."""
    xyz_dom = DomainInfo(
        raw_host="secure-login.xyz",
        subdomain="secure-login",
        domain="secure-login",
        suffix="xyz",
        registered_domain="secure-login.xyz",
        punycode="secure-login.xyz",
    )
    ev = check_high_risk_tld(xyz_dom)
    assert len(ev) == 1
    assert ev[0].type == "high_risk_tld"


def test_bare_ip_hostname():
    """Verify bare IP address is flagged."""
    ip_dom = DomainInfo(
        raw_host="192.0.2.1",
        subdomain="",
        domain="192.0.2.1",
        suffix="",
        registered_domain="192.0.2.1",
        punycode="192.0.2.1",
    )
    ev = check_bare_ip_hostname(ip_dom)
    assert len(ev) == 1
    assert ev[0].type == "bare_ip_hostname"


def test_open_redirect():
    """Verify open-redirect query parameter detection."""
    urls = ["https://legit-site.com/auth?redirect=https://evil-attacker.xyz/login"]
    ev = check_open_redirects_and_params(urls)
    assert len(ev) == 1
    assert ev[0].type == "open_redirect"
