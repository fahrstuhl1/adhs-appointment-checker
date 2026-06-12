"""Client for the public samedi.de Booking API (v3).

Only read-only availability endpoints are used. The base URL defaults to
``https://patient.samedi.de/api/booking/v3`` and can be overridden via the
``BASE_URL`` environment variable / add-on option.

The samedi booking widget (``termin.samedi.de``) talks to this same backend.
Every request carries a set of default query parameters identifying the public
booking widget::

    client_id=<widget client id>  api_key=<widget api key>  source=bw_v3

Relevant endpoints (all GET, JSON responses)::

    /practices/slug_to_id ?practice_slug=&event_category_slug=&event_type_slug=
        -> {practice_id, event_category_id, event_type_id}
    /times  ?event_category_id=&event_type_id=&insurance_id=&from=&to=
        -> {"data": [{"time": "2026-06-15T10:00:00+02:00", ...}, ...]}

The widget uses ``/times`` (not ``/days``) with a ``from``/``to`` range and
derives available days from the returned slots. We do the same.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

LOGGER = logging.getLogger("adhs.samedi")

DEFAULT_BASE_URL = "https://patient.samedi.de/api/booking/v3"
# Public booking-widget credentials shipped with termin.samedi.de.
DEFAULT_CLIENT_ID = "8f0hsw1v0x676r5pqbf4fecv3fo7s5l"
DEFAULT_API_KEY = "TESTING"

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TIMEOUT = 25


def base_url() -> str:
    return os.environ.get("BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def default_client_id() -> str:
    return os.environ.get("CLIENT_ID", DEFAULT_CLIENT_ID)


def default_api_key() -> str:
    return os.environ.get("API_KEY", DEFAULT_API_KEY)


class SamediError(RuntimeError):
    """Raised when the samedi API cannot be queried successfully."""


def _auth_params(doctor: dict[str, Any] | None = None) -> dict[str, str]:
    client_id = ""
    api_key = ""
    if doctor:
        client_id = (doctor.get("client_id") or "").strip()
        api_key = (doctor.get("api_key") or "").strip()
    return {
        "client_id": client_id or default_client_id(),
        "api_key": api_key or default_api_key(),
        "source": "bw_v3",
    }


def _get(path: str, params: dict[str, Any]) -> Any:
    url = f"{base_url()}/{path.lstrip('/')}"
    LOGGER.debug("GET %s params=%s", url, {k: v for k, v in params.items() if k != "api_key"})
    try:
        response = requests.get(
            url,
            params=params,
            timeout=_TIMEOUT,
            headers={
                "Accept": "application/json",
                "User-Agent": "adhs-appointment-checker/0.2 (+home-assistant add-on)",
            },
        )
    except requests.RequestException as exc:
        raise SamediError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        snippet = response.text[:200].replace("\n", " ")
        raise SamediError(f"HTTP {response.status_code}: {snippet}")

    try:
        return response.json()
    except ValueError as exc:
        raise SamediError("Response was not valid JSON.") from exc


def _slots_from_payload(payload: Any) -> list[str]:
    """Return ISO datetime strings of slots from a ``/times`` response."""
    if isinstance(payload, dict):
        items = payload.get("data", [])
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    slots: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get("time") or item.get("date") or item.get("starts_at")
            if isinstance(value, str):
                slots.append(value)
        elif isinstance(item, str):
            slots.append(item)
    return slots


def fetch_availability(doctor: dict[str, Any]) -> dict[str, Any]:
    """Query free slots for a doctor over its date window.

    Returns ``{"days": [iso-date, ...], "slot_count": int}``. Raises
    :class:`SamediError` on transport/HTTP/parse failures.
    """
    category = str(doctor.get("event_category_id", "")).strip()
    event_type = str(doctor.get("event_type_id", "")).strip()
    if not (category and event_type):
        raise SamediError("Missing event_category_id or event_type_id for this doctor.")

    days_ahead = int(doctor.get("days_ahead", 90))
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    params = _auth_params(doctor)
    params.update(
        {
            "event_category_id": category,
            "event_type_id": event_type,
            "from": today.isoformat(),
            "to": horizon.isoformat(),
        }
    )
    insurance_id = (doctor.get("insurance_id") or "").strip()
    if insurance_id:
        params["insurance_id"] = insurance_id

    payload = _get("times", params)
    slots = _slots_from_payload(payload)

    days: set[str] = set()
    valid_slots = 0
    for slot in slots:
        match = _DATE_RE.search(slot)
        if not match:
            continue
        try:
            parsed = datetime.strptime(match.group(0), "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= parsed <= horizon:
            days.add(match.group(0))
            valid_slots += 1

    return {"days": sorted(days), "slot_count": valid_slots}


def resolve_booking_url(url: str) -> dict[str, str]:
    """Resolve a ``termin.samedi.de/b/...`` booking URL to numeric IDs.

    Expected path shape::

        /b/<practice_slug>/<n>/<event_category_slug>/<event_type_slug>

    Returns a dict with ``event_category_id``, ``event_type_id``,
    ``practice_id`` and ``insurance_id`` (from the ``insuranceId`` query param,
    if present). Raises :class:`SamediError` on failure.
    """
    parsed = urlparse(url.strip())
    segments = [s for s in parsed.path.split("/") if s]
    if "b" in segments:
        segments = segments[segments.index("b") + 1 :]
    if len(segments) < 4:
        raise SamediError(
            "URL not understood. Expected a termin.samedi.de/b/<practice>/<n>/"
            "<category>/<type> booking link."
        )
    practice_slug, _idx, category_slug, type_slug = segments[0], segments[1], segments[2], segments[3]

    params = _auth_params()
    params.update(
        {
            "practice_slug": practice_slug,
            "event_category_slug": category_slug,
            "event_type_slug": type_slug,
        }
    )
    payload = _get("practices/slug_to_id", params)
    if not isinstance(payload, dict) or "event_type_id" not in payload:
        raise SamediError(f"Unexpected slug_to_id response: {str(payload)[:200]}")

    insurance = parse_qs(parsed.query).get("insuranceId", [""])[0]
    return {
        "practice_id": str(payload.get("practice_id", "")),
        "event_category_id": str(payload.get("event_category_id", "")),
        "event_type_id": str(payload.get("event_type_id", "")),
        "insurance_id": insurance,
    }
