import uuid

from app.models.problem_dna import (
    DnaSource,
    DnaValidationStatus,
    ProblemDna,
    UrgencyLevel,
)
from app.repositories.problem_dna_repository import ProblemDnaRepository
from tests.test_challenges_api import VALID_PAYLOAD, _create


def _analyze(client, challenge_id):
    return client.post(f"/api/challenges/{challenge_id}/analyze")


def test_analyze_creates_problem_dna(client):
    created = _create(
        client,
        title="Village has contaminated drinking water",
        description="Residents suffer waterborne disease every summer from contaminated wells.",
        location="Barpeta, Assam",
    )
    response = _analyze(client, created["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["regenerated"] is False
    dna = body["dna"]
    assert dna["challenge_id"] == created["id"]
    assert dna["primary_domain"] == "water_sanitation"
    assert dna["primary_domain_label"] == "Water & Sanitation"
    assert dna["generated_by"] == "deterministic_baseline"
    assert dna["analyzer_version"]
    assert 0.0 < dna["confidence_score"] <= 1.0
    assert dna["signals"]["water_sanitation"]
    assert dna["validation_status"] == "pending_validation"


def test_get_dna_for_analyzed_challenge(client):
    created = _create(client)
    _analyze(client, created["id"])
    response = client.get(f"/api/challenges/{created['id']}/dna")
    assert response.status_code == 200
    assert response.json()["primary_domain"] is not None


def test_challenge_with_no_dna_returns_404(client):
    created = _create(client)
    response = client.get(f"/api/challenges/{created['id']}/dna")
    assert response.status_code == 404


def test_analyze_nonexistent_challenge_returns_404(client):
    response = _analyze(client, uuid.uuid4())
    assert response.status_code == 404


def test_get_dna_nonexistent_challenge_returns_404(client):
    response = client.get(f"/api/challenges/{uuid.uuid4()}/dna")
    assert response.status_code == 404


def test_malformed_uuid_returns_422(client):
    assert client.post("/api/challenges/not-a-uuid/analyze").status_code == 422
    assert client.get("/api/challenges/not-a-uuid/dna").status_code == 422


def test_weakly_classified_challenge_is_flagged_for_review(client):
    created = _create(
        client,
        title="Something feels wrong here",
        description="Nobody knows what to do about the situation lately.",
        location="Somewhere",
    )
    response = _analyze(client, created["id"])
    dna = response.json()["dna"]
    assert dna["primary_domain"] is None
    assert dna["confidence_score"] == 0.0
    assert dna["validation_status"] == "needs_review"


def test_single_weak_keyword_is_flagged_for_review(client):
    # One distinct taxonomy term (confidence 0.15 < 0.45 threshold).
    created = _create(
        client,
        title="Soil problem in our area",
        description="The ground quality is bad.",
        location="X",
    )
    dna = _analyze(client, created["id"]).json()["dna"]
    assert dna["primary_domain"] == "agriculture"
    assert dna["confidence_score"] == 0.15
    assert dna["validation_status"] == "needs_review"


def test_converging_evidence_reaches_pending_validation(client):
    # Three distinct taxonomy terms (confidence 0.45, exactly at threshold).
    created = _create(
        client,
        title="Farmers report soil problems",
        description="Their crops are failing.",
        location="X",
    )
    dna = _analyze(client, created["id"]).json()["dna"]
    assert dna["confidence_score"] == 0.45
    assert dna["validation_status"] == "pending_validation"


def test_rerunning_analysis_is_idempotent_and_regenerates(client):
    created = _create(
        client,
        title="Borewells failing in drought village",
        description="Farming families lose crops every summer due to water shortage.",
        location="Anantapur, Andhra Pradesh",
    )
    first = _analyze(client, created["id"]).json()
    second = _analyze(client, created["id"]).json()

    assert second["regenerated"] is True
    assert second["dna"]["primary_domain"] == first["dna"]["primary_domain"]
    assert second["dna"]["confidence_score"] == first["dna"]["confidence_score"]
    assert second["dna"]["keywords"] == first["dna"]["keywords"]

    # Still exactly one DNA row per challenge (1:1).
    listing = client.get("/api/challenges").json()
    assert len(listing["items"]) == 1
    fetched = client.get(f"/api/challenges/{created['id']}/dna").json()
    assert fetched["primary_domain"] == first["dna"]["primary_domain"]


def test_analysis_does_not_change_challenge_fields(client):
    created = _create(client)
    before = client.get(f"/api/challenges/{created['id']}").json()
    _analyze(client, created["id"])
    after = client.get(f"/api/challenges/{created['id']}").json()
    for field in ("title", "description", "location", "status"):
        assert after[field] == before[field]


def test_generated_dna_is_not_human_validated(client):
    created = _create(
        client,
        title="No street lights on main road",
        description="Dark streets every night; women feel unsafe walking home.",
        location="Mysuru, Karnataka",
    )
    dna = _analyze(client, created["id"]).json()["dna"]
    assert dna["generated_by"] != DnaSource.HUMAN.value
    assert dna["validated_at"] is None
    assert dna["validation_status"] in (
        DnaValidationStatus.PENDING_VALIDATION.value,
        DnaValidationStatus.NEEDS_REVIEW.value,
    )


def test_existing_challenge_endpoints_unaffected(client):
    # Phase 1 flow still works end-to-end alongside DNA endpoints.
    created = _create(client, **VALID_PAYLOAD)
    updated = client.patch(
        f"/api/challenges/{created['id']}", json={"location": "Chittoor, AP"}
    )
    assert updated.status_code == 200
    listed = client.get("/api/challenges")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


# --- Concurrent analyze race (unique constraint recovery) ---


def _insert_rival_dna(db_session, challenge_id: str, validated: bool) -> None:
    """Simulate another request that has already committed a DNA row."""
    db_session.add(
        ProblemDna(
            challenge_id=uuid.UUID(challenge_id),
            secondary_domains=[],
            affected_stakeholders=[],
            keywords=[],
            required_expertise=[],
            potential_solution_areas=[],
            signals={},
            generated_by=DnaSource.DETERMINISTIC_BASELINE,
            analyzer_version="rival-request",
            urgency=UrgencyLevel.MEDIUM,
            validation_status=(
                DnaValidationStatus.VALIDATED if validated
                else DnaValidationStatus.PENDING_VALIDATION
            ),
        )
    )
    db_session.commit()


def _hide_existing_dna_once(monkeypatch):
    """Make the service's existence check miss an already-committed row,
    exactly like a request whose check ran before a rival's commit."""
    original = ProblemDnaRepository.get_by_challenge_id
    checked = {"done": False}

    def racing_check(self, challenge_id):
        if not checked["done"]:
            checked["done"] = True
            return None
        return original(self, challenge_id)

    monkeypatch.setattr(ProblemDnaRepository, "get_by_challenge_id", racing_check)


def test_concurrent_analyze_race_recovers_without_error(client, db_session, monkeypatch):
    created = _create(client, **VALID_PAYLOAD)
    _insert_rival_dna(db_session, created["id"], validated=False)
    _hide_existing_dna_once(monkeypatch)

    response = _analyze(client, created["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["regenerated"] is True
    assert body["dna"]["analyzer_version"] != "rival-request"

    # Still exactly one DNA row for the challenge (1:1 preserved).
    fetched = client.get(f"/api/challenges/{created['id']}/dna")
    assert fetched.status_code == 200
    assert fetched.json()["primary_domain"] == "agriculture"
    assert fetched.json()["analyzer_version"] != "rival-request"


def test_concurrent_analyze_race_respects_validated_protection(client, db_session, monkeypatch):
    created = _create(client, **VALID_PAYLOAD)
    _insert_rival_dna(db_session, created["id"], validated=True)
    _hide_existing_dna_once(monkeypatch)

    response = _analyze(client, created["id"])
    assert response.status_code == 409
    assert "validated" in response.json()["detail"].lower()
