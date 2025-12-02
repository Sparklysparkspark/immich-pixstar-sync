# src/immich_pixstar_sync/pixstar_mailer.py

from __future__ import annotations

from email.message import EmailMessage
from typing import Iterable

import mimetypes
import smtplib

from .config import Settings


class PixStarMailer:
    """
    Sends photos as email attachments to Pix-Star frames via SMTP.
    """

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
        Send `content` as a single image attachment to the given Pix-Star addresses.
        """
        to_list = list(to_addrs)
        if not to_list:
            return

        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "image/jpeg"

        maintype, subtype = mime_type.split("/", 1)

        msg = EmailMessage()
        msg["From"] = self._user
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = subject
        msg.set_content(body)

        msg.add_attachment(
            content,
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
