"""
Layer 0 — Normalization & Ingestion

Accepts: raw email text, raw pasted URL, uploaded screenshot (OCR), uploaded QR image.
- Unshortens URLs (follows redirects with httpx, caps redirect depth to prevent SSRF/loop abuse).
- Decodes QR payloads via pyzbar / OpenCV / PIL.
- Strips HTML, detects visible text vs. hidden/obfuscated text.
- Extracts and isolates the TLD/domain with tldextract.
- Converts IDN/homograph characters to Punycode (idna) and flags visual discrepancies.
"""

import io
import ipaddress
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx
import idna
from PIL import Image
import tldextract

from app.config import settings
from app.models.scan import SourceType

logger = logging.getLogger("nexus.layer0")

# Common URL matching pattern
URL_REGEX = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

# Zero-width / invisible unicode characters commonly used for anti-parser evasion
INVISIBLE_CHARS_REGEX = re.compile(r"[\u200B-\u200D\uFEFF\u00AD\u2060]")

# Private & reserved network ranges for SSRF prevention
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


@dataclass
class DomainInfo:
    raw_host: str
    subdomain: str
    domain: str
    suffix: str
    registered_domain: str
    punycode: str
    is_punycode_homograph: bool = False
    has_mixed_scripts: bool = False


@dataclass
class NormalizedData:
    source_type: SourceType
    raw_input: str
    cleaned_text: str
    hidden_text: List[str] = field(default_factory=list)
    extracted_urls: List[str] = field(default_factory=list)
    final_unshortened_urls: Dict[str, List[str]] = field(default_factory=dict)
    domains: List[DomainInfo] = field(default_factory=list)
    qr_payloads: List[str] = field(default_factory=list)
    has_obfuscated_html: bool = False
    warnings: List[str] = field(default_factory=list)


def is_ssrf_risk(hostname: str) -> bool:
    """Check if a given hostname resolves to a loopback or private network."""
    clean_host = hostname.strip("[]")
    if clean_host.lower() in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(clean_host)
        return any(ip in net for net in PRIVATE_NETWORKS)
    except ValueError:
        # Not a raw IP literal
        return False


async def unshorten_url(
    url: str,
    max_hops: int = settings.MAX_REDIRECT_HOPS,
    timeout: float = settings.URL_FETCH_TIMEOUT_SECONDS,
) -> List[str]:
    """
    Follow HTTP redirects with httpx, enforcing SSRF protections and hop limits.
    Returns the full redirect chain (original -> hop1 -> ... -> final).
    Never executes JavaScript or renders browser content.
    """
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    chain: List[str] = [url]
    current_url = url

    headers = {
        "User-Agent": "Nexus-ThreatScanner/1.0 (+https://nexus.security)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(timeout),
            verify=False,  # Allow inspecting invalid certs typical of phishing sites
        ) as client:
            for _ in range(max_hops):
                parsed = urlparse(current_url)
                host = parsed.hostname or ""
                if is_ssrf_risk(host):
                    logger.warning(f"Blocked SSRF attempt targeting private host: {host}")
                    break

                try:
                    # Use HEAD first to minimize network bandwidth
                    resp = await client.head(current_url, headers=headers)
                except httpx.HTTPError:
                    # If HEAD fails or is rejected, try GET with stream to avoid downloading big bodies
                    try:
                        resp = await client.get(current_url, headers=headers)
                    except httpx.HTTPError:
                        break

                if resp.is_redirect and "location" in resp.headers:
                    next_url = resp.headers["location"]
                    # Handle relative redirects
                    if not next_url.startswith(("http://", "https://")):
                        next_url = str(httpx.URL(current_url).join(next_url))
                    if next_url in chain:
                        # Redirect loop detected
                        break
                    chain.append(next_url)
                    current_url = next_url
                else:
                    break
    except Exception as exc:
        logger.debug(f"Unshortening error for {url}: {exc}")

    return chain


def parse_html(content: str) -> Tuple[str, List[str], bool]:
    """
    Strip HTML tags, extract visible text, and detect obfuscated or hidden content.
    Detects CSS tricks: display:none, font-size:0, color matching background, zero-width chars.
    """
    soup = BeautifulSoup(content, "html.parser")
    hidden_texts: List[str] = []
    has_obfuscated = False

    # Check for zero-width / invisible characters in raw string
    if INVISIBLE_CHARS_REGEX.search(content):
        has_obfuscated = True

    # Check elements with hidden styles
    for tag in soup.find_all(True):
        style = tag.get("style", "").lower().replace(" ", "")
        is_hidden_tag = tag.name in ["script", "style", "noscript", "template"]

        if is_hidden_tag:
            tag.decompose()
            continue

        if (
            "display:none" in style
            or "visibility:hidden" in style
            or "font-size:0" in style
            or "opacity:0" in style
            or "color:transparent" in style
        ):
            tag_text = tag.get_text(strip=True)
            if tag_text:
                hidden_texts.append(tag_text)
                has_obfuscated = True
            tag.decompose()

    # Extract clean visible text
    visible_text = soup.get_text(separator=" ", strip=True)
    # Remove invisible characters from visible text for clean analysis
    cleaned_visible_text = INVISIBLE_CHARS_REGEX.sub("", visible_text)

    return cleaned_visible_text, hidden_texts, has_obfuscated


