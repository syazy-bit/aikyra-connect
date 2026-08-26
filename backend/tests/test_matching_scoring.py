"""Pure unit tests for the Phase 4B deterministic scoring core.

No database involved — DNA/challenge/institution are lightweight fakes
shaped exactly like the ORM entities' relevant attributes.
"""

from types import SimpleNamespace

from app.services import matching_service as ms


def _dna(
    *,
    primary_domain="water_sanitation",
    secondary_domains=None,
    required_expertise=None,
    potential_solution_areas=None,
    keywords=None,
    urgency="medium",
    confidence=0.60,
):
    return SimpleNamespace(
        primary_domain=primary_domain,
        secondary_domains=secondary_domains or [],
        required_expertise=required_expertise or [],
        potential_solution_areas=potential_solution_areas or [],
        keywords=keywords or [],
        urgency=urgency,
        confidence_score=confidence,
    )


def _challenge(location="Anantapur, Andhra Pradesh"):
    return SimpleNamespace(location=location)


def _institution(
    *,
    domains=None,
    capabilities=None,
    location="Anantapur, Andhra Pradesh",
    name="Test University",
):
    return SimpleNamespace(
        domains=domains or [],
        capabilities=capabilities or {},
        location=location,
        name=name,
    )


# --- Eligibility ---------------------------------------------------------------


def test_eligible_dna():
    assert ms.is_eligible_dna(_dna()) is True


def test_ineligible_when_no_primary_domain():
    assert ms.is_eligible_dna(_dna(primary_domain=None)) is False


def test_ineligible_below_confidence_threshold():
    assert ms.is_eligible_dna(_dna(confidence=0.44)) is False
    assert ms.is_eligible_dna(_dna(confidence=0.45)) is True


def test_ineligible_when_dna_missing():
    assert ms.is_eligible_dna(None) is False


# --- Factor 1: domain relevance (max 35) -----------------------------------------


def test_primary_domain_exact_points():
    match = ms.match_institution(_dna(), _challenge(), _institution(domains=["water_sanitation"]))
    assert match.breakdown["domain"]["points"] == 25
    assert match.breakdown["domain"]["detail"] == ["Water & Sanitation"]


def test_primary_plus_two_secondary_hits_maximum_domain_points():
    match = ms.match_institution(
        _dna(secondary_domains=["agriculture", "energy"]),
        _challenge(),
        _institution(domains=["water_sanitation", "agriculture", "energy"]),
    )
    assert match.breakdown["domain"]["points"] == 35
    assert len(match.breakdown["domain"]["detail"]) == 3


def test_secondary_only_match_scores_five_per_hit():
    match = ms.match_institution(
        _dna(secondary_domains=["agriculture"]),
        _challenge(),
        _institution(domains=["agriculture"]),
    )
    assert match.breakdown["domain"]["points"] == 5


def test_secondary_beyond_cap_ignored():
    # DNA never carries >2 secondaries, but the scorer must stay safe.
    match = ms.match_institution(
        _dna(secondary_domains=["agriculture", "energy", "education"]),
        _challenge(),
        _institution(
            domains=[
                "water_sanitation",
                "agriculture",
                "energy",
                "education",
            ]
        ),
    )
    assert match.breakdown["domain"]["points"] == 35  # 25 + 5 + 5 (third ignored)


def test_no_domain_overlap_zero_domain_points_and_blocks_urgency():
    match = ms.match_institution(
        _dna(urgency="critical"),
        _challenge(),
        _institution(domains=["education"]),
    )
    assert match.breakdown["domain"]["points"] == 0
    assert match.breakdown["urgency"]["points"] == 0
    assert match.score < ms.MIN_MATCH_SCORE


# --- Factor 2: expertise overlap ratio math (max 25) ------------------------------


def test_expertise_full_ratio():
    match = ms.match_institution(
        _dna(required_expertise=["Hydrology", "IoT sensing"]),
        _challenge(),
        _institution(capabilities={"expertise": ["hydrology", "iot sensing", "gis"]}),
    )
    assert match.breakdown["expertise"]["points"] == 25
    assert set(match.breakdown["expertise"]["detail"]) == {"Hydrology", "IoT sensing"}


def test_expertise_half_ratio_rounds_half_up():
    # 2 of 4 matched → 12.5 → 13 (documented half-up rule)
    match = ms.match_institution(
        _dna(
            required_expertise=[
                "Hydrology",
                "IoT sensing",
                "Robotics",
                "Carpentry",
            ]
        ),
        _challenge(),
        _institution(capabilities={"expertise": ["Hydrology", "IoT sensing"]}),
    )
    assert match.breakdown["expertise"]["points"] == 13


