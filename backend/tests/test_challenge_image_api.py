"""Public photo evidence for reported problems (challenges).

Covers:
- upload (POST /api/challenges/{id}/image) — public write, public image
- retrieval (GET /api/challenges/{id}/image) — public, matching the challenge
- server-generated filenames, magic-byte validation, size limit, path safety
- orphan prevention on successful replacement; preservation on failed replace

The uploads directory is redirected to a per-test tmp_path via UPLOADS_DIR.
"""

import re

import pytest

from app.core.config import get_settings
from app.models.challenge import Challenge

# Minimal, structurally valid image fixtures (pass magic-byte checks).
JPG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"  # signature
    b"\x00\x00\x00\x0dIHDR"  # IHDR chunk header
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"  # IHDR data
    b"\x90wS\xde\x00\x00\x00\x00IEND\xaeB`\x82"
)
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8L\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
TEXT_BYTES = b"hello, this is definitely not an image"
STORED_PATH_RE = re.compile(r"^reports/[0-9a-f]{32}\.(jpg|png|webp)$")


@pytest.fixture(autouse=True)
def uploads_root(tmp_path, monkeypatch):
    """Isolate uploaded files into a per-test temp dir and expose its path."""
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _create_challenge(c, **overrides):
    payload = {
        "title": "Flooded roads in low-lying ward",
        "description": "Rainwater pools for days, cutting off access for residents.",
        "location": "Nagpur, Maharashtra",
        **overrides,
    }
    resp = c.post("/api/challenges", json=payload)
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _upload(c, challenge_id, filename, data, content_type=None):
    files = {"file": (filename, data, content_type)}
    return c.post(f"/api/challenges/{challenge_id}/image", files=files)


def _row(db_session, challenge_id):
    return db_session.query(Challenge).filter(Challenge.id == challenge_id).one()


# 1. JSON creation without image still succeeds -------------------------------


def test_create_without_image_succeeds(client):
    body = _create_challenge(client)
    assert body["has_image"] is False
    assert client.get(f"/api/challenges/{body['id']}/image").status_code == 404


# 2-4. Valid images upload + association + server-generated filename ----------


@pytest.mark.parametrize(
    "filename,data,ctype,ext",
    [
        ("photo.jpg", JPG_BYTES, "image/jpeg", "jpg"),
        ("photo.png", PNG_BYTES, "image/png", "png"),
        ("photo.webp", WEBP_BYTES, "image/webp", "webp"),
    ],
)
def test_valid_image_upload_succeeds(
    auth_client, db_session, filename, data, ctype, ext
):
    challenge = _create_challenge(auth_client)
    resp = _upload(auth_client, challenge["id"], filename, data, ctype)
    assert resp.status_code == 200, resp.json()
    assert resp.json()["has_image"] is True
    row = _row(db_session, challenge["id"])
    assert row.image_path is not None
    # Stored filename is server-generated and never the client filename.
    assert STORED_PATH_RE.match(row.image_path)
    assert filename not in row.image_path


# 5. Oversized image rejected --------------------------------------------------


def test_oversized_image_rejected(auth_client, db_session):
    challenge = _create_challenge(auth_client)
    big = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 1024) + b"\xff\xd9"
    resp = _upload(auth_client, challenge["id"], "big.jpg", big, "image/jpeg")
    assert resp.status_code == 400
    # No image stored.
    assert _row(db_session, challenge["id"]).image_path is None


# 6. Unsupported file type rejected -------------------------------------------


def test_unsupported_file_type_rejected(auth_client, db_session):
    challenge = _create_challenge(auth_client)
    resp = _upload(auth_client, challenge["id"], "notes.txt", TEXT_BYTES, "text/plain")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


# 7. Filename spoofing: evil.jpg containing non-image bytes rejected ----------


def test_filename_spoofing_rejected(auth_client, db_session):
    challenge = _create_challenge(auth_client)
    # A .jpg filename carrying a text payload must not be accepted.
    resp = _upload(auth_client, challenge["id"], "evil.jpg", TEXT_BYTES, "image/jpeg")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


# 17. Malformed / corrupt image bytes rejected --------------------------------


def test_corrupt_image_bytes_rejected(auth_client, db_session):
    challenge = _create_challenge(auth_client)
    # Truncated JPEG: has the SOI header but no EOI marker.
    truncated_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
    resp = _upload(auth_client, challenge["id"], "broken.jpg", truncated_jpg, "image/jpeg")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


# 10. GET image returns the correct bytes + content type ---------------------


def test_get_image_returns_bytes(client, auth_client, db_session):
    challenge = _create_challenge(auth_client)
    _upload(auth_client, challenge["id"], "photo.jpg", JPG_BYTES, "image/jpeg")
    resp = client.get(f"/api/challenges/{challenge['id']}/image")
    assert resp.status_code == 200
    assert resp.content == JPG_BYTES
    assert resp.headers["content-type"] == "image/jpeg"


