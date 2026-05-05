import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_ADAM_AND_EVE  = 'adam_and_eve'
EMAIL_DOMAIN_ADAM_AND_EVE = 'adamandeve.com'


def parse_adam_and_eve(email):
    """Parse Adam & Eve tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Adam Eve] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    for link in soup.find_all('a'):
        linkText = link.text
        if linkText:
            match = re.search(r'(\d{26})', linkText)
            if match and match.group(1) not in tracking_numbers:
                tracking_numbers.append(match.group(1))

        href = link.get('href') or ''
        href_match = re.search(r'trackingnumber=(\d{26})', href)
        if href_match and href_match.group(1) not in tracking_numbers:
            tracking_numbers.append(href_match.group(1))

    _LOGGER.debug(f"[Adam Eve] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
