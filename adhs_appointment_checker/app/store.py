"""Persistent storage for configuration and last results.

State is kept as JSON files inside the add-on's persistent data directory
(``DATA_DIR``, defaults to ``/config`` inside the container, or ``./data`` when
running locally for development).

Two files are used:

* ``config.json`` — user configuration: global settings + list of doctors.
* ``state.json``  — the last check result per doctor (volatile-ish data).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from typing import Any

_LOCK = threading.RLock()

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
STATE_PATH = os.path.join(DATA_DIR, "state.json")


def _default_interval() -> int:
    try:
        return int(os.environ.get("DEFAULT_INTERVAL_MINUTES", "60"))
    except (TypeError, ValueError):
        return 60


def _seed_doctors() -> list[dict[str, Any]]:
    """Practices pre-configured on first run (Praxis Viola Berg, ADHS-Diagnostik)."""
    base = {
        "insurance_id": "public",
        "days_ahead": 90,
        "enabled": True,
    }
    seeds = [
        {"name": "Viola Berg – ADHS-Diagnostik (GKV)",
         "event_category_id": "127359", "event_type_id": "338226"},
        {"name": "Susann Bergmann – ADHS-Diagnostik (GKV)",
         "event_category_id": "139923", "event_type_id": "399111"},
        {"name": "Melanie Scholz – ADHS-Diagnostik (GKV)",
         "event_category_id": "139924", "event_type_id": "399114"},
    ]
    return [_normalize_doctor({**base, **seed}) for seed in seeds]


# Bumping this re-runs the one-time seeding migration below, adding any seed
# doctors that are not already present. User deletions are respected because the
# marker is stored once the migration has run.
SEED_VERSION = 1


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def load_config() -> dict[str, Any]:
    with _LOCK:
        cfg = _read_json(CONFIG_PATH, None) or {}
        changed = False

        if "interval_minutes" not in cfg:
            cfg["interval_minutes"] = _default_interval()
            changed = True
        if "doctors" not in cfg:
            cfg["doctors"] = []
            changed = True

        # One-time seeding migration: also fixes installs upgraded from an
        # earlier version whose config.json already existed with no doctors.
        if int(cfg.get("seed_version", 0) or 0) < SEED_VERSION:
            existing_types = {d.get("event_type_id") for d in cfg["doctors"]}
            for seed in _seed_doctors():
                if seed["event_type_id"] not in existing_types:
                    cfg["doctors"].append(seed)
            cfg["seed_version"] = SEED_VERSION
            changed = True

        if changed:
            _write_json(CONFIG_PATH, cfg)
        return cfg


def save_config(cfg: dict[str, Any]) -> None:
    with _LOCK:
        _write_json(CONFIG_PATH, cfg)


def get_interval_minutes() -> int:
    cfg = load_config()
    try:
        value = int(cfg.get("interval_minutes", _default_interval()))
    except (TypeError, ValueError):
        value = _default_interval()
    return max(5, min(value, 1440))


def set_interval_minutes(minutes: int) -> None:
    with _LOCK:
        cfg = load_config()
        cfg["interval_minutes"] = max(5, min(int(minutes), 1440))
        save_config(cfg)


def list_doctors() -> list[dict[str, Any]]:
    return load_config().get("doctors", [])


def get_doctor(doctor_id: str) -> dict[str, Any] | None:
    for doctor in list_doctors():
        if doctor.get("id") == doctor_id:
            return doctor
    return None


def _normalize_doctor(data: dict[str, Any]) -> dict[str, Any]:
    def _clean_int(value: Any, fallback: int) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return fallback

    return {
        "id": data.get("id") or uuid.uuid4().hex,
        "name": (data.get("name") or "").strip() or "Unnamed doctor",
        "client_id": (data.get("client_id") or "").strip(),
        "api_key": (data.get("api_key") or "").strip(),
        "practice_id": (data.get("practice_id") or "").strip(),
        "event_category_id": str(data.get("event_category_id") or "").strip(),
        "event_type_id": str(data.get("event_type_id") or "").strip(),
        "insurance_id": (data.get("insurance_id") or "").strip(),
        "days_ahead": max(1, min(_clean_int(data.get("days_ahead"), 90), 365)),
        "enabled": bool(data.get("enabled", True)),
    }


def upsert_doctor(data: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        cfg = load_config()
        doctor = _normalize_doctor(data)
        doctors = cfg.get("doctors", [])
        for index, existing in enumerate(doctors):
            if existing.get("id") == doctor["id"]:
                doctors[index] = doctor
                break
        else:
            doctors.append(doctor)
        cfg["doctors"] = doctors
        save_config(cfg)
        return doctor


def delete_doctor(doctor_id: str) -> None:
    with _LOCK:
        cfg = load_config()
        cfg["doctors"] = [d for d in cfg.get("doctors", []) if d.get("id") != doctor_id]
        save_config(cfg)
        state = load_state()
        if doctor_id in state:
            del state[doctor_id]
            save_state(state)


# --------------------------------------------------------------------------- #
# State (last results)
# --------------------------------------------------------------------------- #
def load_state() -> dict[str, Any]:
    with _LOCK:
        return _read_json(STATE_PATH, {}) or {}


def save_state(state: dict[str, Any]) -> None:
    with _LOCK:
        _write_json(STATE_PATH, state)


def get_doctor_state(doctor_id: str) -> dict[str, Any]:
    return load_state().get(doctor_id, {})


def set_doctor_state(doctor_id: str, result: dict[str, Any]) -> None:
    with _LOCK:
        state = load_state()
        state[doctor_id] = result
        save_state(state)
