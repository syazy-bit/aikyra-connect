"""Deterministic institution-matching baseline (Phase 4B) — NOT AI.

Given a challenge's Problem DNA, scores verified+active institutions with
explainable weighted factors. This is the institutional mirror of
`related_challenge_service.py`: named weight constants, a pure scoring
function, human-readable reasons, and no persistence.

A future embedding/semantic scorer can replace `match_institution`
without touching routes, repositories, or the response contract.
"""

import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import taxonomy
from app.core.exceptions import ConflictError, NotFoundError
from app.core.text import extract_location_tokens as _location_tokens
from app.repositories.discovery_repository import DiscoveryRepository
from app.repositories.matching_repository import MatchingRepository
from app.schemas.matching import (
    MatchItem,
    MatchedInstitution,
    MatchListResponse,
    ScoreFactor,
)

MATCHER_VERSION = "rule-match-baseline-v1"

# --- DNA eligibility (mirrors related_challenge_service.is_eligible) -----
MIN_DNA_CONFIDENCE = 0.45

# --- Candidate pool -------------------------------------------------------
MAX_CANDIDATE_POOL = 1000
MIN_CANDIDATES_AFTER_FILTER = 25
MIN_MATCH_SCORE = 15

# --- Factor maxima (total = 100) ------------------------------------------
MAX_DOMAIN_POINTS = 35
WEIGHT_PRIMARY_DOMAIN = 25
WEIGHT_PER_SECONDARY_DOMAIN = 5
MAX_SECONDARY_HITS = 2

MAX_EXPERTISE_POINTS = 25
MAX_RESEARCH_POINTS = 15
MAX_FACILITIES_POINTS = 5
FACILITY_POINTS_PER_MATCH = 2

MAX_TRACK_RECORD_POINTS = 5

LOCATION_POINTS_PER_SHARED_TOKEN = 4
MAX_LOCATION_POINTS = 10

URGENCY_BONUS_CRITICAL = 5
URGENCY_BONUS_HIGH = 3

# Tokens too generic to create phrase-overlap evidence on their own.
_GENERIC_WORDS = frozenset({"and", "of", "the", "for", "in"})
_MIN_TOKEN_LENGTH = 3

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def is_eligible_dna(dna) -> bool:
    """Only reliable DNA drives recommendations."""
    return (
        dna is not None
        and dna.primary_domain is not None
        and dna.confidence_score is not None
        and float(dna.confidence_score) >= MIN_DNA_CONFIDENCE
    )


def _phrase_tokens(phrase: str) -> set[str]:
    tokens: set[str] = set()
    for token in _WORD_PATTERN.findall(phrase.lower()):
        if len(token) < _MIN_TOKEN_LENGTH or token in _GENERIC_WORDS:
            continue
        tokens.add(token)
        # Light plural folding so "borewells" can evidence "borewell".
        if token.endswith("s") and len(token) >= 4:
            tokens.add(token[:-1])
    return tokens


def _merged_tokens(phrases: list[str]) -> set[str]:
    tokens: set[str] = set()
    for phrase in phrases:
        tokens |= _phrase_tokens(phrase)
    return tokens


def _ratio_points(max_points: int, matched_count: int, total_count: int) -> int:
    """Proportional points, rounded half-up for deterministic integers."""
    if total_count <= 0 or matched_count <= 0:
        return 0
    return int(math.floor(max_points * matched_count / total_count + 0.5))


@dataclass(frozen=True)
class InstitutionMatch:
    """Scored candidate — pure data, no ORM behavior."""

    institution: object  # Institution ORM instance
    score: int
    breakdown: dict[str, dict]
    reasons: list[str]


