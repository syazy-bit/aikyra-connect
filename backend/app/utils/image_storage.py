"""Minimal image storage abstraction for public photo evidence.

Keeps file-serving logic out of the service/repository layers so a future
object-storage backend can be swapped in without touching report logic.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

# Canonical mapped extensions (never preserved from client filenames).
_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class ImageValidationError(Exception):
    """Raised when an uploaded file is not a supported, size-compliant image."""


def _detect_extension(data: bytes) -> str | None:
    """Detect the image format from magic bytes and light structural markers.

    Never trusts the client filename, extension, or MIME type. Returns None
    when the bytes do not describe a supported image (rejects spoofed headers,
    truncated containers, and non-image files smuggled under an image name).
    """
    if data[:3] == b"\xff\xd8\xff" and b"\xff\xd9" in data:
        # JPEG: SOI marker + EOI marker.
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 16 and data[12:16] == b"IHDR":
        # PNG: signature followed by the mandatory first IHDR chunk.
        return "png"
    # WebP container: 'RIFF' + 4-byte size + 'WEBP' + a known first chunk.
    if (
        len(data) >= 16
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
        and data[12:16] in (b"VP8 ", b"VP8L", b"VP8X")
    ):
        return "webp"
    return None


class ImageStorage:
    """Interface for storing and retrieving challenge evidence images.

    All references are server-generated, relative storage paths. Clients never
    supply a filesystem path, filename, or URL.
    """

    def store(self, data: bytes) -> str:
        raise NotImplementedError

    def read(self, reference: str) -> tuple[bytes, str]:
        raise NotImplementedError

    def delete(self, reference: str) -> None:
        raise NotImplementedError


class LocalFileStorage(ImageStorage):
    """Filesystem-backed storage for the local/dev/demo environment.

    Files live under ``<uploads_dir>/reports/<server-generated-id>.<ext>`` and
    are only ever served through the API endpoint — never via StaticFiles.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root if root is not None else get_settings().uploads_dir).resolve()
        self.reports_dir = self.root / "reports"

    def store(self, data: bytes) -> str:
        if not data:
            raise ImageValidationError("The image file is empty.")
        if len(data) > MAX_IMAGE_BYTES:
            raise ImageValidationError(
                "The image is larger than 5 MB. Please upload a smaller photo."
            )
        ext = _detect_extension(data)
        if ext is None:
            raise ImageValidationError(
                "Unsupported file type. Only JPG, PNG or WebP images are allowed."
            )
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        relative = f"reports/{filename}"
        (self.reports_dir / filename).write_bytes(data)
        return relative

    def _safe_resolve(self, reference: str) -> Path:
        """Resolve a stored reference while preventing path traversal."""
        base = self.root.resolve()
        rel = Path(reference)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Invalid storage reference.")
        candidate = (base / rel).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError("Invalid storage reference.")
        return candidate

    def read(self, reference: str) -> tuple[bytes, str]:
        path = self._safe_resolve(reference)
        if not path.is_file():
            raise FileNotFoundError(reference)
        data = path.read_bytes()
        ext = path.suffix.lstrip(".").lower()
        return data, _CONTENT_TYPES.get(ext, "application/octet-stream")

    def delete(self, reference: str) -> None:
        """Best-effort cleanup. Never raises — a failed deletion (e.g. a
        tampered reference) must not break an otherwise-committed operation."""
        try:
            path = self._safe_resolve(reference)
        except ValueError:
            return
        try:
            path.unlink()
        except OSError:
            pass
