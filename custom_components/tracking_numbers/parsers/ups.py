import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_UPS = 'ups'
EMAIL_DOMAIN_UPS = 'ups.com'


def parse_ups(email):
    """Parse UPS tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Ups] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    links = [link.get('href') for link in soup.find_all('a')]
    _LOGGER.debug(f"[Ups] Found {len(links)} links in email body")

    for link in links:
        if not link:
            continue

        match = re.search('tracknum=(.*?)&', link)
        if match:
            tracking_num = match.group(1)
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Ups] Found tracking number: {tracking_num}")
                tracking_numbers.append(tracking_num)
            else:
                _LOGGER.debug(f"[Ups] Skipping duplicate tracking number: {tracking_num}")

    _LOGGER.debug(f"[Ups] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