def test_expertise_one_of_two_matches_rounds_up_to_thirteen():
    match = ms.match_institution(
        _dna(required_expertise=["Hydrology", "Robotics"]),
        _challenge(),
        _institution(capabilities={"disciplines": ["hydrology engineering"]}),
    )
    assert match.breakdown["expertise"]["points"] == 13  # 12.5 → 13


def test_expertise_partial_token_match_counts():
    # "Data Science" shares token "science" with "Computer Science"
    match = ms.match_institution(
        _dna(required_expertise=["Data Science"]),
        _challenge(),
        _institution(capabilities={"expertise": ["Computer Science"]}),
    )
    assert match.breakdown["expertise"]["points"] == 25


def test_expertise_no_required_items_means_zero_without_error():
    match = ms.match_institution(
        _dna(required_expertise=[]),
        _challenge(),
        _institution(capabilities={"expertise": ["anything"]}),
    )
    assert match.breakdown["expertise"]["points"] == 0


def test_expertise_empty_capability_sections_safe():
    match = ms.match_institution(
        _dna(required_expertise=["Hydrology"]),
        _challenge(),
        _institution(capabilities={}),
    )
    assert match.breakdown["expertise"]["points"] == 0
    assert match.breakdown["research"]["points"] == 0


# --- Factor 3: research / solution capability ratio math (max 15) ------------------


def test_research_ratio_exact_thirds():
    match = ms.match_institution(
        _dna(potential_solution_areas=["Water purification", "Desalination", "Reuse"]),
        _challenge(),
        _institution(
            capabilities={
                "research_areas": ["low-cost water purification"],
                "technologies": ["Reverse osmosis desalination"],
            }
        ),
    )
    assert match.breakdown["research"]["points"] == 10  # 2 of 3 → 10.0


def test_research_third_hits_exact_five():
    match = ms.match_institution(
        _dna(potential_solution_areas=["Water purification", "A", "B"]),
        _challenge(),
        _institution(capabilities={"technologies": ["water purification unit"]}),
    )
    assert match.breakdown["research"]["points"] == 5


# --- Factor 4: facilities (max 5) ---------------------------------------------------


def test_facilities_two_matches_four_points():
    match = ms.match_institution(
        _dna(
            potential_solution_areas=["Water quality monitoring"],
            required_expertise=["Hydrology"],
        ),
        _challenge(),
        _institution(
            capabilities={
                "facilities": ["Water Testing Lab", "Hydrology Field Station"]
            }
        ),
    )
    assert match.breakdown["facilities"]["points"] == 4


def test_facilities_capped_at_five():
    match = ms.match_institution(
        _dna(
            potential_solution_areas=["Water purification"],
            required_expertise=["Hydrology", "Chemistry"],
        ),
        _challenge(),
        _institution(
            capabilities={
                "facilities": [
                    "Water Testing Lab",
                    "Hydrology Lab",
                    "Chemistry Lab",
                ]
            }
        ),
    )
    assert match.breakdown["facilities"]["points"] == 5


def test_unrelated_facilities_score_zero():
    match = ms.match_institution(
        _dna(potential_solution_areas=["Water purification"], keywords=[]),
        _challenge(),
        _institution(capabilities={"facilities": ["Robotics Workshop"]}),
    )
    assert match.breakdown["facilities"]["points"] == 0


# --- Factor 5: track record (max 5) --------------------------------------------------


def test_project_experience_hit_scores_five():
    match = ms.match_institution(
        _dna(keywords=["borewell", "water"], required_expertise=[]),
        _challenge(),
        _institution(
            capabilities={"project_experience": ["Village borewell audits 2025"]}
        ),
    )
    assert match.breakdown["track_record"]["points"] == 5
    assert match.breakdown["track_record"]["detail"] == [
        "Village borewell audits 2025"
    ]


def test_unrelated_experience_scores_zero():
    match = ms.match_institution(
        _dna(keywords=["borewell"], required_expertise=[]),
        _challenge(),
        _institution(capabilities={"project_experience": ["Mall construction"]}),
    )
    assert match.breakdown["track_record"]["points"] == 0


# --- Factor 6: geographic relevance (max 10) ------------------------------------------


def test_location_shared_tokens_scale_and_cap():
    one = ms.match_institution(
        _dna(), _challenge("Anantapur district"), _institution(location="Anantapur")
    )
    assert one.breakdown["location"]["points"] == 4

    two = ms.match_institution(
        _dna(),
        _challenge("Anantapur, Andhra Pradesh"),
        _institution(location="Anantapur Andhra"),
    )
    assert two.breakdown["location"]["points"] == 8

    three = ms.match_institution(
        _dna(),
        _challenge("Anantapur, Andhra Pradesh"),
        _institution(location="Anantapur Andhra Pradesh campus"),
    )
    assert three.breakdown["location"]["points"] == 10


