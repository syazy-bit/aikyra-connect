import time
import uuid
from datetime import datetime

VALID_PAYLOAD = {
    "title": "Borewells failing in drought village",
    "description": "400 farming families lose crops every summer due to failing borewells.",
    "location": "Anantapur, Andhra Pradesh",
}


def _create(client, **overrides):
    payload = {**VALID_PAYLOAD, **overrides}
    response = client.post("/api/challenges", json=payload)
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Create ---

def test_create_valid_challenge(client):
    body = _create(client)
    assert body["title"] == VALID_PAYLOAD["title"]
    assert body["description"] == VALID_PAYLOAD["description"]
    assert body["location"] == VALID_PAYLOAD["location"]
    assert body["status"] == "submitted"
    uuid.UUID(body["id"])
    assert body["created_at"]
    assert body["updated_at"]


def test_create_invalid_empty_title(client):
    response = client.post("/api/challenges", json={**VALID_PAYLOAD, "title": "   "})
    assert response.status_code == 422


def test_create_invalid_empty_description(client):
    response = client.post("/api/challenges", json={**VALID_PAYLOAD, "description": "   "})
    assert response.status_code == 422


def test_create_invalid_empty_location(client):
    response = client.post("/api/challenges", json={**VALID_PAYLOAD, "location": ""})
    assert response.status_code == 422


def test_create_missing_location(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "location"}
    response = client.post("/api/challenges", json=payload)
    assert response.status_code == 422


def test_create_title_too_long(client):
    response = client.post("/api/challenges", json={**VALID_PAYLOAD, "title": "x" * 201})
    assert response.status_code == 422


def test_create_description_too_long(client):
    response = client.post(
        "/api/challenges", json={**VALID_PAYLOAD, "description": "x" * 5001}
    )
    assert response.status_code == 422


def test_create_location_too_long(client):
    response = client.post("/api/challenges", json={**VALID_PAYLOAD, "location": "x" * 201})
    assert response.status_code == 422


# --- Retrieve ---

def test_get_challenge_by_id(client):
    created = _create(client)
    response = client.get(f"/api/challenges/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_challenge_returns_404(client):
    random_id = uuid.uuid4()
    response = client.get(f"/api/challenges/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_malformed_uuid_returns_422(client):
    response = client.get("/api/challenges/not-a-uuid")
    assert response.status_code == 422


# --- List / pagination ---

def test_list_challenges_default_pagination(client):
    for i in range(3):
        _create(client, title=f"Challenge {i}")
        time.sleep(0.01)
    response = client.get("/api/challenges")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["skip"] == 0
    assert len(body["items"]) == 3


def test_list_challenges_custom_limit_and_skip(client):
    for i in range(5):
        _create(client, title=f"Challenge {i}")
        time.sleep(0.01)
    page_one = client.get("/api/challenges?skip=0&limit=2").json()
    page_two = client.get("/api/challenges?skip=2&limit=2").json()
    assert [c["title"] for c in page_one["items"]] == ["Challenge 4", "Challenge 3"]
    assert [c["title"] for c in page_two["items"]] == ["Challenge 2", "Challenge 1"]


def test_list_challenges_orders_by_created_at_desc(client):
    older = _create(client, title="Older challenge")
    time.sleep(0.05)
    newer = _create(client, title="Newer challenge")
    response = client.get("/api/challenges")
    titles = [c["title"] for c in response.json()["items"]]
    assert titles.index("Newer challenge") < titles.index("Older challenge")
    assert newer["created_at"] >= older["created_at"]


def test_list_challenges_limit_validation(client):
    too_high = client.get("/api/challenges?limit=101")
    too_low = client.get("/api/challenges?limit=0")
    negative_skip = client.get("/api/challenges?skip=-1")
    assert too_high.status_code == 422
    assert too_low.status_code == 422
    assert negative_skip.status_code == 422


# --- Update ---

def test_update_challenge_fields(client):
    created = _create(client)
    response = client.patch(
        f"/api/challenges/{created['id']}",
        json={"location": "Tumakuru, Karnataka", "description": "Updated description."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Tumakuru, Karnataka"
    assert body["description"] == "Updated description."
    assert body["title"] == VALID_PAYLOAD["title"]


def test_public_patch_cannot_modify_status(client):
    created = _create(client)
    response = client.patch(
        f"/api/challenges/{created['id']}", json={"status": "validated"}
    )
    assert response.status_code == 200
    assert response.json()["status"] != "validated"
    assert response.json()["status"] == "submitted"


def test_update_rejects_invalid_status_value(client):
    # Status is not part of the public update schema at all.
    created = _create(client)
    response = client.patch(
        f"/api/challenges/{created['id']}", json={"status": "banana"}
    )
    assert response.json()["status"] == "submitted"
    assert response.status_code == 200


def test_patch_with_empty_payload_returns_unchanged(client):
    created = _create(client)
    before = client.get(f"/api/challenges/{created['id']}").json()
    response = client.patch(f"/api/challenges/{created['id']}", json={})
    assert response.status_code == 200
    after = response.json()
    assert after["title"] == before["title"]
    assert after["description"] == before["description"]
    assert after["location"] == before["location"]
    assert after["status"] == before["status"]


def test_updated_at_changes_after_successful_update(client):
    created = _create(client)
    original_updated_at = datetime.fromisoformat(created["updated_at"])
    original_created_at = datetime.fromisoformat(created["created_at"])
    assert original_updated_at == original_created_at
    time.sleep(0.02)
    response = client.patch(
        f"/api/challenges/{created['id']}", json={"title": "Renamed challenge"}
    )
    new_updated_at = datetime.fromisoformat(response.json()["updated_at"])
    assert new_updated_at > original_updated_at


def test_update_nonexistent_challenge_returns_404(client):
    response = client.patch(f"/api/challenges/{uuid.uuid4()}", json={"title": "Nope"})
    assert response.status_code == 404
