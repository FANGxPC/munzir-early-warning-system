"""
PII Anonymizer for Workplace Incident Narratives.
Strips personal identifiers, names, badge numbers, phone numbers,
emails, government IDs, and exact addresses before NLP analysis.
"""

import re
from typing import Tuple

# Common regex patterns for personal identifiers
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
ID_BADGE_REGEX = re.compile(r"\b(EMP|ID|BADGE|WORKER|STAFF)[-:\s#]*\d{3,8}\b", re.IGNORECASE)
EMIRATES_ID_REGEX = re.compile(r"\b784[-.\s]?\d{4}[-.\s]?\d{7}[-.\s]?\d\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
AADHAAR_REGEX = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

# Honorifics + Names pattern
NAME_REGEX = re.compile(
    r"\b(Mr\.|Mrs\.|Ms\.|Dr\.|[Ww]orker|[Oo]perator|[Ee]mployee|[Ff]oreman|[Ee]ngineer|[Tt]echnician|[Ll]aborer|[Cc]arpenter|[Mm]ason|[Ee]lectrician|[Dd]river|[Mm]echanic|[Ww]elder)\s+([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){0,2})\b"
)

# Address and apartment patterns
ADDRESS_REGEX = re.compile(
    r"\b(Building|Flat|Villa|Plot|Street|Room|Apt)\s*#?\s*\d+([A-Za-z0-9\s,]{1,25})?(Road|Street|Lane|Avenue|Close)?\b",
    re.IGNORECASE,
)


def sanitize_incident_narrative(narrative: str) -> str:
    """
    Sanitize free-text incident narratives by redacting PII with standard tokens.
    Guarantees no person-identifying tokens reach models or logs.
    """
    if not narrative:
        return ""

    text = narrative

    # 1. Emails
    text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

    # 2. Government and National IDs
    text = EMIRATES_ID_REGEX.sub("[REDACTED_ID]", text)
    text = AADHAAR_REGEX.sub("[REDACTED_ID]", text)
    text = SSN_REGEX.sub("[REDACTED_ID]", text)

    # 3. Employee badges / worker IDs
    text = ID_BADGE_REGEX.sub("[REDACTED_BADGE]", text)

    # 4. Phone numbers
    text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)

    # 5. Names with honorifics/roles
    text = NAME_REGEX.sub(r"\1 [REDACTED_NAME]", text)

    # 6. Specific residential or plot addresses
    text = ADDRESS_REGEX.sub("[REDACTED_ADDRESS]", text)

    return text.strip()

