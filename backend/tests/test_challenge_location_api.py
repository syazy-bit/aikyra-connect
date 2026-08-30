import uuid

VALID_PAYLOAD = {
    "title": "Borewells failing in drought village",
    "description": "400 farming families lose crops every summer due to failing borewells.",
    "location": "Anantapur, Andhra Pradesh",
}

GUWAHATI = {"latitude": 26.1445, "longitude": 91.7362}


def _create(client, **overrides):
    payload = {**VALID_PAYLOAD, **overrides}
    response = client.post("/api/challenges", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- Create: coords accepted / persisted ---


def test_create_with_coordinates(client):
    created = _create(client, **GUWAHATI)
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["latitude"] == GUWAHATI["latitude"]
    assert detail["longitude"] == GUWAHATI["longitude"]


def test_create_without_coordinates_keeps_them_null(client):
    created = _create(client)
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["latitude"] is None
    assert detail["longitude"] is None


def test_create_without_coordinates_response_has_no_coord_keys(client):
    # The create echo (ChallengeResponse) must NOT expose coordinates — the
    # smallest public surface; coords surface only on the detail endpoint.
    created = _create(client, **GUWAHATI)
    assert "latitude" not in created
    assert "longitude" not in created


def test_create_coordinate_boundaries_accepted(client):
    for lat, lng in [(90, 180), (-90, -180), (0, 0), (90, -180)]:
        created = _create(client, latitude=lat, longitude=lng)
        detail = client.get(f"/api/challenges/{created['id']}").json()
        assert detail["latitude"] == lat
        assert detail["longitude"] == lng


# --- Create: validation failures (422) ---


def test_create_latitude_out_of_range(client):
    for bad in (90.0001, -90.0001, 91, 200):
        r = client.post("/api/challenges", json={**VALID_PAYLOAD, "latitude": bad, "longitude": 0})
        assert r.status_code == 422, (bad, r.status_code)


def test_create_longitude_out_of_range(client):
    for bad in (180.0001, -180.0001, 190, -200):
        r = client.post("/api/challenges", json={**VALID_PAYLOAD, "latitude": 0, "longitude": bad})
        assert r.status_code == 422, (bad, r.status_code)


def test_create_rejects_nan_and_infinity(client):
    for bad in ("NaN", "Infinity", "-Infinity"):
        r = client.post(
            "/api/challenges",
            json={**VALID_PAYLOAD, "latitude": 0, "longitude": bad},
        )
        assert r.status_code == 422, (bad, r.status_code)
        r = client.post(
            "/api/challenges",
            json={**VALID_PAYLOAD, "latitude": bad, "longitude": 0},
        )
        assert r.status_code == 422, (bad, r.status_code)


def test_create_rejects_non_numeric_coordinate(client):
    r = client.post(
        "/api/challenges", json={**VALID_PAYLOAD, "latitude": "abc", "longitude": 91.0}
    )
    assert r.status_code == 422


def test_create_rejects_latitude_only(client):
    r = client.post("/api/challenges", json={**VALID_PAYLOAD, "latitude": 26.1})
    assert r.status_code == 422


def test_create_rejects_longitude_only(client):
    r = client.post("/api/challenges", json={**VALID_PAYLOAD, "longitude": 91.7})
    assert r.status_code == 422


# --- Detail-only public exposure ---


def test_detail_exposes_coordinates_list_does_not(client):
    created = _create(client, **GUWAHATI)
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert "latitude" in detail and "longitude" in detail

    listing = client.get("/api/challenges").json()
    item = next(i for i in listing["items"] if i["id"] == created["id"])
    assert "latitude" not in item
    assert "longitude" not in item
    assert "has_coordinates" not in item


# --- Update: set / clear / partial rejection ---


def test_update_sets_coordinates(client):
    created = _create(client)
    r = client.patch(
        f"/api/challenges/{created['id']}", json=GUWAHATI
    )
    assert r.status_code == 200
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["latitude"] == GUWAHATI["latitude"]
    assert detail["longitude"] == GUWAHATI["longitude"]


def test_update_clears_coordinates(client):
    created = _create(client, **GUWAHATI)
    r = client.patch(
        f"/api/challenges/{created['id']}",
        json={"latitude": None, "longitude": None},
    )
    assert r.status_code == 200
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["latitude"] is None
    assert detail["longitude"] is None


def test_update_rejects_latitude_only(client):
    created = _create(client)
    r = client.patch(f"/api/challenges/{created['id']}", json={"latitude": 26.1})
    assert r.status_code == 422


def test_update_rejects_longitude_only(client):
    created = _create(client)
    r = client.patch(f"/api/challenges/{created['id']}", json={"longitude": 91.7})
    assert r.status_code == 422


def test_update_non_coordinate_fields_leave_coords_untouched(client):
    created = _create(client, **GUWAHATI)
    r = client.patch(
        f"/api/challenges/{created['id']}", json={"title": "Renamed"}
    )
    assert r.status_code == 200
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["title"] == "Renamed"
    assert detail["latitude"] == GUWAHATI["latitude"]
    assert detail["longitude"] == GUWAHATI["longitude"]


def test_update_out_of_range_coordinates_rejected(client):
    created = _create(client)
    r = client.patch(
        f"/api/challenges/{created['id']}", json={"latitude": 91, "longitude": 0}
    )
    assert r.status_code == 422


# --- Unknown / malicious keys ignored ---


def test_unknown_coord_keys_are_ignored(client):
    created = _create(client, **GUWAHATI)
    r = client.patch(f"/api/challenges/{created['id']}", json={"gps": {"lat": 1}})
    assert r.status_code == 200
    detail = client.get(f"/api/challenges/{created['id']}").json()
    assert detail["latitude"] == GUWAHATI["latitude"]


# --- 404s still work ---


def test_detail_unknown_id_404(client):
    assert client.get(f"/api/challenges/{uuid.uuid4()}").status_code == 404
