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


def _attempts(target: str) -> list[tuple[str, dict]]:
    """Return ordered (notify-service, extra-payload) attempts for a target.

    Home Assistant has two notification mechanisms:

    * legacy notify services, e.g. ``notify.mobile_app_x`` / ``notify.persistent_notification``
      → POST ``/services/notify/<name>`` with ``message``/``title``;
    * modern notify *entities*, e.g. ``notify.iphone_max`` (Companion app)
      → POST ``/services/notify/send_message`` with ``entity_id`` + ``message``/``title``.

    We pick based on the configured value and, for a bare name, fall back to the
    entity call if the legacy service does not exist.
    """
    if target.startswith("notify."):
        return [("send_message", {"entity_id": target})]
    if "." in target:  # a full entity id of some other form
        return [("send_message", {"entity_id": target})]
    # Bare name: try legacy service first, then the notify entity of that name.
    return [(target, {}), ("send_message", {"entity_id": f"notify.{target}"})]


def send(title: str, message: str, service: str | None = None) -> str | None:
    """Send a notification. Returns ``None`` on success or an error string."""
    target = (service or resolve_service()).strip() or DEFAULT_SERVICE
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        msg = "Kein SUPERVISOR_TOKEN – Versand nur im Home-Assistant-Add-on möglich."
        LOGGER.info("%s (%s — %s)", msg, title, message)
        return msg

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    attempts = _attempts(target)
    last_error = ""

    for index, (notify_service, extra) in enumerate(attempts):
        url = f"{_CORE_API}/services/notify/{notify_service}"
        payload = {**extra, "message": message, "title": title}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
        except requests.RequestException as exc:
            LOGGER.warning("Notification request failed: %s", exc)
            return f"Anfrage fehlgeschlagen: {exc}"

        if response.status_code < 400:
            LOGGER.info("Notification sent via notify.%s -> %s", notify_service, target)
            return None

        # Home Assistant usually returns the real reason as JSON {"message": ...}.
        detail = response.text[:200].replace("\n", " ").strip()
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("message"):
                detail = str(body["message"])
        except ValueError:
            pass
        last_error = f"HTTP {response.status_code}: {detail}"
        LOGGER.warning("notify.%s failed: %s", notify_service, last_error)

        # On a 400 there may be a further attempt (legacy -> entity); try it.
        if response.status_code == 400 and index < len(attempts) - 1:
            continue
        break

    hint = (
        " — Prüfe den genauen Namen unter Entwicklerwerkzeuge → Aktionen/Zustände. "
        "Lege entweder einen Notify-Dienst (z. B. „mobile_app_iphone_max“) oder die "
        "Notify-Entität (z. B. „notify.iphone_max“) als Wert fest."
    )
    return f"„{target}“ fehlgeschlagen: {last_error}{hint}"
