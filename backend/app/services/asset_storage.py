from __future__ import annotations

import base64
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def media_kind(file_name: str, mime_type: str, fallback: str = "output") -> str:
    suffix = Path(file_name or "").suffix.lower()
    mime = str(mime_type or "")
    if mime.startswith("video/") or suffix in VIDEO_SUFFIXES:
        return "videos"
    if mime.startswith("image/") or suffix in IMAGE_SUFFIXES:
        return "images"
    return fallback or "output"


def safe_filename(name: str, fallback: str = "upload.bin") -> str:
    base = Path(name or fallback).name
    stem = Path(base).stem or Path(fallback).stem or "upload"
    suffix = Path(base).suffix[:12]
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "upload"
    return f"{stem}{suffix}"


def decode_data_url(value: str) -> tuple[bytes, str]:
    if not isinstance(value, str):
        raise ValueError("dataUrl must be a string")
    if "," not in value or not value.startswith("data:"):
        return base64.b64decode(value), "application/octet-stream"
    header, encoded = value.split(",", 1)
    mime_type = "application/octet-stream"
    if header.startswith("data:") and ";" in header:
        mime_type = header[5:].split(";", 1)[0] or mime_type
    return base64.b64decode(encoded), mime_type


def encode_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def asset_record(file_path: Path, asset_type: str, mime_type: str | None = None, file_name: str | None = None) -> dict:
    path = Path(file_path)
    resolved_mime_type = mime_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "assetId": f"asset_{uuid.uuid4().hex[:12]}",
        "type": asset_type,
        "fileName": file_name or path.name,
        "mimeType": resolved_mime_type,
        "path": str(path),
        "sizeBytes": path.stat().st_size if path.exists() else 0,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def path_within_storage(path: str | Path, allowed_roots: list[Path]) -> bool:
    try:
        resolved = Path(path).resolve()
    except (TypeError, OSError):
        return False
    return any(resolved == root.resolve() or root.resolve() in resolved.parents for root in allowed_roots)
