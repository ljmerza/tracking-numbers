import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_HUE = 'hue'
EMAIL_DOMAIN_HUE = 'luzernsolutions'


def parse_hue(email):
    """Parse Phillips Hue tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Hue] Starting parser")

    body = email[EMAIL_ATTR_BODY]
    matches = re.findall(r'tracking number is: (.*?)<', body)
    for tracking_number in matches:
        if tracking_number not in tracking_numbers:
            tracking_numbers.append(tracking_number)

    _LOGGER.debug(f"[Hue] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
