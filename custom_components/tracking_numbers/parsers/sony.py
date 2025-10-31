import logging
import re, base64

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_SONY = 'sony'
EMAIL_DOMAIN_SONY = 'sony.com'


def parse_sony(email):
    """Parse Sony tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Sony] Starting parser")

    matches = re.findall(r'tracking_numbers=(.*?)&', email[EMAIL_ATTR_BODY])
    for tracking_number in matches:
        if tracking_number not in tracking_numbers:
            tracking_numbers.append(tracking_number)

    _LOGGER.debug(f"[Sony] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