def test_location_stop_words_never_create_matches():
    match = ms.match_institution(
        _dna(), _challenge("Near the main road"), _institution(location="Main Road")
    )
    assert match.breakdown["location"]["points"] == 0
    assert match.breakdown["location"]["detail"] == []


def test_location_junk_or_disjoint_locations_zero():
    match = ms.match_institution(
        _dna(), _challenge("xyzzy"), _institution(location="qwerty")
    )
    assert match.breakdown["location"]["points"] == 0


# --- Factor 7: urgency modifier (max 5) ----------------------------------------------


def test_urgency_critical_with_domain_match():
    match = ms.match_institution(
        _dna(urgency="critical"), _challenge(), _institution(domains=["water_sanitation"])
    )
    assert match.breakdown["urgency"]["points"] == 5


def test_urgency_high_with_domain_match():
    match = ms.match_institution(
        _dna(urgency="high"), _challenge(), _institution(domains=["water_sanitation"])
    )
    assert match.breakdown["urgency"]["points"] == 3


def test_urgency_medium_low_score_zero():
    for level in ("medium", "low"):
        match = ms.match_institution(
            _dna(urgency=level), _challenge(), _institution(domains=["water_sanitation"])
        )
        assert match.breakdown["urgency"]["points"] == 0


def test_urgency_gated_on_domain_relevance():
    match = ms.match_institution(
        _dna(urgency="critical"),
        _challenge(),
        _institution(domains=["education"]),  # no domain overlap with water challenge
    )
    assert match.breakdown["urgency"]["points"] == 0


# --- Score invariants, reasons, determinism -------------------------------------------


def _rich_fixture():
    dna = _dna(
        secondary_domains=["agriculture", "energy"],
        required_expertise=["Hydrology", "IoT sensing"],
        potential_solution_areas=["Water purification", "Low-cost sensing"],
        keywords=["borewell", "water"],
        urgency="critical",
    )
    institution = _institution(
        domains=["water_sanitation", "agriculture", "energy"],
        capabilities={
            "expertise": ["Hydrology", "IoT sensing"],
            "disciplines": ["Environmental Engineering"],
            "research_areas": ["Water purification", "Low-cost sensing"],
            "technologies": ["Remote sensing"],
            "facilities": [
                "Water Testing Lab",
                "Hydrology Field Lab",
                "Purification Pilot Plant",
            ],
            "project_experience": ["Village borewell audits 2025"],
        },
    )
    return ms.match_institution(dna, _challenge(), institution)


def test_breakdown_sum_equals_score():
    match = _rich_fixture()
    total = sum(factor["points"] for factor in match.breakdown.values())
    assert total == match.score


def test_score_clamped_between_0_and_100():
    match = _rich_fixture()
    assert 0 <= match.score <= 100
    # The rich fixture saturates every factor.
    assert match.score == 100


def test_every_nonzero_factor_has_reason():
    match = _rich_fixture()
    assert match.reasons, "a strong fixture must produce human-readable reasons"
    joined = " ".join(match.reasons).lower()
    if match.breakdown["domain"]["points"]:
        assert "works in" in joined
    if match.breakdown["expertise"]["points"]:
        assert "expertise includes" in joined
    if match.breakdown["facilities"]["points"]:
        assert "facilities include" in joined
    if match.breakdown["track_record"]["points"]:
        assert "prior experience" in joined
    if match.breakdown["location"]["points"]:
        assert "located near" in joined


def test_zero_factors_have_empty_details_but_present_keys():
    match = ms.match_institution(
        _dna(primary_domain="education"),
        _challenge("Somewhere"),
        _institution(domains=[], capabilities={}, location="Elsewhere"),
    )
    assert set(match.breakdown.keys()) == {
        "domain",
        "expertise",
        "research",
        "facilities",
        "track_record",
        "location",
        "urgency",
    }
    for factor in match.breakdown.values():
        if factor["points"] == 0:
            assert factor["detail"] == []


def test_deterministic_output():
    first = _rich_fixture()
    second = _rich_fixture()
    assert first.score == second.score
    assert first.breakdown == second.breakdown
    assert first.reasons == second.reasons


def test_sort_matches_score_desc_then_name_asc():
    a = ms.InstitutionMatch(_institution(name="beta college"), 40, {}, [])
    b = ms.InstitutionMatch(_institution(name="Alpha College"), 40, {}, [])
    c = ms.InstitutionMatch(_institution(name="gamma institute"), 55, {}, [])
    ordered = ms.sort_matches([a, b, c])
    assert [m.institution.name for m in ordered] == [
        "gamma institute",
        "Alpha College",
        "beta college",
    ]


def test_matcher_version_declared():
    assert isinstance(ms.MATCHER_VERSION, str) and ms.MATCHER_VERSION
