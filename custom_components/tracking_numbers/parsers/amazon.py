import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_AMAZON = 'amazon'
EMAIL_DOMAIN_AMAZON = 'amazon.com'

def parse_amazon(email):
    """Parse Amazon tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')

    _LOGGER.debug(f"[Amazon] Starting parser - Subject: {subject}")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')

    # Try to find order number in subject line (old format)
    _LOGGER.debug("[Amazon] Checking for old format: 'Your AmazonSmile/Amazon.com order #...'")
    order_number_match = re.search('Your AmazonSmile order #(.*?) has shipped', email[EMAIL_ATTR_SUBJECT])
    if not order_number_match:
        order_number_match = re.search('Your Amazon.com order #(.*?) has shipped', email[EMAIL_ATTR_SUBJECT])

    # If not in subject, check if it's the new "Shipped: ..." format
    if not order_number_match:
        _LOGGER.debug("[Amazon] Old format not found, checking for new format: 'Shipped: ...'")
        # New format has subject like "Shipped: Product Name..."
        # Check if subject starts with "Shipped:" to confirm it's a shipping email
        if not re.search(r'^Shipped:', email[EMAIL_ATTR_SUBJECT]):
            _LOGGER.debug("[Amazon] Not a recognized Amazon shipping email format")
            return tracking_numbers

        # Extract order number from body - it appears after "Order #"
        # Pattern matches both plain text and HTML versions
        _LOGGER.debug("[Amazon] Searching for order number in email body")
        body_text = email[EMAIL_ATTR_BODY]
        order_number_match = re.search(r'Order\s*#\s*\D*(\d{3}-\d{7}-\d{7})', body_text)

        if not order_number_match:
            _LOGGER.debug("[Amazon] No order number found in email body")
            return tracking_numbers

    order_number = order_number_match.group(1)
    _LOGGER.debug(f"[Amazon] Found order number: {order_number}")

    # find the link that has 'track package' text
    _LOGGER.debug("[Amazon] Searching for 'track package' links")
    linkElements = soup.find_all('a')
    for linkElement in linkElements:
        if not re.search(r'track package', linkElement.text, re.IGNORECASE):
            continue

        # if found we no get url and check for duplicates
        link = linkElement.get('href')
        _LOGGER.debug(f"[Amazon] Found tracking link: {link}")

        # make sure we dont have dupes
        order_numbers = list(map(lambda x: x['tracking_number'], tracking_numbers))
        if order_number not in order_numbers:
            tracking_numbers.append({
                'link': link,
                'tracking_number': order_number
            })
            _LOGGER.debug(f"[Amazon] Added tracking entry for order: {order_number}")
        else:
            _LOGGER.debug(f"[Amazon] Skipping duplicate order: {order_number}")

    _LOGGER.debug(f"[Amazon] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
