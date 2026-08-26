"""Phase 4A — Institution Foundation API tests.

Covers: registration, validation (fields, formats, taxonomy, capabilities),
duplicate name/website protection, retrieval, listing (pagination, search,
type/domain filters, sorting), PATCH behavior, 404/409/422 semantics and
Phase 1–3 backward compatibility.
"""

import time
import uuid
from datetime import datetime

VALID_PAYLOAD = {
    "name": "Regional Institute of Technology",
    "institution_type": "university",
    "location": "Anantapur, Andhra Pradesh",
    "description": "A public engineering university focused on rural technology.",
    "website": "https://rit.ac.in",
    "contact_email": "contact@rit.ac.in",
    "domains": ["water_sanitation", "agriculture"],
    "capabilities": {
        "departments": ["Civil Engineering", "Computer Science"],
        "expertise": ["Soil-moisture sensing", "IoT", "GIS"],
        "facilities": ["Water Testing Lab"],
        "research_areas": ["Low-cost water quality monitoring"],
    },
}

MINIMAL_PAYLOAD = {
    "name": "Village Innovation Hub",
    "institution_type": "innovation_hub",
    "location": "Tumakuru, Karnataka",
}


def _create(c, payload=None, **overrides):
    body = {**(payload or VALID_PAYLOAD), **overrides}
    response = c.post("/api/institutions", json=body)
    assert response.status_code == 201, response.json()
    return response.json()


# --- Registration -------------------------------------------------------------


def test_register_full_institution(auth_client):
    body = _create(auth_client)
    assert body["name"] == VALID_PAYLOAD["name"]
    assert body["institution_type"] == "university"
    assert body["status"] == "active"
    assert body["verification_status"] == "unverified"
    assert body["verified_at"] is None
    assert body["verified_by"] is None
    assert body["verification_note"] is None
    uuid.UUID(body["id"])
    assert body["created_at"]
    assert body["updated_at"]
    # Human-entered data only — no AI provenance exists on institutions.
    assert body["domains"] == ["water_sanitation", "agriculture"]
    assert body["capabilities"]["departments"] == ["Civil Engineering", "Computer Science"]


def test_register_minimal_institution_defaults(auth_client):
    body = _create(auth_client, MINIMAL_PAYLOAD)
    assert body["description"] is None
    assert body["website"] is None
    assert body["contact_email"] is None
    assert body["domains"] == []
    assert body["capabilities"] == {}
    assert body["status"] == "active"
    assert body["verification_status"] == "unverified"


def test_register_returns_domain_labels(auth_client):
    body = _create(auth_client)
    labels = {ref["key"]: ref["label"] for ref in body["domain_labels"]}
    assert labels["water_sanitation"] == "Water & Sanitation"
    assert labels["agriculture"] == "Agriculture"


def test_register_dedupes_domains_preserving_order(auth_client):
    body = _create(
        auth_client,
        domains=["agriculture", "education", "agriculture", "education"],
    )
    assert body["domains"] == ["agriculture", "education"]


def test_register_all_institution_types(auth_client):
    for i, inst_type in enumerate(
        ["university", "college", "research_institute", "innovation_hub"]
    ):
        body = _create(
            auth_client,
            name=f"Type Test Institution {i}",
            institution_type=inst_type,
            website=None,
        )
        assert body["institution_type"] == inst_type


# --- Field / format validation -------------------------------------------------


def test_register_missing_required_fields(auth_client):
    for field in ("name", "institution_type", "location"):
        payload = {k: v for k, v in MINIMAL_PAYLOAD.items() if k != field}
        response = auth_client.post("/api/institutions", json=payload)
        assert response.status_code == 422


def test_register_blank_name_rejected(auth_client):
    response = auth_client.post(
        "/api/institutions", json={**MINIMAL_PAYLOAD, "name": "   "}
    )
    assert response.status_code == 422


def test_register_name_too_long(auth_client):
    response = auth_client.post(
        "/api/institutions", json={**MINIMAL_PAYLOAD, "name": "x" * 251}
    )
    assert response.status_code == 422


def test_register_invalid_institution_type(auth_client):
    response = auth_client.post(
        "/api/institutions",
        json={**MINIMAL_PAYLOAD, "institution_type": "industry"},
    )
    assert response.status_code == 422


