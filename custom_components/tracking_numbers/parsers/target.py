import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_TARGET = 'target'
EMAIL_DOMAIN_TARGET = 'target.com'


def parse_target(email):
    """Parse Target tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug(f"[Target] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    paragraphs = [paragraph.text for paragraph in soup.find_all('p')]
    _LOGGER.debug(f"[Target] Found {len(paragraphs)} paragraphs in email body")

    for paragraph in paragraphs:
        if not paragraph:
            continue

        # Try to match Target Local Delivery (TLMD) tracking numbers
        tlmd_match = re.search(r'Target Local Delivery \(TLMD\)\s*(?:Tracking #|Tracking #)\s*(\S+)', paragraph)
        if tlmd_match:
            tracking_num = tlmd_match.group(1)
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Target] Found TLMD tracking number: {tracking_num}")
                tracking_numbers.append(tracking_num)
            else:
                _LOGGER.debug(f"[Target] Skipping duplicate tracking number: {tracking_num}")
            continue

        # Also check for UPS tracking numbers (original pattern)
        ups_match = re.search(r'United Parcel Service Tracking # (\S{18})', paragraph)
        if ups_match:
            tracking_num = ups_match.group(1)
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Target] Found UPS tracking number: {tracking_num}")
                tracking_numbers.append(tracking_num)
            else:
                _LOGGER.debug(f"[Target] Skipping duplicate tracking number: {tracking_num}")

    _LOGGER.debug(f"[Target] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
