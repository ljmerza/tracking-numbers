import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_BEST_BUY = 'best_buy'
EMAIL_DOMAIN_BEST_BUY = 'bestbuy.com'


def parse_best_buy(email):
    """Parse Best Buy tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Best Buy] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    elements = soup.find_all('a')
    _LOGGER.debug(f"[Best Buy] Found {len(elements)} link elements")

    for element in elements:
        link = element.get('href')
        if not link:
            continue
        if 'shipment/tracking' in link:
            _LOGGER.debug(f"[Best Buy] Found shipment/tracking link: {link}")
            tracking_number = element.text
            if tracking_number and tracking_number not in tracking_numbers:
                _LOGGER.debug(f"[Best Buy] Found tracking number: {tracking_number.strip()}")
                tracking_numbers.append(tracking_number.strip())
            elif tracking_number in tracking_numbers:
                _LOGGER.debug(f"[Best Buy] Skipping duplicate tracking number: {tracking_number.strip()}")

    _LOGGER.debug(f"[Best Buy] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