def test_register_invalid_website_rejected(auth_client):
    for bad in ("rit.ac.in", "ftp://rit.ac.in", "https://", "not a url"):
        response = auth_client.post(
            "/api/institutions", json={**MINIMAL_PAYLOAD, "website": bad}
        )
        assert response.status_code == 422, bad


def test_register_invalid_email_rejected(auth_client):
    for bad in ("plainaddress", "missing@tld", "@no-local.com", "user@"):
        response = auth_client.post(
            "/api/institutions", json={**MINIMAL_PAYLOAD, "contact_email": bad}
        )
        assert response.status_code == 422, bad


def test_register_description_too_long(auth_client):
    response = auth_client.post(
        "/api/institutions", json={**MINIMAL_PAYLOAD, "description": "x" * 5001}
    )
    assert response.status_code == 422


# --- Taxonomy validation --------------------------------------------------------


def test_register_unknown_domain_rejected(auth_client):
    response = auth_client.post(
        "/api/institutions",
        json={**MINIMAL_PAYLOAD, "domains": ["quantum_mechanics"]},
    )
    assert response.status_code == 422
    assert "unknown domain 'quantum_mechanics'" in response.json()["detail"][0]["msg"]


def test_register_domains_come_from_taxonomy_api(auth_client, client):
    """Domain slugs accepted by registration must be exactly the taxonomy
    API's domain keys — institutions never depend on hardcoded lists."""
    taxonomy = client.get("/api/taxonomy").json()
    taxonomy_keys = [d["key"] for d in taxonomy["domains"]]
    created = _create(auth_client, domains=taxonomy_keys)
    assert sorted(created["domains"]) == sorted(taxonomy_keys)


# --- Capabilities validation ------------------------------------------------------


def test_register_unknown_capability_section_rejected(auth_client):
    response = auth_client.post(
        "/api/institutions",
        json={**MINIMAL_PAYLOAD, "capabilities": {"labz": ["Mystery Lab"]}},
    )
    assert response.status_code == 422


def test_register_capability_item_must_be_string(auth_client):
    response = auth_client.post(
        "/api/institutions",
        json={**MINIMAL_PAYLOAD, "capabilities": {"expertise": [42]}},
    )
    assert response.status_code == 422


def test_register_capability_section_size_cap(auth_client):
    response = auth_client.post(
        "/api/institutions",
        json={
            **MINIMAL_PAYLOAD,
            "capabilities": {"expertise": [f"Area {i}" for i in range(41)]},
        },
    )
    assert response.status_code == 422


def test_register_capability_items_stripped_and_deduped(auth_client):
    body = _create(
        auth_client,
        capabilities={"expertise": ["  IoT  ", "IoT", "", "   ", "GIS"]},
    )
    assert body["capabilities"]["expertise"] == ["IoT", "GIS"]


# --- Duplicate protection ------------------------------------------------------------


def test_duplicate_exact_name_conflict(auth_client):
    _create(auth_client)
    response = auth_client.post("/api/institutions", json=VALID_PAYLOAD)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "already exists" in detail
    assert "id:" in detail


def test_duplicate_normalized_name_conflict(auth_client):
    _create(auth_client)
    for variant in (
        "regional institute of TECHNOLOGY",
        "Regional Institute of Technology.",
        "  regional-institute-of-technology  ",
    ):
        response = auth_client.post(
            "/api/institutions",
            json={**MINIMAL_PAYLOAD, "name": variant},
        )
        assert response.status_code == 409, variant


def test_same_name_different_type_still_conflict(auth_client):
    _create(auth_client)
    response = auth_client.post(
        "/api/institutions",
        json={**VALID_PAYLOAD, "institution_type": "college"},
    )
    assert response.status_code == 409


def test_database_unique_index_guard(client, db_session):
    """The normalized unique index must reject rows even without the
    service-level check (defense in depth)."""
    from sqlalchemy.exc import IntegrityError

    from app.models.institution import Institution, InstitutionType

    db_session.add(
        Institution(
            id=uuid.uuid4(),
            name="Guard Test University",
            institution_type=InstitutionType.UNIVERSITY,
            location="Somewhere",
            domains=[],
            capabilities={},
        )
    )
    db_session.commit()
    duplicate = Institution(
        id=uuid.uuid4(),
        name="guard test UNIVERSITY!",
        institution_type=InstitutionType.COLLEGE,
        location="Elsewhere",
        domains=[],
        capabilities={},
    )
    db_session.add(duplicate)
    try:
        db_session.commit()
        raised = False
    except IntegrityError:
        db_session.rollback()
        raised = True
    assert raised


