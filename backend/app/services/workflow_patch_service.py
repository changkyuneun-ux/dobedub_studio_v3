from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from backend.app.services import metadata_loader, workflow_parser
from backend.app.services.workflow_parser import PARAM_LABELS, PARAM_UI_KEYS


def apply_keyframe_images(workflow: dict, image_names: list[str], segments: list[dict] | None = None) -> list[dict]:
    applied = []
    for node_id, file_name in zip(workflow_parser.find_keyframe_images_ordered(workflow, segments), image_names):
        if node_id and file_name and workflow.get(node_id):
            workflow[node_id]["inputs"]["image"] = file_name
            applied.append({"node": node_id, "image": file_name})
    return applied


def validate_applied_images(workflow: dict, image_names: list[str], segments: list[dict] | None = None) -> None:
    missing = []
    nodes = workflow_parser.find_keyframe_images_ordered(workflow, segments)
    for node_id, expected_name in zip(nodes, image_names):
        actual_name = workflow.get(node_id, {}).get("inputs", {}).get("image")
        if actual_name != expected_name:
            missing.append({"node": node_id, "expected": expected_name, "actual": actual_name})
    if missing:
        raise ValueError(f"Workflow image patch failed: {json.dumps(missing, ensure_ascii=False)}")


def apply_image_slots(workflow: dict, image_names: dict[str, str]) -> list[dict]:
    slots = workflow_parser.find_image_slots(workflow)
    applied = []
    for role, file_name in image_names.items():
        node_id = slots.get(role)
        if node_id and file_name and workflow.get(node_id):
            workflow[node_id]["inputs"]["image"] = file_name
            applied.append({"role": role, "node": node_id, "image": file_name})
    return applied


def set_prompt_text(workflow: dict, node_id: str | None, text: str | None) -> str | None:
    if not node_id or text is None:
        return node_id
    inputs = workflow.get(node_id, {}).setdefault("inputs", {})
    inputs["text"] = str(text).strip()
    return node_id


def apply_segment_prompts(
    workflow: dict,
    segments: list[dict],
    positive_texts: list[str] | None = None,
    negative_additions: list[str] | None = None,
) -> list[dict]:
    positive_texts = positive_texts or []
    negative_additions = negative_additions or []
    applied = []
    for index, segment in enumerate(segments):
        positive_text = positive_texts[index] if index < len(positive_texts) else ""
        negative_text = negative_additions[index] if index < len(negative_additions) else ""
        if segment.get("positive_node") and str(positive_text).strip():
            workflow[segment["positive_node"]]["inputs"]["text"] = str(positive_text).strip()
            applied.append({"segment": index + 1, "node": segment["positive_node"], "field": "positive"})
        if segment.get("negative_node") and str(negative_text).strip():
            set_prompt_text(workflow, segment["negative_node"], negative_text)
            applied.append({"segment": index + 1, "node": segment["negative_node"], "field": "negative"})
    return applied


def apply_single_prompt(workflow: dict, positive_text: str | None, negative_text: str | None) -> list[dict]:
    applied = []
    positive_node = workflow_parser.find_prompt_node(workflow, "Positive")
    negative_node = workflow_parser.find_prompt_node(workflow, "Negative")
    if positive_node and str(positive_text or "").strip():
        workflow[positive_node]["inputs"]["text"] = str(positive_text).strip()
        applied.append({"node": positive_node, "field": "positive"})
    if negative_node and str(negative_text or "").strip():
        set_prompt_text(workflow, negative_node, negative_text)
        applied.append({"node": negative_node, "field": "negative"})
    return applied


def ui_config_to_param_config(node_config: dict) -> dict:
    return {
        "fps": node_config.get("fps"),
        "output_fps": node_config.get("outputFps", node_config.get("output_fps")),
        "frames": node_config.get("frames"),
        "duration_seconds": node_config.get("durationSeconds", node_config.get("duration_seconds")),
        "steps": node_config.get("steps"),
        "cfg_scale": node_config.get("cfgScale", node_config.get("cfg_scale")),
        "motion_shift": node_config.get("motionShift", node_config.get("motion_shift")),
        "seed": node_config.get("seed"),
        "bit_depth": node_config.get("bitDepth", node_config.get("bit_depth")),
        "video_format": node_config.get("videoFormat", node_config.get("video_format")),
        "video_codec": node_config.get("videoCodec", node_config.get("video_codec")),
    }


def values_equal(left, right) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return abs(float(left) - float(right)) < 1e-9
    except (TypeError, ValueError):
        return str(left) == str(right)