# 11. GET unknown challenge -> 404 --------------------------------------------


def test_get_image_unknown_challenge_404(client):
    from uuid import uuid4

    assert client.get(f"/api/challenges/{uuid4()}/image").status_code == 404


# 12. GET challenge without image -> 404 --------------------------------------


def test_get_image_without_image_404(client):
    challenge = _create_challenge(client)
    resp = client.get(f"/api/challenges/{challenge['id']}/image")
    assert resp.status_code == 404


# 13. Anonymous report + photo (public write, matching the public model) ---------
#
# Challenges are public and owner-less: anyone may create one, anyone may read
# one, so a challenge's evidence photo is public and the write is public too.
# This mirrors the exact flow the frontend ReportProblem runs without a login.


@pytest.mark.parametrize(
    "filename,data,ctype,ext",
    [
        ("photo.jpg", JPG_BYTES, "image/jpeg", "jpg"),
        ("photo.png", PNG_BYTES, "image/png", "png"),
        ("photo.webp", WEBP_BYTES, "image/webp", "webp"),
    ],
)
def test_anonymous_valid_image_upload_succeeds(
    client, db_session, filename, data, ctype, ext
):
    challenge = _create_challenge(client)
    resp = _upload(client, challenge["id"], filename, data, ctype)
    assert resp.status_code == 200, resp.json()
    assert resp.json()["id"] == challenge["id"]
    assert resp.json()["has_image"] is True
    row = _row(db_session, challenge["id"])
    assert row.image_path is not None
    # Associated with exactly the created challenge; store a server-generated name.
    assert STORED_PATH_RE.match(row.image_path)
    assert row.image_path.endswith(f".{ext}")
    # The client filename never controls the stored filename.
    assert filename not in row.image_path


def test_anonymous_create_then_upload_does_not_duplicate(client, db_session):
    """The frontend's create-then-upload flow must never create extra challenges."""
    before = db_session.query(Challenge).count()
    challenge = _create_challenge(client)
    assert db_session.query(Challenge).count() == before + 1

    resp = _upload(client, challenge["id"], "photo.jpg", JPG_BYTES, "image/jpeg")
    assert resp.status_code == 200
    assert resp.json()["id"] == challenge["id"]

    # Still exactly one challenge — the upload only mutated that challenge.
    assert db_session.query(Challenge).count() == before + 1
    assert STORED_PATH_RE.match(_row(db_session, challenge["id"]).image_path)


def test_anonymous_failed_upload_preserves_created_challenge(client, db_session):
    """A failed photo upload keeps the already-created report intact."""
    challenge = _create_challenge(client)
    resp = _upload(client, challenge["id"], "broken.jpg", TEXT_BYTES, "image/jpeg")
    assert resp.status_code == 400

    # The created challenge is preserved, still reachable, and image-less.
    assert client.get(f"/api/challenges/{challenge['id']}").status_code == 200
    assert _row(db_session, challenge["id"]).image_path is None

    # A later valid upload to the same challenge still works.
    ok = _upload(client, challenge["id"], "ok.jpg", JPG_BYTES, "image/jpeg")
    assert ok.status_code == 200
    assert ok.json()["id"] == challenge["id"]


def test_anonymous_location_and_photo_flow(client, db_session):
    challenge = _create_challenge(client, location="Sambalpur, Odisha")
    assert challenge["location"] == "Sambalpur, Odisha"

    resp = _upload(client, challenge["id"], "photo.png", PNG_BYTES, "image/png")
    assert resp.status_code == 200

    detail = client.get(f"/api/challenges/{challenge['id']}")
    assert detail.status_code == 200
    assert detail.json()["location"] == "Sambalpur, Odisha"
    assert detail.json()["has_image"] is True
    assert client.get(f"/api/challenges/{challenge['id']}/image").status_code == 200


def test_anonymous_upload_unknown_challenge_404(client):
    from uuid import uuid4

    resp = _upload(client, uuid4(), "photo.jpg", JPG_BYTES, "image/jpeg")
    assert resp.status_code == 404


def test_anonymous_oversized_image_rejected(client, db_session):
    challenge = _create_challenge(client)
    big = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 1024) + b"\xff\xd9"
    resp = _upload(client, challenge["id"], "big.jpg", big, "image/jpeg")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


def test_anonymous_spoofed_image_rejected(client, db_session):
    challenge = _create_challenge(client)
    resp = _upload(client, challenge["id"], "evil.jpg", TEXT_BYTES, "image/jpeg")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


def test_anonymous_truncated_image_rejected(client, db_session):
    challenge = _create_challenge(client)
    truncated_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
    resp = _upload(client, challenge["id"], "broken.jpg", truncated_jpg, "image/jpeg")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


def test_anonymous_unsupported_format_rejected(client, db_session):
    challenge = _create_challenge(client)
    resp = _upload(client, challenge["id"], "notes.txt", TEXT_BYTES, "text/plain")
    assert resp.status_code == 400
    assert _row(db_session, challenge["id"]).image_path is None


