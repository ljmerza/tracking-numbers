import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_WALMART = 'walmart'
EMAIL_DOMAIN_WALMART = 'walmart.com'

_TRACKING_LINK_RE = re.compile(
    r'https?://(?:[\w.-]*\.)?w-mt\.co/[^\s"\'<>]+',
    re.IGNORECASE,
)
_TRACKING_NUM_RE = re.compile(r'^\d{12,30}$')


def parse_walmart(email):
    """Parse Walmart shipment notifications.

    Walmart wraps the carrier tracking number in a `w-mt.co` redirect link.
    We pull the digit-only anchor text (the actual tracking number) and keep
    the redirect URL so the user can click through to the carrier tracker.
    """
    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Walmart] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Walmart] Empty email body; skipping")
        return []

    soup = BeautifulSoup(body, 'html.parser')
    tracking_numbers = []

    for a in soup.find_all('a', href=True):
        href = a['href']
        if not _TRACKING_LINK_RE.search(href):
            continue
        text = (a.get_text() or '').strip()
        if not _TRACKING_NUM_RE.match(text):
            continue

        if any(t['tracking_number'] == text for t in tracking_numbers):
            _LOGGER.debug(f"[Walmart] Skipping duplicate tracking number: {text}")
            continue

        _LOGGER.debug(f"[Walmart] Found tracking number: {text}")
        tracking_numbers.append({'tracking_number': text, 'link': href})

    _LOGGER.debug(f"[Walmart] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