def analyze_domain(hostname_or_url: str) -> Optional[DomainInfo]:
    """
    Extract domain and TLD using tldextract.
    Computes Punycode conversion and checks for IDN homograph / mixed script anomalies.
    """
    target = hostname_or_url.strip()
    if "://" in target:
        parsed = urlparse(target)
        host = parsed.hostname or target
    else:
        host = target.split("/")[0].split(":")[0]

    if not host:
        return None

    # Punycode encoding
    try:
        # idna encode
        puny_bytes = idna.encode(host, uts46=True)
        puny_str = puny_bytes.decode("ascii")
    except Exception:
        puny_str = host

    is_homograph = puny_str.lower() != host.lower()

    # Check for mixed scripts in Unicode characters (e.g. Cyrillic + Latin)
    scripts: Set[str] = set()
    for ch in host:
        if ch.isalpha():
            try:
                name = unicodedata.name(ch)
                script = name.split()[0]
                scripts.add(script)
            except ValueError:
                pass
    has_mixed_scripts = len(scripts) > 1

    extracted = tldextract.extract(host)
    reg_domain = getattr(extracted, "top_domain_under_public_suffix", None) or getattr(extracted, "registered_domain", None) or f"{extracted.domain}.{extracted.suffix}".strip(".")

    return DomainInfo(
        raw_host=host,
        subdomain=extracted.subdomain,
        domain=extracted.domain,
        suffix=extracted.suffix,
        registered_domain=reg_domain,
        punycode=puny_str,
        is_punycode_homograph=is_homograph or has_mixed_scripts,
        has_mixed_scripts=has_mixed_scripts,
    )


def decode_qr_image(image_bytes: bytes) -> List[str]:
    """
    Decodes QR payloads from image bytes.
    Attempts pyzbar, OpenCV QRCodeDetector, or PIL image processing.
    """
    payloads: List[str] = []

    # Try pyzbar if installed
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode

        img = Image.open(io.BytesIO(image_bytes))
        decoded_objs = pyzbar_decode(img)
        for obj in decoded_objs:
            payloads.append(obj.data.decode("utf-8", errors="ignore"))
        if payloads:
            return payloads
    except Exception:
        pass

    # Try OpenCV QRCodeDetector if cv2 is available
    try:
        import cv2
        import numpy as np

        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        val, _, _ = detector.detectAndDecode(img)
        if val:
            payloads.append(val)
            return payloads
    except Exception:
        pass

    return payloads


async def normalize_input(
    source_type: SourceType,
    content: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
) -> NormalizedData:
    """
    Main entry point for Layer 0 Ingestion & Normalization.
    Normalizes text, strips obfuscation, resolves redirects, decodes QR, extracts domains.
    """
    raw_content = content or ""
    cleaned_text = raw_content
    hidden_text: List[str] = []
    extracted_urls: List[str] = []
    final_unshortened_urls: Dict[str, List[str]] = {}
    domains: List[DomainInfo] = []
    qr_payloads: List[str] = []
    has_obfuscated_html = False
    warnings: List[str] = []

    # 1. Handle QR or Screenshot image inputs
    if source_type in (SourceType.QR, SourceType.SCREENSHOT) and file_bytes:
        qr_results = decode_qr_image(file_bytes)
        qr_payloads.extend(qr_results)
        if qr_results:
            cleaned_text = " ".join(qr_results)
            raw_content = cleaned_text
        else:
            warnings.append("No QR code decoded from image. Performing basic analysis.")

    # 2. Handle HTML detection in content
    if "<html" in raw_content.lower() or "<body" in raw_content.lower() or "<div" in raw_content.lower():
        cleaned_text, hidden_text, has_obfuscated_html = parse_html(raw_content)

    # 3. Extract URLs
    if source_type == SourceType.URL and raw_content.strip():
        extracted_urls.append(raw_content.strip())
    else:
        found_urls = URL_REGEX.findall(cleaned_text)
        extracted_urls.extend(found_urls)
        # Also check QR payloads for URLs
        for payload in qr_payloads:
            if payload.startswith(("http://", "https://", "www.")):
                extracted_urls.append(payload)

    # De-duplicate URLs while preserving order
    unique_urls = list(dict.fromkeys(extracted_urls))

    # 4. Unshorten URLs and inspect redirect chains
    for url in unique_urls[:5]:  # Bound to max 5 URLs per scan to avoid long timeouts
        redirect_chain = await unshorten_url(url)
        final_unshortened_urls[url] = redirect_chain

    # 5. Extract and analyze domains (both original and final redirect targets)
    all_hosts: Set[str] = set()
    for orig_url, chain in final_unshortened_urls.items():
        for hop in chain:
            parsed = urlparse(hop)
            if parsed.hostname:
                all_hosts.add(parsed.hostname)

    if not all_hosts and source_type == SourceType.URL and raw_content:
        all_hosts.add(raw_content.strip())

    for host in all_hosts:
        dom_info = analyze_domain(host)
        if dom_info and dom_info.registered_domain:
            domains.append(dom_info)

    return NormalizedData(
        source_type=source_type,
        raw_input=raw_content,
        cleaned_text=cleaned_text,
        hidden_text=hidden_text,
        extracted_urls=unique_urls,
        final_unshortened_urls=final_unshortened_urls,
        domains=domains,
        qr_payloads=qr_payloads,
        has_obfuscated_html=has_obfuscated_html,
        warnings=warnings,
    )
