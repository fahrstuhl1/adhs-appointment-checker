"""Send notifications to Home Assistant via the Supervisor proxy.

Inside the add-on container, ``SUPERVISOR_TOKEN`` is available and the core API
is reachable at ``http://supervisor/core/api``. We call a notify service whose
name is configured in the web UI (falling back to the ``notify_service`` add-on
option, default ``persistent_notification``). When running outside HA (local
dev) sending is a no-op that reports why.
"""

from __future__ import annotations

import logging
import os

import requests

LOGGER = logging.getLogger("adhs.notify")

_CORE_API = "http://supervisor/core/api"
DEFAULT_SERVICE = "persistent_notification"


def env_default_service() -> str:
    return os.environ.get("NOTIFY_SERVICE", DEFAULT_SERVICE).strip() or DEFAULT_SERVICE


def resolve_service() -> str:
    """UI-configured service if set, otherwise the add-on option / default."""
    try:
        from . import store

        configured = (store.get_notify_service() or "").strip()
    except Exception:  # pragma: no cover - store should always import
        configured = ""
    return configured or env_default_service()


def send(title: str, message: str, service: str | None = None) -> str | None:
    """Send a notification. Returns ``None`` on success or an error string."""
    service = (service or resolve_service()).strip() or DEFAULT_SERVICE
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        msg = "Kein SUPERVISOR_TOKEN – Versand nur im Home-Assistant-Add-on möglich."
        LOGGER.info("%s (%s — %s)", msg, title, message)
        return msg

    url = f"{_CORE_API}/services/notify/{service}"
    payload = {"message": message, "title": title}
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
    except requests.RequestException as exc:
        LOGGER.warning("Notification request failed: %s", exc)
        return f"Anfrage fehlgeschlagen: {exc}"

    if response.status_code >= 400:
        snippet = response.text[:160].replace("\n", " ")
        LOGGER.warning("notify.%s failed: HTTP %s %s", service, response.status_code, snippet)
        return f"notify.{service} fehlgeschlagen: HTTP {response.status_code} {snippet}"

    LOGGER.info("Notification sent via notify.%s", service)
    return None