def test_distinct_names_accepted(auth_client):
    _create(auth_client)
    body = _create(
        auth_client, name="Coastal Engineering College", website=None
    )
    assert body["name"] == "Coastal Engineering College"


# --- IntegrityError race protection (H1 regression) ---------------------------


def test_concurrent_registration_race_returns_409(auth_client, monkeypatch):
    """Regression (review finding H1): when a concurrent registration wins
    the race — its row lands between this request's duplicate pre-check and
    its insert — the database unique constraint fires and the API must
    return a structured 409, never an unhandled 500."""
    from app.models.institution import Institution, InstitutionType
    from app.repositories.institution_repository import InstitutionRepository

    original_create = InstitutionRepository.create

    def racing_create(self, data):
        self.db.add(
            Institution(
                id=uuid.uuid4(),
                name="Race Condition UNIVERSITY!",
                institution_type=InstitutionType.COLLEGE,
                location="Won the race",
                domains=[],
                capabilities={},
            )
        )
        self.db.flush()
        return original_create(self, data)

    monkeypatch.setattr(InstitutionRepository, "create", racing_create)

    response = auth_client.post(
        "/api/institutions",
        json={
            "name": "race condition university",
            "institution_type": "university",
            "location": "Lost the race",
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert "detail" in body
    assert "already exists" in body["detail"]
    assert "Institution" not in body["detail"]  # domain message, not raw DB error


def test_concurrent_rename_race_returns_409(auth_client, monkeypatch):
    """The same race protection must apply on the update path: another
    institution takes the target normalized name between the PATCH
    pre-check and the write."""
    from app.models.institution import Institution, InstitutionType
    from app.repositories.institution_repository import InstitutionRepository

    created = _create(auth_client)

    original_update = InstitutionRepository.update

    def racing_update(self, institution, data):
        self.db.add(
            Institution(
                id=uuid.uuid4(),
                name="Taken Name University!",
                institution_type=InstitutionType.RESEARCH_INSTITUTE,
                location="Elsewhere",
                domains=[],
                capabilities={},
            )
        )
        self.db.flush()
        return original_update(self, institution, {"name": "taken name university"})

    monkeypatch.setattr(InstitutionRepository, "update", racing_update)

    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={"name": "Taken Name University"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_website_host_conflict(auth_client):
    _create(auth_client)
    response = auth_client.post(
        "/api/institutions",
        json={**MINIMAL_PAYLOAD, "website": "http://RIT.ac.in/index.html"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_similar_but_distinct_websites_accepted(auth_client):
    _create(auth_client)
    body = _create(auth_client, name="Other University", website="https://rit2.ac.in")
    assert body["website"] == "https://rit2.ac.in"


def test_patch_to_existing_other_name_conflicts(auth_client):
    first = _create(auth_client)
    second = _create(auth_client, MINIMAL_PAYLOAD)
    response = auth_client.patch(
        f"/api/institutions/{second['id']}", json={"name": first["name"]}
    )
    assert response.status_code == 409


def test_patch_keeping_own_name_allowed(auth_client):
    created = _create(auth_client)
    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={"name": "Regional Institute of Technology!"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Regional Institute of Technology!"


# --- Retrieval --------------------------------------------------------------------------


def test_get_institution_by_id(auth_client, client):
    created = _create(auth_client)
    response = client.get(f"/api/institutions/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["capabilities"] == VALID_PAYLOAD["capabilities"]
    assert body["domain_labels"][0]["key"] == "water_sanitation"


def test_get_nonexistent_institution_returns_404(client):
    response = client.get(f"/api/institutions/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "Institution" in response.json()["detail"]
    assert "not found" in response.json()["detail"].lower()


def test_get_malformed_uuid_returns_422(client):
    response = client.get("/api/institutions/not-a-uuid")
    assert response.status_code == 422


# --- Listing: pagination / search / filters / sorting -------------------------------------


def test_list_envelope_shape(auth_client, client):
    _create(auth_client)
    body = client.get("/api/institutions").json()
    assert set(body.keys()) == {"items", "total", "skip", "limit"}
    assert body["total"] == 1
    assert body["skip"] == 0
    assert body["limit"] == 20
    item = body["items"][0]
    assert "capabilities" not in item  # trimmed projection
    assert "domain_labels" in item


def test_list_pagination_and_ordering(auth_client, client):
    for i in range(5):
        _create(auth_client, name=f"Institution {i}", website=None)
        time.sleep(0.01)
    page_one = client.get("/api/institutions?skip=0&limit=2").json()
    page_two = client.get("/api/institutions?skip=2&limit=2").json()
    assert [i["name"] for i in page_one["items"]] == [
        "Institution 4",
        "Institution 3",
    ]
    assert [i["name"] for i in page_two["items"]] == [
        "Institution 2",
        "Institution 1",
    ]
    assert page_one["total"] == 5


def test_list_pagination_validation(client):
    assert client.get("/api/institutions?limit=101").status_code == 422
    assert client.get("/api/institutions?limit=0").status_code == 422
    assert client.get("/api/institutions?skip=-1").status_code == 422


def test_list_search_matches_name_description_location(auth_client, client):
    _create(auth_client)  # Regional Institute…, Anantapur, rural technology
    _create(auth_client, MINIMAL_PAYLOAD)

    by_name = client.get("/api/institutions?q=regional").json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["name"] == VALID_PAYLOAD["name"]

    by_location = client.get("/api/institutions?q=tumakuru").json()
    assert by_location["total"] == 1
    assert by_location["items"][0]["name"] == MINIMAL_PAYLOAD["name"]

    by_desc = client.get("/api/institutions?q='rural technology'").json()
    assert by_desc["total"] >= 1

    no_match = client.get("/api/institutions?q=zanzibar").json()
    assert no_match["total"] == 0


def test_list_sort_options(auth_client, client):
    older = _create(auth_client, name="Alpha College", location="Old Town", website=None)
    time.sleep(0.05)
    newer = _create(
        auth_client, name="Beta University", location="New Town",
        website=None,
    )

    newest = client.get("/api/institutions").json()["items"]
    assert newest[0]["id"] == newer["id"]

    oldest = client.get("/api/institutions?sort=oldest").json()["items"]
    assert oldest[0]["id"] == older["id"]

    relevance = client.get("/api/institutions?q=beta&sort=relevance").json()["items"]
    assert relevance[0]["id"] == newer["id"]

    missing_q = client.get("/api/institutions?sort=relevance")
    assert missing_q.status_code == 422


def test_list_filter_by_type(auth_client, client):
    _create(auth_client)
    _create(auth_client, MINIMAL_PAYLOAD)

    universities = client.get("/api/institutions?types=university").json()
    assert universities["total"] == 1
    assert universities["items"][0]["institution_type"] == "university"

    hubs_csv = client.get("/api/institutions?types=innovation_hub,college").json()
    assert hubs_csv["total"] == 1
    assert hubs_csv["items"][0]["institution_type"] == "innovation_hub"

    invalid = client.get("/api/institutions?types=industry")
    assert invalid.status_code == 422


def test_list_filter_by_domain(auth_client, client):
    _create(auth_client)
    _create(auth_client, MINIMAL_PAYLOAD, domains=["education"])

    filtered = client.get("/api/institutions?domains=water_sanitation").json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["name"] == VALID_PAYLOAD["name"]

    multi = client.get("/api/institutions?domains=water_sanitation,education").json()
    assert multi["total"] == 2

    unknown = client.get("/api/institutions?domains=astrology")
    assert unknown.status_code == 422
    assert "unknown domain 'astrology'" in unknown.json()["detail"][0]["msg"]


def test_list_combined_filters_and_search(auth_client, client):
    _create(auth_client)
    _create(auth_client, MINIMAL_PAYLOAD, domains=["education"])

    combined = client.get(
        "/api/institutions?q=regional&types=university&domains=water_sanitation"
    ).json()
    assert combined["total"] == 1

    mismatched = client.get(
        "/api/institutions?q=regional&types=innovation_hub"
    ).json()
    assert mismatched["total"] == 0


# --- PATCH ----------------------------------------------------------------------------------


def test_patch_all_field_groups(auth_client):
    created = _create(auth_client)
    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={
            "name": "Renamed Institute of Technology",
            "institution_type": "research_institute",
            "description": "Updated description.",
            "location": "Chitradurga, Karnataka",
            "website": "https://new-domain.edu.in",
            "contact_email": "hello@new-domain.edu.in",
            "domains": ["energy"],
            "capabilities": {
                "expertise": ["Solar micro-grids"],
                "technologies": ["Smart metering"],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed Institute of Technology"
    assert body["institution_type"] == "research_institute"
    assert body["location"] == "Chitradurga, Karnataka"
    assert body["website"] == "https://new-domain.edu.in"
    assert body["domains"] == ["energy"]
    assert body["capabilities"]["expertise"] == ["Solar micro-grids"]
    # Capabilities replace-whole: sections absent from the payload are gone.
    assert "departments" not in body["capabilities"]
    assert [ref["label"] for ref in body["domain_labels"]] == ["Energy"]


def test_patch_empty_payload_returns_unchanged(auth_client, client):
    created = _create(auth_client)
    before = client.get(f"/api/institutions/{created['id']}").json()
    time.sleep(0.02)
    response = auth_client.patch(f"/api/institutions/{created['id']}", json={})
    assert response.status_code == 200
    after = response.json()
    assert after["name"] == before["name"]
    assert after["capabilities"] == before["capabilities"]


def test_patch_updated_at_advances(auth_client):
    created = _create(auth_client)
    original = datetime.fromisoformat(created["updated_at"])
    time.sleep(0.02)
    updated = auth_client.patch(
        f"/api/institutions/{created['id']}", json={"description": "Fresh text."}
    ).json()
    assert datetime.fromisoformat(updated["updated_at"]) > original


def test_patch_nonexistent_returns_404(auth_client):
    response = auth_client.patch(
        f"/api/institutions/{uuid.uuid4()}", json={"name": "Ghost University"}
    )
    assert response.status_code == 404


def test_patch_rejects_invalid_values(auth_client):
    created = _create(auth_client)
    assert (
        auth_client.patch(
            f"/api/institutions/{created['id']}",
            json={"institution_type": "industry"},
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/institutions/{created['id']}",
            json={"domains": ["fake_domain"]},
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/institutions/{created['id']}", json={"website": "nope"}
        ).status_code
        == 422
    )


def test_patch_cannot_change_verification_or_lifecycle(auth_client):
    """Trust/workflow fields are rejected by extra='forbid' on InstitutionUpdate."""
    created = _create(auth_client)
    response = auth_client.patch(
        f"/api/institutions/{created['id']}",
        json={
            "verification_status": "verified",
            "status": "inactive",
            "verified_by": str(uuid.uuid4()),
            "verification_note": "self-approved",
        },
    )
    assert response.status_code == 422
    assert "extra" in str(response.json()).lower() or "forbidden" in str(response.json()).lower()


# --- Phase 1–3 backward compatibility ----------------------------------------------------------


def test_phase_1_3_flows_unaffected(client):
    challenge_payload = {
        "title": "Borewells failing in drought village",
        "description": "400 farming families lose crops every summer.",
        "location": "Anantapur, Andhra Pradesh",
    }
    created = client.post("/api/challenges", json=challenge_payload)
    assert created.status_code == 201

    listed = client.get("/api/challenges").json()
    assert listed["total"] == 1

    analyzed = client.post(f"/api/challenges/{created.json()['id']}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["dna"]["primary_domain"] in ("water_sanitation", "agriculture")

    related = client.get(f"/api/challenges/{created.json()['id']}/related")
    assert related.status_code == 200
    assert set(related.json().keys()) == {"items"}

    taxonomy = client.get("/api/taxonomy").json()
    assert len(taxonomy["domains"]) == 14
    assert taxonomy["urgency_levels"] == ["low", "medium", "high", "critical"]

    health = client.get("/health")
    assert health.status_code == 200


def test_challenge_discovery_does_not_leak_institutions(auth_client, client):
    _create(auth_client)
    challenges = client.get("/api/challenges").json()
    assert challenges["total"] == 0
