#!/usr/bin/env python3
"""Smoke check for local and S3 asset storage adapters."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.storage_backends import LocalAssetStorage, S3AssetStorage  # noqa: E402


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.uploads = []

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.uploads.append((filename, bucket, key, ExtraArgs or {}))
        self.objects[(bucket, key)] = {
            "Bucket": bucket,
            "Key": key,
            "Body": Path(filename).read_bytes(),
            "ContentType": (ExtraArgs or {}).get("ContentType"),
        }

    def delete_object(self, **kwargs):
        self.deleted.append((kwargs["Bucket"], kwargs["Key"]))
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://example.test/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}&op={operation}"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-storage-") as tmp:
        root = Path(tmp)
        local = LocalAssetStorage(root)
        stored = local.save_bytes("uploads/sample.png", b"image", file_name="sample.png", mime_type="image/png")
        assert stored.storage_backend == "local"
        assert Path(stored.storage_key).exists()
        assert local.delete(stored.storage_key) is True
        assert local.delete(stored.storage_key) is False

        source = root / "source.mp4"
        source.write_bytes(b"video")
        fake = FakeS3Client()
        s3 = S3AssetStorage(bucket="bucket", prefix="dobedub", client=fake)
        stored_file = s3.save_file("outputs/source.mp4", source, file_name="source.mp4", mime_type="video/mp4")
        assert stored_file.storage_backend == "s3"
        assert stored_file.storage_key == "dobedub/outputs/source.mp4"
        assert ("bucket", "dobedub/outputs/source.mp4") in fake.objects
        assert s3.presigned_url(stored_file.storage_key).startswith("https://example.test/")
        assert s3.delete(stored_file.storage_key) is True
        assert ("bucket", "dobedub/outputs/source.mp4") in fake.deleted

    print("OK storage backend smoke check passed")


if __name__ == "__main__":
    main()
