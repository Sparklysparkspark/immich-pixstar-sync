# src/immich_pixstar_sync/immich_client.py

from __future__ import annotations

from typing import Dict, List, Optional, Any

import requests


class ImmichClient:
    """
    Minimal Immich API wrapper for:
    - listing users
    - getting favorites for a user
    - downloading an asset
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        # Expect base_url WITHOUT trailing slash, e.g. "https://photos.example.com/api"
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

    # ---------- users ----------

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Returns a user dict (from /api/users) matching the given email,
        or None if not found.
        """
        url = f"{self.base_url}/users"  # NOTE: plural 'users' for new Immich API
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        try:
            users = resp.json()
        except Exception as exc:  # noqa: BLE001
            snippet = resp.text[:200].replace("\n", " ").strip()
            raise RuntimeError(
                f"Immich /users returned non-JSON "
                f"(status={resp.status_code}, content-type={resp.headers.get('content-type')}, "
                f"body_prefix={snippet!r})"
            ) from exc

        for u in users:
            if u.get("email") == email:
                return u
        return None



    # ---------- favorites ----------

    def get_favorites(self) -> List[Dict[str, Any]]:
        """
        Returns a list of favorite assets for *this API key's user*.

        Uses /api/search/metadata with isFavorite=true.
        We do NOT send userId; Immich infers the user from the token.
        """
        url = f"{self.base_url}/search/metadata"
        payload: Dict[str, Any] = {
            "isFavorite": True,
            "order": "desc",
            "orderBy": "fileCreatedAt",
            "size": 250,
        }

        resp = self.session.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # Shape: {"albums": {...}, "assets": {"items": [...], ...}}
        if isinstance(data, dict) and "assets" in data:
            assets = data["assets"]
            if isinstance(assets, dict) and "items" in assets:
                return assets["items"]

        raise RuntimeError(f"Unexpected response from /search/metadata: {type(data)}")

    # ---------- download ----------

    def download_asset(self, asset_id: str) -> bytes:
        """
        Downloads the original file of an asset and returns the raw bytes.
        """
        url = f"{self.base_url}/assets/{asset_id}/original"
        resp = self.session.get(url, timeout=120)
        resp.raise_for_status()
        return resp.content



