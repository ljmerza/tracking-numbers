import logging
import quopri
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, ups_regex


_LOGGER = logging.getLogger(__name__)
ATTR_HOUSE_OF_NOA = 'house_of_noa'
EMAIL_DOMAIN_HOUSE_OF_NOA = 'House of Noa'
_ORIGIN = 'House of Noa'

_UPS_FULL_MATCH = re.compile(ups_regex, re.IGNORECASE)
_UPS_INLINE_PATTERN = re.compile(r'\b1Z[A-Z0-9]{16}\b', re.IGNORECASE)
_TRACK_NUM_PARAM = re.compile(r'tracknums(?:=|%3D)([A-Z0-9]+)', re.IGNORECASE)


def parse_house_of_noa(email):
    """Parse House of Noa tracking numbers."""
    body = email.get(EMAIL_ATTR_BODY, '')
    tracking_numbers: list[dict[str, str]] = []
    seen: set[str] = set()

    if not body:
        _LOGGER.debug("[House of Noa] Empty email body; skipping parser")
        return tracking_numbers

    decoded_body = _qp_decode(body)
    soup = BeautifulSoup(decoded_body, 'html.parser')

    _LOGGER.debug("[House of Noa] Starting parser")

    # Extract tracking info from explicit UPS tracking links
    for anchor in soup.find_all('a', href=True):
        raw_href = anchor.get('href')
        href = _qp_decode(raw_href)
        if not href:
            continue

        match = _TRACK_NUM_PARAM.search(href)
        if not match:
            continue

        candidate = _normalize_tracking_number(match.group(1))
        if not candidate:
            continue

        _append_tracking(tracking_numbers, seen, candidate, link=href)

    # Fallback: scan the visible text for UPS tracking numbers
    plain_text = soup.get_text(" ", strip=True)
    for candidate in _UPS_INLINE_PATTERN.findall(plain_text):
        normalized = _normalize_tracking_number(candidate)
        if not normalized:
            continue
        _append_tracking(tracking_numbers, seen, normalized)

    _LOGGER.debug("[House of Noa] Parser complete - Found %d tracking number(s)", len(tracking_numbers))
    return tracking_numbers


def _append_tracking(tracking_numbers, seen, tracking_number, link=None):
    """Append a new tracking entry if it is unique."""
    if not tracking_number or tracking_number in seen:
        return

    seen.add(tracking_number)
    entry = {
        'tracking_number': tracking_number,
        'origin': _ORIGIN,
    }
    if link:
        entry['link'] = link
    tracking_numbers.append(entry)


def _normalize_tracking_number(value: str) -> str:
    """Return a cleaned tracking number if it matches a UPS format."""
    if not value:
        return ''

    decoded = _qp_decode(value)
    clean_value = re.sub(r'[^A-Za-z0-9]', '', decoded or '')
    normalized = clean_value.upper()

    if not normalized:
        return ''

    if _UPS_FULL_MATCH.fullmatch(normalized):
        return normalized

    return ''


def _qp_decode(value: str | None) -> str:
    """Decode quoted-printable fragments safely."""
    if not value:
        return ''

    decoded = quopri.decodestring(value)
    if isinstance(decoded, bytes):
        return decoded.decode('utf-8', errors='ignore')
    return decoded
