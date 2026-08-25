"""Phase 3 discovery API tests: search, filters, sorting, pagination."""

import time

from tests.test_challenges_api import VALID_PAYLOAD, _create


def _seed(client):
    """Seed a small deterministic dataset and return dict of created items."""
    water = _create(
        client,
        title="Contaminated drinking water in village",
        description="Residents drink contaminated water; children fall sick every summer.",
        location="Barpeta, Assam",
    )
    time.sleep(0.02)
    farm = _create(
        client,
        title="Dry soil leaves fields barren",
        description="Farmers need irrigation support to save their crops.",
        location="Nashik, Maharashtra",
    )
    time.sleep(0.02)
    school = _create(
        client,
        title="School building has no toilets",
        description="Students avoid school due to lack of toilets; dropout rising.",
        location="Barpeta, Assam",
    )
    for item in (water, farm, school):
        response = client.post(f"/api/challenges/{item['id']}/analyze")
        assert response.status_code == 200
    return {"water": water, "farm": farm, "school": school}


# --- Envelope & pagination ---

def test_discovery_envelope_shape(client):
    _seed(client)
    body = client.get("/api/challenges").json()
    assert set(body) == {"items", "total", "skip", "limit"}
    assert body["total"] == 3
    first = body["items"][0]
    for field in ("id", "title", "description", "location", "status", "created_at"):
        assert field in first
    assert "dna" in first


def test_discovery_pagination(client):
    _seed(client)
    page = client.get("/api/challenges?limit=2&skip=2").json()
    assert page["total"] == 3
    assert len(page["items"]) == 1


def test_discovery_limit_validation(client):
    assert client.get("/api/challenges?limit=101").status_code == 422
    assert client.get("/api/challenges?skip=-1").status_code == 422


# --- DNA embedding in list results ---

def test_list_items_include_dna_summary(client):
    _seed(client)
    items = client.get("/api/challenges?limit=50").json()["items"]
    with_dna = [i for i in items if i["dna"] is not None]
    assert len(with_dna) == 3
    sample = next(i for i in with_dna if i["dna"]["primary_domain"] == "water_sanitation")
    assert sample["dna"]["primary_domain_label"] == "Water & Sanitation"
    assert sample["dna"]["urgency"] in ("low", "medium", "high", "critical")
    assert sample["dna"]["validation_status"] in ("pending_validation", "needs_review")


# --- Search ---

def test_search_matches_word(client):
    _seed(client)
    body = client.get("/api/challenges?q=contaminated").json()
    titles = [i["title"] for i in body["items"]]
    assert body["total"] >= 1
    assert all("water" in t.lower() or "Contaminated" in t for t in titles)


def test_search_stems_morphological_variants(client):
    _seed(client)
    # 'irrigating' stems to the same root as 'irrigation' — no verbatim hit.
    body = client.get("/api/challenges?q=irrigating").json()
    assert body["total"] == 1
    assert "irrigat" not in body["items"][0]["title"].lower()


def test_search_no_results(client):
    _seed(client)
    body = client.get("/api/challenges?q=zeppelin").json()
    assert body["total"] == 0
    assert body["items"] == []


def test_search_operator_safe_input(client):
    _seed(client)
    response = client.get("/api/challenges?q=" + '"unbalanced quote AND OR NOT -')
    assert response.status_code == 200  # websearch_to_tsquery never errors


def test_search_too_long_rejected(client):
    _seed(client)
    response = client.get("/api/challenges?q=" + "x" * 201)
    assert response.status_code == 422


def test_relevance_sort_without_search_rejected(client):
    _seed(client)
    response = client.get("/api/challenges?sort=relevance")
    assert response.status_code == 422


def test_unknown_domain_rejected(client):
    _seed(client)
    response = client.get("/api/challenges?domains=not_a_domain")
    assert response.status_code == 422


def test_unknown_urgency_rejected(client):
    _seed(client)
    response = client.get("/api/challenges?urgencies=banana")
    assert response.status_code == 422


# --- Filters ---

def test_filter_by_single_domain(client):
    seeded = _seed(client)
    body = client.get("/api/challenges?domains=agriculture").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["farm"]["id"]}
    assert all(i["dna"]["primary_domain"] == "agriculture" for i in body["items"])


def test_filter_by_multiple_domains(client):
    seeded = _seed(client)
    body = client.get("/api/challenges?domains=agriculture,education").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["farm"]["id"], seeded["school"]["id"]}


def test_filter_by_urgencies_multi_value(client):
    _seed(client)
    body = client.get("/api/challenges?urgencies=high,critical").json()
    assert all(i["dna"]["urgency"] in ("high", "critical") for i in body["items"])


def test_filter_combined_domain_and_search(client):
    seeded = _seed(client)
    body = client.get("/api/challenges?domains=water_sanitation&q=contaminated").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["water"]["id"]}


def test_filter_by_location_substring_and_wildcard_escape(client):
    seeded = _seed(client)
    body = client.get("/api/challenges?location=barpeta").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["water"]["id"], seeded["school"]["id"]}

    # % and _ are matched literally, not as wildcards.
    none = client.get("/api/challenges?location=%").json()
    assert none["total"] == 0


def test_has_dna_filter(client):
    _create(client, title="Unanalyzed problem", **{
        k: v for k, v in VALID_PAYLOAD.items() if k != "title"
    })
    _seed(client)
    analyzed = client.get("/api/challenges?has_dna=true").json()
    unanalyzed = client.get("/api/challenges?has_dna=false").json()
    assert analyzed["total"] == 3
    assert all(i["dna"] is not None for i in analyzed["items"])
    assert unanalyzed["total"] == 1
    assert unanalyzed["items"][0]["dna"] is None
    assert unanalyzed["items"][0]["title"] == "Unanalyzed problem"


