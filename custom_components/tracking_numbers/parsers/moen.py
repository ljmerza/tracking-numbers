import logging
import quopri
import re

from bs4 import BeautifulSoup

from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_MOEN = 'moen'
EMAIL_DOMAIN_MOEN = 'moen.com'


def _decode_body(raw_body):
    """Decode quoted-printable Moen emails to plain HTML."""
    if raw_body is None:
        return ''

    if isinstance(raw_body, bytes):
        raw_bytes = raw_body
    else:
        raw_bytes = raw_body.encode('utf-8', errors='ignore')

    decoded = quopri.decodestring(raw_bytes)
    decoded_text = decoded.decode('utf-8', errors='ignore')
    if decoded_text.strip():
        return decoded_text

    if isinstance(raw_body, str):
        return raw_body

    return raw_body.decode('utf-8', errors='ignore')


def parse_moen(email):
    """Parse Moen tracking emails."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')

    _LOGGER.debug(f"[Moen] Starting parser - Subject: {subject}")

    order_match = re.search(r'order\s*(\d+)', subject, re.IGNORECASE)
    if not order_match:
        _LOGGER.debug("[Moen] No order number found in subject line")
        return tracking_numbers

    order_number = order_match.group(1)
    body = _decode_body(email.get(EMAIL_ATTR_BODY, ''))
    soup = BeautifulSoup(body or '', 'html.parser')

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        if not href:
            continue

        link = href.strip()
        if 'TrackConfirmAction' not in link:
            continue

        tracking_text = anchor.get_text(strip=True)
        tracking_number = order_number

        tracking_match = re.search(r'(\d{10,})', tracking_text)
        if tracking_match:
            tracking_number = tracking_match.group(1)

        if 'qtc_tLabels1=' in link:
            base, _, _ = link.partition('qtc_tLabels1=')
            normalized_link = f"{base}qtc_tLabels1={tracking_number}"
        else:
            normalized_link = link

        tracking_numbers.append({
            'link': normalized_link,
            'tracking_number': tracking_number,
            'carrier': 'USPS',
            'origin': EMAIL_DOMAIN_MOEN,
        })
        _LOGGER.debug(f"[Moen] Added tracking entry: order {order_number}, tracking {tracking_number}, link {normalized_link}")
        break

    if not tracking_numbers:
        _LOGGER.debug("[Moen] No USPS tracking link found in email body")

    _LOGGER.debug(f"[Moen] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
