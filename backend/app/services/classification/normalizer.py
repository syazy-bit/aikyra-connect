import re


def normalize(text: str) -> str:
    """Lowercase and collapse non-alphanumeric characters to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def contains_phrase(normalized_text: str, phrase: str) -> bool:
    """Match a keyword against normalized text.

    Multi-word phrases match as substrings; single words match on word
    boundaries so 'art' does not match 'particle'.
    """
    phrase = normalize(phrase)
    if not phrase:
        return False
    if " " in phrase:
        return phrase in normalized_text
    return re.search(rf"\b{re.escape(phrase)}\b", normalized_text) is not None
