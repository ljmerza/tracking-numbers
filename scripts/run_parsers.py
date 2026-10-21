"""Run the tracking-number parsers and delivery-date extraction offline.

Feeds saved emails through the same parser matching the coordinator uses
(sender-domain substring match, then `parse_*`, then delivery-date fill-in)
and prints what each email yields. No Home Assistant install needed.

Inputs (default: .data/fixtures/*.json, .data/*.eml, email.log):

  *.json  fixture: {"from", "subject", "date" (naive UTC ISO), "body" (HTML),
          optional "expected": {"tracking_numbers": [...],
          "estimated_delivery": "YYYY-MM-DD"|null, "delivered_date": ...|null,
          "order_number": "..."|null}}
  *.eml   raw RFC 822 message
  *.log   Gmail "Show original" dump (preamble before Delivered-To: is skipped)

Fixtures with an "expected" block are checked; the script exits 1 if any
check fails. Run from the repo root:

  python3 scripts/run_parsers.py
  python3 scripts/run_parsers.py .data/fixtures/usps_*.json --tz America/New_York
"""

from __future__ import annotations

import argparse
import email as email_lib
import email.policy
import importlib
import json
import sys
import types
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "custom_components" / "tracking_numbers"
DEFAULT_GLOBS = (".data/fixtures/*.json", ".data/*.eml", "email.log")


def load_package():
    """Import the integration's parsers without running its HA-dependent __init__."""
    package = types.ModuleType("tracking_numbers")
    package.__path__ = [str(PACKAGE_DIR)]
    sys.modules["tracking_numbers"] = package
    parsers_list = importlib.import_module("tracking_numbers.parsers_list")
    delivery_date = importlib.import_module("tracking_numbers.parsers.delivery_date")
    return parsers_list, delivery_date


def _naive_utc_iso(value) -> str | None:
    if not value:
        return None
    try:
        sent = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if sent.tzinfo is not None:
        sent = sent.astimezone(timezone.utc).replace(tzinfo=None)
    return sent.isoformat()


def _from_message(raw: bytes, source: str) -> dict:
    message = email_lib.message_from_bytes(raw, policy=email.policy.default)
    html_parts, text_parts = [], []
    for part in message.walk():
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        if content_type not in ("text/html", "text/plain"):
            continue
        try:
            content = part.get_content()
        except (LookupError, ValueError):
            continue
        (html_parts if content_type == "text/html" else text_parts).append(content)
    return {
        "source": source,
        "from": str(message.get("From", "")),
        "subject": str(message.get("Subject", "")),
        "date": _naive_utc_iso(message.get("Date")),
        # Same preference as the coordinator: HTML for link parsing, else text.
        "body": "\n".join(html_parts) or "\n".join(text_parts),
    }


def load_email(path: Path) -> dict:
    if path.suffix == ".json":
        data = json.loads(path.read_text())
        data.setdefault("source", str(path))
        return data
    raw = path.read_bytes()
    if path.suffix == ".log":
        start = raw.find(b"Delivered-To:")
        if start > 0:
            raw = raw[start:]
    return _from_message(raw, str(path))


def run_email(data: dict, parsers_list, delivery_date, tz) -> list[tuple[str, dict]]:
    """Mirror coordinator._fetch_and_parse_emails for a single email."""
    from tracking_numbers.const import (
        EMAIL_ATTR_BODY,
        EMAIL_ATTR_DATE,
        EMAIL_ATTR_FROM,
        EMAIL_ATTR_SUBJECT,
    )

    email = {
        EMAIL_ATTR_FROM: data.get("from", ""),
        EMAIL_ATTR_SUBJECT: data.get("subject", ""),
        EMAIL_ATTR_BODY: data.get("body", ""),
        EMAIL_ATTR_DATE: data.get("date"),
    }
    email_dates = None
    results: list[tuple[str, dict]] = []
    for attr, email_domain, parser in parsers_list.parsers:
        if email_domain not in email[EMAIL_ATTR_FROM]:
            continue
        # Generic is a fallback: skipped once a specific parser found something
        if attr == "generic" and results:
            continue
        try:
            found = parser(email=email)
        except Exception as err:  # pylint: disable=broad-except
            results.append((attr, {"error": repr(err)}))
            continue
        if not found:
            continue
        items = [dict(x) if isinstance(x, dict) else {"tracking_number": str(x)} for x in found]
        if email_dates is None:
            email_dates = delivery_date.extract_delivery_dates(email, tz)
        delivery_date.apply_delivery_dates(items, email_dates)
        results.extend((attr, item) for item in items)
    return results


def check(expected: dict, results: list[tuple[str, dict]]) -> list[str]:
    """Compare a fixture's expected block against parser output."""
    failures = []
    by_number: dict[str, dict] = {}
    for _, item in results:
        number = item.get("tracking_number")
        if number and number not in by_number:
            by_number[number] = item

    for number in expected.get("tracking_numbers") or []:
        item = by_number.get(number)
        if item is None:
            failures.append(f"missing tracking number {number}")
            continue
        for key in ("estimated_delivery", "delivered_date", "order_number"):
            if key not in expected:
                continue
            if item.get(key) != expected[key]:
                failures.append(f"{number} {key}: got {item.get(key)!r}, expected {expected[key]!r}")
    return failures


def main() -> int:
    arg_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    arg_parser.add_argument("paths", nargs="*", type=Path, help="emails/fixtures to run (default: saved samples)")
    arg_parser.add_argument("--tz", default="America/New_York", help="timezone for resolving 'today'/weekdays")
    arg_parser.add_argument("--all", action="store_true", help="also print the generic parser's hits")
    args = arg_parser.parse_args()

    paths = args.paths or sorted(p for pattern in DEFAULT_GLOBS for p in REPO_ROOT.glob(pattern))
    if not paths:
        print("No emails found.", file=sys.stderr)
        return 1

    parsers_list, delivery_date = load_package()
    tz = ZoneInfo(args.tz)
    checked = failed = 0

    for path in paths:
        data = load_email(path)
        results = run_email(data, parsers_list, delivery_date, tz)
        print(f"\n== {path.name}")
        print(f"   from: {data.get('from')}  date: {data.get('date')}")
        print(f"   subject: {data.get('subject')}")
        shown = [(a, i) for a, i in results if args.all or a != "generic"]
        if not shown:
            print("   (no parser matched)")
        for attr, item in shown:
            dates = ", ".join(f"{k}={item[k]}" for k in delivery_date.DELIVERY_DATE_KEYS if item.get(k))
            label = item.get("error") or item.get("tracking_number")
            order = f"  order={item['order_number']}" if item.get("order_number") else ""
            print(f"   [{attr}] {label}{order}" + (f"  ({dates})" if dates else ""))

        expected = data.get("expected")
        if expected is not None:
            checked += 1
            failures = check(expected, results)
            if failures:
                failed += 1
                for failure in failures:
                    print(f"   FAIL: {failure}")
            else:
                print("   OK")

    if checked:
        print(f"\n{checked - failed}/{checked} fixtures passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
