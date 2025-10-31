import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, EMAIL_ATTR_SUBJECT


_LOGGER = logging.getLogger(__name__)
ATTR_UBIQUITI  = 'ubiquiti'
# Support both Shopify emails and direct ui.com emails
EMAIL_DOMAIN_UBIQUITI = 'ui.com'


def parse_ubiquiti(email):
    """Parse Ubiquiti tracking numbers."""
    tracking_numbers = []
    order_number = None

    subject = email[EMAIL_ATTR_SUBJECT]

    # Check for shipment notification (Shopify format)
    # Example: "A shipment from order #12345 is on the way"
    shipment_match = re.search(r'A shipment from order #(.*?) is on the way', subject)
    if shipment_match:
        order_number = shipment_match.group(1)
        _LOGGER.debug("Found Ubiquiti shipment order: %s", order_number)

    # Check for order confirmation or shipped (ui.com direct format)
    # Example: "Order US3515587 confirmed" or "Order US3486245 shipped"
    confirmation_match = re.search(r'Order ([A-Z]{2}\d+) (confirmed|shipped)', subject)
    if confirmation_match:
        order_number = confirmation_match.group(1)
        _LOGGER.debug("Found Ubiquiti order: %s (%s)", order_number, confirmation_match.group(2))

    if not order_number:
        _LOGGER.debug("No Ubiquiti order number found in subject: %s", subject)
        return tracking_numbers

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    links = soup.find_all('a')

    _LOGGER.debug("Found %d total links in email body", len(links))

    order_link = None

    for link_tag in links:
        href = link_tag.get('href')
        if not href:
            continue

        _LOGGER.debug("Checking link: %s", href[:100] if len(href) > 100 else href)

        # Check for Shopify order link format: /(\d{26})/orders/
        shopify_match = re.search(r'/(\d{26})/orders/', href)
        if shopify_match:
            order_link = href
            _LOGGER.debug("Found Shopify order link: %s", href)
            break

        # Check for ui.com store order link: store.ui.com/.../order/...
        # This might be wrapped in tracking URL or URL encoded
        # Example direct: https://store.ui.com/us/en/order/f11376e1-2d33-4a40-8daa-fcc19a10a040/status
        # Example wrapped: https://tracking.com/L0/https:%2F%2Fstore.ui.com%2F...
        if 'store.ui.com' in href or 'store%2Eui%2Ecom' in href or '%2Fstore.ui.com' in href:
            if '/order/' in href or '%2Forder%2F' in href:
                order_link = href
                _LOGGER.debug("Found store.ui.com order link: %s", href)
                break

        # Check for account.ui.com order link: account.ui.com/orders/...
        if 'account.ui.com' in href or 'account%2Eui%2Ecom' in href:
            if '/order' in href or '%2Forder' in href:
                order_link = href
                _LOGGER.debug("Found account.ui.com order link: %s", href)
                break

    if order_link:
        tracking_numbers.append({
            "tracking_number": order_number,
            "link": order_link,
        })
        _LOGGER.debug("Ubiquiti parser found tracking: %s -> %s", order_number, order_link)
    else:
        _LOGGER.debug("Ubiquiti parser found order %s but no order link", order_number)

    return tracking_numbers
