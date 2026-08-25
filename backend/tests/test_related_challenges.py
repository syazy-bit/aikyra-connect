"""Related-challenge and taxonomy endpoint tests (Phase 3)."""

import time
import uuid
from decimal import Decimal

from app.models.problem_dna import DnaSource, DnaValidationStatus, ProblemDna, UrgencyLevel
from tests.test_challenges_api import _create

STRONG_WATER = {
    "title": "Contaminated drinking water in flood-hit village",
    "description": "Sewage contamination of drinking water supply; waterborne disease spreading among residents.",
    "location": "Barpeta, Assam",
}


def _seed_two_water_challenges(client):
    first = _create(client, **STRONG_WATER)
    second = _create(
        client,
        title="Borewell water quality deteriorating in nearby town",
        description="Drinking water from borewells shows contamination; families worry about disease.",
        location="Barpeta rural",
    )
    for item in (first, second):
        response = client.post(f"/api/challenges/{item['id']}/analyze")
        assert response.status_code == 200
    return first, second


def test_taxonomy_endpoint_shape(client):
    body = client.get("/api/taxonomy").json()
    keys = [d["key"] for d in body["domains"]]
    labels = [d["label"] for d in body["domains"]]
    assert len(keys) == len(set(keys)) == 14
    assert "water_sanitation" in keys
    assert "Water & Sanitation" in labels
    water = next(d for d in body["domains"] if d["key"] == "water_sanitation")
    assert isinstance(water["subdomains"], list) and water["subdomains"]
    assert set(body["urgency_levels"]) == {"low", "medium", "high", "critical"}


def test_related_returns_same_domain_with_reasons(client):
    first, second = _seed_two_water_challenges(client)
    body = client.get(f"/api/challenges/{first['id']}/related").json()
    ids = [item["challenge"]["id"] for item in body["items"]]
    assert second["id"] in ids
    top = next(item for item in body["items"] if item["challenge"]["id"] == second["id"])
    assert top["score"] > 0
    assert top["reasons"]
    assert any("Same problem area" in r or "Shared themes" in r for r in top["reasons"])
    assert top["dna"]["primary_domain"] == "water_sanitation"


def test_related_excludes_self(client):
    first, _ = _seed_two_water_challenges(client)
    body = client.get(f"/api/challenges/{first['id']}/related").json()
    assert all(item["challenge"]["id"] != first["id"] for item in body["items"])


def test_related_empty_when_source_has_no_dna(client):
    created = _create(client)
    body = client.get(f"/api/challenges/{created['id']}/related").json()
    assert body == {"items": []}


def test_related_skips_low_confidence_candidates(client):
    source = _create(client, **STRONG_WATER)
    client.post(f"/api/challenges/{source['id']}/analyze")
    weak = _create(
        client,
        title="Soil problem nearby",
        description="The ground quality is bad.",
        location="Barpeta",
    )
    client.post(f"/api/challenges/{weak['id']}/analyze")

    # Force the weak candidate's DNA below the eligibility threshold.
    dna = (
        client.get(f"/api/challenges/{weak['id']}/dna").json()
    )
    # confidence 0.15 -> not eligible; related list must not include it.
    assert dna["confidence_score"] < 0.45
    body = client.get(f"/api/challenges/{source['id']}/related").json()
    assert all(item["challenge"]["id"] != weak["id"] for item in body["items"])


def test_related_nonexistent_challenge_404(client):
    import uuid

    response = client.get(f"/api/challenges/{uuid.uuid4()}/related")
    assert response.status_code == 404


def test_related_limit_validation(client):
    source, _ = _seed_two_water_challenges(client)
    assert client.get(f"/api/challenges/{source['id']}/related?limit=0").status_code == 422
    assert client.get(f"/api/challenges/{source['id']}/related?limit=21").status_code == 422


def test_related_scoring_is_deterministic(client):
    first, _ = _seed_two_water_challenges(client)
    one = client.get(f"/api/challenges/{first['id']}/related").json()
    two = client.get(f"/api/challenges/{first['id']}/related").json()
    assert one == two


def _seed_pair_with_locations(client, location_a: str, location_b: str):
    """Two strongly-related water challenges differing only in location."""
    first = _create(
        client,
        title="Contaminated drinking water in flood-hit village",
        description="Sewage contamination of drinking water supply; waterborne disease spreading among residents.",
        location=location_a,
    )
    second = _create(
        client,
        title="Borewell water quality deteriorating nearby",
        description="Drinking water from borewells shows contamination; families worry about disease.",
        location=location_b,
    )
    for item in (first, second):
        assert client.post(f"/api/challenges/{item['id']}/analyze").status_code == 200
    return first, second


def test_generic_geographic_words_do_not_create_location_similarity(client):
    """'Barpeta District' vs 'Anantapur District' share only the stop-word
    'district' — that must NOT produce 'Similar location'."""
    first, second = _seed_pair_with_locations(
        client, "Barpeta District", "Anantapur District"
    )
    body = client.get(f"/api/challenges/{first['id']}/related").json()
    top = next(
        item for item in body["items"] if item["challenge"]["id"] == second["id"]
    )
    assert not any("location" in reason.lower() for reason in top["reasons"])


def test_genuinely_shared_location_token_still_scores(client):
    """A real shared place token still yields 'Similar location'."""
    first, second = _seed_pair_with_locations(
        client, "Barpeta District", "Barpeta rural block"
    )
    body = client.get(f"/api/challenges/{first['id']}/related").json()
    top = next(
        item for item in body["items"] if item["challenge"]["id"] == second["id"]
    )
    assert any("Similar location" in reason for reason in top["reasons"])


def test_location_tokens_ignore_punctuation(client):
    from app.services.related_challenge_service import _location_tokens

    assert _location_tokens("Barpeta, Assam") == {"barpeta", "assam"}
    assert "district" not in _location_tokens("Anantapur District")
    assert _location_tokens(None) == set()


def test_manually_inserted_validated_dna_participates(client, db_session):
    """A validated-DNA challenge is eligible even though analysis API was never run."""
    source, other = _seed_two_water_challenges(client)

    third = _create(
        client,
        title="Third water supply breakdown in same district",
        description="Drinking water pipeline failure leaves families without safe water.",
        location="Barpeta",
    )
    db_session.add(
        ProblemDna(
            challenge_id=uuid.UUID(third["id"]),
            primary_domain="water_sanitation",
            secondary_domains=[],
            urgency=UrgencyLevel.HIGH,
            affected_stakeholders=[],
            keywords=["drinking water", "contamination", "families"],
            required_expertise=[],
            potential_solution_areas=[],
            signals={},
            generated_by=DnaSource.HUMAN,
            analyzer_version="human-v1",
            validation_status=DnaValidationStatus.VALIDATED,
            confidence_score=Decimal("0.85"),
        )
    )
    db_session.commit()

    body = client.get(f"/api/challenges/{source['id']}/related").json()
    ids = [item["challenge"]["id"] for item in body["items"]]
    assert third["id"] in ids
