import logging
import quopri
import re
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_DSW = 'DSW'
EMAIL_DOMAIN_DSW = 'dsw.com'

TRACKING_PARAM_RE = re.compile(
    r'tracking_numbers(?:=|%3[dD])([^&"\'>\\s]+)',
    re.IGNORECASE,
)

_CARRIER_MAP = {
    'FEDEX': 'FedEx',
    'UPS': 'UPS',
    'USPS': 'USPS',
}


def parse_dsw(email):
    """Parse DSW tracking numbers."""
    body = email.get(EMAIL_ATTR_BODY, '') or ''
    tracking_entries: list[dict] = []
    seen_numbers: set[str] = set()

    if not body:
        _LOGGER.debug("[Dsw] Empty email body received; skipping")
        return tracking_entries

    try:
        decoded_bytes = quopri.decodestring(body.encode('utf-8', errors='ignore'))
        decoded_body = decoded_bytes.decode('utf-8', errors='replace')
    except Exception as err:  # pragma: no cover - defensive
        _LOGGER.debug("[Dsw] Failed to decode body as quoted-printable: %s", err)
        decoded_body = body

    soup = BeautifulSoup(decoded_body, 'html.parser')

    def _add_tracking_number(number: str, link: str | None = None, carrier: str | None = None) -> None:
        tracking_number = (number or '').strip()
        if not tracking_number or tracking_number in seen_numbers:
            return

        seen_numbers.add(tracking_number)
        entry = {'tracking_number': tracking_number}
        if link:
            entry['link'] = link
        if carrier:
            entry['carrier'] = carrier
        tracking_entries.append(entry)

    # Extract tracking info from anchor tags first
    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        if not href or 'tracking_numbers' not in href.lower():
            continue

        decoded_href = unquote(href)
        parsed = urlparse(decoded_href)
        params = parse_qs(parsed.query)
        candidates = params.get('tracking_numbers') or []

        carrier = None
        path_parts = [part for part in parsed.path.split('/') if part]
        if len(path_parts) >= 2 and path_parts[0].lower() == 'ftracking':
            carrier_code = path_parts[1].upper()
            carrier = _CARRIER_MAP.get(carrier_code, carrier_code.title())

        canonical_link = decoded_href
        for candidate in candidates:
            _add_tracking_number(candidate, canonical_link, carrier)

    # Fallback: scan body for tracking_numbers parameter
    if not tracking_entries:
        for match in TRACKING_PARAM_RE.findall(decoded_body):
            _add_tracking_number(match)

    _LOGGER.debug("[Dsw] Parser complete - Found %d tracking number(s)", len(tracking_entries))
    return tracking_entries
