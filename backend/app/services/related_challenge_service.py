"""Deterministic related-challenge recommendations.

Phase 3 baseline — NOT AI. Scores are computed from existing Problem DNA
with explainable weights, and only challenges with sufficiently reliable
DNA (confidence >= MIN_CONFIDENCE and a primary domain) are ever suggested.
A future embedding-based scorer can replace `score_candidate` without
touching routes, repositories, or the response contract.
"""

from dataclasses import dataclass

from app.core import taxonomy
from app.core.text import extract_location_tokens as _location_tokens

MIN_CONFIDENCE = 0.45

WEIGHT_SAME_DOMAIN = 3.0
WEIGHT_SHARED_SUBDOMAIN = 2.0
WEIGHT_SECONDARY_OVERLAP = 1.0
WEIGHT_PER_SHARED_KEYWORD = 1.0
MAX_KEYWORD_SCORE = 3.0
WEIGHT_LOCATION_OVERLAP = 1.0
WEIGHT_SAME_URGENCY = 0.5


@dataclass(frozen=True)
class RelatedCandidate:
    challenge: object  # Challenge ORM instance
    dna: object        # ProblemDna ORM instance


@dataclass(frozen=True)
class RelatedChallenge:
    challenge: object
    dna: object
    score: float
    reasons: list[str]


def is_eligible(dna) -> bool:
    """Only reliable DNA participates in recommendation relationships."""
    return (
        dna is not None
        and dna.primary_domain is not None
        and dna.confidence_score is not None
        and float(dna.confidence_score) >= MIN_CONFIDENCE
    )


def _shared(values_a: list, values_b: list) -> list[str]:
    set_b = set(values_b)
    return [v for v in values_a if v in set_b]


def score_candidate(source_dna, source_challenge, candidate_dna, candidate_challenge) -> tuple[float, list[str]]:
    """Deterministic weighted similarity with human-readable reasons."""
    score = 0.0
    reasons: list[str] = []

    if candidate_dna.primary_domain == source_dna.primary_domain:
        score += WEIGHT_SAME_DOMAIN
        reasons.append(
            f"Same problem area: {taxonomy.domain_label(source_dna.primary_domain)}"
        )

    if (
        source_dna.subdomain
        and candidate_dna.subdomain == source_dna.subdomain
    ):
        score += WEIGHT_SHARED_SUBDOMAIN
        reasons.append(f"Same sub-area: {candidate_dna.subdomain}")

    source_secondary = source_dna.secondary_domains or []
    secondary_overlap = (
        [candidate_dna.primary_domain] if candidate_dna.primary_domain in source_secondary else []
    )
    if secondary_overlap:
        score += WEIGHT_SECONDARY_OVERLAP * len(secondary_overlap)
        labels = ", ".join(filter(None, (taxonomy.domain_label(s) for s in secondary_overlap)))
        reasons.append(f"Related problem areas: {labels}")

    shared_keywords = _shared(
        (source_dna.keywords or [])[:12], (candidate_dna.keywords or [])[:12]
    )
    if shared_keywords:
        keyword_score = min(MAX_KEYWORD_SCORE, WEIGHT_PER_SHARED_KEYWORD * len(shared_keywords))
        score += keyword_score
        shown = ", ".join(shared_keywords[:3])
        reasons.append(f"Shared themes: {shown}")

    if _location_tokens(source_challenge.location) & _location_tokens(candidate_challenge.location):
        score += WEIGHT_LOCATION_OVERLAP
        reasons.append("Similar location")

    if candidate_dna.urgency == source_dna.urgency:
        score += WEIGHT_SAME_URGENCY

    return round(score, 2), reasons
