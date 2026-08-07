#!/usr/bin/env python3
"""Portable workflow/model inventory for a RunPod ComfyUI container.

This file intentionally uses only the Python standard library so it can be
uploaded to a RunPod Pod without the DOBEDUB application source tree.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


MODEL_FILE_SUFFIXES = {".bin", ".ckpt", ".gguf", ".pt", ".pth", ".safetensors"}
MODEL_BUCKET_DIRECTORIES = {
    "checkpoints": ("checkpoints",),
    "controlnet": ("controlnet",),
    "clip_vision": ("clip_vision",),
    "embeddings": ("embeddings",),
    "loras": ("loras",),
    "text_encoders": ("text_encoders", "clip"),
    "unet": ("unet", "diffusion_models"),
    "upscale_models": ("upscale_models",),
    "vae": ("vae",),
    "video_models": ("video_models",),
}


def model_bucket(class_type: str, field: str) -> str:
    text = f"{class_type} {field}".lower()
    if "controlnet" in text or "control_net" in text:
        return "controlnet"
    if "clip_vision" in text or "clipvision" in text:
        return "clip_vision"
    if "embedding" in text:
        return "embeddings"
    if "upscale" in text:
        return "upscale_models"
    if "lora" in text:
        return "loras"
    if "vae" in text:
        return "vae"
    if "clip" in text or "text_encoder" in text or "text encoder" in text:
        return "text_encoders"
    if "unet" in text or "diffusion" in text:
        return "unet"
    if "checkpoint" in text or "ckpt" in text:
        return "checkpoints"
    if "video" in text and ("model" in text or "name" in text):
        return "video_models"
    return ""


def is_link_value(value: object) -> bool:
    return isinstance(value, list) and len(value) >= 2 and isinstance(value[0], str)


def extract_references(workflows_dir: Path) -> list[dict]:
    references = []
    for workflow_path in sorted(workflows_dir.glob("*.json")):
        if workflow_path.name.endswith(".paramconfig.json"):
            continue
        try:
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"warning: skipped {workflow_path}: {error}")
            continue
        if not isinstance(workflow, dict):
            continue
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            class_type = str(node.get("class_type") or "")
            title = str((node.get("_meta") or {}).get("title") or class_type or "Node")
            for field, value in (node.get("inputs") or {}).items():
                if is_link_value(value) or not isinstance(value, str):
                    continue
                reference_path = value.replace("\\", "/").lstrip("/").strip()
                bucket = model_bucket(class_type, str(field))
                if not bucket or Path(reference_path).suffix.lower() not in MODEL_FILE_SUFFIXES:
                    continue
                references.append({
                    "workflowId": workflow_path.name,
                    "nodeId": str(node_id),
                    "nodeTitle": title,
                    "classType": class_type,
                    "field": str(field),
                    "bucket": bucket,
                    "fileName": Path(reference_path).name,
                    "referencePath": reference_path,
                })
    return sorted(references, key=lambda item: (item["bucket"], item["fileName"], item["workflowId"], item["nodeId"]))


def scan_models(models_dir: Path) -> list[dict]:
    files = []
    for bucket, directories in MODEL_BUCKET_DIRECTORIES.items():
        for directory in directories:
            base = models_dir / directory
            if not base.is_dir():
                continue
            for path in sorted(candidate for candidate in base.rglob("*") if candidate.is_file()):
                if path.suffix.lower() not in MODEL_FILE_SUFFIXES:
                    continue
                files.append({
                    "bucket": bucket,
                    "directory": directory,
                    "fileName": path.name,
                    "relativePath": str(path.relative_to(models_dir)),
                    "bucketRelativePath": str(path.relative_to(base)),
                    "sizeBytes": path.stat().st_size,
                })
    return files


def summarize_references(references: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for reference in references:
        key = (reference["bucket"], reference["referencePath"])
        item = grouped.setdefault(key, {
            "bucket": reference["bucket"],
            "fileName": reference["fileName"],
            "referencePath": reference["referencePath"],
            "workflows": set(),
            "nodes": [],
        })
        item["workflows"].add(reference["workflowId"])
        node = {key: reference[key] for key in ("workflowId", "nodeId", "nodeTitle", "classType", "field")}
        if node not in item["nodes"]:
            item["nodes"].append(node)
    return sorted(({
        **item,
        "workflows": sorted(item["workflows"]),
        "nodes": sorted(item["nodes"], key=lambda node: (node["workflowId"], node["nodeId"], node["field"])),
    } for item in grouped.values()), key=lambda item: (item["bucket"], item["fileName"], item["referencePath"]))


def build_report(workflows_dir: Path, models_dir: Path) -> dict:
    references = extract_references(workflows_dir)
    reference_summary = summarize_references(references)
    model_files = scan_models(models_dir)
    used_paths = set()
    referenced_files = []
    missing_references = []
    for reference in reference_summary:
        matches = [
            item for item in model_files
            if item["bucket"] == reference["bucket"]
            and (item["bucketRelativePath"] == reference["referencePath"] or item["fileName"] == reference["fileName"])
        ]
        if matches:
            referenced_files.append({**reference, "files": matches, "status": "present"})
            used_paths.update(item["relativePath"] for item in matches)
        else:
            missing_references.append({**reference, "status": "missing"})
    unused_candidates = [{**item, "status": "unused-candidate"} for item in model_files if item["relativePath"] not in used_paths]
    buckets = defaultdict(lambda: {"referenced": 0, "present": 0, "missing": 0, "unusedCandidates": 0, "unusedBytes": 0})
    for item in reference_summary:
        buckets[item["bucket"]]["referenced"] += 1
    for item in referenced_files:
        buckets[item["bucket"]]["present"] += 1
    for item in missing_references:
        buckets[item["bucket"]]["missing"] += 1
    for item in unused_candidates:
        buckets[item["bucket"]]["unusedCandidates"] += 1
        buckets[item["bucket"]]["unusedBytes"] += item["sizeBytes"]
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workflowsDir": str(workflows_dir),
        "modelsDir": str(models_dir),
        "inventoryAvailable": True,
        "safetyNotice": "unusedCandidates are comparison candidates only. Move/quarantine and test every active workflow before deletion.",
        "workflowReferences": references,
        "referencedFiles": referenced_files,
        "missingReferences": missing_references,
        "unusedCandidates": unused_candidates,
        "summary": {
            "workflowCount": len({item["workflowId"] for item in references}),
            "referenceCount": len(reference_summary),
            "actualModelFileCount": len(model_files),
            "unusedCandidateCount": len(unused_candidates),
            "unusedCandidateBytes": sum(item["sizeBytes"] for item in unused_candidates),
            "buckets": dict(sorted(buckets.items())),
        },
    }


def write_report(report: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "workflow-model-inventory.json"
    csv_path = output_dir / "workflow-model-inventory.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["recordType", "status", "bucket", "fileName", "relativePath", "sizeBytes", "referencePath", "workflows", "nodes"])
        writer.writeheader()
        for item in report["referencedFiles"]:
            writer.writerow({
                "recordType": "reference", "status": item["status"], "bucket": item["bucket"], "fileName": item["fileName"],
                "referencePath": item["referencePath"], "workflows": ", ".join(item["workflows"]),
                "nodes": "; ".join(f"{node['workflowId']}:{node['nodeId']}:{node['field']}" for node in item["nodes"]),
            })
        for item in report["unusedCandidates"]:
            writer.writerow({"recordType": "model-file", "status": item["status"], "bucket": item["bucket"], "fileName": item["fileName"], "relativePath": item["relativePath"], "sizeBytes": item["sizeBytes"]})
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ComfyUI workflow model selections to model files. No files are changed.")
    parser.add_argument("--workflows-dir", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/model-inventory"))
    args = parser.parse_args()
    if not args.workflows_dir.is_dir():
        parser.error(f"workflow directory does not exist: {args.workflows_dir}")
    if not args.models_dir.is_dir():
        parser.error(f"models directory does not exist: {args.models_dir}")
    try:
        json_path, csv_path = write_report(build_report(args.workflows_dir, args.models_dir), args.output_dir)
    except OSError as error:
        parser.error(f"cannot write report to {args.output_dir}: {error}")
    print(json.dumps({"json": str(json_path), "csv": str(csv_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
