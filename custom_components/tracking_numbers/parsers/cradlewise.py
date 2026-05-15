import logging
import re

from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT, ups_regex


_LOGGER = logging.getLogger(__name__)
ATTR_CRADLEWISE = 'cradlewise'
EMAIL_DOMAIN_CRADLEWISE = 'cradlewise.com'

_LABELED_TRACKING_RE = re.compile(
    r'(?:UPS|FedEx|USPS|DHL)\s+tracking\s+number\s*[:\-]?\s*([A-Z0-9]{10,})',
    re.IGNORECASE,
)


def parse_cradlewise(email):
    """Parse Cradlewise shipment notifications.

    Cradlewise ships via Shopify; the carrier tracking number appears inline as
    ``UPS tracking number: 1Z...`` in both the text/plain and HTML bodies.
    """
    tracking_numbers = []

    subject = email.get(EMAIL_ATTR_SUBJECT, '') or ''
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    _LOGGER.debug(f"[Cradlewise] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Cradlewise] Empty email body; skipping")
        return []

    for match in _LABELED_TRACKING_RE.finditer(body):
        tracking_num = match.group(1).upper()
        if tracking_num not in tracking_numbers:
            _LOGGER.debug(f"[Cradlewise] Found labeled tracking number: {tracking_num}")
            tracking_numbers.append(tracking_num)

    if not tracking_numbers:
        for match in re.finditer(ups_regex, body, flags=re.IGNORECASE):
            tracking_num = match.group(0).upper()
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Cradlewise] Found UPS-pattern tracking number: {tracking_num}")
                tracking_numbers.append(tracking_num)

    _LOGGER.debug(
        f"[Cradlewise] Parser complete - Found {len(tracking_numbers)} tracking number(s)"
    )
    return tracking_numbers
