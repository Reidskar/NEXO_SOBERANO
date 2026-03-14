import logging
logger = logging.getLogger(__name__)

def _detect_direct_harm(content: str, file_urls: List[str]) -> Optional[str]:
    lowered = (content or "").lower()

    spam_patterns = [r"(.)\1{9,}", r"(https?://\S+\s*){6,}"]
    for pattern in spam_patterns:
        if re.search(pattern, lowered):
            return "spam"

    doxxing_patterns = [
        r"\b\d{8,}\b",  # secuencias numéricas largas
        r"[\w\.-]+@[\w\.-]+\.\w+",  # emails
        r"\b(?:direcci[oó]n|domicilio|rut|dni|pasaporte)\b",
    ]
    for pattern in doxxing_patterns:
        if re.search(pattern, lowered):
            return "doxxing"

    malware_terms = [".exe", ".bat", ".scr", "payload", "stealer", "keylogger", "ransomware"]
    if any(term in lowered for term in malware_terms):
        return "malware"

    for url in file_urls:
        u = (url or "").lower()
        if any(ext in u for ext in [".exe", ".bat", ".scr", ".dll", ".js"]):
            return "malware"

    return None
