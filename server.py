#!/usr/bin/env python3
"""Local API + static server for DOBEDUB STUDIO.

The server defaults to dry-run job execution for local development. When
RUNPOD_DRY_RUN=0 is set with RunPod credentials, it patches real ComfyUI
Export(API) workflow JSON files and submits them to RunPod Serverless.
"""

from __future__ import annotations

import json
import os
import base64
import hashlib
import html
import mimetypes
import re
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


APP_DIR = Path(__file__).resolve().parent
DEFAULT_WORKFLOWS_DIR = APP_DIR / "workflows"


def load_env_file(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


load_env_file(APP_DIR / ".env")

def app_relative_path(value, default):
    path = Path(value) if value else Path(default)
    return path if path.is_absolute() else APP_DIR / path


WORKFLOWS_DIR = app_relative_path(os.environ.get("WORKFLOWS_DIR"), DEFAULT_WORKFLOWS_DIR)
DATA_DIR = app_relative_path(os.environ.get("STUDIO_DATA_DIR"), APP_DIR / "data")
METADATA_DIR = app_relative_path(os.environ.get("METADATA_DIR"), APP_DIR / "metadata")
HISTORY_PATH = DATA_DIR / "history.json"
ASSETS_PATH = DATA_DIR / "assets.json"
CONFIGS_PATH = DATA_DIR / "configs.json"
SEGMENT_DEFAULTS_PATH = DATA_DIR / "segment-defaults.json"
BUNDLED_SEGMENT_DEFAULTS_PATH = APP_DIR / "data" / "segment-defaults.json"
REPORTS_DIR = DATA_DIR / "reports"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = app_relative_path(os.environ.get("OUTPUTS_DIR"), DATA_DIR / "outputs")
MANUAL_PATH = APP_DIR / "docs" / "dobedub-studio-user-manual.md"
OBJECT_INFO_PATH = METADATA_DIR / "comfyui-object-info.json"
MODELS_METADATA_PATH = METADATA_DIR / "comfyui-models.json"
WORKFLOW_WIDGET_MAP_PATH = METADATA_DIR / "workflow-widget-map.json"
METADATA_MANIFEST_PATH = METADATA_DIR / "metadata-manifest.json"
DRY_RUN = os.environ.get("RUNPOD_DRY_RUN", "1") != "0"
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
RUNPOD_BASE_URL = os.environ.get("RUNPOD_BASE_URL", "https://api.runpod.ai/v2")
RUNPOD_TIMEOUT = int(os.environ.get("RUNPOD_TIMEOUT", "30"))
TERMINAL_RUNPOD_STATES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}

VIDEO_NODE_TYPES = {"WanFirstLastFrameToVideo", "WanImageToVideo"}

JOBS: dict[str, dict] = {}


def is_real_secret(value, placeholder):
    return bool(value and value.strip() and value.strip() != placeholder)


def runpod_is_configured():
    return (
        is_real_secret(RUNPOD_API_KEY, "your_runpod_api_key")
        and is_real_secret(RUNPOD_ENDPOINT_ID, "your_runpod_endpoint_id")
    )


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    tmp.replace(path)


