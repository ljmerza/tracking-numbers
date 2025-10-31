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
        match = re.search('United Parcel Service Tracking # (\S{18})', paragraph)
        if match:
            tracking_num = match.group(1)
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Target] Found tracking number: {tracking_num}")
                tracking_numbers.append(tracking_num)
            else:
                _LOGGER.debug(f"[Target] Skipping duplicate tracking number: {tracking_num}")

    _LOGGER.debug(f"[Target] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
