#!/usr/bin/env python3
"""Export workflow model references and optional ComfyUI model-directory comparison."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.model_inventory_service import build_model_inventory, write_inventory_reports  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List model files referenced by workflows and compare them with a ComfyUI models directory."
    )
    parser.add_argument("--workflows-dir", type=Path, default=PROJECT_ROOT / "workflows")
    parser.add_argument(
        "--models-dir",
        type=Path,
        help="ComfyUI models root, for example /workspace/ComfyUI/models. Omit to export references only.",
    )
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "model-inventory")
    args = parser.parse_args()

    if not args.workflows_dir.is_dir():
        parser.error(f"workflow directory does not exist: {args.workflows_dir}")
    if args.models_dir and not args.models_dir.is_dir():
        parser.error(
            f"models directory does not exist: {args.models_dir}. "
            "Run without --models-dir for a reference-only report, or run this command where the ComfyUI model volume is mounted."
        )

    report = build_model_inventory(args.workflows_dir, args.models_dir)
    try:
        json_path, csv_path = write_inventory_reports(report, args.output_dir)
    except OSError as error:
        parser.error(
            f"cannot write report to {args.output_dir}: {error}. "
            "Choose a writable path such as ~/Desktop/model-inventory on macOS."
        )
    print(json.dumps({
        "json": str(json_path),
        "csv": str(csv_path),
        "inventoryAvailable": report["inventoryAvailable"],
        "referenceCount": report["summary"]["referenceCount"],
        "unusedCandidateCount": report["summary"]["unusedCandidateCount"],
        "missingReferenceCount": len(report["missingReferences"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
