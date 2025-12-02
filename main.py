#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List
from logging.handlers import RotatingFileHandler

# --- Make sure Python can see the "src" directory as a package root ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from immich_pixstar_sync.config import Settings, PixStarAccount, load_settings
from immich_pixstar_sync.immich_client import ImmichClient
from immich_pixstar_sync.pixstar_mailer import PixStarMailer
from immich_pixstar_sync.state_store import StateStore

logger = logging.getLogger(__name__)


# ----- logging setup ---------------------------------------------------------

def setup_logging() -> None:
    """
    Configure rotating file logging so logs never grow without bound.
    Keeps at most ~10MB of logs (2x 5MB files).
    """
    log_path = Path(__file__).with_name("immich-pixstar.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if main() is ever called more than once
    if root_logger.handlers:
        root_logger.handlers.clear()

    # File handler with rotation: 5MB per file, 1 backup => ~10MB total
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=1,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Also log to console (useful when running manually)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


# ----- helpers ---------------------------------------------------------------

def resolve_user_ids(
    admin_client: ImmichClient,
    accounts: List[PixStarAccount],
) -> Dict[str, str]:
    """
    Use an admin-style Immich client (settings.immich_api_key) to resolve
    email -> userId mappings for logging and sanity-checks.

    NOTE: This does *not* affect which favorites are synced; that is entirely
    based on each account's own immich_api_key.
    """
    email_to_user_id: Dict[str, str] = {}

    for account in accounts:
        email = account.immich_email
        user = admin_client.get_user_by_email(email)
        if user is None:
            logger.warning("No Immich user found for %s, skipping.", email)
            continue

        user_id = user.get("id") or user.get("userId")
        if not user_id:
            logger.warning(
                "Immich user for %s has no 'id' field, skipping.", email
            )
            continue

        email_to_user_id[email] = str(user_id)
        logger.info("Resolved %s -> %s", email, user_id)

    return email_to_user_id


def sync_account_once(
    account: PixStarAccount,
    client: ImmichClient,
    mailer: PixStarMailer,
    state_store: StateStore,
    force_resend: bool = False,
) -> None:
    """
    Sync favorites for one Immich account exactly once.

    If force_resend=True, we ignore StateStore and send *all* current favorites.
    Otherwise, we only send newly-favorited assets.
    """
    email = account.immich_email

    try:
        favorites = client.get_favorites()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch favorites for %s: %s", email, exc)
        return

    if force_resend:
        assets_to_send = favorites
    else:
        seen_ids = state_store.get_seen(email)
        assets_to_send = [a for a in favorites if a.get("id") not in seen_ids]

    if not assets_to_send:
        if force_resend:
            logger.info("%s: no favorites to resend.", email)
        return

    logger.info(
        "%s: %d favorite(s) to send to %s%s",
        email,
        len(assets_to_send),
        account.pixstar_emails,
        " (forced resend)" if force_resend else "",
    )

    for asset in assets_to_send:
        asset_id = asset.get("id")
        if not asset_id:
            continue

        filename = (
            asset.get("originalFileName")
            or asset.get("deviceAssetId")
            or f"{asset_id}.jpg"
        )

        # Download from Immich with THIS user's API key
        try:
            content = client.download_asset(asset_id)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to download asset %s for %s: %s",
                asset_id,
                email,
                exc,
            )
            continue

        # Email to that user's Pix-Star frame(s)
        try:
            mailer.send_photo(
                to_addrs=account.pixstar_emails,
                subject=f"New Immich favorite from {email}",
                body="This photo was marked as a favorite in Immich.",
                filename=filename,
                content=content,
            )
            logger.info(
                "Sent asset %s (%s) for %s to %s",
                asset_id,
                filename,
                email,
                ", ".join(account.pixstar_emails),
            )
            # Even in forced resend mode, marking as seen is fine:
            # it keeps normal mode from re-spamming later.
            state_store.add_seen(email, asset_id)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to email asset %s for %s -> %s: %s",
                asset_id,
                email,
                ", ".join(account.pixstar_emails),
                exc,
            )


# ----- main -------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Immich favorites to Pix-Star frames."
    )
    parser.add_argument(
        "--resend-all",
        action="store_true",
        help="One-shot mode: resend *all* current favorites for selected user(s).",
    )
    parser.add_argument(
        "--user",
        help="Immich email to target for --resend-all. If omitted with --resend-all, all accounts are used.",
    )
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="With --resend-all, target all configured accounts.",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    logger.info("Starting immich-pixstar-sync...")

    args = parse_args()

    settings: Settings = load_settings()

    # Admin client for resolving user IDs (logs only)
    admin_client = ImmichClient(
        base_url=settings.immich_base_url,
        api_key=settings.immich_api_key,
    )
    email_to_user_id = resolve_user_ids(admin_client, settings.pixstar_accounts)

    # Per-account Immich clients, each with its own API key from pixstar_mapping.json.
    clients: Dict[str, ImmichClient] = {
        account.immich_email: ImmichClient(
            base_url=settings.immich_base_url,
            api_key=account.immich_api_key or settings.immich_api_key,
        )
        for account in settings.pixstar_accounts
    }

    mailer = PixStarMailer(settings)
    state_store = StateStore(settings.state_path)

    # ----- One-shot resend mode -----
    if args.resend_all:
        # Determine which accounts to target
        if args.user:
            target_accounts = [
                a for a in settings.pixstar_accounts if a.immich_email == args.user
            ]
            if not target_accounts:
                logger.error("No account configured for user %s", args.user)
                return
        elif args.all_users:
            target_accounts = settings.pixstar_accounts
        else:
            logger.error(
                "With --resend-all you must specify either --user <email> or --all-users."
            )
            return

        logger.info("Running in one-shot resend mode.")
        for account in target_accounts:
            email = account.immich_email
            user_id = email_to_user_id.get(email)
            if user_id:
                logger.info("Resend for %s (userId=%s)", email, user_id)
            else:
                logger.info("Resend for %s (userId unresolved)", email)

            client = clients[email]
            sync_account_once(
                account=account,
                client=client,
                mailer=mailer,
                state_store=state_store,
                force_resend=True,
            )
        logger.info("Resend-all operation complete.")
        return

    # ----- Normal loop mode -----
    poll = settings.poll_interval_seconds
    logger.info(
        "Starting Immich → Pix-Star sync loop (interval %ss). Press Ctrl+C to stop.",
        poll,
    )

    try:
        while True:
            for account in settings.pixstar_accounts:
                email = account.immich_email
                user_id = email_to_user_id.get(email)
                if user_id:
                    logger.debug("Processing %s (userId=%s)", email, user_id)
                else:
                    logger.debug("Processing %s (userId unresolved)", email)

                client = clients[email]
                sync_account_once(
                    account=account,
                    client=client,
                    mailer=mailer,
                    state_store=state_store,
                    force_resend=False,
                )

            time.sleep(poll)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")


if __name__ == "__main__":
    main()
