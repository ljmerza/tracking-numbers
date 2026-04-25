import logging
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_MIXBOOK = 'mixbook'
EMAIL_DOMAIN_MIXBOOK = 'mixbook.com'

_SHIPMENT_LINK_RE = re.compile(
    r'https?://(?:www\.)?mixbook\.com/my/shipments/[^"\'\s<>]+',
    re.IGNORECASE,
)
_ORDER_IN_SUBJECT_RE = re.compile(r'order\s*#\s*(\d+)', re.IGNORECASE)


def parse_mixbook(email):
    """Parse Mixbook order shipment notifications.

    Mixbook ships the carrier tracking number only in the text/plain MIME part,
    which the coordinator drops when an HTML alternative exists. We surface the
    order number plus the tokenized Mixbook tracking URL — clicking it
    redirects to the underlying carrier's tracker.
    """
    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Mixbook] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Mixbook] Empty email body; skipping")
        return []

    soup = BeautifulSoup(body, 'html.parser')

    shipment_link = None
    for a in soup.find_all('a', href=True):
        href = a['href']
        if _SHIPMENT_LINK_RE.match(href):
            shipment_link = href
            break

    if not shipment_link:
        match = _SHIPMENT_LINK_RE.search(body)
        if match:
            shipment_link = match.group(0)

    if not shipment_link:
        _LOGGER.debug("[Mixbook] No shipment tracking link found")
        return []

    order_number = None
    for a in soup.find_all('a', href=True):
        qs = parse_qs(urlparse(a['href']).query)
        oid = (qs.get('oid') or [''])[0].strip()
        if oid:
            order_number = oid
            break

    if not order_number:
        m = _ORDER_IN_SUBJECT_RE.search(subject)
        if m:
            order_number = m.group(1)

    if not order_number:
        _LOGGER.debug("[Mixbook] No order number found; skipping")
        return []

    _LOGGER.debug(f"[Mixbook] Found order number: {order_number}, link: {shipment_link}")
    _LOGGER.debug("[Mixbook] Parser complete - Found 1 tracking number(s)")

    return [{
        'tracking_number': order_number,
        'link': shipment_link,
        'carrier': 'Mixbook',
    }]
