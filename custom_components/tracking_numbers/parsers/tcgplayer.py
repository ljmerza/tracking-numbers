import logging
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    EMAIL_ATTR_SUBJECT,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
    ups_regex,
    usps_regex,
)


_LOGGER = logging.getLogger(__name__)
ATTR_TCGPLAYER = 'tcgplayer'
EMAIL_DOMAIN_TCGPLAYER = 'tcgplayer.com'

_TCGPLAYER_LINK_TEXT_RE = re.compile(r'Track\s+Your\s+Package\s*-+\s*([A-Z0-9]+)', re.IGNORECASE)
_TCGPLAYER_LINK_HREF_RE = re.compile(r'shipment\.co/track/([A-Z0-9]+)', re.IGNORECASE)
_TCGPLAYER_SHIPPED_RE = re.compile(r'has\s+shipped', re.IGNORECASE)
_TCGPLAYER_ORDER_HREF_RE = re.compile(r'orderhistory\?SearchString=([A-Z0-9-]+)', re.IGNORECASE)
_TCGPLAYER_ORDER_TEXT_RE = re.compile(r'Order(?:\s+Number)?:\s*([A-Z0-9]+(?:-[A-Z0-9]+)+)', re.IGNORECASE)
_TCGPLAYER_ORDER_LINK = 'https://store.tcgplayer.com/myaccount/orderhistory?SearchString='
_TCGPLAYER_TEXT_RES = (
    re.compile(USPS_TRACKING_NUMBER_REGEX),
    re.compile(UPS_TRACKING_NUMBER_REGEX),
)
# Same carrier patterns find_carrier() uses to build a carrier tracking link
_TCGPLAYER_CARRIER_RES = (re.compile(usps_regex), re.compile(ups_regex))


def parse_tcgplayer(email):
    """Parse TCGplayer tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[TCGplayer] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[TCGplayer] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')

    # Order the shipment belongs to: the order-history link, else "Order Number: X"
    order_number = None
    order_link = None
    for link_element in soup.find_all('a'):
        href = (link_element.get('href') or '').strip()
        match = _TCGPLAYER_ORDER_HREF_RE.search(href)
        if match:
            order_number = match.group(1)
            order_link = href
            break
    if not order_number:
        match = _TCGPLAYER_ORDER_TEXT_RE.search(subject or '') or _TCGPLAYER_ORDER_TEXT_RE.search(
            soup.get_text(' ', strip=True)
        )
        if match:
            order_number = match.group(1)
            order_link = f'{_TCGPLAYER_ORDER_LINK}{order_number}'
    if order_number:
        _LOGGER.debug(f"[TCGplayer] Found order number: {order_number}")

    def _add_tracking_number(number, link=None, order=None, order_href=None):
        number = number.strip()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        if link:
            entry['link'] = link
        order = order or order_number
        if order:
            entry['order_number'] = order
            entry['order_link'] = order_href or order_link or f'{_TCGPLAYER_ORDER_LINK}{order}'
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[TCGplayer] Found tracking number: {number}")

    # TCGplayer Direct: <a href="https://tcgp.shipment.co/track/<num>">Track Your Package -- <num></a>
    for link_element in soup.find_all('a'):
        href = (link_element.get('href') or '').strip()
        match = _TCGPLAYER_LINK_TEXT_RE.search(link_element.get_text(' ', strip=True))
        if not match:
            match = _TCGPLAYER_LINK_HREF_RE.search(href)
        if match:
            number = match.group(1)
            # USPS/UPS numbers get the carrier's own tracking page (built from the
            # number); keep TCGplayer's shipment.co tracker for anything else.
            if any(regex.search(number.upper()) for regex in _TCGPLAYER_CARRIER_RES):
                _add_tracking_number(number)
            else:
                _add_tracking_number(number, href or None)

    # Fallback: bare USPS/UPS numbers in the body text
    if not tracking_numbers:
        text = soup.get_text(' ', strip=True)
        for regex in _TCGPLAYER_TEXT_RES:
            for match in regex.findall(text):
                _add_tracking_number(match)

    # Seller-shipped orders ("shipped ... without Delivery Confirmation") carry no tracking
    # number; fall back to the seller order number and link to the order history.
    if not tracking_numbers and _TCGPLAYER_SHIPPED_RE.search(subject):
        for link_element in soup.find_all('a'):
            href = (link_element.get('href') or '').strip()
            match = _TCGPLAYER_ORDER_HREF_RE.search(href)
            if match:
                _add_tracking_number(match.group(1), href, match.group(1), href)

    _LOGGER.debug(f"[TCGplayer] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
