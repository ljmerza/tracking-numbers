import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_WAYFAIR = 'wayfair'
EMAIL_DOMAIN_WAYFAIR = 'wayfair.com'


def parse_wayfair(email):
    """Parse Wayfair tracking numbers."""
    tracking_numbers = []

    _LOGGER.debug("Wayfair parser called")
    subject = email.get(EMAIL_ATTR_SUBJECT, '')
    _LOGGER.debug(f"Wayfair parser - Email subject: {subject}")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')

    # Check if it's a shipping notification email
    if not re.search(r'track your package|your order is on the way|has shipped', subject, re.IGNORECASE):
        _LOGGER.debug("Wayfair parser: Subject doesn't match shipping email pattern")
        return tracking_numbers

    _LOGGER.debug("Wayfair parser: Subject matches shipping email")

    # Look for order number in the email body (handles encoded characters like =E2=80=8C)
    order_number_match = re.search(r'Order[^0-9]*?(\d{10})', email[EMAIL_ATTR_BODY], re.IGNORECASE)
    order_number = order_number_match.group(1) if order_number_match else None
    _LOGGER.debug(f"Wayfair parser - Order number from body: {order_number}")

    # Find all links that contain 'track_package'
    link_elements = soup.find_all('a', href=True)
    _LOGGER.debug(f"Wayfair parser - Found {len(link_elements)} total links")

    for link_element in link_elements:
        link = link_element.get('href')

        if not link or 'track_package' not in link:
            continue

        _LOGGER.debug(f"Wayfair parser - Found track_package link: {link[:100]}")

        # Extract order number from link if not found in body (handles =3D encoded =)
        if not order_number:
            # Try order_id parameter with encoded equals sign
            order_id_match = re.search(r'order_id=3D(\d+)', link)
            if not order_id_match:
                # Try regular equals sign
                order_id_match = re.search(r'order_id=(\d+)', link)
            if order_id_match:
                order_number = order_id_match.group(1)
                _LOGGER.debug(f"Wayfair parser - Order number from link: {order_number}")

        # Use order number as tracking number if available
        if order_number:
            # Check for duplicates
            order_numbers = [x['tracking_number'] for x in tracking_numbers]
            if order_number not in order_numbers:
                tracking_numbers.append({
                    'link': link,
                    'tracking_number': order_number
                })
                _LOGGER.debug(f"Wayfair parser - Added tracking number: {order_number}")
            break  # Only need one tracking entry per order

    _LOGGER.debug(f"Wayfair parser - Total tracking numbers found: {len(tracking_numbers)}")
    return tracking_numbers
