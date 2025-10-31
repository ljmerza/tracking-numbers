import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_NULEAF = 'nuleaf'
EMAIL_DOMAIN_NULEAF = 'nuleafnaturals.com'


def parse_nuleaf(email):
    """Parse NuLeaf tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Nuleaf] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    elements = soup.find_all('a')
    for element in elements:
        link = element.get('href')
        if not link:
            continue
        if 'emailtrk' in link:
            tracking_number = element.text
            if tracking_number and tracking_number not in tracking_numbers:
                tracking_numbers.append(tracking_number)

    _LOGGER.debug(f"[Nuleaf] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
