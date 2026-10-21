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
ATTR_STRIDE_RITE = 'stride_rite'
EMAIL_DOMAIN_STRIDE_RITE = 'striderite.com'

# Shopify shipping template: "UPS tracking number: <a href=...>1Z...</a>"
_STRIDE_RITE_TRACKING_RE = re.compile(r'\b(UPS|USPS|FedEx|DHL)\s+tracking\s+number:?\s*((?=[A-Z]*\d)[A-Z0-9]{8,})', re.IGNORECASE)
_STRIDE_RITE_ORDER_RE = re.compile(r'\border\s+#?(SR\d+)\b', re.IGNORECASE)
_STRIDE_RITE_VIEW_ORDER_RE = re.compile(r'view\s+your\s+order', re.IGNORECASE)
_STRIDE_RITE_CARRIERS = {'ups': 'UPS', 'usps': 'USPS', 'fedex': 'FedEx', 'dhl': 'DHL'}
_STRIDE_RITE_TEXT_RES = (
    re.compile(UPS_TRACKING_NUMBER_REGEX),
    re.compile(USPS_TRACKING_NUMBER_REGEX),
)


def parse_stride_rite(email):
    """Parse Stride Rite tracking numbers along with the order they belong to."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[Stride Rite] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Stride Rite] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True)

    order_number = None
    match = _STRIDE_RITE_ORDER_RE.search(subject or '') or _STRIDE_RITE_ORDER_RE.search(text)
    if match:
        order_number = match.group(1).upper()
        _LOGGER.debug(f"[Stride Rite] Found order number: {order_number}")

    order_link = None
    for link_element in soup.find_all('a'):
        href = (link_element.get('href') or '').strip()
        if href and _STRIDE_RITE_VIEW_ORDER_RE.search(link_element.get_text(' ', strip=True)):
            order_link = href
            break

    def _add_tracking_number(number, carrier=None):
        number = number.strip().upper()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        # No tracking link: the email's link is a striderite.com click-tracking
        # redirect, so the carrier link is built from the number instead.
        entry = {'tracking_number': number}
        if carrier:
            entry['carrier'] = carrier
        if order_number:
            entry['order_number'] = order_number
            if order_link:
                entry['order_link'] = order_link
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[Stride Rite] Found tracking number: {number}")

    for match in _STRIDE_RITE_TRACKING_RE.finditer(text):
        _add_tracking_number(match.group(2), _STRIDE_RITE_CARRIERS.get(match.group(1).lower()))

    # Fallback: bare UPS/USPS numbers in the body text
    if not tracking_numbers:
        for regex in _STRIDE_RITE_TEXT_RES:
            for match in regex.findall(text):
                _add_tracking_number(match)

    _LOGGER.debug(f"[Stride Rite] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
