"""Phase 4B — matching endpoint integration tests (real PostgreSQL).

Verified+active institutions are seeded through the ORM because the public
API deliberately provides no way to reach the `verified` state before the
authentication/verification phase exists.
"""

import uuid

from app.models.institution import (
    Institution,
    InstitutionStatus,
    InstitutionType,
    InstitutionVerificationStatus,
)

WATER_CHALLENGE = {
    "title": "Village borewells failing",
    "description": (
        "Drinking water from our village borewells is contaminated and the "
        "water supply fails every summer. Open defecation and broken "
        "sanitation make it worse for families."
    ),
    "location": "Anantapur, Andhra Pradesh",
}

WEAK_CHALLENGE = {
    "title": "Strange noises near the community hall",
    "description": "People report unusual sounds around the old hall at night.",
    "location": "Somewhere",
}


def _seed_institution(
    db_session,
    *,
    name,
    domains=None,
    capabilities=None,
    location="Anantapur, Andhra Pradesh",
    verification_status=InstitutionVerificationStatus.VERIFIED,
    status=InstitutionStatus.ACTIVE,
    institution_type=InstitutionType.UNIVERSITY,
):
    institution = Institution(
        id=uuid.uuid4(),
        name=name,
        institution_type=institution_type,
        location=location,
        domains=domains or [],
        capabilities=capabilities or {},
        status=status,
        verification_status=verification_status,
    )
    db_session.add(institution)
    db_session.commit()
    return institution


def _create_water_challenge(client):
    created = client.post("/api/challenges", json=WATER_CHALLENGE)
    assert created.status_code == 201
    body = created.json()
    analyzed = client.post(f"/api/challenges/{body['id']}/analyze")
    assert analyzed.status_code == 200
    dna = analyzed.json()["dna"]
    assert dna["primary_domain"] is not None
    assert float(dna["confidence_score"]) >= 0.45
    return body


# --- Error paths -------------------------------------------------------------------


def test_unknown_challenge_returns_404(client):
    response = client.get(f"/api/challenges/{uuid.uuid4()}/matches")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_malformed_uuid_returns_422(client):
    response = client.get("/api/challenges/not-a-uuid/matches")
    assert response.status_code == 422


def test_missing_dna_returns_409(client):
    created = client.post("/api/challenges", json=WATER_CHALLENGE)
    response = client.get(f"/api/challenges/{created.json()['id']}/matches")
    assert response.status_code == 409
    assert "reliable Problem DNA" in response.json()["detail"]


def test_low_confidence_dna_returns_409(client):
    created = client.post("/api/challenges", json=WEAK_CHALLENGE)
    cid = created.json()["id"]
    analyzed = client.post(f"/api/challenges/{cid}/analyze")
    assert analyzed.status_code == 200  # DNA exists but is unreliable
    response = client.get(f"/api/challenges/{cid}/matches")
    assert response.status_code == 409
    assert "reliable Problem DNA" in response.json()["detail"]


# --- Eligibility gate ----------------------------------------------------------------


def test_empty_eligible_pool_returns_200_with_zero_pool(client):
    created = _create_water_challenge(client)
    response = client.get(f"/api/challenges/{created['id']}/matches")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["pool_size"] == 0
    assert body["total"] == 0
    assert body["dna_eligible"] is True
    assert set(body.keys()) == {
        "challenge_id",
        "dna_eligible",
        "pool_size",
        "items",
        "total",
        "skip",
        "limit",
    }


def test_verified_and_active_institution_is_recommended(client, db_session):
    created = _create_water_challenge(client)
    _seed_institution(
        db_session,
        name="Anantapur Water University",
        domains=["water_sanitation"],
    )
    response = client.get(f"/api/challenges/{created['id']}/matches")
    body = response.json()
    assert body["pool_size"] == 1
    assert body["total"] == 1
    assert body["items"][0]["institution"]["name"] == "Anantapur Water University"
    assert body["items"][0]["institution"]["verification_status"] == "verified"


def test_unverified_institution_excluded(client, db_session):
    created = _create_water_challenge(client)
    _seed_institution(
        db_session,
        name="Unverified University",
        domains=["water_sanitation"],
        verification_status=InstitutionVerificationStatus.UNVERIFIED,
    )
    _seed_institution(
        db_session,
        name="Eligible University",
        domains=["water_sanitation"],
    )
    items = client.get(f"/api/challenges/{created['id']}/matches").json()["items"]
    names = [i["institution"]["name"] for i in items]
    assert "Eligible University" in names
    assert "Unverified University" not in names


