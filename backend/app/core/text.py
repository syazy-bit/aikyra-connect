"""Shared text utilities.

Single source of truth for generic location stop-words and tokenization,
used by both discovery filtering and related-challenge scoring so the two
features can never drift apart.
"""

import re

# Generic geographic/administrative words carry no location identity;
# they must never create location evidence on their own.
LOCATION_STOP_WORDS = frozenset(
    {"district", "block", "near", "main", "road", "street", "nagar"}
)

# Tokens shorter than this are treated as noise (typos, initials, state-code
# fragments like "ka") and never drive location matching.
MIN_LOCATION_TOKEN_LENGTH = 3

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def extract_location_tokens(location: str | None) -> set[str]:
    """Meaningful location tokens from free text.

    Lowercases, splits on non-alphanumeric boundaries (so punctuation and
    wildcard characters are stripped rather than matched), removes generic
    stop-words, and drops sub-minimum-length noise tokens. Deterministic.
    """
    words = _TOKEN_PATTERN.findall((location or "").lower())
    return {
        word
        for word in words
        if word not in LOCATION_STOP_WORDS and len(word) >= MIN_LOCATION_TOKEN_LENGTH
    }
