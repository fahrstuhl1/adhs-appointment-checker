# ADHS Appointment Checker — Home Assistant Add-on

A [Home Assistant](https://www.home-assistant.io/) add-on that periodically
(hourly by default) checks [samedi.de](https://www.samedi.de/) for available
appointment slots — built for the frustrating hunt for an **ADHS**
(ADHD) diagnosis/therapy appointment, where slots appear and vanish within
minutes.

It ships a small **web UI** (via Home Assistant Ingress) to:

- configure the doctors/practices to watch (one entry per appointment type),
- set how far ahead to look and how often to check,
- see the **last result** at a glance (earliest free day, number of free days,
  last checked time, errors),
- and get a Home Assistant notification when a new (or earlier) slot appears.

> This project started from the idea of the
> `steward-ha/samedi-availability-checker` script and turns it into a
> self-contained, configurable HA add-on with a web interface.

## How it works

samedi powers the online booking widget (`termin.samedi.de`) on many German
practice websites. It talks to the Booking API v3 (base
`https://patient.samedi.de/api/booking/v3`), authenticated with the public
widget's `client_id` + `api_key`. The add-on uses the same read-only endpoints:

- `GET /practices/slug_to_id?practice_slug=…&event_category_slug=…&event_type_slug=…`
  → resolves a booking link to numeric IDs,
- `GET /times?event_category_id=…&event_type_id=…&insurance_id=…&from=…&to=…`
  → the concrete free time slots in a date range.

The add-on polls `/times` for each configured doctor over your chosen date
window and records the result (free days + slot count). When a doctor that
previously had **no** free days suddenly has some — or when the **earliest**
free day moves closer — it fires a notification.

### Pre-configured for Praxis Viola Berg (ADHS-Diagnostik, GKV)

On first run, three doctors are seeded out of the box — **Viola Berg**,
**Susann Bergmann** and **Melanie Scholz** — for the statutory-insurance ADHS
diagnostics appointments. Edit or remove them in the web UI as you like.

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Open the **⋮** menu (top right) → **Repositories** and add:
   `https://github.com/fahrstuhl1/adhs-appointment-checker`
3. Install **ADHS Appointment Checker** from the store.
4. Start the add-on and open the **Web UI** (the "OPEN WEB UI" button / sidebar
   panel).

See [`adhs_appointment_checker/DOCS.md`](adhs_appointment_checker/DOCS.md) for
configuration details, including how to find a practice's `client_id`,
`event_category_id` and `event_type_id`.

## Adding more doctors

The easiest way: paste a samedi booking link
(`https://termin.samedi.de/b/…?insuranceId=public`) into the **samedi-Buchungs-URL**
field of the add form — the add-on resolves the IDs automatically. See
[`adhs_appointment_checker/DOCS.md`](adhs_appointment_checker/DOCS.md) for the
manual route (DevTools → Network → `…/api/booking/v3/times`).

## Disclaimer

This add-on only **reads** publicly available booking availability — it does
not book anything for you. Be a good citizen and keep the check interval
reasonable (hourly is plenty). Use at your own risk; samedi's API may change.