def match_institution(dna, challenge, institution) -> InstitutionMatch:
    """Deterministic weighted scoring of one institution against one
    challenge's Problem DNA. Returns score, factor breakdown and reasons.

    Invariant maintained by construction: sum(breakdown[factor]["points"])
    == score.
    """
    breakdown: dict[str, dict] = {}
    reasons: list[str] = []

    # 1. Domain relevance (max 35) -----------------------------------------
    inst_domains = set(institution.domains or [])
    domain_detail: list[str] = []
    domain_points = 0
    primary_domain = dna.primary_domain
    if primary_domain and primary_domain in inst_domains:
        domain_points += WEIGHT_PRIMARY_DOMAIN
        domain_detail.append(taxonomy.domain_label(primary_domain) or primary_domain)
    secondary_hits = [
        slug
        for slug in (dna.secondary_domains or [])[:MAX_SECONDARY_HITS]
        if slug in inst_domains and slug != primary_domain
    ]
    for slug in secondary_hits:
        domain_points += WEIGHT_PER_SECONDARY_DOMAIN
        domain_detail.append(taxonomy.domain_label(slug) or slug)
    breakdown["domain"] = {
        "points": min(domain_points, MAX_DOMAIN_POINTS),
        "max": MAX_DOMAIN_POINTS,
        "detail": domain_detail,
    }
    if domain_detail:
        reasons.append(f"Works in {', '.join(domain_detail)}")

    capabilities = institution.capabilities or {}

    def _factor(
        key: str,
        max_points: int,
        dna_items: list[str],
        capability_sections: list[str],
    ) -> tuple[int, list[str]]:
        """Shared ratio-based overlap for expertise/research factors."""
        items = [item for item in (dna_items or []) if isinstance(item, str)]
        reference = _merged_tokens(
            [
                entry
                for section in capability_sections
                for entry in (capabilities.get(section) or [])
                if isinstance(entry, str)
            ]
        )
        matched = [item for item in items if _phrase_tokens(item) & reference]
        points = _ratio_points(max_points, len(matched), len(items))
        detail = matched[:4]
        breakdown[key] = {"points": points, "max": max_points, "detail": detail}
        return points, detail

    # 2. Expertise overlap (max 25) ----------------------------------------
    expertise_points, expertise_matched = _factor(
        "expertise",
        MAX_EXPERTISE_POINTS,
        dna.required_expertise or [],
        ["expertise", "disciplines"],
    )
    if expertise_matched:
        reasons.append(f"Expertise includes {', '.join(expertise_matched[:3])}")

    # 3. Solution / research capability (max 15) ---------------------------
    research_points, research_matched = _factor(
        "research",
        MAX_RESEARCH_POINTS,
        dna.potential_solution_areas or [],
        ["research_areas", "technologies"],
    )
    if research_matched:
        reasons.append(f"Research & technology cover {', '.join(research_matched[:3])}")

    # 4. Facilities capability (max 5) -------------------------------------
    need_tokens = _merged_tokens(
        [str(item) for item in (dna.potential_solution_areas or [])]
        + [str(item) for item in (dna.required_expertise or [])]
    )
    facility_items = [
        entry
        for entry in (capabilities.get("facilities") or [])
        if isinstance(entry, str)
    ]
    facilities_matched = [
        item for item in facility_items if _phrase_tokens(item) & need_tokens
    ]
    facilities_points = min(
        MAX_FACILITIES_POINTS, FACILITY_POINTS_PER_MATCH * len(facilities_matched)
    )
    breakdown["facilities"] = {
        "points": facilities_points,
        "max": MAX_FACILITIES_POINTS,
        "detail": facilities_matched[:3],
    }
    if facilities_matched:
        reasons.append(f"Facilities include {', '.join(facilities_matched[:2])}")

    # 5. Track record (max 5) ----------------------------------------------
    evidence_tokens = _merged_tokens(
        [str(item) for item in (dna.keywords or [])]
        + [str(item) for item in (dna.required_expertise or [])]
    )
    experience_items = [
        entry
        for entry in (capabilities.get("project_experience") or [])
        if isinstance(entry, str)
    ]
    experience_hit = next(
        (item for item in experience_items if _phrase_tokens(item) & evidence_tokens),
        None,
    )
    track_record_points = MAX_TRACK_RECORD_POINTS if experience_hit else 0
    breakdown["track_record"] = {
        "points": track_record_points,
        "max": MAX_TRACK_RECORD_POINTS,
        "detail": [experience_hit] if experience_hit else [],
    }
    if experience_hit:
        reasons.append(f"Prior experience: {experience_hit}")

    # 6. Geographic relevance (max 10) -------------------------------------
    shared_locations = sorted(
        _location_tokens(challenge.location) & _location_tokens(institution.location)
    )
    location_points = min(
        MAX_LOCATION_POINTS,
        LOCATION_POINTS_PER_SHARED_TOKEN * len(shared_locations),
    )
    breakdown["location"] = {
        "points": location_points,
        "max": MAX_LOCATION_POINTS,
        "detail": shared_locations[:3],
    }
    if shared_locations:
        reasons.append(
            f"Located near the challenge area ({', '.join(shared_locations[:2])})"
        )

    # 7. Urgency modifier (max 5, gated on domain relevance) ----------------
    urgency_value = getattr(dna.urgency, "value", dna.urgency)
    urgency_points = 0
    if domain_points > 0:
        if urgency_value == "critical":
            urgency_points = URGENCY_BONUS_CRITICAL
        elif urgency_value == "high":
            urgency_points = URGENCY_BONUS_HIGH
    breakdown["urgency"] = {
        "points": urgency_points,
        "max": URGENCY_BONUS_CRITICAL,
        "detail": [urgency_value] if urgency_points else [],
    }
    if urgency_points:
        reasons.append(f"{urgency_value.capitalize()}-urgency challenge")

    score = min(100, max(0, sum(factor["points"] for factor in breakdown.values())))
    return InstitutionMatch(
        institution=institution,
        score=score,
        breakdown=breakdown,
        reasons=reasons,
    )