def test_inactive_verified_institution_excluded(client, db_session):
    created = _create_water_challenge(client)
    _seed_institution(
        db_session,
        name="Retired University",
        domains=["water_sanitation"],
        status=InstitutionStatus.INACTIVE,
    )
    response = client.get(f"/api/challenges/{created['id']}/matches")
    assert response.json()["pool_size"] == 0
    assert response.json()["items"] == []


def test_rejected_and_suspended_institutions_excluded(client, db_session):
    created = _create_water_challenge(client)
    _seed_institution(
        db_session,
        name="Rejected College",
        domains=["water_sanitation"],
        verification_status=InstitutionVerificationStatus.REJECTED,
        institution_type=InstitutionType.COLLEGE,
    )
    _seed_institution(
        db_session,
        name="Suspended Institute",
        domains=["water_sanitation"],
        verification_status=InstitutionVerificationStatus.SUSPENDED,
        institution_type=InstitutionType.RESEARCH_INSTITUTE,
    )
    body = client.get(f"/api/challenges/{created['id']}/matches").json()
    assert body["pool_size"] == 0
    assert body["items"] == []


# --- Scoring behavior through the API ---------------------------------------------


def _strong_water_institution(db_session, name="Coastal Institute of Rural Technology"):
    return _seed_institution(
        db_session,
        name=name,
        domains=["water_sanitation", "agriculture"],
        capabilities={
            "expertise": ["hydrology", "iot sensing"],
            "research_areas": ["low-cost sensing"],
            "technologies": ["remote sensing"],
            "facilities": ["Water Testing Lab"],
            "project_experience": ["village borewell audit program"],
        },
    )


def test_domain_breakdown_exact_points(client, db_session):
    created = _create_water_challenge(client)
    _seed_institution(db_session, name="Exact Domain University", domains=["water_sanitation"])
    item = client.get(f"/api/challenges/{created['id']}/matches").json()["items"][0]
    assert item["score_breakdown"]["domain"]["points"] == 25
    assert item["score_breakdown"]["domain"]["max"] == 35
    assert any("Works in" in reason for reason in item["reasons"])
    assert item["institution"]["domain_labels"][0]["label"] == "Water & Sanitation"


def test_secondary_domain_overlap_scores(client, db_session):
    created = _create_water_challenge(client)
    # The classifier may assign agriculture as a secondary domain; an
    # institution carrying both must never score below one that carries only
    # the primary. Assert relative behavior rather than classifier specifics.
    _seed_institution(
        db_session,
        name="Primary Only University",
        domains=["water_sanitation"],
        location="Far away land",
    )
    _seed_institution(
        db_session,
        name="Primary Plus University",
        domains=["water_sanitation", "agriculture"],
        location="Far away land",
    )
    items = client.get(f"/api/challenges/{created['id']}/matches").json()["items"]
    scores = {i["institution"]["name"]: i["score"] for i in items}
    assert scores["Primary Plus University"] >= scores["Primary Only University"]


def test_expertise_overlap_appears_in_breakdown(client, db_session):
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    item = client.get(f"/api/challenges/{created['id']}/matches").json()["items"][0]
    expertise = item["score_breakdown"]["expertise"]
    assert expertise["max"] == 25
    assert expertise["points"] > 0
    assert expertise["detail"], "nonzero factor must expose matched evidence"
    assert any("Expertise includes" in r for r in item["reasons"])


def test_facilities_and_track_record_factors(client, db_session):
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    item = client.get(f"/api/challenges/{created['id']}/matches").json()["items"][0]
    assert item["score_breakdown"]["facilities"]["points"] > 0
    assert item["score_breakdown"]["track_record"]["points"] == 5
    assert any("Facilities include" in r for r in item["reasons"])
    assert any("Prior experience" in r for r in item["reasons"])


def test_geographic_overlap_factor(client, db_session):
    created = _create_water_challenge(client)
    # Domain match clears the score threshold; location detail proves the
    # geographic factor fired.
    _seed_institution(db_session, name="Local University", domains=["water_sanitation"])
    item = client.get(f"/api/challenges/{created['id']}/matches").json()["items"][0]
    assert item["score_breakdown"]["location"]["points"] > 0
    assert "anantapur" in item["score_breakdown"]["location"]["detail"]


def test_urgency_breakdown_matches_dna(client, db_session):
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    item = client.get(f"/api/challenges/{created['id']}/matches").json()["items"][0]
    urgency = item["score_breakdown"]["urgency"]
    if urgency["points"]:
        assert urgency["detail"] in (["critical"], ["high"])
        assert any("-urgency challenge" in r for r in item["reasons"])


