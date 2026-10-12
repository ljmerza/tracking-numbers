"""Shared delivery-date extraction for shipping emails.

Parsers may set `estimated_delivery` / `delivered_date` (YYYY-MM-DD) on the
dicts they return. For everything else the coordinator falls back to
`extract_delivery_dates`, which scans the subject and body text for common
phrasings ("Arriving Thursday", "Expected Delivery by ...", "Delivered:") and
resolves them against the email's send date.
"""
import logging
import re
from datetime import date, datetime, timedelta, timezone, tzinfo

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_DATE, EMAIL_ATTR_SUBJECT

_LOGGER = logging.getLogger(__name__)

ATTR_ESTIMATED_DELIVERY = 'estimated_delivery'
ATTR_DELIVERED_DATE = 'delivered_date'
DELIVERY_DATE_KEYS = (ATTR_ESTIMATED_DELIVERY, ATTR_DELIVERED_DATE)

_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
_WEEKDAYS = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
}

_MONTH_RE = (
    r'(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|'
    r'aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?'
)
_WEEKDAY_RE = r'(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
_WEEKDAY_PREFIX_RE = r'(?:(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?,?\s+)?'

# One date expression. Named groups tell _resolve which form matched.
_DATE_RE = (
    r'(?:'
    + _WEEKDAY_PREFIX_RE + _MONTH_RE + r'\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(?P<year>\d{4}))?'
    + r'|' + _WEEKDAY_PREFIX_RE + r'(?P<num_month>\d{1,2})/(?P<num_day>\d{1,2})(?:/(?P<num_year>\d{4}|\d{2}))?\b'
    + r'|(?P<relative>today|tonight|tomorrow|overnight)'
    + r'|' + _WEEKDAY_RE
    + r')'
)
_DATE_PATTERN = re.compile(_DATE_RE, re.IGNORECASE)

# Phrases that introduce an expected delivery date; the date must follow
# within a short window.
_ESTIMATE_PHRASES = re.compile(
    r'(?:estimated|expected|scheduled|anticipated|projected|new)\s+(?:delivery|arrival)(?:\s+date)?'
    r'|delivery\s+(?:date|estimate|expected|by)'
    r'|arriv(?:ing|es|e)(?:\s+(?:on|by))?'
    r'|(?:will|should|expected\s+to)\s+(?:arrive|be\s+delivered)'
    r'|expects?\s+to\s+deliver(?:\s+your\s+(?:package|item))?'
    r'|get\s+it\s+(?:by|on)',
    re.IGNORECASE,
)

# "Out for delivery" as a status statement means today. A bare label isn't
# enough: Amazon's progress bar reads "Ordered Shipped Out for delivery Delivered"
# on every shipping email.
_OUT_FOR_DELIVERY = re.compile(
    r'(?:is|are|now)\s+out\s+for\s+delivery|^out\s+for\s+delivery\b',
    re.IGNORECASE | re.MULTILINE,
)

# Phrases that mean the package already arrived.
_DELIVERED_PHRASES = re.compile(
    r'(?:was|has\s+been|have\s+been|were|is|got)\s+delivered'
    r'|^delivered\b'
    r'|\b(?:we|carrier)\s+delivered'
    r'|\b(?:order|just)\s+delivered\b'
    r'|\b(?:order|package|parcel|item)\s+has\s+arrived\b(?!\s+(?:at|in)\b)'  # not "arrived at the Post Office"
    r'|\bdropped\s+off\s+on\b'
    r'|\bdelivered\s+(?:on|at)\b',
    re.IGNORECASE | re.MULTILINE,
)
# "will be delivered on Friday" is a promise, not a delivery.
_FUTURE_BEFORE = re.compile(r'\b(?:will|to|should|may|can)\s+be\s+$', re.IGNORECASE)

# "Estimated to arrive in 1-3 days" -> send date + upper bound.
_IN_DAYS = re.compile(
    r'\bin\s+(?P<low>\d{1,2})(?:\s*(?:-|–|to)\s*(?P<high>\d{1,2}))?\s+(?P<business>business\s+)?days?\b',
    re.IGNORECASE,
)

# How far past a phrase its date may start.
_PHRASE_WINDOW = 40
# Year inference: a month/day without a year further than this in the past is
# taken to be next year (December email, January delivery).
_YEAR_ROLLOVER_DAYS = 180

_INVISIBLE_RE = re.compile('[­͏​-‏⁠-⁩﻿]')


def _email_text(email) -> str:
    """Subject plus visible body text, whitespace-collapsed."""
    subject = email.get(EMAIL_ATTR_SUBJECT) or ''
    body = email.get(EMAIL_ATTR_BODY) or ''
    body_text = BeautifulSoup(body, 'html.parser').get_text(' ', strip=True)
    text = f"{subject}\n{body_text}"
    text = _INVISIBLE_RE.sub('', text)
    return re.sub(r'[ \t\r\f\v\xa0]+', ' ', text)


