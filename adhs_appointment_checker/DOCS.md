# ADHS Appointment Checker

This add-on periodically queries the public **samedi.de Booking API** for open
appointment slots and shows the result in a built-in web UI (Home Assistant
Ingress). It was built to help with the notoriously hard hunt for an **ADHS**
(ADHD) appointment, where free slots are taken within minutes.

## Configuration (add-on options)

| Option | Default | Description |
| --- | --- | --- |
| `log_level` | `info` | Log verbosity (`trace`…`fatal`). |
| `default_interval_minutes` | `60` | Initial check interval used until you change it in the web UI. |
| `base_url` | `https://patient.samedi.de/api/booking/v3` | Base URL of the samedi Booking API. Only change this if samedi moves the API. |
| `notify_service` | `persistent_notification` | The Home Assistant `notify.<service>` used for alerts (e.g. `mobile_app_pixel`). |

The list of doctors and the active check interval are managed in the **web UI**
and stored persistently in the add-on's `/config` directory
(`config.json` + `state.json`).

## Using the web UI

1. Start the add-on and click **Open Web UI**.
2. Under **Arzt hinzufügen**, add one entry per appointment you want to watch.
3. Use **Jetzt alle prüfen** to run an immediate check, or wait for the hourly
   schedule.
4. The table shows, per doctor: status, earliest free day, number of free days,
   and the last-checked timestamp.

## Pre-configured doctors

On first start the add-on seeds three entries for the **Praxis Viola Berg**
ADHS-Diagnostik (gesetzlich versichert):

| Name | event_category_id | event_type_id |
| --- | --- | --- |
| Viola Berg | 127359 | 338226 |
| Susann Bergmann | 139923 | 399111 |
| Melanie Scholz | 139924 | 399114 |

You can edit or delete these in the web UI.

## Adding a doctor from a booking URL (easiest)

In the **Arzt hinzufügen** form, paste the samedi booking link
(`https://termin.samedi.de/b/<practice>/<n>/<doctor>/<type>?insuranceId=public`)
into the **samedi-Buchungs-URL** field and submit. The add-on resolves the
`event_category_id` / `event_type_id` (and `insurance_id`) automatically via the
samedi `practices/slug_to_id` endpoint.

## Adding a doctor manually

The `termin.samedi.de` widget queries the samedi Booking API v3
`GET /times?event_category_id=…&event_type_id=…&insurance_id=…&from=…&to=…`,
authenticated with the public widget's `client_id` + `api_key` (shipped as
add-on options). To find the IDs by hand:

1. Open the doctor's booking page in a desktop browser.
2. Open **Developer Tools → Network** (Ctrl/Cmd+Shift+I).
3. Select the appointment category/type and watch for a request to
   `patient.samedi.de/api/booking/v3/times` — its query string contains
   `event_category_id`, `event_type_id` and `insurance_id`.
4. Copy those into a doctor entry.

`insurance_id` is usually `public` for statutory ("gesetzlich") insurance.

## Notifications

When a doctor that previously had **no** free days gains availability — or when
the **earliest** free day moves closer — the add-on sends a notification via
`notify.<notify_service>`. With the default `persistent_notification`, alerts
appear in the Home Assistant UI. Set `notify_service` to a mobile app notify
service to get push notifications.

## Notes & limitations

- The add-on only **reads** availability; it never books anything.
- Please keep the interval reasonable (hourly is the default and recommended).
- samedi's API is not officially documented for third-party polling and may
  change; if checks start failing, re-verify the IDs and `base_url`.
