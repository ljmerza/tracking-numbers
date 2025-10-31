import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY
from ..const import EMAIL_ATTR_SUBJECT

_LOGGER = logging.getLogger(__name__)
ATTR_FEDEX = 'fedex'
EMAIL_DOMAIN_FEDEX = 'fedex.com'


def parse_fedex(email):
    """Parse FedEx tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')

    _LOGGER.debug(f"[Fedex] Starting parser - Subject: {subject}")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    links = [link.get('href') for link in soup.find_all('a')]
    _LOGGER.debug(f"[Fedex] Found {len(links)} links in email body")

    for link in links:
        if not link:
            continue
        match = re.search('tracknumbers=(.*?)&', link)
        if match:
            tracking_num = match.group(1)
            if tracking_num not in tracking_numbers:
                _LOGGER.debug(f"[Fedex] Found tracking number in link: {tracking_num}")
                tracking_numbers.append(tracking_num)
            else:
                _LOGGER.debug(f"[Fedex] Skipping duplicate tracking number: {tracking_num}")

    _LOGGER.debug("[Fedex] Checking subject line for tracking number")
    match = re.search('FedEx Shipment (.*?): Your package is on its way', email[EMAIL_ATTR_SUBJECT])
    if match:
        tracking_num = match.group(1)
        if tracking_num not in tracking_numbers:
            _LOGGER.debug(f"[Fedex] Found tracking number in subject: {tracking_num}")
            tracking_numbers.append(tracking_num)
        else:
            _LOGGER.debug(f"[Fedex] Skipping duplicate tracking number from subject: {tracking_num}")
    
    _LOGGER.debug(f"[Fedex] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
