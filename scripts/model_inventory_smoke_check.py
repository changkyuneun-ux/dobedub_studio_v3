#!/usr/bin/env python3
"""Smoke check for workflow model-reference and storage-inventory reporting."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.model_inventory_service import build_model_inventory, write_inventory_reports  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-model-inventory-") as tmp:
        root = Path(tmp)
        workflows_dir = root / "workflows"
        models_dir = root / "models"
        workflows_dir.mkdir()
        for relative in (
            "checkpoints/used-checkpoint.safetensors",
            "checkpoints/unused-checkpoint.safetensors",
            "loras/used-lora.safetensors",
            "unet/used-unet.safetensors",
            "vae/unused-vae.safetensors",
        ):
            path = models_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"model")
        write_json(workflows_dir / "example.json", {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "used-checkpoint.safetensors"}},
            "2": {"class_type": "LoraLoader", "inputs": {"lora_name": "used-lora.safetensors"}},
            "3": {"class_type": "UNETLoader", "inputs": {"unet_name": "used-unet.safetensors"}},
            "4": {"class_type": "VAELoader", "inputs": {"vae_name": "missing-vae.safetensors"}},
        })
        report = build_model_inventory(workflows_dir, models_dir)
        assert report["inventoryAvailable"] is True
        assert report["summary"]["referenceCount"] == 4
        assert {item["fileName"] for item in report["missingReferences"]} == {"missing-vae.safetensors"}
        assert {item["fileName"] for item in report["unusedCandidates"]} == {"unused-checkpoint.safetensors", "unused-vae.safetensors"}
        json_path, csv_path = write_inventory_reports(report, root / "report")
        assert json_path.exists() and csv_path.exists()
        assert "unused-checkpoint.safetensors" in csv_path.read_text(encoding="utf-8")
    print("OK model inventory smoke check passed")


if __name__ == "__main__":
    main()
