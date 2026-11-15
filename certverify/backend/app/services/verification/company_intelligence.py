from dataclasses import dataclass, field
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import httpx


@dataclass
class CompanyVerificationResult:
    org_name: str
    website_provided: Optional[str]
    website_active: bool
    website_matches_org: bool
    ssl_valid: bool
    online_presence_found: bool
    search_summary: str
    mca_hint: bool
    confidence_score: float
    evidence_sources: List[str] = field(default_factory=list)


@dataclass
class ISOVerificationResult:
    claimed: bool
    status: str
    standards: List[str] = field(default_factory=list)
    evidence_found: bool = False


async def verify_company(
    org_name: Optional[str], website: Optional[str] = None
) -> CompanyVerificationResult:
    evidence: List[str] = []
    online = False
    web_active = False
    web_match = False
    ssl = False
    mca = False
    summary = ""

    if not org_name or len(org_name.strip()) < 3:
        return CompanyVerificationResult(
            org_name="",
            website_provided=website,
            website_active=False,
            website_matches_org=False,
            ssl_valid=False,
            online_presence_found=False,
            search_summary="No organization name provided",
            mca_hint=False,
            confidence_score=0.0,
            evidence_sources=[],
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=headers) as client:
        # 1. Live Web Search via DuckDuckGo HTML endpoint
        discovered_urls: List[str] = []
        try:
            r = await client.post("https://html.duckduckgo.com/html/", data={"q": org_name})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                discovered_urls = [
                    a.get("href", "")
                    for a in soup.select("a.result__url")
                    if a.get("href") and "duckduckgo.com" not in a.get("href")
                ]
                snippets = [s.get_text().strip() for s in soup.select(".result__snippet")]
                if snippets:
                    summary = " ".join(snippets[:2])[:300]
                if discovered_urls or snippets:
                    online = True
                    for u in discovered_urls[:5]:
                        evidence.append(u)
        except Exception:
            pass

        # Fallback to DuckDuckGo Instant Answer if HTML search had an issue
        if not online:
            try:
                r = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": org_name, "format": "json", "no_html": "1"},
                )
                if r.status_code == 200:
                    data = r.json()
                    abstract_url = data.get("AbstractURL")
                    if abstract_url:
                        evidence.append(abstract_url)
                        online = True
                    if data.get("RelatedTopics"):
                        online = True
                    if data.get("AbstractText"):
                        summary = data.get("AbstractText", "")[:300]
            except Exception:
                pass

        # 2. MCA / Corporate Registry Check
        # In India, registered companies appear in MCA, ZaubaCorp, TheCompanyCheck, Tofler, etc.
        registry_domains = ["mca.gov.in", "zaubacorp.com", "thecompanycheck.com", "tofler.in", "instafinancials.com"]
        for ev in evidence:
            if any(reg in ev.lower() for reg in registry_domains):
                mca = True
                break

        if not mca and online:
            try:
                r_mca = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": f"{org_name} MCA registration CIN"},
                )
                if r_mca.status_code == 200:
                    soup_mca = BeautifulSoup(r_mca.text, "html.parser")
                    mca_urls = [
                        a.get("href", "")
                        for a in soup_mca.select("a.result__url")
                        if a.get("href")
                    ]
                    mca_snippets = [s.get_text() for s in soup_mca.select(".result__snippet")]
                    has_cin = any("cin" in s.lower() or "u7" in s.lower() or "incorporat" in s.lower() for s in mca_snippets)
                    if any(any(reg in u.lower() for reg in registry_domains) for u in mca_urls) or has_cin:
                        mca = True
                        evidence.append("mca_registered_entity")
            except Exception:
                pass

        # 3. Target Website Verification
        target_web = website
        if not target_web and discovered_urls:
            # Pick first non-aggregator domain
            for u in discovered_urls:
                if not any(agg in u for agg in ["wikipedia", "facebook", "linkedin", "twitter", "instagram", "youtube", "zaubacorp"]):
                    target_web = u
                    break

        if target_web:
            if not target_web.startswith("http://") and not target_web.startswith("https://"):
                target_web = f"https://{target_web}"

            ssl = target_web.startswith("https://")
            try:
                web_resp = await client.get(target_web, timeout=6.0)
                web_active = web_resp.status_code < 400
                if web_active:
                    if target_web not in evidence:
                        evidence.insert(0, target_web)
                    # Verify name matching in page content
                    clean_org = "".join(ch for ch in org_name.lower() if ch.isalnum() or ch == " ")
                    tokens = [t for t in clean_org.split() if len(t) > 3 and t not in ["private", "limited", "company"]]
                    body_lower = web_resp.text.lower()
                    web_match = any(token in body_lower for token in tokens) if tokens else True
            except Exception:
                web_active = False

    # Calculate Enterprise Confidence
    score = 0.0
    if online:
        score += 0.45
    if web_active:
        score += 0.25
    if web_match:
        score += 0.15
    if mca:
        score += 0.15

    confidence = round(min(1.0, score), 2)

    return CompanyVerificationResult(
        org_name=org_name,
        website_provided=target_web or website,
        website_active=web_active,
        website_matches_org=web_match or (online and len(evidence) > 1),
        ssl_valid=ssl,
        online_presence_found=online,
        search_summary=summary,
        mca_hint=mca,
        confidence_score=confidence,
        evidence_sources=evidence[:6],
    )


async def verify_iso(org_name: str, ocr_text: str) -> ISOVerificationResult:
    iso_patterns = [
        "iso 9001:2015",
        "iso 9001",
        "iso 14001",
        "iso 27001",
        "iso 45001",
        "iso/iec 27001",
        "iso 22000",
        "iso certified",
    ]
    ocr_lower = ocr_text.lower()
    found = [p.upper() for p in iso_patterns if p in ocr_lower]

    evidence = False
    verified_standards = list(found)

    # 1. Search company ISO verification online
    if org_name and len(org_name.strip()) > 3:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=headers) as client:
                r = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": f"{org_name} ISO certification 9001"},
                )
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    snippets = [s.get_text() for s in soup.select(".result__snippet")]
                    for s in snippets:
                        s_lower = s.lower()
                        if "iso 9001:2015" in s_lower or "iso 9001" in s_lower:
                            evidence = True
                            if "ISO 9001:2015" not in verified_standards:
                                verified_standards.append("ISO 9001:2015")
                            break
                        elif "iso" in s_lower and "certified" in s_lower:
                            evidence = True
                            if not verified_standards:
                                verified_standards.append("ISO 9001:2015")
                            break
        except Exception:
            pass

    claimed = bool(found) or evidence

    status = (
        "EVIDENCE_FOUND"
        if evidence
        else ("CLAIMED_UNVERIFIED" if claimed else "NOT_CLAIMED")
    )

    return ISOVerificationResult(
        claimed=claimed,
        status=status,
        standards=verified_standards if verified_standards else ["ISO 9001:2015"] if evidence else [],
        evidence_found=evidence,
    )
