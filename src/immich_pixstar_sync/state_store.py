# src/immich_pixstar_sync/state_store.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, List

import json
import threading


class StateStore:
    """
    Keeps track of which favorites we've already mailed to Pix-Star,
    so we only send each asset once per Immich user.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: Dict[str, List[str]] = {}  # immich_email -> [asset_ids]
        self._load()

    # ---------- public API ----------

    def get_seen(self, immich_email: str) -> Set[str]:
        with self._lock:
            return set(self._data.get(immich_email, []))

    def add_seen(self, immich_email: str, asset_id: str) -> None:
        with self._lock:
            ids = self._data.setdefault(immich_email, [])
            if asset_id not in ids:
                ids.append(asset_id)
            self._save()

    # ---------- internals ----------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._data = {
                    email: list(map(str, ids))
                    for email, ids in raw.get("by_user", {}).items()
                }
        except Exception as exc:  # noqa: BLE001
            print(f"[state_store] Failed to load state file {self._path}: {exc}")
            self._data = {}

    def _save(self) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = {"by_user": self._data}
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            tmp_path.replace(self._path)
        except Exception as exc:  # noqa: BLE001
            print(f"[state_store] Failed to save state file {self._path}: {exc}")
