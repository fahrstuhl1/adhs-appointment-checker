# Changelog

## 0.1.0

- Initial release.
- Hourly (configurable) checks of samedi.de availability via the public
  Booking API v3 `/days` endpoint.
- Web UI (Home Assistant Ingress) to manage doctors, the check interval, and to
  view the last result per doctor.
- Home Assistant notifications when a slot becomes available or moves earlier.
