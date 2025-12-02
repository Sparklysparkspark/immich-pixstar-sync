# src/immich_pixstar_sync/config.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import json
import os

from dotenv import load_dotenv
load_dotenv()

@dataclass
class PixStarAccount:
    """One Immich user mapped to one-or-more Pix-Star frame addresses."""
    immich_email: str
    immich_api_key: str | None
    pixstar_emails: List[str]


@dataclass
class Settings:
    immich_base_url: str        # e.g. https://photos.example.com/api
    immich_api_key: str

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool          # STARTTLS if True and port != 465

    poll_interval_seconds: int  # how often to check favorites
    state_path: Path            # JSON file to track already-sent favorites

    pixstar_accounts: List[PixStarAccount]


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Create a .env (or set it in your environment)."
        )
    return value


def load_pixstar_mapping(path: Path) -> List[PixStarAccount]:
    if not path.exists():
        raise RuntimeError(
            f"Pix-Star mapping file not found at {path}. "
            "Copy pixstar_mapping.example.json to pixstar_mapping.json "
            "and edit it to match your users."
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Only support camelCase:
    # - defaultPixstarEmails
    # - accounts[].immichUser
    # - accounts[].immichApiKey
    # - accounts[].pixstarEmails
    default_pixstar_emails = data.get("defaultPixstarEmails", [])
    if not isinstance(default_pixstar_emails, list):
        raise RuntimeError(
            f"defaultPixstarEmails must be a list in {path}, "
            f"got {type(default_pixstar_emails).__name__}"
        )

    accounts: List[PixStarAccount] = []

    for idx, entry in enumerate(data.get("accounts", []), start=1):
        immich_email = entry.get("immichUser")
        if not immich_email:
            raise RuntimeError(
                f"Account #{idx} in {path} is missing 'immichUser'."
            )

        immich_api_key = entry.get("immichApiKey")
        if not immich_api_key:
            raise RuntimeError(
                f"Account #{idx} for {immich_email} in {path} is missing 'immichApiKey'."
            )

        pixstar_emails = entry.get("pixstarEmails") or default_pixstar_emails
        if not pixstar_emails:
            raise RuntimeError(
                f"Account #{idx} for {immich_email} in {path} has no "
                f"'pixstarEmails' and no 'defaultPixstarEmails'."
            )
        if not isinstance(pixstar_emails, list):
            raise RuntimeError(
                f"'pixstarEmails' for account #{idx} in {path} must be a list."
            )

        accounts.append(
            PixStarAccount(
                immich_email=str(immich_email),
                immich_api_key=str(immich_api_key),
                pixstar_emails=[str(e) for e in pixstar_emails],
            )
        )

    if not accounts:
        raise RuntimeError(
            f"No accounts found in {path}. "
            "Make sure it has an 'accounts' array with immichUser, immichApiKey, and pixstarEmails."
        )

    return accounts



def load_settings() -> Settings:
    # Immich
    immich_base_url = _env("IMMICH_BASE_URL").rstrip("/") 
    immich_api_key = _env("IMMICH_API_KEY")

    # SMTP (Pix-Star)
    smtp_host = _env("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = _env("SMTP_USER")
    smtp_password = _env("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # Polling + state
    poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
    state_path = Path(os.getenv("STATE_PATH", "pixstar_sync_state.json"))

    mapping_path = Path(
        os.getenv("PIXSTAR_MAPPING_PATH", "pixstar_mapping.json")
    )
    pixstar_accounts = load_pixstar_mapping(mapping_path)

    return Settings(
        immich_base_url=immich_base_url,
        immich_api_key=immich_api_key,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        smtp_use_tls=smtp_use_tls,
        poll_interval_seconds=poll_interval_seconds,
        state_path=state_path,
        pixstar_accounts=pixstar_accounts,
    )
