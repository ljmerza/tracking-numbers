import logging
import quopri
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    FEDEX_TRACKING_NUMBER_REGEX,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
)


_LOGGER = logging.getLogger(__name__)
ATTR_THRIFT_BOOKS = 'thrift_books'
EMAIL_DOMAIN_THRIFT_BOOKS = 'thriftbooks'

track_copy_pattern = re.compile(r"track\s+(?:my\s+)?package", re.IGNORECASE)
order_number_patterns = (
    re.compile(r"Order\s*#\s*:?\s*(\d+)", re.IGNORECASE),
    re.compile(r"Order\s+Number\s*:?\s*#?\s*(\d+)", re.IGNORECASE),
)
tracking_regexes = (
    re.compile(USPS_TRACKING_NUMBER_REGEX),
    re.compile(UPS_TRACKING_NUMBER_REGEX),
    re.compile(FEDEX_TRACKING_NUMBER_REGEX),
)

def parse_thrift_books(email):
    """Parse thrift books tracking numbers."""
    body = email.get(EMAIL_ATTR_BODY, '')
    if not body:
        _LOGGER.debug("[Thriftbooks] Empty email body received; skipping")
        return []

    tracking_entries: list[dict] = []
    seen: set[str] = set()

    def _add_entry(number: str, link: str | None = None) -> None:
        normalized = number.strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        entry = {'tracking_number': normalized}
        if link:
            entry['link'] = link
        tracking_entries.append(entry)

    if '=\r' in body or '=\n' in body:
        decoded = quopri.decodestring(body)
        body = decoded.decode('utf-8', errors='ignore') if isinstance(decoded, bytes) else decoded

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(" ", strip=True)

    track_link: str | None = None
    track_link_priority = 99  # lower is better
    track_link_length = 0
    for element in soup.find_all('a'):
        raw_href = element.get('href')
        href = None
        if raw_href:
            href = raw_href.strip()
            if href.startswith('3D"') and href.endswith('"'):
                href = href[3:-1]
            href = href.replace('=\r\n', '').replace('=\n', '')
        if not href:
            continue
        anchor_text = element.get_text(" ", strip=True)
        lower_text = anchor_text.lower()
        lower_href = href.lower()
        if 'narvar.com' not in lower_href and 'spmailtechno' not in lower_href:
            continue

        priority = 3
        if track_copy_pattern.search(anchor_text):
            priority = 1
        elif 'track' in lower_text:
            priority = 2

        if (
            track_link is None
            or priority < track_link_priority
            or (priority == track_link_priority and len(href) > track_link_length)
        ):
            track_link = href
            track_link_priority = priority
            track_link_length = len(href)
            if priority == 1:
                break

    for regex in tracking_regexes:
        for match in regex.findall(text):
            if isinstance(match, tuple):
                match = next((m for m in match if m), '')
            _add_entry(match, track_link)

    order_numbers: set[str] = set()
    for pattern in order_number_patterns:
        for match in pattern.findall(text):
            order_numbers.add(match)

    if not order_numbers:
        for label in soup.find_all(string=re.compile(r"order\s*(?:number|#)", re.IGNORECASE)):
            neighbor = label.find_next(string=re.compile(r"\d{6,}"))
            if neighbor:
                order_numbers.add(neighbor.strip())

    for order_number in order_numbers:
        _add_entry(order_number, track_link)

    _LOGGER.debug(f"[Thriftbooks] Parser complete - Found {len(tracking_entries)} tracking number(s)")
    return tracking_entries
