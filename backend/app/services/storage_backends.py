from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredObject:
    storage_backend: str
    storage_key: str
    file_name: str
    mime_type: str
    size_bytes: int
    public_url: str | None = None


class LocalAssetStorage:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def save_bytes(self, key: str, data: bytes, *, file_name: str, mime_type: str | None = None) -> StoredObject:
        path = self.root_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        resolved_mime = mime_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return StoredObject(
            storage_backend="local",
            storage_key=str(path),
            file_name=file_name,
            mime_type=resolved_mime,
            size_bytes=len(data),
        )

    def save_file(self, key: str, source_path: Path, *, file_name: str | None = None, mime_type: str | None = None) -> StoredObject:
        data = Path(source_path).read_bytes()
        return self.save_bytes(key, data, file_name=file_name or Path(source_path).name, mime_type=mime_type)

    def delete(self, storage_key: str) -> bool:
        path = Path(storage_key)
        if not path.exists():
            return False
        path.unlink()
        return True


class S3AssetStorage:
    def __init__(self, *, bucket: str, prefix: str = "", client=None):
        if not bucket:
            raise ValueError("S3 bucket is required")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client or self._default_client()

    def save_bytes(self, key: str, data: bytes, *, file_name: str, mime_type: str | None = None) -> StoredObject:
        storage_key = self._key(key)
        resolved_mime = mime_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        self.client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=data,
            ContentType=resolved_mime,
        )
        return StoredObject(
            storage_backend="s3",
            storage_key=storage_key,
            file_name=file_name,
            mime_type=resolved_mime,
            size_bytes=len(data),
            public_url=f"s3://{self.bucket}/{storage_key}",
        )

    def save_file(self, key: str, source_path: Path, *, file_name: str | None = None, mime_type: str | None = None) -> StoredObject:
        path = Path(source_path)
        storage_key = self._key(key)
        resolved_mime = mime_type or mimetypes.guess_type(file_name or path.name)[0] or "application/octet-stream"
        extra_args = {"ContentType": resolved_mime}
        self.client.upload_file(str(path), self.bucket, storage_key, ExtraArgs=extra_args)
        return StoredObject(
            storage_backend="s3",
            storage_key=storage_key,
            file_name=file_name or path.name,
            mime_type=resolved_mime,
            size_bytes=path.stat().st_size if path.exists() else 0,
            public_url=f"s3://{self.bucket}/{storage_key}",
        )

    def delete(self, storage_key: str) -> bool:
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)
        return True

    def presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )

    def _key(self, key: str) -> str:
        cleaned = str(key or "").strip().lstrip("/")
        if not cleaned:
            raise ValueError("storage key is required")
        return f"{self.prefix}/{cleaned}" if self.prefix else cleaned

    @staticmethod
    def _default_client():
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for STORAGE_BACKEND=s3") from exc
        return boto3.client("s3")
