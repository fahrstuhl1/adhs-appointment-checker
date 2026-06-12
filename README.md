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

samedi powers the online booking widget on many German practice websites. Its
public Booking API (v3, base `https://patient.samedi.de/api/booking/v3`)
exposes read-only endpoints for appointment availability:

- `GET /days?client_id=…&event_category_id=…&event_type_id=…&from=…&to=…`
  → the days that currently have free slots,
- `GET /times?client_id=…&event_category_id=…&event_type_id=…&date=…`
  → the concrete time slots on a given day,
- `GET /insurances?client_id=…` → list of health insurances.

The add-on polls the `/days` endpoint for each configured doctor over your
chosen date window and records the result. When a doctor that previously had
**no** free days suddenly has some — or when the **earliest** free day moves
closer — it fires a notification.

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

## Finding the IDs of a doctor

Open the practice's online booking page in your browser, open the developer
tools **Network** tab, and start a booking. You will see requests to
`patient.samedi.de/api/booking/v3/…` containing `client_id`,
`event_category_id` and `event_type_id` as query parameters. Copy those into a
doctor entry in the web UI.

## Disclaimer

This add-on only **reads** publicly available booking availability — it does
not book anything for you. Be a good citizen and keep the check interval
reasonable (hourly is plenty). Use at your own risk; samedi's API may change.
