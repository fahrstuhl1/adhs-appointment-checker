"""Send notifications to Home Assistant via the Supervisor proxy.

Inside the add-on container, ``SUPERVISOR_TOKEN`` is available and the core API
is reachable at ``http://supervisor/core/api``. We call a notify service
(``persistent_notification`` by default, configurable via the ``notify_service``
option). When running outside HA (local dev) this becomes a no-op.
"""

from __future__ import annotations

import logging
import os

import requests

LOGGER = logging.getLogger("adhs.notify")

_CORE_API = "http://supervisor/core/api"


def _notify_service() -> str:
    return os.environ.get("NOTIFY_SERVICE", "persistent_notification").strip() or "persistent_notification"


def send(title: str, message: str) -> None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        LOGGER.info("No SUPERVISOR_TOKEN; notification suppressed: %s — %s", title, message)
        return

    service = _notify_service()
    url = f"{_CORE_API}/services/notify/{service}"
    payload = {"message": message, "title": title}
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        if response.status_code >= 400:
            LOGGER.warning(
                "Notification via notify.%s failed: HTTP %s %s",
                service,
                response.status_code,
                response.text[:200],
            )
    except requests.RequestException as exc:
        LOGGER.warning("Notification request failed: %s", exc)
