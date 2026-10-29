import logging
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    EMAIL_ATTR_SUBJECT,
    TRACKING_NUMBER_URLS,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
)


_LOGGER = logging.getLogger(__name__)
ATTR_SMARTWINGS = 'smartwings'
EMAIL_DOMAIN_SMARTWINGS = 'smartwingshome.com'

# Shopify template: "UPS® tracking number: 1Z..." (number is usually wrapped in a link)
_LABELED_TRACKING_RE = re.compile(
    r'tracking\s+number\s*[:\-]?\s*([A-Z0-9]{10,})',
    re.IGNORECASE,
)
_UPS_RE = re.compile(UPS_TRACKING_NUMBER_REGEX)
_USPS_RE = re.compile(USPS_TRACKING_NUMBER_REGEX)
# "Order #138440" in the subject and header of every Shopify email
_ORDER_RE = re.compile(r'\border\s+#\s*(\d+)\b', re.IGNORECASE)
# "Order #138440 confirmed" / "Thank you for your order!"
_CONFIRMED_RE = re.compile(r'\border\s+#\s*\d+\s+confirmed\b|thank\s+you\s+for\s+your\s+order', re.IGNORECASE)
# The email's "View your order" link is a click-tracking redirect to a URL with an
# auth key, so link to the account's order list instead.
_ORDER_LINK = 'https://www.smartwingshome.com/account'


def parse_smartwings(email):
    """Parse SmartWings (Shopify) shipment notifications.

    Handles both "A shipment from order #N is on the way" and "... has been
    delivered" emails, which carry ``UPS® tracking number: 1Z...``. Order
    confirmation emails carry no tracking number and yield an order-only entry
    (``tracking_number == order_number``) until the shipment email arrives.
    """
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A') or 'N/A'
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[SmartWings] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[SmartWings] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True)

    order_number = None
    match = _ORDER_RE.search(subject) or _ORDER_RE.search(text)
    if match:
        order_number = match.group(1)
        _LOGGER.debug(f"[SmartWings] Found order number: {order_number}")

    def _add_tracking_number(number):
        number = number.strip().upper()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        if _UPS_RE.fullmatch(number):
            entry['link'] = f"{TRACKING_NUMBER_URLS['ups']}{number}"
        elif _USPS_RE.fullmatch(number):
            entry['link'] = f"{TRACKING_NUMBER_URLS['usps']}{number}"
        if order_number:
            entry['order_number'] = order_number
            entry['order_link'] = _ORDER_LINK
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[SmartWings] Found tracking number: {number}")

    for match in _LABELED_TRACKING_RE.finditer(text):
        candidate = match.group(1)
        # Only accept values that contain a digit (ignores prose like "tracking number information")
        if any(c.isdigit() for c in candidate):
            _add_tracking_number(candidate)

    # Fallback: bare UPS numbers anywhere in the text
    if not tracking_numbers:
        for number in _UPS_RE.findall(text):
            _add_tracking_number(number)

    # Order confirmation: no tracking number yet, so track the order itself
    if not tracking_numbers and order_number and (
        _CONFIRMED_RE.search(subject) or _CONFIRMED_RE.search(text)
    ):
        _add_tracking_number(order_number)

    _LOGGER.debug(f"[SmartWings] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
