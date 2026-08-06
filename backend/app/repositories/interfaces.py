from __future__ import annotations

from typing import Protocol


class StudioRepository(Protocol):
    """Persistence contract for JSON and future DB-backed implementations."""

    def load_history(self) -> list[dict]:
        ...

    def append_history(self, item: dict) -> list[dict]:
        ...

    def delete_history_item(self, task_id: str) -> dict:
        ...

    def load_configs(self) -> list[dict]:
        ...

    def append_config(self, item: dict) -> list[dict]:
        ...

    def create_upload(self, payload: dict) -> dict:
        ...

    def get_asset(self, asset_id: str):
        ...

    def register_asset(self, file_path, asset_type: str, mime_type: str | None = None, file_name: str | None = None) -> dict:
        ...

    def hydrate_input_images(self, item: dict) -> list[dict]:
        ...
