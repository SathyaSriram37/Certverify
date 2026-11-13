import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def clean_name(raw: str) -> Optional[str]:
    """Cleans names from surrounding titles, symbols, and artifacts."""
    if not raw:
        return None
    # Strip salutations and trailing punctuation
    cleaned = re.sub(
        r"^(?i:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Er\.?|Miss)\s*",
        "",
        raw.strip(" .,:-_/\"'"),
    ).strip(" .,:-_/\"'")
    # Remove leading 'that ' or 'to '
    cleaned = re.sub(r"^(?i:that|to|for|of)\s+", "", cleaned).strip()
    
    # Filter out false positives
    disallowed = [
        "certificate", "completion", "achievement", "participation", "masterclass",
        "successfully", "successful", "excellence", "recognition", "award",
        "iso 9001", "quality management", "international", "standard", "accredited",
        "training program", "workshop", "webinar", "course"
    ]
    if any(d in cleaned.lower() for d in disallowed) or len(cleaned) < 3 or len(cleaned) > 60:
        return None
    return cleaned


def parse_date(date_str: str) -> Optional[datetime]:
    """Parses various date formats safely."""
    clean_str = re.sub(r"(st|nd|rd|th),?", "", date_str.strip())
    clean_str = re.sub(r"\s+", " ", clean_str)

    formats = [
        "%B %d %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%d %b %Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except Exception:
            continue
    return None


def extract(text: str, layout_blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Optional[Any]]:
    """
    Enterprise Spatial & Semantic Entity Extractor.
    Extracts Candidate, Organization, Accreditation, Standards,
    Certificate Number, Issue Date, Expiration Date, and Signatories.
    """
    result: Dict[str, Optional[Any]] = {
        "candidate_name": None,
        "organization_name": None,
        "accreditation_body": None,
        "standard_code": None,
        "issue_date": None,
        "expiry_date": None,
        "is_expired": False,
        "cert_number": None,
        "website": None,
        "email": None,
        "signatory": None,
    }

    if not text:
        return result

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # --- 1. CANDIDATE / RECIPIENT NAME ---
    # Pattern A: Standard Educational / Training Awards
    name_patterns = [
        r"(?i:is\s+proudly\s+presented\s+to|presented\s+to|awarded\s+to|conferred\s+upon|certifies\s+that|certify\s+that|granted\s+to)\s+(?:(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Er\.?)\s*/?\s*(?:Ms\.?|Mrs\.?)?\s*)?([A-Z][A-Za-z0-9\.\s]{2,45}?)(?=\s+has\b|\s+of\b|\s+for\b|\s+on\b|\s+having\b|\s+who\b|\n|$)",
        r"(?i:This\s+is\s+to\s+certify\s+that)\s+(?:(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Er\.?)\s*)?([A-Z][A-Za-z0-9\.\s]{2,45}?)(?=\s+has\b|\s+of\b|\s+having\b|\n|$)",
        r"(?i:candidate\s+name|student\s+name|recipient|name)\s*[:\-]\s*([A-Z][A-Za-z0-9\.\s]{2,45})",
    ]
    for pat in name_patterns:
        m = re.search(pat, text)
        if m:
            cand = clean_name(m.group(1))
            if cand:
                result["candidate_name"] = cand
                break

    # Pattern B: ISO / Corporate Certified Entity ("Management System of XYZ Pvt Ltd...")
    iso_entity_patterns = [
        r"(?i:management\s+system\s+of|quality\s+management\s+system\s+of|certified\s+that\s+the\s+management\s+system\s+of)\s*[:\-]?\s*([A-Z][A-Za-z0-9\.\,\s\-]{3,65}?)(?=\s+has\s+been\s+assessed|\s+conforms|\s+for\s+the\s+following|\n\n|\n)",
        r"(?i:this\s+is\s+to\s+certify\s+that\s+the\s+operations\s+of)\s*[:\-]?\s*([A-Z][A-Za-z0-9\.\,\s\-]{3,65}?)(?=\s+have\s+been|\s+has\s+been|\n)",
    ]
    for pat in iso_entity_patterns:
        m = re.search(pat, text)
        if m:
            entity_name = m.group(1).strip(" .,-")
            if entity_name and len(entity_name) >= 3:
                result["candidate_name"] = entity_name  # The certified client/company
                break

    # Pattern C: Layout-Aware Spatial Extraction (if available)
    if not result["candidate_name"] and layout_blocks:
        # Candidate names on certificates are typically in the middle vertical zone (30% to 70% height) with large font
        middle_blocks = [
            b for b in layout_blocks
            if b.get("is_heading") or b.get("font_size", 0) >= 14.0
        ]
        for mb in middle_blocks:
            c_text = mb.get("text", "").strip()
            # If not matching certificate heading
            if not any(k in c_text.lower() for k in ["certificate", "completion", "achievement", "participation", "international", "quality"]):
                cand = clean_name(c_text)
                if cand and len(cand.split()) in [2, 3, 4]:
                    result["candidate_name"] = cand
                    break

    # --- 2. STANDARDS & ACCREDITATION ---
    standard_match = re.search(
        r"\b(ISO(?:\s*[/_]?\s*IEC)?\s*(?:9001|14001|27001|45001|22000|17025)(?::\d{4})?|CMMI(?:\s*DEV)?\s*Level\s*[1-5]|SOC\s*2\s*Type\s*(?:I|II))\b",
        text,
        re.IGNORECASE,
    )
    if standard_match:
        result["standard_code"] = standard_match.group(0).upper().replace("  ", " ")

    accred_match = re.search(
        r"\b(IAF|UKAS|NABCB|ANAB|DAkkS|JAS-ANZ|ANSI|AICTE|UGC|NAAC|NBA|NABL)\b",
        text,
    )
    if accred_match:
        result["accreditation_body"] = accred_match.group(1).upper()

    # --- 3. ISSUING ORGANIZATION ---
    org_kws = [
        "limited", "private", "pvt", "ltd", "inc", "technologies", "university",
        "college", "institute", "school", "corp", "academy", "foundation",
        "corporation", "solutions", "labs", "global certifications",
        "registrars", "quality cert", "bureau veritas", "tuv", "bsi", "dnv", "sgs",
        "amazon web services", "google", "microsoft", "cisco", "oracle", "udemy", "coursera"
    ]
    ignore_headings = [
        "certificate of", "statement of", "award of", "diploma of",
        "marksheet", "transcript", "provisional certificate", "verification report"
    ]

    matched_org = None
    for line in lines:
        l_lower = line.lower()
        if any(ig in l_lower for ig in ignore_headings):
            continue
        if any(k in l_lower for k in org_kws):
            cleaned = re.sub(
                r"^(?i:conducted\s+by|issued\s+by|organized\s+by|presented\s+by|authorized\s+by|certified\s+by|assessment\s+by|at|from)\s*[:\-]?\s*",
                "",
                line,
            ).strip(". ,-")
            # Ensure it's not the candidate name we already found
            if cleaned and cleaned.lower() != (result["candidate_name"] or "").lower() and len(cleaned) >= 3:
                matched_org = cleaned
                break

    if not matched_org and lines:
        # Fallback to the top prominent line
        for line in lines[:4]:
            if not any(ig in line.lower() for ig in ignore_headings) and len(line) >= 4:
                matched_org = line.strip(". ,-")
                break

    result["organization_name"] = matched_org

    # --- 4. DATES (ISSUE DATE & EXPIRATION DATE) ---
    date_regex = (
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b"
        r"|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b"
        r"|\b\d{2}[-/]\d{2}[-/]\d{4}\b"
        r"|\b\d{4}[-/]\d{2}[-/]\d{2}\b"
    )

    # A: Expiry Date Context
    expiry_match = re.search(
        r"(?i:valid\s+(?:until|thru|to)|expiry\s+date|expiration\s+date|recertification\s+due|validity)\s*[:\-]?\s*(" + date_regex + ")",
        text,
    )
    if expiry_match:
        result["expiry_date"] = expiry_match.group(1).strip()
        parsed_exp = parse_date(result["expiry_date"])
        if parsed_exp and parsed_exp < datetime.now(timezone.utc).replace(tzinfo=None):
            result["is_expired"] = True

    # B: Issue Date Context
    issue_match = re.search(
        r"(?i:date\s+of\s+issue|issue\s+date|effective\s+date|registered\s+on|certified\s+since|awarded\s+on|issued\s+on|date)\s*[:\-]?\s*(" + date_regex + ")",
        text,
    )
    if issue_match:
        result["issue_date"] = issue_match.group(1).strip()
    else:
        # General date search
        all_dates = re.findall(date_regex, text, re.IGNORECASE)
        if all_dates:
            # If expiry was found, pick an earlier date for issue
            if result["expiry_date"] and len(all_dates) > 1:
                result["issue_date"] = all_dates[0].strip()
            else:
                result["issue_date"] = all_dates[-1].strip()

    # --- 5. CERTIFICATE NUMBER / CREDENTIAL ID ---
    cert_num_patterns = [
        r"(?i:certificate\s*(?:no|id|number)|cert\s*id|registration\s*(?:no|number)|license\s*no|credential\s*id|ref\s*no|document\s*id|serial\s*no)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\.\-]{3,30})",
        r"\b(ISO\s*[-/]?\s*[A-Z0-9]{4,20})\b",
        r"\b([A-Z0-9]{2,8}_[A-Z0-9]{4,16})\b",
        r"\b([A-Z]{2,4}-[0-9]{4,10})\b",
    ]
    for pat in cert_num_patterns:
        m = re.search(pat, text)
        if m:
            result["cert_number"] = m.group(1).strip(" .,-")
            break

    # --- 6. WEBSITE & EMAIL ---
    web_match = re.search(r"https?://(?:www\.)?[\w.\-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?", text)
    if web_match:
        result["website"] = web_match.group(0).strip(" .,)")
    else:
        domain_match = re.search(r"\b(?:www\.)[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}\b", text)
        if domain_match:
            result["website"] = f"https://{domain_match.group(0).strip(' .,)')}"

    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    if email_match:
        result["email"] = email_match.group(0).strip()

    # --- 7. SIGNATORY AUTHORITY ---
    sig_match = re.search(
        r"(?i:authorized\s+signatory|managing\s+director|director|lead\s+auditor|registrar|dean|controller\s+of\s+examinations|principal|president|founder)\s*[\n:\-]?\s*([A-Z][a-z]+(?: [A-Z][a-z]+){1,3})",
        text,
    )
    if sig_match:
        result["signatory"] = sig_match.group(1).strip()
    else:
        sig_rev = re.search(
            r"([A-Z][a-z]+(?: [A-Z][a-z]+){1,3})\s*\n\s*(?:Authorized\s+Signatory|Managing\s+Director|Director|Lead\s+Auditor|Registrar|Dean|Principal)",
            text,
        )
        if sig_rev:
            result["signatory"] = sig_rev.group(1).strip()

    return result
