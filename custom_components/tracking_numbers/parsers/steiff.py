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
ATTR_STEIFF = 'steiff'
EMAIL_DOMAIN_STEIFF = 'steiff.com'

_STEIFF_SHIPPED_RE = re.compile(r'on\s+the\s+way|has\s+shipped', re.IGNORECASE)
_STEIFF_FORWARDED_RE = re.compile(r'forwarded\s+to\s+our\s+shipping', re.IGNORECASE)
# Carrier tracking pages, e.g. tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=<number>
_STEIFF_HREF_RE = re.compile(r'(?:qtc_tLabels1|tracknumbers|tracknum|trknbr|tLabels)=([A-Z0-9]+)', re.IGNORECASE)
_STEIFF_CARRIER_LINK_RE = re.compile(r'usps\.com|ups\.com|fedex\.com|track', re.IGNORECASE)
_STEIFF_ORDER_RE = re.compile(r'Your\s+order\s+#?\s*(\d{8,})', re.IGNORECASE)
_STEIFF_TEXT_RES = (
    re.compile(USPS_TRACKING_NUMBER_REGEX),
    re.compile(UPS_TRACKING_NUMBER_REGEX),
)


def parse_steiff(email):
    """Parse Steiff tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[Steiff] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Steiff] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True)

    if not (_STEIFF_SHIPPED_RE.search(subject) or _STEIFF_FORWARDED_RE.search(text)):
        _LOGGER.debug("[Steiff] Not a shipping email; skipping")
        return tracking_numbers

    def _add_tracking_number(number, link=None):
        number = number.strip()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        if link:
            entry['link'] = link
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[Steiff] Found tracking number: {number}")

    carrier_links = []
    for link_element in soup.find_all('a', href=True):
        href = link_element['href'].strip()
        match = _STEIFF_HREF_RE.search(href)
        if match:
            _add_tracking_number(match.group(1), href)
        elif _STEIFF_CARRIER_LINK_RE.search(href):
            carrier_links.append(href)

    # Bare USPS/UPS numbers in the body text
    if not tracking_numbers:
        for regex in _STEIFF_TEXT_RES:
            for match in regex.findall(text):
                _add_tracking_number(match, carrier_links[0] if carrier_links else None)

    # No carrier number, only a tracking link: fall back to the order number
    if not tracking_numbers and carrier_links:
        order_match = _STEIFF_ORDER_RE.search(text)
        if order_match:
            _add_tracking_number(order_match.group(1), carrier_links[0])

    _LOGGER.debug(f"[Steiff] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
