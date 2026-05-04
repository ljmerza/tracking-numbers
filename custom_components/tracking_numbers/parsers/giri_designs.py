import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_GIRI_DESIGNS = 'giri_designs'
EMAIL_DOMAIN_GIRI_DESIGNS = 'giridesigns.com'

_TRACKING_LABEL_RE = re.compile(
    r'(fedex|ups|usps|dhl)?\s*tracking\s+number',
    re.IGNORECASE,
)
_TRACKING_NUM_RE = re.compile(r'^\d{10,30}$')
_CARRIER_NORMALIZE = {
    'fedex': 'FedEx',
    'ups': 'UPS',
    'usps': 'USPS',
    'dhl': 'DHL',
}


def parse_giri_designs(email):
    """Parse Giri Designs (Shopify) shipment notifications.

    Shopify renders the carrier tracking number as the anchor text of a
    tokenized `_t/c/v3/...` redirect link, prefixed with a "<carrier>
    tracking number:" label. We pull the digit-only anchor, keep the
    redirect URL, and surface the carrier from the label when present.
    """
    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Giri Designs] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Giri Designs] Empty email body; skipping")
        return []

    soup = BeautifulSoup(body, 'html.parser')
    tracking_numbers = []

    for a in soup.find_all('a', href=True):
        text = (a.get_text() or '').strip()
        if not _TRACKING_NUM_RE.match(text):
            continue

        parent_text = a.parent.get_text(' ', strip=True) if a.parent else ''
        label_match = _TRACKING_LABEL_RE.search(parent_text)
        if not label_match:
            continue

        if any(t['tracking_number'] == text for t in tracking_numbers):
            _LOGGER.debug(f"[Giri Designs] Skipping duplicate tracking number: {text}")
            continue

        entry = {'tracking_number': text, 'link': a['href']}
        carrier_token = (label_match.group(1) or '').lower()
        if carrier_token:
            entry['carrier'] = _CARRIER_NORMALIZE.get(carrier_token, carrier_token.upper())

        _LOGGER.debug(f"[Giri Designs] Found tracking number: {text}")
        tracking_numbers.append(entry)

    _LOGGER.debug(f"[Giri Designs] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
