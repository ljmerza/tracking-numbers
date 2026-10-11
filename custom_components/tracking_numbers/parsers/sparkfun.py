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
ATTR_SPARKFUN = 'sparkfun'
EMAIL_DOMAIN_SPARKFUN = 'sparkfun.com'

_SPARKFUN_SHIPPED_RE = re.compile(r'has\s+shipped|ship\s+notification|ready\s+to\s+ship', re.IGNORECASE)
_SPARKFUN_LABEL_RE = re.compile(r'Tracking\s+Number', re.IGNORECASE)
# Generic carrier number (e.g. FedEx SmartPost) following the "Tracking Number" label; must contain a digit
_SPARKFUN_GENERIC_RE = re.compile(r'\b(?=[A-Z0-9]*\d)[A-Z0-9]{12,34}\b')
_SPARKFUN_TEXT_RES = (
    re.compile(UPS_TRACKING_NUMBER_REGEX),
    re.compile(USPS_TRACKING_NUMBER_REGEX),
)


def parse_sparkfun(email):
    """Parse SparkFun tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[SparkFun] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[SparkFun] Empty email body received; skipping")
        return tracking_numbers

    if not _SPARKFUN_SHIPPED_RE.search(subject):
        _LOGGER.debug("[SparkFun] Subject doesn't match shipping email pattern; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True)

    def _find_link(number):
        """Prefer the anchor wrapping the number, else a tracking-looking anchor."""
        fallback = None
        for link_element in soup.find_all('a', href=True):
            href = link_element['href'].strip()
            if not href.lower().startswith('http'):
                continue
            if number in link_element.get_text(' ', strip=True) or number in href:
                return href
            if fallback is None and 'tracking' in href.lower():
                fallback = href
        return fallback

    def _add_tracking_number(number):
        number = number.strip()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        link = _find_link(number)
        if link:
            entry['link'] = link
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[SparkFun] Found tracking number: {number}")

    # Known carrier formats anywhere in the body (UPS, USPS)
    for regex in _SPARKFUN_TEXT_RES:
        for match in regex.findall(text):
            _add_tracking_number(match)

    # Other carriers (e.g. FedEx SmartPost): first long number after the "Tracking Number" label
    if not tracking_numbers:
        label = _SPARKFUN_LABEL_RE.search(text)
        if label:
            match = _SPARKFUN_GENERIC_RE.search(text, label.end())
            if match:
                _add_tracking_number(match.group(0))

    _LOGGER.debug(f"[SparkFun] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
