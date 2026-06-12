"""Client for the public samedi.de Booking API (v3).

Only read-only availability endpoints are used. The base URL defaults to
``https://patient.samedi.de/api/booking/v3`` and can be overridden via the
``BASE_URL`` environment variable / add-on option.

Relevant endpoints (all GET, JSON responses)::

    /days   ?client_id=&event_category_id=&event_type_id=&from=&to=
    /times  ?client_id=&event_category_id=&event_type_id=&date=
    /insurances ?client_id=

The ``/days`` endpoint returns the days that currently have at least one free
slot for the given appointment category + type. Response shapes vary slightly
between practices, so parsing is intentionally defensive.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any

import requests

LOGGER = logging.getLogger("adhs.samedi")

DEFAULT_BASE_URL = "https://patient.samedi.de/api/booking/v3"
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def base_url() -> str:
    return os.environ.get("BASE_URL", DEFAULT_BASE_URL).rstrip("/")


class SamediError(RuntimeError):
    """Raised when the samedi API cannot be queried successfully."""


def _extract_dates(payload: Any) -> list[str]:
    """Pull ISO ``YYYY-MM-DD`` day strings out of an arbitrary JSON payload."""
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, str):
            match = _DATE_RE.search(node)
            if match:
                found.add(match.group(0))
        elif isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)

    _walk(payload)
    return sorted(found)


def fetch_available_days(doctor: dict[str, Any], *, timeout: int = 20) -> list[str]:
    """Return a sorted list of ISO date strings that currently have free slots.

    Raises :class:`SamediError` on transport/HTTP/parse failures so the caller
    can record a meaningful error state.
    """
    client_id = doctor.get("client_id", "").strip()
    category = doctor.get("event_category_id", "").strip()
    event_type = doctor.get("event_type_id", "").strip()
    if not (client_id and category and event_type):
        raise SamediError(
            "Missing client_id, event_category_id or event_type_id for this doctor."
        )

    days_ahead = int(doctor.get("days_ahead", 90))
    today = date.today()
    params = {
        "client_id": client_id,
        "event_category_id": category,
        "event_type_id": event_type,
        "from": today.isoformat(),
        "to": (today + timedelta(days=days_ahead)).isoformat(),
    }
    insurance_id = doctor.get("insurance_id", "").strip()
    if insurance_id:
        params["insurance_id"] = insurance_id

    url = f"{base_url()}/days"
    LOGGER.debug("GET %s params=%s", url, params)
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "adhs-appointment-checker/0.1 (+home-assistant add-on)",
            },
        )
    except requests.RequestException as exc:
        raise SamediError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        snippet = response.text[:200].replace("\n", " ")
        raise SamediError(f"HTTP {response.status_code}: {snippet}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SamediError("Response was not valid JSON.") from exc

    days = _extract_dates(payload)
    # Keep only days within the requested window (defensive).
    horizon = today + timedelta(days=days_ahead)
    result: list[str] = []
    for day in days:
        try:
            parsed = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= parsed <= horizon:
            result.append(day)
    return sorted(set(result))