def read_json_if_exists(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return default


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_source_paths():
    paths = []
    if WORKFLOWS_DIR.exists():
        paths.extend(sorted(WORKFLOWS_DIR.glob("*.json")))
    if SEGMENT_DEFAULTS_PATH.exists():
        paths.append(SEGMENT_DEFAULTS_PATH)
    if OBJECT_INFO_PATH.exists():
        paths.append(OBJECT_INFO_PATH)
    return [path for path in paths if path.is_file()]


def metadata_fingerprint():
    digest = hashlib.sha256()
    sources = []
    for path in metadata_source_paths():
        relative = str(path.relative_to(APP_DIR)) if path.is_relative_to(APP_DIR) else str(path)
        file_hash = file_sha256(path)
        digest.update(relative.encode("utf-8"))
        digest.update(file_hash.encode("utf-8"))
        sources.append({
            "path": relative,
            "sha256": file_hash,
            "sizeBytes": path.stat().st_size,
            "modifiedAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return digest.hexdigest(), sources


def inline_markdown(text):
    escaped = html.escape(text or "")
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def render_manual_table(lines):
    rows = []
    for line in lines:
        cells = [inline_markdown(cell.strip()) for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) >= 2 and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in rows[1]):
        header = rows[0]
        body = rows[2:]
    else:
        header = []
        body = rows
    parts = ["<div class=\"manual-table-wrap\"><table>"]
    if header:
        parts.append("<thead><tr>")
        parts.extend(f"<th>{cell}</th>" for cell in header)
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>")
        parts.extend(f"<td>{cell}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "\n".join(parts)


def render_manual_markdown(markdown):
    image_after_heading = {
        "2. 로그인과 접속 상태 확인": ("01-login.png", "그림 1. 로그인 화면"),
        "3. 메인 화면 구성": ("02-main.png", "그림 2. 메인 작업 화면"),
        "10. 작업 이력 조회와 관리": ("03-history.png", "그림 3. 작업 이력 및 결과 조회 모달"),
        "11. Metadata View": ("04-view-configs.png", "그림 4. Metadata View 모달"),
    }
    lines = markdown.splitlines()
    parts = []
    i = 0
    in_list = False
    list_tag = "ul"
    in_code = False
    code_lines = []

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            parts.append(f"</{list_tag}>")
            in_list = False
            list_tag = "ul"

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not stripped:
            close_list()
            i += 1
            continue
        if stripped.startswith("|") and "|" in stripped[1:]:
            close_list()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            parts.append(render_manual_table(table_lines))
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            tag = "h1" if level == 1 else "h2" if level == 2 else "h3"
            heading_id = re.sub(r"[^0-9A-Za-z가-힣]+", "-", text).strip("-")
            parts.append(f"<{tag} id=\"{html.escape(heading_id)}\">{inline_markdown(text)}</{tag}>")
            if text in image_after_heading:
                filename, caption = image_after_heading[text]
                parts.append(
                    "<figure>"
                    f"<img src=\"/docs/manual-assets/{html.escape(filename)}\" alt=\"{html.escape(caption)}\" />"
                    f"<figcaption>{html.escape(caption)}</figcaption>"
                    "</figure>"
                )
            i += 1
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        number = re.match(r"^\d+\.\s+(.+)$", stripped)
        if bullet or number:
            next_tag = "ol" if number else "ul"
            if in_list and list_tag != next_tag:
                close_list()
            if not in_list:
                list_tag = next_tag
                parts.append(f"<{list_tag}>")
                in_list = True
            parts.append(f"<li>{inline_markdown((bullet or number).group(1))}</li>")
            i += 1
            continue
        close_list()
        parts.append(f"<p>{inline_markdown(stripped)}</p>")
        i += 1
    close_list()
    if in_code:
        parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(parts)


def manual_html_page():
    if not MANUAL_PATH.exists():
        raise FileNotFoundError(MANUAL_PATH.name)
    markdown = MANUAL_PATH.read_text(encoding="utf-8")
    modified = datetime.fromtimestamp(MANUAL_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    body = render_manual_markdown(markdown)
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>dobedub studio 사용자 매뉴얼</title>
    <style>
      :root {{ color-scheme: light; --blue: #2f80ff; --line: #d6dde8; --muted: #596574; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; background: #f7f9fc; color: #111827; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", Arial, sans-serif; line-height: 1.62; }}
      main {{ max-width: 980px; margin: 0 auto; padding: 42px 48px 56px; background: #fff; min-height: 100vh; box-shadow: 0 18px 60px rgba(15, 23, 42, 0.12); }}
      h1 {{ margin: 0 0 12px; font-size: 34px; font-weight: 700; letter-spacing: 0; }}
      h2 {{ border-top: 1px solid var(--line); margin: 34px 0 14px; padding-top: 24px; font-size: 25px; letter-spacing: 0; }}
      h3 {{ margin: 24px 0 10px; font-size: 18px; }}
      p {{ margin: 0 0 12px; }}
      ul {{ margin: 0 0 14px 20px; padding: 0; }}
      li {{ margin: 5px 0; }}
      code {{ background: #eef4ff; border: 1px solid #d7e5ff; border-radius: 4px; color: #0f56b3; padding: 1px 5px; }}
      pre {{ background: #111827; border-radius: 8px; color: #f8fafc; overflow: auto; padding: 14px; }}
      figure {{ margin: 18px 0 22px; }}
      figure img {{ border: 1px solid #cbd5e1; border-radius: 8px; display: block; max-width: 100%; width: 100%; }}
      figcaption {{ color: var(--muted); font-size: 13px; margin-top: 8px; text-align: center; }}
      .manual-table-wrap {{ overflow-x: auto; margin: 14px 0 20px; }}
      table {{ border-collapse: collapse; min-width: 720px; width: 100%; }}
      th {{ background: #2563eb; color: #fff; font-weight: 700; }}
      th, td {{ border: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
      td {{ background: #fbfdff; }}
      @media (max-width: 720px) {{ main {{ padding: 28px 20px 40px; }} h1 {{ font-size: 28px; }} h2 {{ font-size: 22px; }} }}
    </style>
  </head>
  <body>
    <main>
      <p style="color: var(--muted); margin-bottom: 24px;">Last updated: {html.escape(modified)}</p>
      {body}
    </main>
  </body>
</html>"""


def index_html_page():
    index_path = APP_DIR / "index.html"
    body = index_path.read_text(encoding="utf-8")
    manual = MANUAL_PATH.read_text(encoding="utf-8") if MANUAL_PATH.exists() else ""
    manual = manual.replace("</script", "<\\/script")
    return body.replace("__MANUAL_MARKDOWN__", manual)


def workflow_files():
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted(path for path in WORKFLOWS_DIR.glob("*.json") if not path.name.endswith(".paramconfig.json"))


def load_workflow(workflow_id: str):
    safe_name = Path(workflow_id).name
    path = WORKFLOWS_DIR / safe_name
    if not path.exists() or path.suffix.lower() != ".json":
        raise FileNotFoundError(safe_name)
    return read_json(path)


def find_load_image_nodes(workflow):
    return [node_id for node_id, node in workflow.items() if node.get("class_type") == "LoadImage"]


def link_node(inputs, role):
    link = inputs.get(role)
    if isinstance(link, list) and link:
        return str(link[0])
    return None


def load_image_ref(workflow, inputs, role):
    node_id = link_node(inputs, role)
    if node_id and workflow.get(node_id, {}).get("class_type") == "LoadImage":
        return node_id
    return None


def find_segments(workflow):
    video_nodes = [
        node_id for node_id, node in workflow.items()
        if node.get("class_type") in VIDEO_NODE_TYPES
    ]
    if len(video_nodes) <= 1:
        return []

    by_id = {}
    for video_node in video_nodes:
        inputs = workflow[video_node].get("inputs", {})
        by_id[video_node] = {
            "video_node": video_node,
            "start_image_node": load_image_ref(workflow, inputs, "start_image"),
            "end_image_node": load_image_ref(workflow, inputs, "end_image"),
            "positive_node": link_node(inputs, "positive"),
            "negative_node": link_node(inputs, "negative"),
        }

    end_nodes = {segment["end_image_node"] for segment in by_id.values() if segment["end_image_node"]}
    starts = [segment for segment in by_id.values() if segment["start_image_node"] not in end_nodes]
    if len(starts) != 1:
        return list(by_id.values())

    ordered = [starts[0]]
    used = {ordered[0]["video_node"]}
    while True:
        current = ordered[-1]
        next_segment = None
        for segment in by_id.values():
          if segment["video_node"] in used:
              continue
          if segment["start_image_node"] == current["end_image_node"]:
              next_segment = segment
              break
        if next_segment is None:
            break
        ordered.append(next_segment)
        used.add(next_segment["video_node"])

    ordered.extend(segment for segment in by_id.values() if segment["video_node"] not in used)
    return ordered


def find_image_slots(workflow):
    for node_id, node in workflow.items():
        if node.get("class_type") not in VIDEO_NODE_TYPES:
            continue
        inputs = node.get("inputs", {})
        slots = {}
        for role in ("start_image", "end_image"):
            ref = load_image_ref(workflow, inputs, role)
            if ref:
                slots[role] = ref
        if slots:
            return slots
    nodes = find_load_image_nodes(workflow)
    return {"image": nodes[0]} if nodes else {}


def prompt_text(workflow, node_id):
    if not node_id:
        return ""
    return workflow.get(node_id, {}).get("inputs", {}).get("text", "") or ""


def find_prompt_node(workflow, label):
    for node_id, node in workflow.items():
        if node.get("class_type") != "CLIPTextEncode":
            continue
        title = node.get("_meta", {}).get("title", "")
        if label in title:
            return node_id
    return None


def keyframe_count(workflow, segments):
    if segments:
        ordered = []
        for segment in segments:
            for key in ("start_image_node", "end_image_node"):
                node_id = segment.get(key)
                if node_id and node_id not in ordered:
                    ordered.append(node_id)
        return len(ordered)
    return len(find_image_slots(workflow))


def find_keyframe_images_ordered(workflow, segments=None):
    segments = segments if segments is not None else find_segments(workflow)
    ordered = []
    for segment in segments:
        for key in ("start_image_node", "end_image_node"):
            node_id = segment.get(key)
            if node_id and node_id not in ordered:
                ordered.append(node_id)
    if ordered:
        return ordered
    slots = find_image_slots(workflow)
    for role in ("start_image", "end_image", "image"):
        node_id = slots.get(role)
        if node_id and node_id not in ordered:
            ordered.append(node_id)
    for node_id in find_load_image_nodes(workflow):
        if node_id not in ordered:
            ordered.append(node_id)
    return ordered


def apply_keyframe_images(workflow, image_names, segments=None):
    applied = []
    for node_id, file_name in zip(find_keyframe_images_ordered(workflow, segments), image_names):
        if node_id and file_name and workflow.get(node_id):
            workflow[node_id]["inputs"]["image"] = file_name
            applied.append({"node": node_id, "image": file_name})
    return applied


def validate_applied_images(workflow, image_names, segments=None):
    missing = []
    nodes = find_keyframe_images_ordered(workflow, segments)
    for node_id, expected_name in zip(nodes, image_names):
        actual_name = workflow.get(node_id, {}).get("inputs", {}).get("image")
        if actual_name != expected_name:
            missing.append({"node": node_id, "expected": expected_name, "actual": actual_name})
    if missing:
        raise ValueError(f"Workflow image patch failed: {json.dumps(missing, ensure_ascii=False)}")


def apply_image_slots(workflow, image_names):
    slots = find_image_slots(workflow)
    applied = []
    for role, file_name in image_names.items():
        node_id = slots.get(role)
        if node_id and file_name and workflow.get(node_id):
            workflow[node_id]["inputs"]["image"] = file_name
            applied.append({"role": role, "node": node_id, "image": file_name})
    return applied


def set_prompt_text(workflow, node_id, text):
    if not node_id or text is None:
        return node_id
    inputs = workflow.get(node_id, {}).setdefault("inputs", {})
    inputs["text"] = str(text).strip()
    return node_id


def apply_segment_prompts(workflow, segments, positive_texts=None, negative_additions=None):
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


def apply_single_prompt(workflow, positive_text, negative_text):
    applied = []
    positive_node = find_prompt_node(workflow, "Positive")
    negative_node = find_prompt_node(workflow, "Negative")
    if positive_node and str(positive_text or "").strip():
        workflow[positive_node]["inputs"]["text"] = str(positive_text).strip()
        applied.append({"node": positive_node, "field": "positive"})
    if negative_node and str(negative_text or "").strip():
        set_prompt_text(workflow, negative_node, negative_text)
        applied.append({"node": negative_node, "field": "negative"})
    return applied


def load_param_config(workflow_id):
    base = Path(workflow_id).stem
    path = WORKFLOWS_DIR / f"{base}.paramconfig.json"
    if not path.exists():
        return None
    return read_json(path)


def ui_config_to_param_config(node_config):
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


def apply_node_config_to_workflow(workflow, workflow_id, segments_payload):
    param_config = load_param_config(workflow_id)
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


def build_wan_node_config_snapshot(workflow_id, segments_payload):
    try:
        workflow = load_workflow(workflow_id)
    except FileNotFoundError:
        workflow = {}
    param_config = load_param_config(workflow_id) or {}
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
                    target_metadata(workflow, target)
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


def values_equal(left, right):
    if left is None or right is None:
        return left is right
    try:
        return abs(float(left) - float(right)) < 1e-9
    except (TypeError, ValueError):
        return str(left) == str(right)


def default_config(index):
    return {
        "fps": 16,
        "frames": 81 if index == 1 else 96,
        "steps": 20,
        "cfgScale": 5.0,
        "motionShift": 1.0,
        "seed": 4920381920 + index - 1,
    }


PARAM_UI_KEYS = {
    "fps": "fps",
    "output_fps": "outputFps",
    "frames": "frames",
    "duration_seconds": "durationSeconds",
    "steps": "steps",
    "cfg_scale": "cfgScale",
    "motion_shift": "motionShift",
    "seed": "seed",
    "bit_depth": "bitDepth",
    "video_format": "videoFormat",
    "video_codec": "videoCodec",
}

PARAM_LABELS = {
    "fps": "FPS",
    "output_fps": "Final Output FPS",
    "frames": "Frames",
    "duration_seconds": "Duration",
    "steps": "Sampling Steps",
    "cfg_scale": "CFG Scale",
    "motion_shift": "Motion Shift",
    "seed": "Seed",
    "bit_depth": "Final Bit Depth",
    "video_format": "Final Format",
    "video_codec": "Final Codec",
}

PARAM_DESCRIPTIONS = {
    "fps": "초당 프레임 수입니다. 높을수록 재생은 부드럽지만 출력 프레임/처리량이 증가합니다.",
    "output_fps": "최종 출력 비디오의 초당 프레임 수입니다. 세그먼트 생성 FPS와 별도로 최종 결합 영상 저장에 적용됩니다.",
    "frames": "생성할 총 프레임 수입니다. 길이와 움직임 범위를 직접 결정합니다.",
    "duration_seconds": "영상 길이입니다. duration 기반 workflow에서는 내부 수식으로 프레임 길이에 반영됩니다.",
    "steps": "샘플링 반복 횟수입니다. 높을수록 디테일은 늘 수 있지만 생성 시간이 증가합니다.",
    "cfg_scale": "프롬프트 반영 강도입니다. 과도하게 높으면 왜곡이나 경직된 움직임이 생길 수 있습니다.",
    "motion_shift": "움직임 변화량입니다. workflow 내 연결된 sampling 노드에 동일하게 반영될 수 있습니다.",
    "seed": "결과 재현값입니다. 같은 입력/설정에서 동일한 결과를 재현할 때 사용합니다.",
    "bit_depth": "최종 출력 비디오의 비트 깊이입니다. 기본값 8을 권장합니다.",
    "video_format": "SaveVideo format 값입니다. ComfyUI 환경에서 지원하는 값만 사용해야 하며 기본값은 auto입니다.",
    "video_codec": "SaveVideo codec 값입니다. ComfyUI 환경에서 지원하는 값만 사용해야 하며 기본값은 auto입니다.",
}


def config_from_param_spec(workflow_id, index):
    param_config = load_param_config(workflow_id)
    fallback = default_config(index)
    if not param_config:
        return fallback, []
    specs = param_config.get("segments") or []
    segment_spec = specs[index - 1] if index - 1 < len(specs) else {}
    params = segment_spec.get("params") or {}
    config = {}
    controls = []
    for param_name, param_spec in params.items():
        ui_key = PARAM_UI_KEYS.get(param_name)
        if not ui_key:
            continue
        default_value = param_spec.get("default")
        if default_value is None:
            continue
        config[ui_key] = default_value
        controls.append({
            "key": ui_key,
            "param": param_name,
            "label": PARAM_LABELS.get(param_name, param_name),
            "type": param_spec.get("type", "float"),
            "min": param_spec.get("min"),
            "max": param_spec.get("max"),
            "default": default_value,
            "randomizable": bool(param_spec.get("randomizable")),
            "options": param_spec.get("options") or [],
            "description": param_spec.get("description") or param_spec.get("note") or PARAM_DESCRIPTIONS.get(param_name, ""),
            "note": param_spec.get("note", ""),
            "targets": param_spec.get("targets") or [],
        })
    for key, value in fallback.items():
        config.setdefault(key, value)
    return config, controls


def workflow_schema(workflow_id):
    ensure_metadata_current()
    workflow = load_workflow(workflow_id)
    segments = find_segments(workflow)
    slots = find_image_slots(workflow)

    def subgraph_info(video_node, index):
        node = workflow.get(video_node or "", {})
        title = (node.get("_meta") or {}).get("title") or node.get("class_type") or "Subgraph"
        return {
            "nodeId": video_node or "",
            "subgraphName": title,
            "displayName": f"{title}_{index}",
        }

    if segments:
        mode = "multi_segment"
        segment_items = []
        for index, segment in enumerate(segments, start=1):
            config, controls = config_from_param_spec(workflow_id, index)
            segment_items.append({
                "index": index,
                **subgraph_info(segment.get("video_node"), index),
                "startImageIndex": index,
                "endImageIndex": index + 1,
                "defaultPositivePrompt": prompt_text(workflow, segment.get("positive_node")),
                "defaultNegativePrompt": prompt_text(workflow, segment.get("negative_node")),
                "config": config,
                "configControls": controls,
            })
    else:
        mode = "dual" if {"start_image", "end_image"}.issubset(slots) else "single"
        config, controls = config_from_param_spec(workflow_id, 1)
        video_node = next(
            (
                node_id for node_id, node in workflow.items()
                if node.get("class_type") in VIDEO_NODE_TYPES
            ),
            "",
        )
        segment_items = [{
            "index": 1,
            **subgraph_info(video_node, 1),
            "startImageIndex": 1,
            "endImageIndex": 2 if mode == "dual" else None,
            "defaultPositivePrompt": prompt_text(workflow, find_prompt_node(workflow, "Positive")),
            "defaultNegativePrompt": prompt_text(workflow, find_prompt_node(workflow, "Negative")),
            "config": config,
            "configControls": controls,
        }]

    return {
        "workflowId": workflow_id,
        "name": Path(workflow_id).stem,
        "mode": mode,
        "keyframeCount": keyframe_count(workflow, segments),
        "segmentCount": len(segment_items),
        "segments": segment_items,
    }


def node_title(node):
    return (node.get("_meta") or {}).get("title") or node.get("class_type") or "Node"


def is_link_value(value):
    return isinstance(value, list) and len(value) >= 2 and isinstance(value[0], str)


def serializable_input_value(value):
    if is_link_value(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def object_info_class(object_info, class_type):
    if not isinstance(object_info, dict):
        return {}
    return object_info.get(class_type) or {}


def object_info_input_options(class_info, field):
    if not isinstance(class_info, dict):
        return []
    inputs = class_info.get("input") or {}
    for group in ("required", "optional"):
        fields = inputs.get(group) or {}
        spec = fields.get(field)
        if isinstance(spec, list) and spec and isinstance(spec[0], list):
            return [str(item) for item in spec[0]]
    return []


def model_bucket_for_field(class_type, field):
    field_text = str(field or "").lower()
    class_text = str(class_type or "").lower()
    if not (
        field_text.endswith("_name")
        or field_text in {"ckpt_name", "vae_name", "lora_name", "clip_name", "unet_name", "model_name"}
        or "model_name" in field_text
        or "checkpoint" in field_text
    ):
        return ""
    text = f"{class_text} {field_text}"
    if "lora" in text:
        return "loras"
    if "vae" in text:
        return "vae"
    if "clip" in text or "text_encoder" in text or "text encoder" in text:
        return "text_encoders"
    if "unet" in text or "diffusion" in text:
        return "unet"
    if "ckpt" in text or "checkpoint" in text:
        return "checkpoints"
    if "upscale" in text:
        return "upscale_models"
    if "wan" in text or "video" in text:
        return "video_models"
    if "model" in text:
        return "models"
    return ""


def add_model_value(model_map, bucket, value):
    if not bucket or not isinstance(value, str) or not value.strip():
        return
    values = model_map.setdefault(bucket, [])
    if value not in values:
        values.append(value)


def workflow_model_references(workflow, object_info=None):
    model_map = {}
    for node in workflow.values():
        class_type = node.get("class_type", "")
        class_info = object_info_class(object_info, class_type)
        for field, value in (node.get("inputs") or {}).items():
            if is_link_value(value):
                continue
            bucket = model_bucket_for_field(class_type, field)
            add_model_value(model_map, bucket, value)
            for option in object_info_input_options(class_info, field):
                add_model_value(model_map, bucket, option)
    return {key: sorted(values) for key, values in sorted(model_map.items())}


def target_metadata(workflow, target):
    node_id = str(target.get("node", ""))
    field = target.get("field", "")
    node = workflow.get(node_id, {})
    return {
        "nodeId": node_id,
        "field": field,
        "classType": node.get("class_type", ""),
        "title": node_title(node) if node else "",
    }


def metadata_param_controls(workflow, segment_spec):
    controls = []
    for param_name, param_spec in (segment_spec.get("params") or {}).items():
        targets = [target_metadata(workflow, target) for target in (param_spec.get("targets") or [])]
        controls.append({
            "param": param_name,
            "uiKey": PARAM_UI_KEYS.get(param_name, param_name),
            "label": PARAM_LABELS.get(param_name, param_name),
            "type": param_spec.get("type", "float"),
            "min": param_spec.get("min"),
            "max": param_spec.get("max"),
            "default": param_spec.get("default"),
            "randomizable": bool(param_spec.get("randomizable")),
            "sync": bool(param_spec.get("sync")),
            "options": param_spec.get("options") or [],
            "description": param_spec.get("description") or param_spec.get("note") or PARAM_DESCRIPTIONS.get(param_name, ""),
            "note": param_spec.get("note", ""),
            "targets": targets,
        })
    return controls


def workflow_nodes_metadata(workflow, object_info=None):
    nodes = []
    for node_id, node in sorted(workflow.items(), key=lambda item: item[0]):
        class_type = node.get("class_type", "")
        class_info = object_info_class(object_info, class_type)
        inputs = []
        links = []
        for field, value in (node.get("inputs") or {}).items():
            if is_link_value(value):
                links.append({"field": field, "sourceNodeId": value[0], "sourceOutput": value[1]})
                continue
            bucket = model_bucket_for_field(class_type, field)
            inputs.append({
                "field": field,
                "value": serializable_input_value(value),
                "modelBucket": bucket,
                "options": object_info_input_options(class_info, field),
            })
        nodes.append({
            "nodeId": node_id,
            "classType": class_type,
            "title": node_title(node),
            "inputs": inputs,
            "links": links,
            "hasObjectInfo": bool(class_info),
        })
    return nodes


def build_workflow_widget_metadata(workflow_id, workflow, object_info=None):
    param_config = load_param_config(workflow_id) or {}
    segments = find_segments(workflow)
    segment_specs = param_config.get("segments") or []
    video_nodes = [
        node_id for node_id, node in workflow.items()
        if node.get("class_type") in VIDEO_NODE_TYPES
    ]
    if segments:
        segment_items = []
        for index, segment in enumerate(segments, start=1):
            video_node = segment.get("video_node")
            spec = segment_specs[index - 1] if index - 1 < len(segment_specs) else {}
            segment_items.append({
                "index": index,
                "nodeId": video_node,
                "subgraphName": node_title(workflow.get(video_node, {})),
                "displayName": f"{node_title(workflow.get(video_node, {}))}_{index}",
                "classType": workflow.get(video_node, {}).get("class_type", ""),
                "positiveNode": segment.get("positive_node"),
                "negativeNode": segment.get("negative_node"),
                "startImageNode": segment.get("start_image_node"),
                "endImageNode": segment.get("end_image_node"),
                "params": metadata_param_controls(workflow, spec),
            })
    else:
        video_node = video_nodes[0] if video_nodes else ""
        spec = segment_specs[0] if segment_specs else {}
        segment_items = [{
            "index": 1,
            "nodeId": video_node,
            "subgraphName": node_title(workflow.get(video_node, {})),
            "displayName": f"{node_title(workflow.get(video_node, {}))}_1",
            "classType": workflow.get(video_node, {}).get("class_type", ""),
            "positiveNode": find_prompt_node(workflow, "Positive"),
            "negativeNode": find_prompt_node(workflow, "Negative"),
            "startImageNode": find_keyframe_images_ordered(workflow, [])[0] if find_keyframe_images_ordered(workflow, []) else "",
            "endImageNode": "",
            "params": metadata_param_controls(workflow, spec),
        }]
    return {
        "workflowId": workflow_id,
        "name": Path(workflow_id).stem,
        "nodeCount": len(workflow),
        "nodes": workflow_nodes_metadata(workflow, object_info),
        "segments": segment_items,
        "models": workflow_model_references(workflow, object_info),
    }


def merge_model_metadata(workflow_metadata_items):
    merged = {}
    for item in workflow_metadata_items.values():
        for bucket, values in (item.get("models") or {}).items():
            merged.setdefault(bucket, [])
            for value in values:
                if value not in merged[bucket]:
                    merged[bucket].append(value)
    return {key: sorted(values) for key, values in sorted(merged.items())}


def rebuild_metadata():
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    object_info = read_json_if_exists(OBJECT_INFO_PATH, {})
    fingerprint, sources = metadata_fingerprint()
    workflows = {}
    for path in workflow_files():
        workflow = read_json(path)
        workflows[path.name] = build_workflow_widget_metadata(path.name, workflow, object_info)
    models = merge_model_metadata(workflows)
    manifest = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "workflow-json",
        "workflowDirectory": str(WORKFLOWS_DIR.relative_to(APP_DIR)) if WORKFLOWS_DIR.is_relative_to(APP_DIR) else str(WORKFLOWS_DIR),
        "fingerprint": fingerprint,
        "workflowCount": len(workflows),
        "hasObjectInfoSnapshot": OBJECT_INFO_PATH.exists(),
        "sources": sources,
    }
    write_json(WORKFLOW_WIDGET_MAP_PATH, {
        "manifest": manifest,
        "workflows": workflows,
    })
    write_json(MODELS_METADATA_PATH, {
        "manifest": manifest,
        "models": models,
    })
    write_json(METADATA_MANIFEST_PATH, manifest)
    return manifest


def ensure_metadata_current(force=False):
    fingerprint, _ = metadata_fingerprint()
    manifest = read_json_if_exists(METADATA_MANIFEST_PATH, {})
    if (
        not force
        and manifest.get("fingerprint") == fingerprint
        and WORKFLOW_WIDGET_MAP_PATH.exists()
        and MODELS_METADATA_PATH.exists()
    ):
        return manifest
    return rebuild_metadata()


def metadata_status():
    manifest = ensure_metadata_current()
    return {
        "ok": True,
        "metadataDir": str(METADATA_DIR),
        "manifest": manifest,
        "files": {
            "objectInfo": {
                "path": str(OBJECT_INFO_PATH),
                "exists": OBJECT_INFO_PATH.exists(),
            },
            "workflowWidgetMap": {
                "path": str(WORKFLOW_WIDGET_MAP_PATH),
                "exists": WORKFLOW_WIDGET_MAP_PATH.exists(),
            },
            "models": {
                "path": str(MODELS_METADATA_PATH),
                "exists": MODELS_METADATA_PATH.exists(),
            },
        },
    }


def workflow_widget_metadata(workflow_id):
    ensure_metadata_current()
    data = read_json_if_exists(WORKFLOW_WIDGET_MAP_PATH, {"workflows": {}})
    item = (data.get("workflows") or {}).get(Path(workflow_id).name)
    if not item:
        raise FileNotFoundError(workflow_id)
    return item


def model_metadata():
    ensure_metadata_current()
    return read_json_if_exists(MODELS_METADATA_PATH, {"models": {}})


def list_workflows():
    ensure_metadata_current()
    result = []
    for path in workflow_files():
        try:
            schema = workflow_schema(path.name)
        except Exception:
            continue
        result.append({
            "id": path.name,
            "name": path.stem,
            "mode": schema["mode"],
            "keyframeCount": schema["keyframeCount"],
            "segmentCount": schema["segmentCount"],
        })
    return result


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def media_kind(file_name, mime_type, fallback="output"):
    suffix = Path(file_name or "").suffix.lower()
    mime = str(mime_type or "")
    if mime.startswith("video/") or suffix in VIDEO_SUFFIXES:
        return "videos"
    if mime.startswith("image/") or suffix in IMAGE_SUFFIXES:
        return "images"
    return fallback or "output"


def hydrate_output_asset(asset, assets=None):
    assets = assets if assets is not None else load_assets()
    item = dict(asset or {})
    stored = assets.get(item.get("assetId"), {})
    file_name = item.get("fileName") or item.get("filename") or stored.get("fileName") or "generated-output"
    mime_type = (
        item.get("mimeType")
        or stored.get("mimeType")
        or mimetypes.guess_type(file_name)[0]
        or "application/octet-stream"
    )
    kind = media_kind(file_name, mime_type, item.get("kind"))
    item.update({
        "fileName": file_name,
        "kind": kind,
        "mimeType": mime_type,
        "downloadUrl": item.get("downloadUrl") or item.get("url") or f"/api/files/{item.get('assetId')}",
        "sizeBytes": item.get("sizeBytes") or stored.get("sizeBytes"),
    })
    return item


def prompt_list_from_pipe(value):
    text = str(value or "").strip()
    if not text:
        return []
    parts = [part.strip() for part in text.split("|") if part.strip()]
    result = []
    for index, part in enumerate(parts, start=1):
        cleaned = re.sub(r"^\s*\d+\s*[:.)-]\s*", "", part).strip()
        if cleaned:
            result.append({"index": index, "text": cleaned})
    return result or [{"index": 1, "text": text}]


def history_prompt_items(item, field, fallback=""):
    stored = item.get(f"{field}Prompts")
    if isinstance(stored, list) and stored:
        result = []
        for index, value in enumerate(stored, start=1):
            if isinstance(value, dict):
                text = value.get("text") or value.get(field) or value.get("prompt") or ""
                prompt_index = value.get("index") or index
            else:
                text = value
                prompt_index = index
            if str(text or "").strip():
                result.append({"index": prompt_index, "text": str(text).strip()})
        if result:
            return result
    segments = item.get("segments") or []
    segment_key = "positivePrompt" if field == "positive" else "negativePromptAddition"
    result = [
        {"index": segment.get("index") or index + 1, "text": str(segment.get(segment_key) or "").strip()}
        for index, segment in enumerate(segments)
        if str(segment.get(segment_key) or "").strip()
    ]
    if result:
        return result
    return prompt_list_from_pipe(item.get(f"{field}Prompt") or fallback)


def hydrate_input_images(item, assets=None):
    assets = assets if assets is not None else load_assets()
    keyframes = item.get("keyframes") or []
    input_assets = item.get("inputAssets") or []
    result = []
    seen = set()
    for index, keyframe in enumerate(keyframes, start=1):
        asset_id = keyframe.get("uploadId") or (input_assets[index - 1] if index - 1 < len(input_assets) else "")
        stored = assets.get(asset_id, {}) if asset_id else {}
        file_name = keyframe.get("fileName") or stored.get("fileName") or "-"
        if asset_id or file_name != "-":
            key = (asset_id, file_name)
            if key not in seen:
                result.append({"index": keyframe.get("index") or index, "assetId": asset_id, "fileName": file_name})
                seen.add(key)
    for index, asset_id in enumerate(input_assets, start=1):
        if any(item.get("assetId") == asset_id for item in result):
            continue
        stored = assets.get(asset_id, {})
        result.append({"index": index, "assetId": asset_id, "fileName": stored.get("fileName") or "-"})
    return result


def hydrate_history_item(item, assets=None):
    hydrated = dict(item or {})
    hydrated["outputAssets"] = [
        hydrate_output_asset(asset, assets)
        for asset in hydrated.get("outputAssets") or []
    ]
    user = hydrated.get("user") or {}
    hydrated["workerName"] = hydrated.get("workerName") or user.get("name") or hydrated.get("userName") or "-"
    hydrated["positivePrompts"] = history_prompt_items(hydrated, "positive", hydrated.get("prompt", ""))
    hydrated["negativePrompts"] = history_prompt_items(hydrated, "negative", hydrated.get("negativePrompt", ""))
    hydrated["inputImages"] = hydrated.get("inputImages") or hydrate_input_images(hydrated, assets)
    hydrated["wanNodeConfig"] = hydrated.get("wanNodeConfig") or {}
    return hydrated


def load_history():
    if not HISTORY_PATH.exists():
        return []
    assets = load_assets()
    return [hydrate_history_item(item, assets) for item in read_json(HISTORY_PATH)]


def append_history(item):
    history = load_history()
    history.insert(0, item)
    write_json(HISTORY_PATH, history[:200])
    return history


def load_configs():
    if not CONFIGS_PATH.exists():
        return []
    return read_json(CONFIGS_PATH)


def append_config(item):
    configs = load_configs()
    configs.insert(0, item)
    write_json(CONFIGS_PATH, configs[:200])
    return configs


def load_segment_defaults():
    defaults = {}
    if BUNDLED_SEGMENT_DEFAULTS_PATH.exists():
        defaults.update(read_json(BUNDLED_SEGMENT_DEFAULTS_PATH))
    if SEGMENT_DEFAULTS_PATH.exists() and SEGMENT_DEFAULTS_PATH != BUNDLED_SEGMENT_DEFAULTS_PATH:
        defaults.update(read_json(SEGMENT_DEFAULTS_PATH))
    return defaults


def workflow_segment_defaults(workflow_id):
    defaults = load_segment_defaults()
    safe_name = Path(workflow_id).name
    if safe_name not in defaults:
        raise KeyError(safe_name)
    return defaults[safe_name]


def prompt_options():
    history = load_history()
    configs = load_configs()
    options = {"positive": [], "negative": []}

    def add_option(kind, text, label, source, workflow_id="", segment_index=None):
        cleaned = str(text or "").strip()
        if not cleaned:
            return
        option_id = f"{kind}_{uuid.uuid5(uuid.NAMESPACE_URL, f'{kind}:{source}:{label}:{cleaned}').hex[:12]}"
        if any(item["text"] == cleaned and item["label"] == label for item in options[kind]):
            return
        options[kind].append({
            "id": option_id,
            "label": label,
            "text": cleaned,
            "source": source,
            "workflowId": workflow_id,
            "segmentIndex": segment_index,
        })

    for item in history:
        workflow_id = item.get("workflowId") or item.get("workflowName") or item.get("workflow") or ""
        timestamp = item.get("timestamp") or "-"
        for prompt in item.get("positivePrompts") or []:
            label = f"{timestamp} / {Path(workflow_id).stem or 'workflow'} / Segment {prompt.get('index', 1)}"
            add_option("positive", prompt.get("text"), label, "history", workflow_id, prompt.get("index"))
        for prompt in item.get("negativePrompts") or []:
            label = f"{timestamp} / {Path(workflow_id).stem or 'workflow'} / Segment {prompt.get('index', 1)}"
            add_option("negative", prompt.get("text"), label, "history", workflow_id, prompt.get("index"))

    for item in configs:
        snapshot = item.get("snapshot") or {}
        workflow_id = snapshot.get("workflowId") or item.get("workflowId") or ""
        timestamp = item.get("timestamp") or "-"
        for segment in snapshot.get("segments") or []:
            label = f"{timestamp} / {Path(workflow_id).stem or 'workflow'} / Segment {segment.get('index', 1)}"
            add_option("positive", segment.get("positivePrompt"), label, "config", workflow_id, segment.get("index"))
            add_option("negative", segment.get("negativePromptAddition") or segment.get("negativePrompt"), label, "config", workflow_id, segment.get("index"))

    return {
        "positive": options["positive"][:100],
        "negative": options["negative"][:100],
    }


def load_assets():
    if not ASSETS_PATH.exists():
        return {}
    return read_json(ASSETS_PATH)


def save_assets(assets):
    write_json(ASSETS_PATH, assets)


def raw_history_items():
    if not HISTORY_PATH.exists():
        return []
    return read_json(HISTORY_PATH)


def item_asset_ids(item):
    asset_ids = []

    def add(value):
        text = str(value or "").strip()
        if text and text not in asset_ids:
            asset_ids.append(text)

    for asset_id in item.get("inputAssets") or []:
        add(asset_id)
    for image in item.get("inputImages") or []:
        if isinstance(image, dict):
            add(image.get("assetId"))
    for keyframe in item.get("keyframes") or []:
        if isinstance(keyframe, dict):
            add(keyframe.get("uploadId"))
    for asset in item.get("outputAssets") or []:
        if isinstance(asset, dict):
            add(asset.get("assetId"))
    return asset_ids


def path_within_storage(path):
    try:
        resolved = Path(path).resolve()
    except (TypeError, OSError):
        return False
    allowed_roots = [UPLOADS_DIR.resolve(), OUTPUTS_DIR.resolve()]
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def delete_asset_file(asset):
    path = asset.get("path")
    if not path or not path_within_storage(path):
        return {"path": path or "", "deleted": False, "reason": "not-managed-path"}
    file_path = Path(path)
    if not file_path.exists():
        return {"path": str(file_path), "deleted": False, "reason": "missing"}
    file_path.unlink()
    return {"path": str(file_path), "deleted": True, "reason": ""}


def delete_history_item(task_id):
    history = raw_history_items()
    target_index = next((index for index, item in enumerate(history) if item.get("taskId") == task_id), None)
    if target_index is None:
        raise KeyError(task_id)

    item = history.pop(target_index)
    assets = load_assets()
    removed_assets = []
    file_results = []

    for asset_id in item_asset_ids(item):
        asset = assets.pop(asset_id, None)
        if not asset:
            file_results.append({"assetId": asset_id, "path": "", "deleted": False, "reason": "asset-metadata-missing"})
            continue
        result = delete_asset_file(asset)
        result["assetId"] = asset_id
        file_results.append(result)
        removed_assets.append(asset_id)

    write_json(HISTORY_PATH, history)
    save_assets(assets)
    return {
        "deleted": True,
        "taskId": task_id,
        "removedAssets": removed_assets,
        "fileResults": file_results,
    }


def register_asset(file_path, asset_type, mime_type=None, file_name=None):
    path = Path(file_path)
    asset_id = f"asset_{uuid.uuid4().hex[:12]}"
    item = {
        "assetId": asset_id,
        "type": asset_type,
        "fileName": file_name or path.name,
        "mimeType": mime_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "sizeBytes": path.stat().st_size,
        "path": str(path),
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    assets = load_assets()
    assets[asset_id] = item
    save_assets(assets)
    return item


def safe_filename(name):
    base = Path(name or "upload.bin").name
    stem = Path(base).stem or "upload"
    suffix = Path(base).suffix[:12]
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "upload"
    return f"{stem}{suffix}"


def decode_data_url(value):
    if not isinstance(value, str):
        raise ValueError("dataUrl must be a string")
    if "," in value and value.startswith("data:"):
        meta, encoded = value.split(",", 1)
        mime_type = meta[5:].split(";", 1)[0] or "application/octet-stream"
    else:
        encoded = value
        mime_type = "application/octet-stream"
    return base64.b64decode(encoded), mime_type


def create_upload(payload):
    file_name = safe_filename(payload.get("fileName"))
    raw, mime_type = decode_data_url(payload.get("dataUrl", ""))
    if len(raw) == 0:
        raise ValueError("uploaded file is empty")
    asset_id = f"asset_{uuid.uuid4().hex[:12]}"
    stored_name = f"{asset_id}_{file_name}"
    path = UPLOADS_DIR / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(raw)

    item = {
        "assetId": asset_id,
        "type": "input_image",
        "fileName": file_name,
        "mimeType": payload.get("mimeType") or mime_type,
        "sizeBytes": len(raw),
        "path": str(path),
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    assets = load_assets()
    assets[asset_id] = item
    save_assets(assets)
    return item


def get_asset(asset_id):
    asset = load_assets().get(asset_id)
    if not asset:
        raise KeyError(asset_id)
    path = Path(asset.get("path", ""))
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(asset_id)
    return asset, path


def asset_to_runpod_image(asset_id, fallback_name=None):
    asset, path = get_asset(asset_id)
    return {
        "name": safe_filename(asset.get("fileName") or fallback_name or path.name),
        "path": str(path),
    }


def encode_file_base64(path):
    with Path(path).open("rb") as stream:
        return base64.b64encode(stream.read()).decode("utf-8")


def build_runpod_images(payload):
    images = []
    for keyframe in payload.get("keyframes") or []:
        upload_id = keyframe.get("uploadId")
        if not upload_id:
            continue
        images.append(asset_to_runpod_image(upload_id, keyframe.get("fileName")))
    return images


def build_runpod_payload(workflow, images):
    input_body = {"workflow": workflow}
    if images:
        input_body["images"] = [
            {"name": image["name"], "image": encode_file_base64(image["path"])}
            for image in images
        ]
    return {"input": input_body}


def save_video_nodes(workflow):
    return [
        node_id for node_id, node in workflow.items()
        if node.get("class_type") == "SaveVideo"
    ]


def save_video_template_inputs(workflow):
    for node_id in save_video_nodes(workflow):
        inputs = workflow.get(node_id, {}).get("inputs") or {}
        if inputs:
            return json.loads(json.dumps(inputs))
    return {"format": "auto", "codec": "auto"}


def next_numeric_node_id(workflow):
    numeric_ids = [
        int(node_id) for node_id in workflow
        if str(node_id).isdigit()
    ]
    return str((max(numeric_ids) if numeric_ids else 1000) + 1)


def segment_create_video_nodes(workflow, workflow_id, segment_count):
    param_config = load_param_config(workflow_id)
    specs = (param_config or {}).get("segments") or []
    result = []
    for index in range(segment_count):
        params = (specs[index].get("params") if index < len(specs) else {}) or {}
        fps_targets = params.get("fps", {}).get("targets") or []
        create_node = ""
        for target in fps_targets:
            node_id = str(target.get("node"))
            if workflow.get(node_id, {}).get("class_type") == "CreateVideo":
                create_node = node_id
                break
        result.append(create_node)
    return result


def existing_save_video_outputs(workflow, workflow_id, segments):
    create_nodes = segment_create_video_nodes(workflow, workflow_id, len(segments))
    final_nodes = []
    segment_outputs = []

    for save_node in save_video_nodes(workflow):
        inputs = workflow.get(save_node, {}).get("inputs") or {}
        filename_prefix = str(inputs.get("filename_prefix") or "")
        linked_create_node = link_node(inputs, "video")
        segment_index = None

        segment_match = re.search(r"segment[_-]?(\d+)", filename_prefix, re.IGNORECASE)
        if segment_match:
            segment_index = int(segment_match.group(1))
        elif linked_create_node and linked_create_node in create_nodes:
            segment_index = create_nodes.index(linked_create_node) + 1

        is_segment_output = bool(segment_index and len(segments) > 1 and "final" not in filename_prefix.lower())
        if is_segment_output:
            segment_outputs.append({
                "segment": segment_index,
                "createVideoNode": linked_create_node,
                "saveNode": save_node,
                "filenamePrefix": filename_prefix,
            })
            continue

        final_nodes.append(save_node)

    if not final_nodes and save_video_nodes(workflow):
        final_nodes.append(save_video_nodes(workflow)[0])

    segment_outputs.sort(key=lambda item: item.get("segment") or 0)
    return {"finalOutputNodes": final_nodes, "segmentOutputs": segment_outputs}


def workflow_output_token(workflow_id):
    match = re.search(r"(\d+)\s*[-_]?key", workflow_id or "", re.IGNORECASE)
    if match:
        return f"{match.group(1)}key"
    stem = Path(workflow_id or "workflow").stem
    return re.sub(r"[^A-Za-z0-9]+", "", stem) or "workflow"


def first_upload_stem(job):
    payload = job.get("payload") or {}
    keyframes = payload.get("keyframes") or []
    first_name = keyframes[0].get("fileName") if keyframes else ""
    return Path(safe_filename(first_name or "upload")).stem or "upload"


def output_file_name(kind, item, index, job, metadata=None, total=1):
    original = safe_filename(item.get("filename") or f"{kind}_{index}")
    suffix = Path(original).suffix
    default_suffix = {"videos": ".mp4", "images": ".png", "gifs": ".gif"}.get(kind, "")
    if not suffix:
        suffix = default_suffix
    sequence = job.setdefault("outputSequence", uuid.uuid4().hex[:6])
    metadata = metadata or {}
    if metadata.get("outputRole") == "segment":
        role_suffix = f"_segment{metadata.get('segmentIndex') or index}"
    elif total > 1 and metadata.get("outputRole") == "final":
        role_suffix = "_final"
    else:
        role_suffix = f"_{index:02d}" if index > 1 else ""
    return f"{first_upload_stem(job)}_{workflow_output_token(job.get('workflowId'))}_{sequence}{role_suffix}{suffix}"


def infer_output_metadata(item, index, total, job):
    patch_summary = job.get("patchSummary") or {}
    segment_outputs = patch_summary.get("segmentOutputs") or []
    final_nodes = set(str(node_id) for node_id in (patch_summary.get("finalOutputNodes") or []))
    node_id = str(item.get("node_id") or item.get("nodeId") or item.get("node") or "")
    filename = str(item.get("filename") or item.get("fileName") or "")
    segment_count = len((job.get("payload") or {}).get("segments") or [])

    for output in segment_outputs:
        if node_id and node_id == str(output.get("saveNode")):
            return {"outputRole": "segment", "segmentIndex": output.get("segment")}
    if node_id and node_id in final_nodes:
        return {"outputRole": "final", "segmentIndex": None}

    match = re.search(r"segment[_-]?(\d+)", filename, re.IGNORECASE)
    if match:
        return {"outputRole": "segment", "segmentIndex": int(match.group(1))}

    if segment_count <= 1:
        return {"outputRole": "final", "segmentIndex": 1}
    if total == segment_count:
        return {"outputRole": "segment", "segmentIndex": index}
    if total == segment_count + 1:
        return (
            {"outputRole": "final", "segmentIndex": None}
            if index == 1
            else {"outputRole": "segment", "segmentIndex": index - 1}
        )
    return {"outputRole": "final" if index == 1 else "extra", "segmentIndex": None}


def save_runpod_outputs(result, job):
    output = result.get("output") or {}
    saved = []
    remote_urls = []
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_items = []
    for kind in ("videos", "images", "gifs"):
        for item in output.get(kind) or []:
            output_items.append((kind, item))
    total = len(output_items)
    for index, (kind, item) in enumerate(output_items, start=1):
        data = item.get("data")
        if item.get("type") == "s3_url" and data:
            remote_urls.append(data)
            continue
        if not data:
            continue
        metadata = infer_output_metadata(item, index, total, job)
        file_name = output_file_name(kind, item, index, job, metadata, total)
        raw = base64.b64decode(data)
        path = OUTPUTS_DIR / file_name
        with path.open("wb") as stream:
            stream.write(raw)
        asset = register_asset(path, f"output_{kind.rstrip('s')}")
        effective_kind = "videos" if asset["mimeType"].startswith("video/") or path.suffix.lower() in {".mp4", ".mov", ".webm"} else kind
        saved.append({
            "assetId": asset["assetId"],
            "fileName": asset["fileName"],
            "downloadUrl": f"/api/files/{asset['assetId']}",
            "kind": effective_kind,
            "mimeType": asset["mimeType"],
            "sizeBytes": asset["sizeBytes"],
            "outputRole": metadata.get("outputRole"),
            "segmentIndex": metadata.get("segmentIndex"),
        })
    return {"assets": saved, "remoteUrls": remote_urls}


def runpod_headers():
    if not runpod_is_configured():
        raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID are required when RUNPOD_DRY_RUN=0")
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def runpod_request(method, path, payload=None):
    url = f"{RUNPOD_BASE_URL.rstrip('/')}/{RUNPOD_ENDPOINT_ID}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method, headers=runpod_headers())
    try:
        with urllib.request.urlopen(request, timeout=RUNPOD_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"RunPod HTTP {exc.code}: {detail}") from exc


def runpod_connection_status():
    if not runpod_is_configured():
        return {
            "ok": False,
            "message": "RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID is not configured.",
        }
    health = runpod_request("GET", "/health")
    workers = health.get("workers") or {}
    jobs = health.get("jobs") or {}
    return {
        "ok": True,
        "endpointId": mask_secret(RUNPOD_ENDPOINT_ID),
        "baseUrl": RUNPOD_BASE_URL,
        "workers": workers,
        "jobs": jobs,
        "message": "RunPod endpoint health check succeeded.",
    }


def prepare_workflow_for_job(payload):
    workflow_id = payload.get("workflowId") or "unknown"
    workflow = load_workflow(workflow_id)
    segments = find_segments(workflow)
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

    patch_summary["nodeConfig"] = apply_node_config_to_workflow(workflow, workflow_id, segment_payloads)
    return workflow, images, patch_summary


def submit_runpod_job(payload):
    workflow, images, patch_summary = prepare_workflow_for_job(payload)
    response = runpod_request("POST", "/run", build_runpod_payload(workflow, images))
    runpod_job_id = response.get("id")
    if not runpod_job_id:
        raise RuntimeError(f"RunPod response did not include job id: {json.dumps(response, ensure_ascii=False)}")
    return {
        "runpodJobId": runpod_job_id,
        "patchSummary": patch_summary,
        "runpodSubmit": response,
    }


def poll_runpod_job(job):
    if str(job.get("status", "")).upper() == "CANCELLED":
        return job.get("runpodStatus") or {"status": "CANCELLED"}, max(0, time.time() - job["createdAt"]), 100
    runpod_status = runpod_request("GET", f"/status/{job['runpodJobId']}")
    state = runpod_status.get("status", "UNKNOWN")
    elapsed = max(0, time.time() - job["createdAt"])
    progress_by_state = {
        "IN_QUEUE": 8,
        "IN_PROGRESS": 45,
        "COMPLETED": 100,
        "FAILED": 100,
        "CANCELLED": 100,
        "TIMED_OUT": 100,
    }
    progress = progress_by_state.get(state, job.get("progress", 12))
    job["status"] = state
    job["progress"] = progress
    job["runpodStatus"] = runpod_status

    if state == "COMPLETED" and not job.get("outputsSaved"):
        saved = save_runpod_outputs(runpod_status, job)
        job["outputAssets"] = saved["assets"]
        job["remoteOutputUrls"] = saved["remoteUrls"]
        final_asset = next((asset for asset in saved["assets"] if asset.get("outputRole") == "final"), None)
        job["outputUrl"] = (
            final_asset["downloadUrl"]
            if final_asset
            else saved["assets"][0]["downloadUrl"]
            if saved["assets"]
            else (saved["remoteUrls"][0] if saved["remoteUrls"] else "")
        )
        job["outputsSaved"] = True
    return runpod_status, elapsed, progress


def cancel_job(task_id):
    job = JOBS.get(task_id)
    if not job:
        raise KeyError(task_id)
    status = str(job.get("status", "")).upper()
    if status in TERMINAL_RUNPOD_STATES:
        return job_status(task_id)
    cancel_response = {}
    if job.get("executionMode") == "runpod":
        cancel_response = runpod_request("POST", f"/cancel/{job['runpodJobId']}")
    else:
        cancel_response = {"status": "CANCELLED", "message": "Dry-run job cancelled locally."}
    job["status"] = "CANCELLED"
    job["progress"] = 100
    job["cancelRequested"] = True
    job["cancelledAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job["runpodCancel"] = cancel_response
    job["runpodStatus"] = {"status": "CANCELLED", "cancel": cancel_response}
    job["historySaved"] = True
    return job_status(task_id)


def create_job(payload):
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now = time.time()
    workflow_id = payload.get("workflowId") or "unknown"
    segments = payload.get("segments") or []
    first_config = (segments[0].get("config") if segments else {}) or {}
    runpod_data = {
        "runpodJobId": f"dryrun_{uuid.uuid4().hex[:10]}",
        "patchSummary": {},
        "runpodSubmit": {},
    }
    execution_mode = "dry-run"
    if not DRY_RUN:
        runpod_data = submit_runpod_job(payload)
        execution_mode = "runpod"
    JOBS[task_id] = {
        "taskId": task_id,
        "runpodJobId": runpod_data["runpodJobId"],
        "executionMode": execution_mode,
        "workflowId": workflow_id,
        "status": "queued",
        "progress": 0,
        "createdAt": now,
        "startedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payload": payload,
        "firstConfig": first_config,
        "patchSummary": runpod_data.get("patchSummary") or {},
        "runpodSubmit": runpod_data.get("runpodSubmit") or {},
        "inputAssets": [
            keyframe.get("uploadId")
            for keyframe in (payload.get("keyframes") or [])
            if keyframe.get("uploadId")
        ],
    }
    return JOBS[task_id]


def job_status(task_id):
    job = JOBS.get(task_id)
    if not job:
        raise KeyError(task_id)
    elapsed = max(0, time.time() - job["createdAt"])
    if job.get("executionMode") == "runpod":
        runpod_status, elapsed, progress = poll_runpod_job(job)
        terminal = runpod_status.get("status") in TERMINAL_RUNPOD_STATES
    else:
        progress = min(100, int(elapsed * 18))
        if progress >= 100:
            job["status"] = "success"
        elif progress > 10:
            job["status"] = "running"
        job["progress"] = progress
        terminal = progress >= 100

    if terminal and str(job.get("status", "")).upper() == "CANCELLED":
        job["historySaved"] = True
    elif terminal and not job.get("historySaved"):
        save_job_history(job)
        job["historySaved"] = True

    return {
        "taskId": task_id,
        "runpodJobId": job["runpodJobId"],
        "status": api_job_status(job),
        "rawStatus": job["status"],
        "elapsedSeconds": round(elapsed, 1),
        "progress": progress,
        "workerSummary": "RunPod serverless" if job.get("executionMode") == "runpod" else "dry-run worker",
        "statusLabel": localized_job_status(job),
        "message": job_status_message(job),
        "outputUrl": job.get("outputUrl", ""),
        "outputAssets": job.get("outputAssets", []),
        "cancelRequested": bool(job.get("cancelRequested")),
    }


def api_job_status(job):
    status = str(job.get("status", "")).upper()
    if status in {"COMPLETED", "SUCCESS"}:
        return "success"
    if status in {"FAILED"}:
        return "fail"
    if status in {"CANCELLED"}:
        return "cancelled"
    if status in {"TIMED_OUT"}:
        return "timed_out"
    if status in {"IN_QUEUE", "QUEUED"}:
        return "queued"
    return "running"


def display_job_status(job):
    status = str(job.get("status", "")).upper()
    if status in {"COMPLETED", "SUCCESS"}:
        return "Completed"
    if status in {"FAILED", "CANCELLED", "TIMED_OUT"}:
        return "Failed"
    return job.get("status", "running")


def localized_job_status(job):
    status = str(job.get("status", "")).upper()
    labels = {
        "QUEUED": "대기",
        "IN_QUEUE": "대기",
        "IN_PROGRESS": "실행 중",
        "RUNNING": "실행 중",
        "COMPLETED": "완료",
        "SUCCESS": "완료",
        "FAILED": "실패",
        "CANCELLED": "취소됨",
        "TIMED_OUT": "시간 초과",
    }
    return labels.get(status, "확인 중")


def save_job_history(job):
    payload = job["payload"]
    user = payload.get("user") or {}
    segments = payload.get("segments") or []
    first_segment = segments[0] if segments else {}
    config = first_segment.get("config") or job.get("firstConfig") or {}
    wan_node_config = build_wan_node_config_snapshot(job["workflowId"], segments)
    append_history({
        "taskId": job["taskId"],
        "timestamp": job["startedAt"],
        "workflowId": job["workflowId"],
        "workflowName": job["workflowId"],
        "runpodJobId": job.get("runpodJobId", ""),
        "executionMode": job.get("executionMode", "dry-run"),
        "user": user,
        "workerName": user.get("name") or user.get("id") or "-",
        "status": display_job_status(job),
        "prompt": first_segment.get("positivePrompt", ""),
        "positivePrompt": " | ".join(
            f"{segment.get('index')}: {segment.get('positivePrompt', '')}"
            for segment in segments
        ),
        "negativePrompt": " | ".join(
            f"{segment.get('index')}: {segment.get('negativePromptAddition', '')}"
            for segment in segments
        ),
        "positivePrompts": [
            {"index": segment.get("index") or index + 1, "text": segment.get("positivePrompt", "")}
            for index, segment in enumerate(segments)
        ],
        "negativePrompts": [
            {"index": segment.get("index") or index + 1, "text": segment.get("negativePromptAddition", "")}
            for index, segment in enumerate(segments)
        ],
        "segmentCount": len(segments) or 1,
        "configJson": config,
        "wanNodeConfig": wan_node_config,
        "fps": config.get("fps", 16),
        "seed": config.get("seed", 4920381920),
        "outputUrl": job.get("outputUrl", ""),
        "outputAssets": job.get("outputAssets", []),
        "remoteOutputUrls": job.get("remoteOutputUrls", []),
        "inputAssets": job.get("inputAssets", []),
        "inputImages": hydrate_input_images({
            "keyframes": payload.get("keyframes") or [],
            "inputAssets": job.get("inputAssets", []),
        }),
        "segments": segments,
        "keyframes": payload.get("keyframes") or [],
        "patchSummary": job.get("patchSummary", {}),
    })


def job_status_message(job):
    if job.get("executionMode") == "runpod":
        status = job.get("status", "UNKNOWN")
        if status == "COMPLETED" and job.get("outputUrl"):
            return "RunPod job completed. Output is ready."
        if status in TERMINAL_RUNPOD_STATES:
            return f"RunPod 상태: {localized_job_status(job)} ({status})"
        return f"RunPod 상태: {localized_job_status(job)} ({status})"
    return "Dry-run job running. Set RUNPOD_DRY_RUN=0 after wiring RunPod execution."


def create_config_snapshot(payload):
    source = payload.get("source") or "studio"
    snapshot = payload.get("snapshot") or {}
    workflow_id = snapshot.get("workflowId") or payload.get("workflowId") or "unknown"
    config_id = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    item = {
        "configId": config_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "workflowId": workflow_id,
        "user": payload.get("user") or snapshot.get("user") or {},
        "name": payload.get("name") or f"{Path(workflow_id).stem} saved config",
        "snapshot": snapshot,
    }
    append_config(item)
    return item


def report_markdown(payload):
    item = payload.get("historyItem") or payload.get("snapshot") or {}
    segments = item.get("segments") if isinstance(item.get("segments"), list) else []
    config = item.get("configJson") or item.get("config") or {}
    wan_node_config = item.get("wanNodeConfig") or {}
    if segments:
        config = segments[0].get("config") or config

    lines = [
        "# DOBEDUB STUDIO 작업 리포트",
        "",
        f"- 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Task ID: {item.get('taskId', '-')}",
        f"- Workflow: {item.get('workflowId') or item.get('workflow') or item.get('workflowName') or '-'}",
        f"- Status: {item.get('status', '-')}",
        f"- FPS: {config.get('fps') or item.get('fps') or '-'}",
        f"- Seed: {config.get('seed') or item.get('seed') or '-'}",
        f"- Segments: {item.get('segmentCount') or len(segments) or item.get('segments') or '-'}",
        "",
        "## Prompt",
        "",
        item.get("positivePrompt") or item.get("prompt") or "-",
        "",
        "## Negative Prompt",
        "",
        item.get("negativePrompt") or "-",
        "",
        "## Node Config",
        "",
        "```json",
        json.dumps(wan_node_config or config, ensure_ascii=False, indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def create_report(payload):
    report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    markdown = report_markdown(payload)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{report_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return {
        "reportId": report_id,
        "downloadUrl": f"/api/reports/{report_id}",
        "markdown": markdown,
    }


def mask_secret(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}...{value[-4:]}"


def directory_status(path):
    path = Path(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "isDirectory": path.is_dir(),
        "writable": path.exists() and os.access(path, os.W_OK),
    }


def workflow_inventory():
    files = workflow_files()
    return {
        "dir": str(WORKFLOWS_DIR),
        "exists": WORKFLOWS_DIR.exists(),
        "count": len(files),
        "items": [path.name for path in files],
    }


def system_status():
    workflows = workflow_inventory()
    data_dir = directory_status(DATA_DIR)
    outputs_dir = directory_status(OUTPUTS_DIR)
    ready = (
        workflows["exists"]
        and workflows["count"] > 0
        and data_dir["writable"]
        and outputs_dir["writable"]
        and (DRY_RUN or runpod_is_configured())
    )
    return {
        "ok": ready,
        "checkedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executionMode": "dry-run" if DRY_RUN else "runpod",
        "dryRun": DRY_RUN,
        "runpod": {
            "configured": runpod_is_configured(),
            "endpointId": mask_secret(RUNPOD_ENDPOINT_ID),
            "baseUrl": RUNPOD_BASE_URL,
        },
        "workflows": workflows,
        "storage": {
            "dataDir": data_dir,
            "outputsDir": outputs_dir,
        },
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[studio] {self.address_string()} - {fmt % args}")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, value, status=HTTPStatus.OK):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, value, status=HTTPStatus.OK):
        body = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_asset_file(self, asset, asset_path, query):
        content_type = asset.get("mimeType") or mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
        file_size = asset_path.stat().st_size
        file_name = str(asset.get("fileName") or asset_path.name).replace('"', "")
        disposition = "attachment" if query.get("download", ["0"])[0] == "1" else "inline"
        range_header = self.headers.get("Range", "")

        if range_header.startswith("bytes="):
            start_text, _, end_text = range_header.removeprefix("bytes=").partition("-")
            try:
                start = int(start_text) if start_text else 0
                end = int(end_text) if end_text else file_size - 1
                start = max(0, min(start, file_size - 1))
                end = max(start, min(end, file_size - 1))
            except ValueError:
                start, end = 0, file_size - 1
            length = end - start + 1
            with asset_path.open("rb") as stream:
                stream.seek(start)
                data = stream.read(length)
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Disposition", f'{disposition}; filename="{file_name}"')
            self.end_headers()
            self.wfile.write(data)
            return

        data = asset_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f'{disposition}; filename="{file_name}"')
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/", "/index.html"}:
                return self.send_html(index_html_page())
            if path == "/api/health":
                status = system_status()
                return self.send_json({
                    "ok": status["ok"],
                    "dryRun": DRY_RUN,
                    "runpodConfigured": runpod_is_configured(),
                    "workflowsDir": str(WORKFLOWS_DIR),
                        "outputsDir": str(OUTPUTS_DIR),
                })
            if path == "/manual":
                return self.send_html(manual_html_page())
            if path == "/api/system/status":
                return self.send_json(system_status())
            if path == "/api/runpod/connection":
                return self.send_json(runpod_connection_status())
            if path.startswith("/api/files/"):
                asset_id = unquote(path.removeprefix("/api/files/").strip("/"))
                asset, asset_path = get_asset(asset_id)
                self.send_asset_file(asset, asset_path, parse_qs(parsed.query))
                return
            if path == "/api/workflows":
                return self.send_json(list_workflows())
            if path.startswith("/api/workflows/") and path.endswith("/schema"):
                workflow_id = unquote(path.removeprefix("/api/workflows/").removesuffix("/schema").strip("/"))
                return self.send_json(workflow_schema(workflow_id))
            if path.startswith("/api/workflows/") and path.endswith("/widget-metadata"):
                workflow_id = unquote(path.removeprefix("/api/workflows/").removesuffix("/widget-metadata").strip("/"))
                return self.send_json(workflow_widget_metadata(workflow_id))
            if path == "/api/metadata/status":
                return self.send_json(metadata_status())
            if path == "/api/metadata/models":
                return self.send_json(model_metadata())
            if path == "/api/segment-defaults":
                return self.send_json(load_segment_defaults())
            if path.startswith("/api/segment-defaults/"):
                workflow_id = unquote(path.removeprefix("/api/segment-defaults/").strip("/"))
                return self.send_json(workflow_segment_defaults(workflow_id))
            if path == "/api/prompts":
                return self.send_json(prompt_options())
            if path.startswith("/api/jobs/"):
                task_id = unquote(path.removeprefix("/api/jobs/").strip("/"))
                return self.send_json(job_status(task_id))
            if path == "/api/history":
                query = parse_qs(parsed.query)
                page = int(query.get("page", ["1"])[0])
                page_size = int(query.get("pageSize", ["50"])[0])
                history = load_history()
                start = max(0, page - 1) * page_size
                return self.send_json({
                    "items": history[start:start + page_size],
                    "page": page,
                    "pageSize": page_size,
                    "total": len(history),
                })
            if path == "/api/configs":
                return self.send_json({"items": load_configs()})
            if path.startswith("/api/reports/"):
                report_id = unquote(path.removeprefix("/api/reports/").strip("/"))
                report_path = REPORTS_DIR / f"{Path(report_id).name}.md"
                if not report_path.exists():
                    raise FileNotFoundError(report_id)
                body = report_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f'attachment; filename="{report_path.name}"')
                self.end_headers()
                self.wfile.write(body)
                return
        except FileNotFoundError as exc:
            return self.send_json({"error": f"File not found: {exc}"}, HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            return self.send_json({"error": f"Job not found: {exc}"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/auth/login":
                payload = self.read_body()
                if not payload.get("id") or not payload.get("password") or not payload.get("name"):
                    return self.send_json({"error": "id, password, name are required"}, HTTPStatus.BAD_REQUEST)
                return self.send_json({"user": {"id": payload["id"], "name": payload["name"]}})
            if parsed.path == "/api/uploads":
                payload = self.read_body()
                if not payload.get("fileName") or not payload.get("dataUrl"):
                    return self.send_json({"error": "fileName and dataUrl are required"}, HTTPStatus.BAD_REQUEST)
                asset = create_upload(payload)
                return self.send_json({
                    "assetId": asset["assetId"],
                    "fileName": asset["fileName"],
                    "mimeType": asset["mimeType"],
                    "sizeBytes": asset["sizeBytes"],
                    "downloadUrl": f"/api/files/{asset['assetId']}",
                }, HTTPStatus.CREATED)
            if parsed.path == "/api/jobs":
                payload = self.read_body()
                if not payload.get("workflowId"):
                    return self.send_json({"error": "workflowId is required"}, HTTPStatus.BAD_REQUEST)
                job = create_job(payload)
                return self.send_json({
                    "taskId": job["taskId"],
                    "runpodJobId": job["runpodJobId"],
                    "status": "queued",
                }, HTTPStatus.CREATED)
            if parsed.path == "/api/metadata/rebuild":
                return self.send_json({"ok": True, "manifest": ensure_metadata_current(force=True)})
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/cancel"):
                task_id = unquote(parsed.path.removeprefix("/api/jobs/").removesuffix("/cancel").strip("/"))
                return self.send_json(cancel_job(task_id))
            if parsed.path.startswith("/api/history/") and parsed.path.endswith("/delete"):
                task_id = unquote(parsed.path.removeprefix("/api/history/").removesuffix("/delete").strip("/"))
                return self.send_json(delete_history_item(task_id))
            if parsed.path == "/api/configs":
                payload = self.read_body()
                item = create_config_snapshot(payload)
                return self.send_json(item, HTTPStatus.CREATED)
            if parsed.path == "/api/reports":
                payload = self.read_body()
                report = create_report(payload)
                return self.send_json(report, HTTPStatus.CREATED)
        except KeyError as exc:
            return self.send_json({"error": f"Job not found: {exc}"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    ensure_metadata_current()
    port = int(os.environ.get("PORT", "8787"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"DOBEDUB STUDIO running at http://{host}:{port}")
    print(f"Workflow directory: {WORKFLOWS_DIR}")
    print(f"Dry run mode: {DRY_RUN}")
    server.serve_forever()


if __name__ == "__main__":
    main()
