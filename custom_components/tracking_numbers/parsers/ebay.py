import logging

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_EBAY = 'ebay'
EMAIL_DOMAIN_EBAY = 'ebay.com'


def parse_ebay(email):
    """Parse eBay tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Ebay] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    elements = [element for element in soup.find_all('span')]
    _LOGGER.debug(f"[Ebay] Found {len(elements)} span elements")

    for element in elements:
        if 'Tracking Number' in element.text:
            _LOGGER.debug("[Ebay] Found 'Tracking Number' span element")
            tracking_link = element.find("a", recursive=False)
            if tracking_link:
                tracking_number = tracking_link.text
                if tracking_number not in tracking_numbers:
                    _LOGGER.debug(f"[Ebay] Found tracking number: {tracking_number}")
                    tracking_numbers.append(tracking_number)
                else:
                    _LOGGER.debug(f"[Ebay] Skipping duplicate tracking number: {tracking_number}")
            else:
                _LOGGER.debug("[Ebay] No tracking link found in span element")

    _LOGGER.debug(f"[Ebay] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
