from dataclasses import dataclass
from typing import Dict
import math
import re


@dataclass
class ClassificationResult:
    cert_type: str
    confidence: float
    all_scores: Dict[str, float]


TAXONOMY_WEIGHTS = {
    "ISO_COMPLIANCE": {
        "patterns": [
            (r"\biso\s*9001(?::2015)?\b", 4.0),
            (r"\biso\s*14001(?::2015)?\b", 4.0),
            (r"\biso\s*27001(?::2022)?\b", 4.0),
            (r"\biso\s*45001(?::2018)?\b", 4.0),
            (r"\bquality\s+management\s+system\b", 3.0),
            (r"\binternational\s+organization\s+for\s+standardization\b", 3.5),
            (r"\baccreditation\s+board\b", 2.5),
            (r"\biaf\b", 2.0),
            (r"\bconforms\s+to\s+the\s+requirements\b", 2.5),
            (r"\bscope\s+of\s+(?:certification|registration)\b", 2.5),
            (r"\bcertificate\s+of\s+registration\b", 2.5),
        ]
    },
    "ACADEMIC_DEGREE": {
        "patterns": [
            (r"\bdegree\s+of\s+bachelor\b", 4.0),
            (r"\bdegree\s+of\s+master\b", 4.0),
            (r"\bdoctor\s+of\s+philosophy\b", 4.0),
            (r"\bprovisional\s+certificate\b", 3.0),
            (r"\bconvocation\b", 3.0),
            (r"\bboard\s+of\s+examinations\b", 2.5),
            (r"\bcontroller\s+of\s+examinations\b", 3.0),
            (r"\bcumulative\s+grade\s+point\b", 2.5),
            (r"\bcgpa\b", 2.0),
            (r"\bmarksheet\b", 3.0),
            (r"\bacademic\s+year\b", 2.0),
            (r"\bsemester\b", 1.5),
            (r"\buniversity\b", 1.5),
        ]
    },
    "PROFESSIONAL_CERTIFICATION": {
        "patterns": [
            (r"\baws\s+certified\b", 4.0),
            (r"\bmicrosoft\s+certified\b", 4.0),
            (r"\bgoogle\s+cloud\s+certified\b", 4.0),
            (r"\bcisco\s+certified\b", 4.0),
            (r"\bcomptia\b", 4.0),
            (r"\bcredential\s*id\b", 2.5),
            (r"\bpearson\s*vue\b", 3.0),
            (r"\bcertified\s+solutions\s+architect\b", 3.5),
            (r"\bproject\s+management\s+professional\b", 4.0),
            (r"\bpmp\b", 3.0),
            (r"\bcissp\b", 4.0),
            (r"\bkubernetes\s+certified\b", 4.0),
        ]
    },
    "COURSE_COMPLETION": {
        "patterns": [
            (r"\bcertificate\s+of\s+completion\b", 3.5),
            (r"\bsuccessfully\s+completed\b", 3.0),
            (r"\bmasterclass\b", 3.0),
            (r"\bbootcamp\b", 3.0),
            (r"\bonline\s+course\b", 2.5),
            (r"\bcoursera\b", 3.0),
            (r"\budemy\b", 3.0),
            (r"\blearning\s+hours\b", 2.0),
            (r"\bhas\s+completed\s+the\s+course\b", 3.0),
        ]
    },
    "EMPLOYMENT_EXPERIENCE": {
        "patterns": [
            (r"\bexperience\s+certificate\b", 4.0),
            (r"\brelieving\s+(?:letter|order)\b", 4.0),
            (r"\bservice\s+certificate\b", 4.0),
            (r"\bwas\s+employed\s+with\b", 3.0),
            (r"\bworked\s+with\s+us\b", 3.0),
            (r"\btenure\s+of\s+employment\b", 3.0),
            (r"\bfull\s+time\s+employee\b", 2.5),
            (r"\bdesignation\b", 2.0),
            (r"\bconduct\s+and\s+character\b", 2.0),
        ]
    },
    "INTERNSHIP": {
        "patterns": [
            (r"\binternship\s+certificate\b", 4.0),
            (r"\bcompleted\s+(?:their|his|her)\s+internship\b", 4.0),
            (r"\bsummer\s+intern\b", 3.5),
            (r"\binternship\s+program\b", 3.5),
            (r"\bgraduate\s+trainee\b", 3.0),
            (r"\btrainee\b", 2.0),
        ]
    },
    "GOVERNMENT_IDENTITY": {
        "patterns": [
            (r"\bgovernment\s+of\b", 3.0),
            (r"\bdepartment\s+of\s+revenue\b", 3.5),
            (r"\btahsildar\b", 4.0),
            (r"\bcommunity\s+certificate\b", 4.0),
            (r"\bnativity\s+certificate\b", 4.0),
            (r"\bincome\s+certificate\b", 4.0),
            (r"\bbirth\s+certificate\b", 4.0),
            (r"\bgazetted\s+officer\b", 3.0),
            (r"\bdistrict\s+collector\b", 3.5),
        ]
    },
    "PARTICIPATION_ACHIEVEMENT": {
        "patterns": [
            (r"\bcertificate\s+of\s+participation\b", 4.0),
            (r"\bcertificate\s+of\s+appreciation\b", 4.0),
            (r"\bparticipated\s+in\b", 3.0),
            (r"\bhackathon\b", 3.5),
            (r"\bconference\b", 2.5),
            (r"\bseminar\b", 2.0),
            (r"\bwon\s+(?:first|second|third)\s+prize\b", 3.5),
        ]
    },
}


def classify(text: str) -> ClassificationResult:
    """
    Calibrated Multi-Class Taxonomy Classifier.
    Computes weighted pattern signals and applies Softmax normalization.
    """
    if not text:
        return ClassificationResult(
            cert_type="OTHER",
            confidence=0.0,
            all_scores={k: 0.0 for k in TAXONOMY_WEIGHTS},
        )

    text_lower = text.lower()
    raw_scores: Dict[str, float] = {}

    for cat, conf in TAXONOMY_WEIGHTS.items():
        score = 0.0
        for pattern, weight in conf["patterns"]:
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                score += weight * min(matches, 3)
        raw_scores[cat] = score

    max_cat = max(raw_scores, key=raw_scores.get)
    max_raw = raw_scores[max_cat]

    if max_raw == 0:
        return ClassificationResult(
            cert_type="GENERAL_CREDENTIAL",
            confidence=0.50,
            all_scores={k: 0.0 for k in TAXONOMY_WEIGHTS},
        )

    # Softmax probability distribution
    exp_scores = {k: math.exp(v / 3.0) for k, v in raw_scores.items()}
    sum_exp = sum(exp_scores.values())
    prob_scores = {k: round(v / sum_exp, 3) for k, v in exp_scores.items()}

    # Calibrate top confidence: High raw signals give higher confidence (e.g. 0.85-0.98)
    scaled_confidence = min(0.98, max(0.60, 0.55 + (max_raw / 18.0)))

    return ClassificationResult(
        cert_type=max_cat,
        confidence=round(scaled_confidence, 2),
        all_scores=prob_scores,
    )