def _reference_date(email, tz: tzinfo | None) -> date:
    """The email's send date in the user's timezone (falls back to today)."""
    raw = email.get(EMAIL_ATTR_DATE)
    sent = None
    if isinstance(raw, datetime):
        sent = raw
    elif isinstance(raw, str) and raw:
        try:
            sent = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            sent = None
    if sent is None:
        return date.today()
    if sent.tzinfo is None:
        # The coordinator stores email timestamps as naive UTC.
        sent = sent.replace(tzinfo=timezone.utc)
    if tz is not None:
        sent = sent.astimezone(tz)
    return sent.date()


def _resolve(match: re.Match, reference: date, *, past: bool) -> date | None:
    """Turn one _DATE_PATTERN match into a calendar date."""
    groups = match.groupdict()
    try:
        if groups.get('month'):
            month = _MONTHS[groups['month'][:3].lower()]
            day = int(groups['day'])
            year = int(groups['year']) if groups.get('year') else None
        elif groups.get('num_month'):
            month = int(groups['num_month'])
            day = int(groups['num_day'])
            year = groups.get('num_year')
            if year:
                year = int(year)
                if year < 100:
                    year += 2000
        elif groups.get('relative'):
            offset = 1 if groups['relative'].lower() in ('tomorrow', 'overnight') else 0
            return reference + timedelta(days=offset)
        elif groups.get('weekday'):
            target = _WEEKDAYS[groups['weekday'].lower()]
            if past:
                return reference - timedelta(days=(reference.weekday() - target) % 7)
            return reference + timedelta(days=(target - reference.weekday()) % 7)
        else:
            return None

        if year is not None:
            return date(year, month, day)
        resolved = date(reference.year, month, day)
        if not past and (reference - resolved).days > _YEAR_ROLLOVER_DAYS:
            resolved = date(reference.year + 1, month, day)
        elif past and (resolved - reference).days > _YEAR_ROLLOVER_DAYS:
            resolved = date(reference.year - 1, month, day)
        return resolved
    except (ValueError, KeyError):
        return None


def _add_days(reference: date, days: int, *, business: bool) -> date:
    """reference + days, skipping weekends for business days."""
    if not business:
        return reference + timedelta(days=days)
    current = reference
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def _date_after(text: str, start: int, reference: date, *, past: bool) -> date | None:
    """First date starting within the window after `start`; for a range, its later end."""
    window = text[start:start + _PHRASE_WINDOW]
    match = _DATE_PATTERN.search(window)
    if not match:
        in_days = None if past else _IN_DAYS.search(window)
        if in_days:
            return _add_days(reference, int(in_days.group('high') or in_days.group('low')),
                             business=bool(in_days.group('business')))
        return None
    resolved = _resolve(match, reference, past=past)
    if resolved is None:
        return None

    # "Oct 14 - Oct 17" / "Oct 5-13" / "Between Thu, Oct 29 and Fri, Oct 30":
    # take the later end, which may run past the window.
    rest = text[start + match.end():start + match.end() + _PHRASE_WINDOW]
    range_match = re.match(r'\s*(?:-|–|—|to|and)\s*', rest, re.IGNORECASE)
    if range_match:
        rest = rest[range_match.end():]
        end_match = _DATE_PATTERN.match(rest)
        if end_match:
            end = _resolve(end_match, reference, past=past)
        else:
            day_only = re.match(r'(\d{1,2})(?:st|nd|rd|th)?\b', rest)
            end = None
            if day_only:
                try:
                    end = resolved.replace(day=int(day_only.group(1)))
                except ValueError:
                    end = None
        if end and end > resolved:
            resolved = end
    return resolved


def extract_delivery_dates(email, tz: tzinfo | None = None) -> dict[str, str]:
    """Return the delivery dates an email mentions, as YYYY-MM-DD strings.

    Keys are only present when found: `estimated_delivery` and/or
    `delivered_date`. `tz` is the user's timezone, used to resolve relative
    words ("today", "Thursday") against the send date.
    """
    try:
        text = _email_text(email)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.debug("[DeliveryDate] Could not read email text: %s", err)
        return {}

    reference = _reference_date(email, tz)
    found: dict[str, str] = {}

    for match in _DELIVERED_PHRASES.finditer(text):
        if _FUTURE_BEFORE.search(text[max(0, match.start() - 20):match.start()]):
            continue
        delivered = _date_after(text, match.end(), reference, past=True)
        if delivered is None or delivered > reference:
            delivered = reference
        found[ATTR_DELIVERED_DATE] = delivered.isoformat()
        break

    for match in _ESTIMATE_PHRASES.finditer(text):
        estimate = _date_after(text, match.end(), reference, past=False)
        if estimate is None:
            continue
        found[ATTR_ESTIMATED_DELIVERY] = estimate.isoformat()
        break
    else:
        if _OUT_FOR_DELIVERY.search(text):
            found[ATTR_ESTIMATED_DELIVERY] = reference.isoformat()

    if found:
        _LOGGER.debug("[DeliveryDate] Found %s", found)
    return found


def apply_delivery_dates(items: list[dict], dates: dict[str, str]) -> list[dict]:
    """Fill email-level dates onto parser results that didn't set their own."""
    if not dates:
        return items
    for item in items:
        for key in DELIVERY_DATE_KEYS:
            if dates.get(key) and not item.get(key):
                item[key] = dates[key]
    return items
