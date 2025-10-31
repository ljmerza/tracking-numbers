import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_DHL = 'dhl'
EMAIL_DOMAIN_DHL = 'dhl'


def parse_dhl(email):
    """Parse DHL tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Dhl] Starting parser")

    matches = re.findall(r'idc=(.*?)"', email[EMAIL_ATTR_BODY])
    _LOGGER.debug(f"[Dhl] Found {len(matches)} potential tracking numbers")

    for tracking_number in matches:
        if tracking_number not in tracking_numbers:
            _LOGGER.debug(f"[Dhl] Found tracking number: {tracking_number}")
            tracking_numbers.append(tracking_number)
        else:
            _LOGGER.debug(f"[Dhl] Skipping duplicate tracking number: {tracking_number}")

    _LOGGER.debug(f"[Dhl] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
