# Changelog

## 0.6.0

- Configure the notification service **in the web UI** (Globale Einstellungen →
  Benachrichtigungsdienst), with a **Test senden** button that reports success
  or the exact error. The UI value overrides the `notify_service` add-on option;
  an empty field falls back to it.

## 0.5.0

- UI: render the "last checked" timestamp as a compact German date/time
  (`12.06.2026 10:57`) instead of the raw ISO string.
- UI: tidy the per-row action buttons (Prüfen / Bearbeiten / Löschen) into a
  consistent, evenly-aligned stack.

## 0.4.0

- Fix: pre-configured doctors now also appear on installs **upgraded** from an
  earlier version (where `config.json` already existed with no doctors). A
  one-time seeding migration adds any missing seed doctors; later deletions are
  respected.

## 0.3.0

- Version bump so Home Assistant detects the update. No functional changes
  beyond 0.2.0.

## 0.2.0

- Use the samedi `/times` endpoint (with the public booking-widget
  `client_id` + `api_key`) as used by `termin.samedi.de`, instead of `/days`.
- Pre-seed three doctors for Praxis Viola Berg (ADHS-Diagnostik, GKV):
  Viola Berg, Susann Bergmann, Melanie Scholz.
- Add doctors directly from a `termin.samedi.de/b/...` booking URL — IDs are
  resolved automatically via `practices/slug_to_id`.
- Show slot count in addition to free days; configurable `client_id` / `api_key`.

## 0.1.0

- Initial release.
- Hourly (configurable) checks of samedi.de availability via the public
  Booking API v3 `/days` endpoint.
- Web UI (Home Assistant Ingress) to manage doctors, the check interval, and to
  view the last result per doctor.
- Home Assistant notifications when a slot becomes available or moves earlier.
