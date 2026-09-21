"""Unit tests for Layer 0: Normalization and Ingestion."""

import pytest
from app.models.scan import SourceType
from app.pipeline.layer0_normalization import (
    analyze_domain,
    is_ssrf_risk,
    normalize_input,
    parse_html,
)


def test_ssrf_detection():
    """Verify SSRF protection flags loopback and private networks."""
    assert is_ssrf_risk("localhost") is True
    assert is_ssrf_risk("127.0.0.1") is True
    assert is_ssrf_risk("10.0.0.5") is True
    assert is_ssrf_risk("192.168.1.1") is True
    assert is_ssrf_risk("172.16.0.1") is True
    assert is_ssrf_risk("::1") is True
    assert is_ssrf_risk("google.com") is False
    assert is_ssrf_risk("8.8.8.8") is False


def test_html_obfuscation_parsing():
    """Verify extraction of hidden text and detection of evasive CSS styles."""
    html = """
    <html>
        <body>
            <p>Please review your invoice.</p>
            <div style="display: none;">hidden malicious payload</div>
            <span style="font-size:0px">stealth tracking</span>
            <p>Legitimate looking footer.</p>
        </body>
    </html>
    """
    clean, hidden, has_obfuscated = parse_html(html)
    assert "Please review your invoice." in clean
    assert "Legitimate looking footer." in clean
    assert "hidden malicious payload" not in clean
    assert "hidden malicious payload" in hidden
    assert "stealth tracking" in hidden
    assert has_obfuscated is True


def test_domain_punycode_homograph():
    """Verify Punycode conversion and homograph flagging."""
    # Cyrillic 'а' (U+0430) instead of Latin 'a'
    cyrillic_paypal = "p\u0430ypal.com"
    dom_info = analyze_domain(cyrillic_paypal)
    assert dom_info is not None
    assert dom_info.is_punycode_homograph is True
    assert "xn--" in dom_info.punycode

    # Normal domain
    normal_paypal = "paypal.com"
    norm_info = analyze_domain(normal_paypal)
    assert norm_info is not None
    assert norm_info.is_punycode_homograph is False


@pytest.mark.asyncio
async def test_normalize_input_email():
    """Verify end-to-end normalization of email content."""
    raw_email = (
        "Subject: Urgent Password Reset\n\n"
        "Please update your password at https://secure-login.update.xyz/auth?next=https://paypal.com immediately."
    )
    res = await normalize_input(source_type=SourceType.EMAIL, content=raw_email)
    assert res.source_type == SourceType.EMAIL
    assert len(res.extracted_urls) >= 1
    assert any(d.suffix == "xyz" for d in res.domains)
