from __future__ import annotations

from pathlib import Path

from backend.app.services import json_repository


class JsonStudioRepository:
    """Current production-compatible adapter backed by JSON files and local/EFS files."""

    def __init__(self, *, history_path: Path, assets_path: Path, configs_path: Path, uploads_dir: Path, outputs_dir: Path):
        self.history_path = history_path
        self.assets_path = assets_path
        self.configs_path = configs_path
        self.uploads_dir = uploads_dir
        self.outputs_dir = outputs_dir

    def load_history(self) -> list[dict]:
        return json_repository.load_history(self.history_path, self.assets_path)

    def append_history(self, item: dict) -> list[dict]:
        return json_repository.append_history(self.history_path, self.assets_path, item)

    def delete_history_item(self, task_id: str) -> dict:
        return json_repository.delete_history_item(
            self.history_path,
            self.assets_path,
            self.uploads_dir,
            self.outputs_dir,
            task_id,
        )

    def load_configs(self) -> list[dict]:
        return json_repository.load_configs(self.configs_path)

    def append_config(self, item: dict) -> list[dict]:
        return json_repository.append_config(self.configs_path, item)

    def create_upload(self, payload: dict) -> dict:
        return json_repository.create_upload(self.assets_path, self.uploads_dir, payload)

    def get_asset(self, asset_id: str):
        return json_repository.get_asset(self.assets_path, asset_id)

    def register_asset(self, file_path, asset_type: str, mime_type: str | None = None, file_name: str | None = None) -> dict:
        return json_repository.register_asset(self.assets_path, Path(file_path), asset_type, mime_type, file_name)

    def hydrate_input_images(self, item: dict) -> list[dict]:
        return json_repository.hydrate_input_images(item, assets_path=self.assets_path)
