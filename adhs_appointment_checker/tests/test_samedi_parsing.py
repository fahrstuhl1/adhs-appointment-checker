"""Tests for parsing the samedi /times response.

The slot shape used here was captured from a live, *populated* /times response
of a real samedi practice (radiology, with free slots):

    {"data": [{"time": "2026-06-15T10:00:00+02:00", "token": "deprecated-..."},
              {"time": "2026-06-16T10:00:00+02:00", "token": "deprecated-..."}]}

Run with:  python -m pytest  (or: python tests/test_samedi_parsing.py)
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import samedi  # noqa: E402


def _real_populated_payload() -> dict:
    today = date.today()
    d1 = (today + timedelta(days=3)).isoformat()
    d2 = (today + timedelta(days=10)).isoformat()
    return {
        "data": [
            {"time": f"{d1}T10:00:00+02:00", "token": "deprecated-aaa"},
            {"time": f"{d1}T10:30:00+02:00", "token": "deprecated-bbb"},
            {"time": f"{d2}T09:00:00+02:00", "token": "deprecated-ccc"},
        ]
    }


def test_slots_from_real_payload():
    payload = _real_populated_payload()
    slots = samedi._slots_from_payload(payload)
    assert len(slots) == 3
    assert all("T" in s for s in slots)


def test_fetch_availability_counts_days_and_slots(monkeypatch):
    payload = _real_populated_payload()
    monkeypatch.setattr(samedi, "_get", lambda path, params: payload)
    res = samedi.fetch_availability(
        {"event_category_id": "1", "event_type_id": "2", "days_ahead": 60, "insurance_id": "public"}
    )
    assert res["slot_count"] == 3
    assert len(res["days"]) == 2  # two distinct days


def test_empty_response_means_no_availability(monkeypatch):
    monkeypatch.setattr(samedi, "_get", lambda path, params: {"data": []})
    res = samedi.fetch_availability({"event_category_id": "1", "event_type_id": "2"})
    assert res == {"days": [], "slot_count": 0}


def test_slots_outside_window_are_ignored(monkeypatch):
    today = date.today()
    far = (today + timedelta(days=400)).isoformat()
    past = (today - timedelta(days=5)).isoformat()
    payload = {"data": [{"time": f"{far}T10:00:00+02:00"}, {"time": f"{past}T10:00:00+02:00"}]}
    monkeypatch.setattr(samedi, "_get", lambda path, params: payload)
    res = samedi.fetch_availability({"event_category_id": "1", "event_type_id": "2", "days_ahead": 90})
    assert res == {"days": [], "slot_count": 0}


if __name__ == "__main__":
    # Minimal runner so the file works without pytest installed.
    class _MP:
        def setattr(self, obj, name, value):
            setattr(obj, name, value)

    test_slots_from_real_payload()
    test_fetch_availability_counts_days_and_slots(_MP())
    test_empty_response_means_no_availability(_MP())
    test_slots_outside_window_are_ignored(_MP())
    print("all parsing tests passed")
