import logging
import quopri
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_COSTWAY = 'costway'
EMAIL_DOMAIN_COSTWAY = 'costway.com'

_COSTWAY_TRACKING_RE = re.compile(
    r'Tracking\s*Number:\s*([A-Z0-9]{8,})',
    re.IGNORECASE,
)


def parse_costway(email):
    """Parse Costway shipment notification tracking numbers."""
    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    raw_body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Costway] Starting parser - Subject: {subject}")

    if not raw_body:
        _LOGGER.debug("[Costway] Empty email body; skipping")
        return []

    decoded_body = raw_body
    if '=\r' in raw_body or '=\n' in raw_body:
        decoded = quopri.decodestring(raw_body)
        decoded_body = decoded.decode('utf-8', errors='ignore') if isinstance(decoded, bytes) else decoded

    text = BeautifulSoup(decoded_body, 'html.parser').get_text(' ', strip=True)

    tracking_numbers: list[str] = []
    for match in _COSTWAY_TRACKING_RE.finditer(text):
        tracking_num = match.group(1)
        if tracking_num not in tracking_numbers:
            _LOGGER.debug(f"[Costway] Found tracking number: {tracking_num}")
            tracking_numbers.append(tracking_num)
        else:
            _LOGGER.debug(f"[Costway] Skipping duplicate tracking number: {tracking_num}")

    _LOGGER.debug(f"[Costway] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