def sort_matches(matches: list[InstitutionMatch]) -> list[InstitutionMatch]:
    """Deterministic order: score descending, then name ascending."""
    return sorted(
        matches,
        key=lambda m: (-m.score, m.institution.name.lower(), m.institution.name),
    )


class MatchingService:
    """Orchestrates challenge → institution recommendations.

    Read-only by design: recommendations are computed from the current
    Problem DNA and current institution capabilities on every request —
    nothing is persisted, so rankings can never go stale.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MatchingRepository(db)
        self.discovery_repository = DiscoveryRepository(db)

    def get_matches(
        self,
        challenge_id: UUID,
        *,
        skip: int = 0,
        limit: int = 10,
    ) -> MatchListResponse:
        result = self.discovery_repository.get_with_dna(challenge_id)
        if result is None:
            raise NotFoundError("Challenge", challenge_id)
        challenge, dna = result
        if not is_eligible_dna(dna):
            raise ConflictError(
                "This challenge does not yet have reliable Problem DNA. "
                "Run analysis first."
            )

        domain_slugs = list(
            dict.fromkeys(
                [dna.primary_domain]
                + [slug for slug in (dna.secondary_domains or []) if slug]
            )
        )
        candidates, pool_size = self.repository.eligible_candidates(
            domain_slugs=domain_slugs or None,
            pool_size=MAX_CANDIDATE_POOL,
            min_after_filter=MIN_CANDIDATES_AFTER_FILTER,
        )

        scored = [
            match_institution(dna, challenge, institution)
            for institution in candidates
        ]
        scored = [m for m in scored if m.score >= MIN_MATCH_SCORE]
        ordered = sort_matches(scored)

        page = ordered[skip : skip + limit]
        items = [
            MatchItem(
                institution=MatchedInstitution.model_validate(match.institution),
                score=match.score,
                score_breakdown={
                    factor: ScoreFactor(**values)
                    for factor, values in match.breakdown.items()
                },
                reasons=match.reasons,
            )
            for match in page
        ]
        return MatchListResponse(
            challenge_id=challenge_id,
            dna_eligible=True,
            pool_size=pool_size,
            items=items,
            total=len(ordered),
            skip=skip,
            limit=limit,
        )
