"""Deterministic keyword/rule-based classifier.

This is an honest baseline, not AI: every output is labeled
`deterministic_baseline` with the analyzer version, and lands in
`pending_validation` (or `needs_review` when evidence is weak). It exists
to make the pipeline testable end-to-end and to give future LLM
classifiers something measurable to beat.

Confidence model
----------------
Each *distinct* matched taxonomy term adds 0.15 confidence, capped at 0.85:

    confidence = min(0.85, 0.15 * distinct_matched_terms)

Rationale: a single keyword hit is frequently a false positive (generic
words such as "water" or "power" appear in many unrelated problems), so it
must never clear the review threshold on its own. Convergent evidence from
3+ distinct terms (confidence >= 0.45) indicates the problem is genuinely
understood by the baseline and may proceed as pending_validation.
"""

import re

from app.core import taxonomy
from app.models.problem_dna import DnaSource, UrgencyLevel
from app.services.classification.normalizer import contains_phrase, normalize
from app.services.classification.schemas import ClassificationResult

_URGENT_TERMS = ("emergency", "outbreak", "epidemic", "immediate",
                 "life-threatening", "dying", "critical condition")
_HIGH_URGENCY_TERMS = ("every year", "recurring", "seasonal", "severe",
                       "frequent", "summer", "monsoon", "winter", "flood",
                       "drought", "spreading")

_GEO_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rural", ("village", "villages", "rural", "gram panchayat", "countryside", "farm")),
    ("semi_urban", ("town", "township", "semi urban", "peri urban")),
    ("urban", ("city", "urban", "municipal", "metro", "metropolitan", "slum")),
)


