# Changelog

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
