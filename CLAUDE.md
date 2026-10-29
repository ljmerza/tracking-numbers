## Project Structure & Module Organization
- `custom_components/tracking_numbers/` houses the integration: `__init__.py` wires config entries, `coordinator.py` runs the polling loop, and `sensor.py` exposes the flat package sensor.
- `parsers/` holds retailer modules named `retailer.py`; each exports `ATTR_*`, `EMAIL_DOMAIN_*`, and `parse_*` symbols registered in `parsers_list.py`.
- Parsers return dicts with `tracking_number` plus optional `carrier`, `link`, `order_number`, `order_link`. When an email has only an order number, emit an order-only entry (`tracking_number == order_number`); the coordinator drops it once a real tracking number appears for the same parser + order.
- `services.yaml`, `strings.json`, and `translations/` define Home Assistant services and localized UI copy.

## Coding Style & Naming Conventions
- Constants belong in `const.py` and use upper snake case; parser helpers should reuse shared regex such as `usps_regex`, `fedex_regex`, and `ups_regex`.
- Parser changes must be additive—extend conditions without regressing legacy behavior unless maintainers explicitly request a rewrite.
- Reference `email.log` when asked to create or adjust parsers; sanitize personal data before sharing snippets externally.
- Saved test emails live in `.data/fixtures/<retailer>_<kind>_<gmail id>.json` (gitignored; trim layout, redact names/tokens, add an `expected` block). Check with `python3 scripts/run_parsers.py` from the repo root (exits 1 on a failed `expected`).
- `parsers_list.py` (and some other files) use CRLF line endings; keep them when editing.