def _dedupe(items: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
        if len(unique) >= cap:
            break
    return unique


class RuleBasedClassifier:
    SOURCE = DnaSource.DETERMINISTIC_BASELINE
    VERSION = "rule-baseline-v1"

    def classify(self, title: str, description: str, location: str) -> ClassificationResult:
        text = normalize(f"{title} {description} {location}")

        domain_signals = self._score_domains(text)
        primary_key, primary_matches = self._select_primary(text, domain_signals)

        if primary_key is None:
            return ClassificationResult(
                primary_domain=None,
                confidence_score=0.0,
                urgency=UrgencyLevel.MEDIUM,
                signals={},
                generated_by=self.SOURCE,
            )

        domain = taxonomy.get_domain(primary_key)
        secondary = self._select_secondary(text, domain_signals, primary_key)
        subdomain, problem_type = self._resolve_subdomain(domain, text)
        matched_terms = _dedupe(
            [term for key in [primary_key, *secondary] for term in domain_signals.get(key, [])],
            cap=12,
        )

        return ClassificationResult(
            primary_domain=primary_key,
            secondary_domains=secondary,
            subdomain=subdomain,
            problem_type=problem_type or domain.problem_type,
            geographic_context=self._detect_geography(text),
            urgency=self._detect_urgency(text),
            affected_stakeholders=self._detect_stakeholders(text),
            keywords=matched_terms,
            required_expertise=self._merge_domains(
                primary_key, secondary, lambda d: list(d.expertise), cap=8
            ),
            potential_solution_areas=self._merge_domains(
                primary_key, secondary, lambda d: list(d.solution_areas), cap=8
            ),
            confidence_score=self._confidence(len(matched_terms)),
            signals={
                key: terms
                for key, terms in ((primary_key, primary_matches), *[
                    (k, domain_signals[k]) for k in secondary
                ])
                if terms
            },
            generated_by=self.SOURCE,
        )

    def _score_domains(self, text: str) -> dict[str, list[str]]:
        signals: dict[str, list[str]] = {}
        for domain in taxonomy.all_domains():
            matched = [
                keyword for keyword in domain.keywords if contains_phrase(text, keyword)
            ]
            # Subdomain keywords also count as domain evidence.
            for subdomain in domain.subdomains:
                matched.extend(
                    keyword for keyword in subdomain.keywords
                    if keyword not in matched and contains_phrase(text, keyword)
                )
            if matched:
                signals[domain.key] = matched
        return signals

    @staticmethod
    def _select_primary(
        text: str, signals: dict[str, list[str]]
    ) -> tuple[str | None, list[str]]:
        """Pick the primary domain.

        Tie-breaking (deterministic, no alphabetical bias):
        1. most matched terms,
        2. earliest first occurrence in the normalized input,
        3. domain key (unreachable in practice — final determinism guard).
        """
        if not signals:
            return None, []
        best = min(
            signals.items(),
            key=lambda kv: (-len(kv[1]), _first_evidence_index(text, kv[1]), kv[0]),
        )
        return best[0], best[1]

    @staticmethod
    def _select_secondary(
        text: str, signals: dict[str, list[str]], primary_key: str
    ) -> list[str]:
        threshold = max(1, len(signals[primary_key]) // 2)
        candidates = sorted(
            (
                (key, terms)
                for key, terms in signals.items()
                if key != primary_key and len(terms) >= threshold
            ),
            key=lambda kv: (-len(kv[1]), _first_evidence_index(text, kv[1]), kv[0]),
        )
        return [key for key, _ in candidates[:2]]

    def _resolve_subdomain(self, domain, text: str) -> tuple[str | None, str | None]:
        best_name: str | None = None
        best_type: str | None = None
        best_count = 0
        for subdomain in domain.subdomains:
            count = sum(1 for k in subdomain.keywords if contains_phrase(text, k))
            if count > best_count:
                best_name, best_type, best_count = subdomain.name, subdomain.problem_type, count
        return best_name, best_type

    @staticmethod
    def _detect_geography(text: str) -> str | None:
        counts = {
            context: sum(1 for term in terms if contains_phrase(text, term))
            for context, terms in _GEO_KEYWORDS
        }
        best = max(counts.items(), key=lambda kv: (kv[1], -list(counts).index(kv[0])))
        return best[0] if best[1] > 0 else None

    @staticmethod
    def _detect_urgency(text: str) -> UrgencyLevel:
        if any(contains_phrase(text, term) for term in _URGENT_TERMS):
            return UrgencyLevel.CRITICAL
        if any(contains_phrase(text, term) for term in _HIGH_URGENCY_TERMS):
            return UrgencyLevel.HIGH
        return UrgencyLevel.MEDIUM

    @staticmethod
    def _detect_stakeholders(text: str) -> list[str]:
        return [
            label for label, terms in taxonomy.STAKEHOLDER_KEYWORDS
            if any(contains_phrase(text, term) for term in terms)
        ]

    def _merge_domains(self, primary_key: str, secondary: list[str], pick, cap: int) -> list[str]:
        domains = [taxonomy.get_domain(primary_key)] + [
            taxonomy.get_domain(key) for key in secondary
        ]
        values: list[str] = []
        for domain in domains:
            if domain is not None:
                values.extend(pick(domain))
        return _dedupe(values, cap=cap)

    @staticmethod
    def _confidence(matched_term_count: int) -> float:
        """0.15 per distinct matched term, capped at 0.85 — see module docstring."""
        if matched_term_count == 0:
            return 0.0
        return round(min(0.85, 0.15 * matched_term_count), 2)


def _first_evidence_index(text: str, terms: list[str]) -> int:
    """Earliest position where any of the terms occurs in normalized text.

    Single words use word-boundary regex; phrases use substring find.
    Returns a large index when nothing is found (should not happen for
    already-matched terms).
    """
    starts = []
    for term in terms:
        term = normalize(term)
        if " " in term:
            starts.append(text.find(term))
        else:
            match = re.search(rf"\b{re.escape(term)}\b", text)
            starts.append(match.start() if match else len(text))
    found = [s for s in starts if s >= 0]
    return min(found) if found else len(text)
