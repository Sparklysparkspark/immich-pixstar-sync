# src/immich_pixstar_sync/pixstar_mailer.py

from __future__ import annotations

from email.message import EmailMessage
from typing import Iterable
from io import BytesIO

from PIL import Image  # make sure Pillow is in requirements.txt
import mimetypes
import smtplib
import logging

from .config import Settings

logger = logging.getLogger(__name__)

PIXSTAR_MAX_WIDTH = 1024
PIXSTAR_MAX_HEIGHT = 768
PIXSTAR_JPEG_QUALITY = 85

# Conservative cap to stay well under Gmail's message size limit
MAX_VIDEO_BYTES = 15 * 1024 * 1024  # 15 MB


class PixStarMailer:
    """
    Sends photos (and small videos) as email attachments to Pix-Star frames via SMTP.
    """

    @staticmethod
    def downscale_for_pixstar(image_bytes: bytes) -> tuple[bytes, str]:
        """
        Takes raw image bytes, downscales to something Pix-Star-friendly,
        and returns (jpeg_bytes, mime_type).
        """
        with Image.open(BytesIO(image_bytes)) as im:
            im = im.convert("RGB")
            width, height = im.size

            # Resize *only* if necessary, keeping aspect ratio
            if width > PIXSTAR_MAX_WIDTH or height > PIXSTAR_MAX_HEIGHT:
                im.thumbnail(
                    (PIXSTAR_MAX_WIDTH, PIXSTAR_MAX_HEIGHT),
                    Image.Resampling.LANCZOS,
                )

            out = BytesIO()
            im.save(out, format="JPEG", quality=PIXSTAR_JPEG_QUALITY, optimize=True)
            return out.getvalue(), "image/jpeg"

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._use_tls = settings.smtp_use_tls

    def send_photo(
        self,
        to_addrs: Iterable[str],
        subject: str,
        body: str,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
    ) -> None:
        """
        Send `content` as a single attachment to the given Pix-Star addresses.

        - Images: downscaled to JPEG for Pix-Star.
        - Videos: sent as-is, but skipped if larger than MAX_VIDEO_BYTES.
        """
        to_list = list(to_addrs)
        if not to_list:
            return

        # If caller didn't pass a mime_type, try to guess from filename
        if not mime_type:
            guessed, _ = mimetypes.guess_type(filename)
            mime_type = guessed or "image/jpeg"

        mime_type = mime_type.lower()
        maintype, subtype = mime_type.split("/", 1)

        # Decide behavior based on type
        if maintype == "image":
            # Always downscale images to Pix-Star-friendly JPEG
            scaled_bytes, scaled_mime = self.downscale_for_pixstar(content)
            maintype, subtype = scaled_mime.split("/", 1)

            # Ensure filename has a JPEG extension
            lower_name = filename.lower()
            if not (lower_name.endswith(".jpg") or lower_name.endswith(".jpeg")):
                filename = f"{filename}.jpg"

            final_bytes = scaled_bytes

        elif maintype == "video":
            # Enforce a size cap for videos to avoid Gmail 552 errors
            if len(content) > MAX_VIDEO_BYTES:
                logger.warning(
                    "Skipping video attachment '%s' for subject '%s': "
                    "size %d bytes exceeds MAX_VIDEO_BYTES=%d",
                    filename,
                    subject,
                    len(content),
                    MAX_VIDEO_BYTES,
                )
                return

            # Send video as-is
            final_bytes = content

        else:
            # Unsupported type for now – log and skip
            logger.info(
                "Skipping unsupported attachment type '%s' for file '%s'",
                mime_type,
                filename,
            )
            return

        msg = EmailMessage()
        msg["From"] = self._user
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = subject
        msg.set_content(body)

        msg.add_attachment(
            final_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

        if self._port == 465:
            # Implicit TLS (e.g. Gmail with SSL)
            with smtplib.SMTP_SSL(self._host, self._port) as smtp:
                smtp.login(self._user, self._password)
                smtp.send_message(msg)
        else:
            # STARTTLS (e.g. port 587)
            with smtplib.SMTP(self._host, self._port) as smtp:
                smtp.ehlo()
                if self._use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                smtp.login(self._user, self._password)
                smtp.send_message(msg)
