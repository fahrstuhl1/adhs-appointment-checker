"""Flask web UI + hourly scheduler entry point for the ADHS Appointment Checker."""

from __future__ import annotations

import logging
import os
from urllib.parse import quote

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, redirect, render_template, request

from . import checker, notify, samedi, store

_JOB_ID = "adhs_check_all"

_LOG_LEVELS = {
    "trace": logging.DEBUG,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "fatal": logging.CRITICAL,
}


def _configure_logging() -> None:
    level = _LOG_LEVELS.get(os.environ.get("LOG_LEVEL", "info").lower(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


LOGGER = logging.getLogger("adhs.main")

app = Flask(__name__)
scheduler = BackgroundScheduler(daemon=True)


@app.template_filter("dt")
def _format_datetime(value: str | None) -> str:
    """Render an ISO timestamp as a compact German date/time, e.g. 12.06.2026 10:57."""
    if not value:
        return "nie"
    try:
        from datetime import datetime

        return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return value


def _base_path() -> str:
    """Return the Home Assistant ingress base path (empty when run standalone)."""
    return request.headers.get("X-Ingress-Path", "")


def reschedule() -> None:
    """(Re)configure the periodic check job from the stored interval."""
    minutes = store.get_interval_minutes()
    scheduler.add_job(
        checker.check_all,
        trigger="interval",
        minutes=minutes,
        id=_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    LOGGER.info("Scheduled availability check every %d minute(s).", minutes)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    doctors = store.list_doctors()
    state = store.load_state()
    edit_id = request.args.get("edit")
    edit_doctor = store.get_doctor(edit_id) if edit_id else None

    items, summary = _build_overview(doctors, state)

    return render_template(
        "index.html",
        base_path=_base_path(),
        interval_minutes=store.get_interval_minutes(),
        base_url=samedi.base_url(),
        items=items,
        summary=summary,
        edit_doctor=edit_doctor,
        notify_service=store.get_notify_service(),
        notify_default=notify.env_default_service(),
        error=request.args.get("error"),
        notice=request.args.get("notice"),
    )


def _status_of(doctor: dict, s: dict) -> str:
    """Classify a doctor row: available / error / none / unknown / disabled."""
    if not doctor.get("enabled", True):
        return "disabled"
    status = s.get("status")
    if status == "ok" and (s.get("available_count") or 0) > 0:
        return "available"
    if status == "error":
        return "error"
    if status == "ok":
        return "none"
    return "unknown"


def _build_overview(doctors: list[dict], state: dict):
    """Return (sorted items, summary) for the dashboard.

    Items are sorted so the most actionable rows come first: available, then
    errors, then 'no slots', unknown and finally disabled; within a group by
    earliest day and name.
    """
    order = {"available": 0, "error": 1, "none": 2, "unknown": 3, "disabled": 4}
    items = []
    for doctor in doctors:
        s = state.get(doctor["id"], {})
        status = _status_of(doctor, s)
        items.append({"doctor": doctor, "s": s, "status": status})

    items.sort(
        key=lambda it: (
            order[it["status"]],
            it["s"].get("earliest_day") or "9999-12-31",
            (it["doctor"].get("name") or "").lower(),
        )
    )

    checked_times = [it["s"].get("checked_at") for it in items if it["s"].get("checked_at")]
    summary = {
        "total": len(doctors),
        "monitored": sum(1 for d in doctors if d.get("enabled", True)),
        "available": sum(1 for it in items if it["status"] == "available"),
        "errors": sum(1 for it in items if it["status"] == "error"),
        "none": sum(1 for it in items if it["status"] == "none"),
        "last_checked": max(checked_times) if checked_times else None,
        "next_check": _next_check_iso(),
    }
    return items, summary


def _next_check_iso() -> str | None:
    job = scheduler.get_job(_JOB_ID)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None



@app.post("/settings")
def save_settings():
    try:
        minutes = int(request.form.get("interval_minutes", "60"))
    except ValueError:
        minutes = 60
    store.set_interval_minutes(minutes)
    store.set_notify_service(request.form.get("notify_service", ""))
    reschedule()
    return redirect(f"{_base_path()}/?notice={quote('Einstellungen gespeichert.')}")


@app.post("/notify/test")
def test_notify():
    # Persist the field first so the test uses what the user just typed.
    store.set_notify_service(request.form.get("notify_service", ""))
    error = notify.send(
        title="ADHS Appointment Checker – Test",
        message="Dies ist eine Test-Benachrichtigung. Wenn du das siehst, funktioniert es.",
    )
    if error:
        return redirect(f"{_base_path()}/?error={quote(error)}")
    service = notify.resolve_service()
    return redirect(f"{_base_path()}/?notice={quote(f'Test-Benachrichtigung über notify.{service} gesendet.')}")


@app.post("/doctors")
def save_doctor():
    data = {
        "id": request.form.get("id") or None,
        "name": request.form.get("name"),
        "event_category_id": request.form.get("event_category_id"),
        "event_type_id": request.form.get("event_type_id"),
        "insurance_id": request.form.get("insurance_id"),
        "days_ahead": request.form.get("days_ahead"),
        "enabled": request.form.get("enabled") == "on",
    }

    booking_url = (request.form.get("booking_url") or "").strip()
    if booking_url and not (data["event_category_id"] and data["event_type_id"]):
        try:
            resolved = samedi.resolve_booking_url(booking_url)
            data["event_category_id"] = resolved["event_category_id"]
            data["event_type_id"] = resolved["event_type_id"]
            data["practice_id"] = resolved["practice_id"]
            if resolved["insurance_id"] and not data["insurance_id"]:
                data["insurance_id"] = resolved["insurance_id"]
        except samedi.SamediError as exc:
            LOGGER.warning("Could not resolve booking URL: %s", exc)
            return redirect(f"{_base_path()}/?error={quote(str(exc))}")

    store.upsert_doctor(data)
    return redirect(f"{_base_path()}/")


@app.post("/doctors/<doctor_id>/delete")
def remove_doctor(doctor_id: str):
    store.delete_doctor(doctor_id)
    return redirect(f"{_base_path()}/")


@app.post("/doctors/<doctor_id>/check")
def check_one(doctor_id: str):
    doctor = store.get_doctor(doctor_id)
    if doctor:
        checker.check_doctor(doctor)
    return redirect(f"{_base_path()}/")


@app.post("/check")
def check_now():
    checker.check_all(only_enabled=False)
    return redirect(f"{_base_path()}/")


@app.get("/health")
def health():
    return {"status": "ok", "doctors": len(store.list_doctors())}


def main() -> None:
    _configure_logging()
    store.load_config()  # ensure files exist
    scheduler.start()
    reschedule()

    # Kick off an initial check shortly after startup so the UI isn't empty.
    from datetime import datetime, timedelta

    scheduler.add_job(
        checker.check_all,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=10),
        id="adhs_initial_check",
        replace_existing=True,
    )

    from waitress import serve

    LOGGER.info("Serving web UI on 0.0.0.0:8099")
    serve(app, host="0.0.0.0", port=8099, threads=4)


if __name__ == "__main__":
    main()
