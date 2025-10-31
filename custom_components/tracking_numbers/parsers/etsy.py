import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT

_LOGGER = logging.getLogger(__name__)
ATTR_ETSY = 'etsy'
EMAIL_DOMAIN_ETSY = 'account.etsy.com'

TRACK_LINK_TEXT_PATTERN = re.compile(r'track\s+package', re.IGNORECASE)
ORDER_NUMBER_PATTERN = re.compile(r'#\s*(\d+)', re.IGNORECASE)


def _normalize_link(raw_link: str) -> str:
    """Clean up quoted-printable artifacts and whitespace in URLs."""
    link = raw_link.replace('=\n', '').replace('=3D', '=')
    return re.sub(r'\s+', '', link.strip())


def parse_etsy(email):
    """Parse Etsy shipping emails for order tracking."""
    tracking_numbers = []

    subject = email.get(EMAIL_ATTR_SUBJECT, '')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug("[Etsy] Starting parser - Subject: %s", subject)

    soup = BeautifulSoup(body, 'html.parser')

    # Attempt to locate order number from subject or body content
    order_number = None
    subject_match = re.search(ORDER_NUMBER_PATTERN, subject)
    if subject_match:
        order_number = subject_match.group(1)
        _LOGGER.debug("[Etsy] Found order number in subject: %s", order_number)

    if not order_number:
        body_text = soup.get_text(" ", strip=True)
        body_match = re.search(ORDER_NUMBER_PATTERN, body_text)
        if body_match:
            order_number = body_match.group(1)
            _LOGGER.debug("[Etsy] Found order number in body: %s", order_number)

    if not order_number:
        _LOGGER.debug("[Etsy] No order number found; aborting parser")
        return tracking_numbers

    # Find the primary tracking link
    tracking_link = None
    for anchor in soup.find_all('a'):
        anchor_text = (anchor.get_text() or '').strip()
        if re.search(TRACK_LINK_TEXT_PATTERN, anchor_text):
            tracking_link = anchor.get('href')
            if tracking_link:
                tracking_link = _normalize_link(tracking_link)
                _LOGGER.debug("[Etsy] Found tracking link: %s", tracking_link)
                break

    if not tracking_link:
        _LOGGER.debug("[Etsy] No tracking link found; aborting parser")
        return tracking_numbers

    tracking_numbers.append({
        'tracking_number': order_number,
        'link': tracking_link,
    })

    _LOGGER.debug("[Etsy] Parser complete - Found %d tracking number(s)", len(tracking_numbers))
    return tracking_numbers
