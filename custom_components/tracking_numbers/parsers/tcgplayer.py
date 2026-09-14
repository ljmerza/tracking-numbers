import logging
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    EMAIL_ATTR_SUBJECT,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
)


_LOGGER = logging.getLogger(__name__)
ATTR_TCGPLAYER = 'tcgplayer'
EMAIL_DOMAIN_TCGPLAYER = 'tcgplayer.com'

_TCGPLAYER_LINK_TEXT_RE = re.compile(r'Track\s+Your\s+Package\s*-+\s*([A-Z0-9]+)', re.IGNORECASE)
_TCGPLAYER_LINK_HREF_RE = re.compile(r'shipment\.co/track/([A-Z0-9]+)', re.IGNORECASE)
_TCGPLAYER_TEXT_RES = (
    re.compile(USPS_TRACKING_NUMBER_REGEX),
    re.compile(UPS_TRACKING_NUMBER_REGEX),
)


def parse_tcgplayer(email):
    """Parse TCGplayer tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[TCGplayer] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[TCGplayer] Empty email body received; skipping")
        return tracking_numbers

    def _add_tracking_number(number, link=None):
        number = number.strip()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        if link:
            entry['link'] = link
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[TCGplayer] Found tracking number: {number}")

    soup = BeautifulSoup(body, 'html.parser')

    # TCGplayer Direct: <a href="https://tcgp.shipment.co/track/<num>">Track Your Package -- <num></a>
    for link_element in soup.find_all('a'):
        href = (link_element.get('href') or '').strip()
        match = _TCGPLAYER_LINK_TEXT_RE.search(link_element.get_text(' ', strip=True))
        if not match:
            match = _TCGPLAYER_LINK_HREF_RE.search(href)
        if match:
            _add_tracking_number(match.group(1), href or None)

    # Fallback: bare USPS/UPS numbers in the body text
    if not tracking_numbers:
        text = soup.get_text(' ', strip=True)
        for regex in _TCGPLAYER_TEXT_RES:
            for match in regex.findall(text):
                _add_tracking_number(match)

    _LOGGER.debug(f"[TCGplayer] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