def test_below_threshold_candidate_excluded_but_pool_visible(client, db_session):
    created = _create_water_challenge(client)
    # Location-only overlap: 1 shared token = 4 points < MIN_MATCH_SCORE(15).
    _seed_institution(
        db_session,
        name="Barely Related University",
        domains=["transportation"],
        location="Anantapur",
    )
    body = client.get(f"/api/challenges/{created['id']}/matches").json()
    assert body["pool_size"] == 1
    assert body["items"] == []
    assert body["total"] == 0


def test_score_breakdown_sum_invariant_for_every_item(client, db_session):
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    _seed_institution(
        db_session,
        name="Partial Match College",
        domains=["water_sanitation"],
        capabilities={"expertise": ["hydrology"]},
        institution_type=InstitutionType.COLLEGE,
    )
    items = client.get(f"/api/challenges/{created['id']}/matches").json()["items"]
    assert len(items) >= 2
    for item in items:
        total = sum(f["points"] for f in item["score_breakdown"].values())
        assert total == item["score"]
        assert set(item["score_breakdown"].keys()) == {
            "domain",
            "expertise",
            "research",
            "facilities",
            "track_record",
            "location",
            "urgency",
        }
        for factor in item["score_breakdown"].values():
            if factor["points"] > 0:
                assert factor["detail"], f"nonzero factor missing evidence: {factor}"


# --- Ranking determinism & pagination --------------------------------------------------


def test_deterministic_ranking_across_requests(client, db_session):
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    _seed_institution(db_session, name="Second University", domains=["water_sanitation"])
    first = client.get(f"/api/challenges/{created['id']}/matches").json()
    second = client.get(f"/api/challenges/{created['id']}/matches").json()
    assert first == second


def test_equal_scores_ordered_by_name(client, db_session):
    created = _create_water_challenge(client)
    for name in ("beta University", "Alpha University"):
        _seed_institution(db_session, name=name, domains=["water_sanitation"])
    names = [
        i["institution"]["name"]
        for i in client.get(f"/api/challenges/{created['id']}/matches").json()["items"]
    ]
    assert names == sorted(names, key=str.lower)


def test_pagination_skip_limit(client, db_session):
    created = _create_water_challenge(client)
    for i in range(3):
        _seed_institution(
            db_session,
            name=f"Water University {i}",
            domains=["water_sanitation"],
        )
    page_one = client.get(f"/api/challenges/{created['id']}/matches?skip=0&limit=2").json()
    page_two = client.get(f"/api/challenges/{created['id']}/matches?skip=2&limit=2").json()
    assert page_one["total"] == 3
    assert len(page_one["items"]) == 2
    assert len(page_two["items"]) == 1
    all_names = [i["institution"]["name"] for i in page_one["items"]] + [
        i["institution"]["name"] for i in page_two["items"]
    ]
    assert len(set(all_names)) == 3


def test_pagination_validation(client):
    created = client.post("/api/challenges", json=WATER_CHALLENGE)
    cid = created.json()["id"]
    assert client.get(f"/api/challenges/{cid}/matches?limit=0").status_code == 422
    assert client.get(f"/api/challenges/{cid}/matches?limit=51").status_code == 422
    assert client.get(f"/api/challenges/{cid}/matches?skip=-1").status_code == 422


def test_no_client_ranking_parameters(client, db_session):
    """Extra/unknown query params (e.g. sort, min_score) must not change
    ranking or leak controls."""
    created = _create_water_challenge(client)
    _strong_water_institution(db_session)
    baseline = client.get(f"/api/challenges/{created['id']}/matches").json()
    manipulated = client.get(
        f"/api/challenges/{created['id']}/matches"
        "?sort=urgency&min_score=0&weights=domain:100&verified=false"
    ).json()
    assert baseline == manipulated


# --- Phase 1–4A regression --------------------------------------------------------------


def test_existing_endpoints_unaffected(client, db_session):
    created = _create_water_challenge(client)
    cid = created["id"]

    related = client.get(f"/api/challenges/{cid}/related")
    assert related.status_code == 200
    assert set(related.json().keys()) == {"items"}

    dna = client.get(f"/api/challenges/{cid}/dna")
    assert dna.status_code == 200
    assert dna.json()["analyzer_version"] == "rule-baseline-v1"

    taxonomy = client.get("/api/taxonomy")
    assert taxonomy.status_code == 200
    assert len(taxonomy.json()["domains"]) == 14

    institutions = client.get("/api/institutions")
    assert institutions.status_code == 200
    assert set(institutions.json().keys()) == {"items", "total", "skip", "limit"}
