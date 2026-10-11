import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT, TRACKING_NUMBER_URLS, ups_regex, usps_regex


_LOGGER = logging.getLogger(__name__)
ATTR_INOVELLI = 'inovelli'
EMAIL_DOMAIN_INOVELLI = 'inovelli.com'

_LABELED_TRACKING_RE = re.compile(
    r'(UPS|FedEx|USPS|DHL)\s+tracking\s+number\s*[:\-]?\s*([A-Z0-9]{10,})',
    re.IGNORECASE,
)


def parse_inovelli(email):
    """Parse Inovelli order shipment notifications.

    Inovelli ships via Shopify; the HTML body the coordinator passes shows the
    USPS tracking number as ``USPS tracking number: <a ...>9400...</a>`` (the
    number wrapped in a Shopify redirect link). We surface the USPS tracking
    number with a canonical USPS tracking link.
    """
    tracking_numbers = []

    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Inovelli] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Inovelli] Empty email body; skipping")
        return []

    soup = BeautifulSoup(body, 'html.parser')

    seen = set()

    def _add(num, carrier='usps'):
        num = num.upper()
        if num in seen:
            return
        seen.add(num)
        _LOGGER.debug(f"[Inovelli] Found tracking number: {num}")
        tracking_numbers.append({
            'tracking_number': num,
            'carrier': carrier.upper(),
            'link': f"{TRACKING_NUMBER_URLS[carrier]}{num}",
        })

    # Primary: the tracking number is the visible text of an <a> (the Shopify
    # redirect link wrapping it). Match it against the shared USPS pattern.
    for a in soup.find_all('a'):
        candidate = a.get_text(strip=True)
        if candidate and re.fullmatch(usps_regex, candidate):
            _add(candidate)
        elif candidate and re.fullmatch(ups_regex, candidate):
            # Multi-item orders can ship via UPS ("UPS tracking number: 1Z...").
            _add(candidate, 'ups')

    # Fallback: labeled "USPS tracking number: <num>" in the de-tagged text.
    if not tracking_numbers:
        for match in _LABELED_TRACKING_RE.finditer(soup.get_text(' ')):
            carrier = match.group(1).lower()
            _add(match.group(2), carrier if carrier in ('ups', 'usps', 'fedex', 'dhl') else 'usps')

    _LOGGER.debug(
        f"[Inovelli] Parser complete - Found {len(tracking_numbers)} tracking number(s)"
    )
    return tracking_numbers
