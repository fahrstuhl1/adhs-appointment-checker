# Changelog

## 0.9.0

- Redesigned overview into a status dashboard: status tiles at the top
  (Verfügbar / Überwacht / Fehler / Countdown bis zur nächsten Prüfung), doctors
  shown as colour-coded cards **sorted by status** (verfügbar → Fehler → keine →
  ungeprüft → inaktiv) and earliest day, so actionable entries are seen first.
- Auto-refresh: live countdown to the next scheduled check, reloads when due.
- Settings and doctor management moved into a collapsible section to keep the
  status front and centre.

## 0.8.0

- Support modern Home Assistant notify **entities** (e.g. `notify.iphone_max`
  from the Companion app), not just legacy notify services: values starting with
  `notify.` are sent via the `notify.send_message` action with `entity_id`. A
  bare name that isn't a legacy service automatically falls back to the matching
  notify entity. Fixes the HTTP 400 when using a Companion-app notify entity.

## 0.7.0

- Mobile UI: the results table now collapses into stacked, labelled cards on
  narrow screens, so the action buttons (Prüfen/Bearbeiten/Löschen) are no
  longer pushed off-screen in portrait mode.
- Clearer notification errors: surface Home Assistant's actual JSON error
  message and, on HTTP 400, hint that the service name is likely wrong
  (mobile-app services are named `mobile_app_<device>`).

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