# --- Sorting ---

def test_sort_newest_default(client):
    seeded = _seed(client)
    items = client.get("/api/challenges").json()["items"]
    assert items[0]["id"] == seeded["school"]["id"]


def test_sort_oldest(client):
    seeded = _seed(client)
    items = client.get("/api/challenges?sort=oldest").json()["items"]
    assert items[0]["id"] == seeded["water"]["id"]


def test_sort_invalid_value_rejected(client):
    _seed(client)
    response = client.get("/api/challenges?sort=freshest")
    assert response.status_code == 422


# --- Detail response embeds DNA summary ---

def test_get_challenge_embeds_dna_summary(client):
    seeded = _seed(client)
    body = client.get(f"/api/challenges/{seeded['water']['id']}").json()
    assert body["dna"]["primary_domain"] == "water_sanitation"


def test_get_challenge_without_dna_embeds_null_dna(client):
    created = _create(client)
    body = client.get(f"/api/challenges/{created['id']}").json()
    assert body["dna"] is None
    assert body["title"] == created["title"]
    assert body["status"] == "submitted"


def test_get_nonexistent_challenge_returns_404_discovery_shape(client):
    import uuid

    response = client.get(f"/api/challenges/{uuid.uuid4()}")
    assert response.status_code == 404


# --- Location token matching (AND + deterministic relevance fallback) ---

def _seed_locations(client):
    barpeta = _create(
        client,
        title="Contaminated water in Barpeta",
        description="Drinking water contamination affects residents every summer.",
        location="Barpeta, Assam",
    )
    time.sleep(0.02)
    barpeta_rural = _create(
        client,
        title="Borewell contamination in rural Barpeta",
        description="Families rely on contaminated borewell drinking water.",
        location="Barpeta rural, Assam",
    )
    time.sleep(0.02)
    guwahati = _create(
        client,
        title="Flooding near Guwahati market area",
        description="Monsoon flooding damages shops in the city market district.",
        location="Guwahati, Assam",
    )
    return {
        "barpeta": barpeta,
        "barpeta_rural": barpeta_rural,
        "guwahati": guwahati,
    }


def test_location_single_token(client):
    seeded = _seed_locations(client)
    body = client.get("/api/challenges?location=Barpeta").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["barpeta"]["id"], seeded["barpeta_rural"]["id"]}


def test_location_multi_token_prefers_and_semantics(client):
    seeded = _seed_locations(client)
    # Both tokens must be present: excludes Guwahati despite shared 'Assam'.
    body = client.get("/api/challenges?location=Assam Barpeta").json()
    assert body["total"] == 2
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["barpeta"]["id"], seeded["barpeta_rural"]["id"]}


def test_location_multi_word_fallback_returns_sensible_results(client):
    """'Barpeta Main Market': 'market' exists nowhere, so the AND pass is
    empty and the token-ranked fallback returns the Barpeta challenges."""
    seeded = _seed_locations(client)
    body = client.get("/api/challenges?location=Barpeta Main Market").json()
    assert body["total"] == 2
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["barpeta"]["id"], seeded["barpeta_rural"]["id"]}
    # Deterministic tie-break: more matched tokens first, then created_at DESC.
    assert body["items"][0]["id"] == seeded["barpeta_rural"]["id"]
    assert body["items"][1]["id"] == seeded["barpeta"]["id"]


def test_location_district_stopword_still_finds_place(client):
    seeded = _seed_locations(client)
    body = client.get("/api/challenges?location=Barpeta District").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["barpeta"]["id"], seeded["barpeta_rural"]["id"]}


def test_location_generic_only_query_matches_nothing(client):
    _seed_locations(client)
    for query in ("District", "near main road", "!!!"):
        body = client.get(f"/api/challenges?location={query.replace(' ', '%20')}").json()
        assert body["total"] == 0, f"'{query}' must not broaden results"


def test_location_case_insensitive(client):
    seeded = _seed_locations(client)
    upper = client.get("/api/challenges?location=BARPETA").json()
    mixed = client.get("/api/challenges?location=bArPeTa").json()
    assert upper["total"] == mixed["total"] == 2
    assert {i["id"] for i in mixed["items"]} == {
        seeded["barpeta"]["id"],
        seeded["barpeta_rural"]["id"],
    }


def test_location_punctuation_is_normalized(client):
    seeded = _seed_locations(client)
    body = client.get("/api/challenges?location=%22Barpeta!!%22").json()
    ids = {i["id"] for i in body["items"]}
    assert ids == {seeded["barpeta"]["id"], seeded["barpeta_rural"]["id"]}


def test_location_wildcard_characters_are_inert(client):
    _seed_locations(client)
    # Wildcards are stripped by tokenization, never interpreted.
    body = client.get("/api/challenges?location=%25Barpeta%25").json()
    assert body["total"] == 2
    junk = client.get("/api/challenges?location=_%25_").json()
    assert junk["total"] == 0


def test_location_short_noise_tokens_do_not_broaden(client):
    _seed_locations(client)
    body = client.get("/api/challenges?location=Ba 12").json()
    assert body["total"] == 0


def test_location_fallback_respects_other_filters(client):
    seeded = _seed_locations(client)
    client.post(f"/api/challenges/{seeded['barpeta']['id']}/analyze")
    client.post(f"/api/challenges/{seeded['barpeta_rural']['id']}/analyze")
    client.post(f"/api/challenges/{seeded['guwahati']['id']}/analyze")
    body = client.get("/api/challenges?location=Barpeta Market&domains=water_sanitation").json()
    assert body["total"] >= 1
    assert all(i["dna"]["primary_domain"] == "water_sanitation" for i in body["items"])