def apply_node_config_to_workflow(
    workflow: dict,
    workflow_id: str,
    segments_payload: list[dict],
    workflows_dir: Path,
) -> list[dict]:
    param_config = workflow_parser.load_param_config(workflow_id, workflows_dir)
    if not param_config:
        return []
    specs = param_config.get("segments") or []
    applied = []
    for index, segment in enumerate(segments_payload):
        segment_spec = specs[index] if index < len(specs) else {}
        params = segment_spec.get("params") or {}
        node_config = ui_config_to_param_config(segment.get("config") or {})
        for param_name, param_spec in params.items():
            value = node_config.get(param_name, param_spec.get("default"))
            if value is None:
                continue
            if values_equal(value, param_spec.get("default")):
                continue
            for target in param_spec.get("targets") or []:
                node_id = str(target.get("node"))
                field = target.get("field")
                if workflow.get(node_id) and field:
                    workflow[node_id].setdefault("inputs", {})[field] = value
                    applied.append({
                        "segment": index + 1,
                        "param": param_name,
                        "node": node_id,
                        "field": field,
                        "value": value,
                    })
    return applied


def build_wan_node_config_snapshot(
    workflow_id: str,
    segments_payload: list[dict],
    workflows_dir: Path,
) -> dict:
    try:
        workflow = workflow_parser.load_workflow(workflow_id, workflows_dir)
    except FileNotFoundError:
        workflow = {}
    param_config = workflow_parser.load_param_config(workflow_id, workflows_dir) or {}
    specs = param_config.get("segments") or []
    snapshot_segments = []
    for index, segment in enumerate(segments_payload or []):
        segment_spec = specs[index] if index < len(specs) else {}
        params = segment_spec.get("params") or {}
        ui_values = ui_config_to_param_config(segment.get("config") or {})
        param_items = []
        for param_name, param_spec in params.items():
            ui_key = PARAM_UI_KEYS.get(param_name, param_name)
            value = ui_values.get(param_name, param_spec.get("default"))
            param_items.append({
                "param": param_name,
                "uiKey": ui_key,
                "label": PARAM_LABELS.get(param_name, param_name),
                "value": value,
                "default": param_spec.get("default"),
                "type": param_spec.get("type", "float"),
                "min": param_spec.get("min"),
                "max": param_spec.get("max"),
                "options": param_spec.get("options") or [],
                "targets": [
                    metadata_loader.target_metadata(workflow, target)
                    for target in (param_spec.get("targets") or [])
                ],
            })
        snapshot_segments.append({
            "index": segment.get("index") or index + 1,
            "nodeId": segment.get("nodeId", ""),
            "subgraphName": segment.get("subgraphName", ""),
            "displayName": segment.get("displayName", "") or segment.get("subgraphName", "") or f"Subgraph_{index + 1}",
            "config": segment.get("config") or {},
            "params": param_items,
        })
    return {
        "workflowId": workflow_id,
        "capturedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "segments": snapshot_segments,
    }


def prepare_workflow_for_job(
    payload: dict,
    workflows_dir: Path,
    build_runpod_images: Callable[[dict], list[dict]],
    existing_save_video_outputs: Callable[[dict, str, list[dict]], dict],
) -> tuple[dict, list[dict], dict]:
    workflow_id = payload.get("workflowId") or "unknown"
    workflow = workflow_parser.load_workflow(workflow_id, workflows_dir)
    segments = workflow_parser.find_segments(workflow)
    segment_payloads = payload.get("segments") or []
    images = build_runpod_images(payload)
    image_names = [image["name"] for image in images]
    output_summary = existing_save_video_outputs(workflow, workflow_id, segments)
    patch_summary = {
        "images": [],
        "prompts": [],
        "nodeConfig": [],
        "finalOutputNodes": output_summary["finalOutputNodes"],
        "segmentOutputs": output_summary["segmentOutputs"],
    }

    if image_names:
        patch_summary["images"] = apply_keyframe_images(workflow, image_names, segments)
        validate_applied_images(workflow, image_names, segments)

    if segments:
        patch_summary["prompts"] = apply_segment_prompts(
            workflow,
            segments,
            [segment.get("positivePrompt", "") for segment in segment_payloads],
            [segment.get("negativePromptAddition", "") for segment in segment_payloads],
        )
    else:
        first_segment = segment_payloads[0] if segment_payloads else {}
        patch_summary["prompts"] = apply_single_prompt(
            workflow,
            first_segment.get("positivePrompt", ""),
            first_segment.get("negativePromptAddition", ""),
        )

    patch_summary["nodeConfig"] = apply_node_config_to_workflow(workflow, workflow_id, segment_payloads, workflows_dir)
    return workflow, images, patch_summary