def test_anonymous_hostile_filename_never_controls_stored_path(client, db_session):
    challenge = _create_challenge(client)
    resp = _upload(client, challenge["id"], "../../../evil.jpg", JPG_BYTES, "image/jpeg")
    assert resp.status_code == 200, resp.json()
    row = _row(db_session, challenge["id"])
    # Stored path stays safely inside uploads/reports; nothing path-like escapes.
    assert STORED_PATH_RE.match(row.image_path)
    assert ".." not in row.image_path
    assert "evil" not in row.image_path


def test_anonymous_client_cannot_provide_image_path(client, db_session):
    challenge = _create_challenge(client)
    # Only the declared multipart ``file`` field is honored; an extra
    # ``image_path`` field is ignored, so the client can never steer storage.
    resp = client.post(
        f"/api/challenges/{challenge['id']}/image",
        data={"image_path": "../../escape.png"},
        files={"file": ("x.jpg", JPG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 200, resp.json()
    row = _row(db_session, challenge["id"])
    assert STORED_PATH_RE.match(row.image_path)
    assert row.image_path != "../../escape.png"
    assert "escape" not in row.image_path


# 14. Public image retrieval (no auth) matches public challenge visibility ----


def test_get_image_public_without_auth(client, auth_client):
    challenge = _create_challenge(auth_client)
    _upload(auth_client, challenge["id"], "photo.png", PNG_BYTES, "image/png")
    # Public client (anonymous) can read both the challenge and its image.
    assert client.get(f"/api/challenges/{challenge['id']}").status_code == 200
    assert client.get(f"/api/challenges/{challenge['id']}/image").status_code == 200


# 15. Replacement removes old image only after success ------------------------


def test_replacement_removes_old_image_after_success(auth_client, uploads_root, db_session):
    challenge = _create_challenge(auth_client)
    _upload(auth_client, challenge["id"], "one.jpg", JPG_BYTES, "image/jpeg")
    old_path = _row(db_session, challenge["id"]).image_path
    old_file = uploads_root / old_path
    assert old_file.is_file()

    _upload(auth_client, challenge["id"], "two.png", PNG_BYTES, "image/png")
    new_path = _row(db_session, challenge["id"]).image_path
    assert new_path != old_path
    assert not old_file.exists(), "old image should be removed after replacement"
    assert (uploads_root / new_path).is_file()


# 16. Failed replacement leaves the existing image intact ---------------------


def test_failed_replacement_keeps_existing_image(auth_client, uploads_root, db_session):
    challenge = _create_challenge(auth_client)
    _upload(auth_client, challenge["id"], "ok.jpg", JPG_BYTES, "image/jpeg")
    kept_path = _row(db_session, challenge["id"]).image_path
    kept_file = uploads_root / kept_path
    assert kept_file.is_file()

    resp = _upload(auth_client, challenge["id"], "bad.jpg", TEXT_BYTES, "image/jpeg")
    assert resp.status_code == 400
    # Existing image reference and file are untouched.
    assert _row(db_session, challenge["id"]).image_path == kept_path
    assert kept_file.is_file()


# 18. Path traversal cannot escape uploads/reports ----------------------------


def test_path_traversal_cannot_escape(client, auth_client, db_session, uploads_root):
    challenge = _create_challenge(auth_client)
    row = _row(db_session, challenge["id"])
    # A malicious stored reference (e.g. injected server-side) pointing outside.
    row.image_path = "../../escape.txt"
    db_session.commit()
    assert client.get(f"/api/challenges/{challenge['id']}/image").status_code == 404


# 20. No client-controlled image_path can be injected -------------------------


def test_client_cannot_control_stored_path(auth_client, db_session):
    challenge = _create_challenge(auth_client)
    row = _row(db_session, challenge["id"])
    row.image_path = "reports/../../etc/passwd"
    db_session.commit()
    # Never served and never overwritten by the client; a public GET must 404.
    assert (
        auth_client.post(
            f"/api/challenges/{challenge['id']}/image",
            files={"file": ("x.jpg", JPG_BYTES, "image/jpeg")},
        ).status_code
        == 200
    )
    resp = auth_client.get(f"/api/challenges/{challenge['id']}/image")
    assert resp.status_code == 200
    assert resp.content == JPG_BYTES


# Get image returns content-type for each format ------------------------------


@pytest.mark.parametrize(
    "data,ctype",
    [(PNG_BYTES, "image/png"), (WEBP_BYTES, "image/webp")],
)
def test_get_image_content_type(client, auth_client, data, ctype):
    challenge = _create_challenge(auth_client)
    _upload(auth_client, challenge["id"], "img", data, ctype)
    assert client.get(f"/api/challenges/{challenge['id']}/image").headers[
        "content-type"
    ] == ctype
