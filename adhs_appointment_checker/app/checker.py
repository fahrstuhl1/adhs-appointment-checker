"""Orchestrates availability checks and result/notification handling."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from . import notify, samedi, store

LOGGER = logging.getLogger("adhs.checker")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def check_doctor(doctor: dict[str, Any]) -> dict[str, Any]:
    """Run a single check for one doctor, persist the result and notify.

    Returns the new state dict for the doctor.
    """
    doctor_id = doctor["id"]
    previous = store.get_doctor_state(doctor_id)
    prev_earliest = previous.get("earliest_day")
    prev_count = int(previous.get("available_count", 0) or 0)

    result: dict[str, Any] = {
        "checked_at": _now_iso(),
        "name": doctor.get("name"),
    }

    try:
        availability = samedi.fetch_availability(doctor)
        days = availability["days"]
        result.update(
            {
                "status": "ok",
                "available_days": days,
                "available_count": len(days),
                "slot_count": availability["slot_count"],
                "earliest_day": days[0] if days else None,
                "error": None,
            }
        )
        LOGGER.info(
            "Checked '%s': %d slot(s) on %d day(s)%s",
            doctor.get("name"),
            availability["slot_count"],
            len(days),
            f", earliest {days[0]}" if days else "",
        )
    except samedi.SamediError as exc:
        result.update(
            {
                "status": "error",
                # Preserve last known availability so the UI keeps showing it.
                "available_days": previous.get("available_days", []),
                "available_count": prev_count,
                "slot_count": previous.get("slot_count", 0),
                "earliest_day": prev_earliest,
                "error": str(exc),
            }
        )
        LOGGER.warning("Check for '%s' failed: %s", doctor.get("name"), exc)

    store.set_doctor_state(doctor_id, result)

    if result["status"] == "ok":
        _maybe_notify(doctor, prev_count, prev_earliest, result)

    return result


def _maybe_notify(
    doctor: dict[str, Any],
    prev_count: int,
    prev_earliest: str | None,
    result: dict[str, Any],
) -> None:
    new_count = result["available_count"]
    new_earliest = result["earliest_day"]

    became_available = prev_count == 0 and new_count > 0
    got_earlier = (
        new_earliest is not None
        and prev_earliest is not None
        and new_earliest < prev_earliest
    )

    if became_available:
        notify.send(
            title=f"ADHS-Termin verfügbar: {doctor.get('name')}",
            message=(
                f"{new_count} Tag(e) mit freien Terminen gefunden. "
                f"Frühester Termin: {new_earliest}."
            ),
        )
    elif got_earlier:
        notify.send(
            title=f"Früherer ADHS-Termin: {doctor.get('name')}",
            message=f"Neuer frühester Termin: {new_earliest} (vorher {prev_earliest}).",
        )


def check_all(only_enabled: bool = True) -> list[dict[str, Any]]:
    """Check every configured doctor. Returns the list of new states."""
    results = []
    for doctor in store.list_doctors():
        if only_enabled and not doctor.get("enabled", True):
            continue
        results.append(check_doctor(doctor))
    return results
