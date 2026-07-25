import logging
import re

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_EBAY = 'ebay'
EMAIL_DOMAIN_EBAY = 'ebay.com'

# eBay has shipped two shapes of the tracking block:
#   2021: <span>Tracking Number: <a>9400111899223102504339</a></span>
#   2025: <p class="subcopy">Tracking number: <a><span>9434611106150904224655</span></a></p>
# Anchoring on the label text node keeps both parent tags working, and the label
# is matched case-insensitively ("Tracking Number" became "Tracking number").
_EBAY_LABEL_TEXT_RE = re.compile(r"tracking\s+number", re.IGNORECASE)
# Fallback for markup shapes we haven't seen: the label followed by the id in flat text
_EBAY_LABEL_RE = re.compile(r"Tracking\s+number\s*:?\s*([A-Z0-9]{10,35})", re.IGNORECASE)
# eBay surfaces USPS/UPS/FedEx ids; requiring digits keeps link copy such as
# "Track order" from being read as a tracking number
_EBAY_TRACKING_CANDIDATE_RE = re.compile(r"^[A-Z0-9]{10,35}$")
_EBAY_MIN_DIGITS = 6
# The 2025 template puts a <style> block between the label and the link
_EBAY_SKIP_PARENTS = ('style', 'script')

# eBay Standard Delivery notices never print the carrier tracking number, so the
# order number and the order deep link are the only usable identifiers. Order
# numbers look like 19-14915-66402; the link sits behind "Track package",
# "Track order" and "View order details" alike.
_EBAY_ORDER_NUMBER_RE = re.compile(r"Order\s+number\s*:?\s*(\d{2}-\d{5}-\d{5})", re.IGNORECASE)
_EBAY_ORDER_LINK_HINT = '/vod/FetchOrderDetails'
_EBAY_FALLBACK_CARRIER = 'eBay'


def _add_tracking_number(tracking_numbers: list[str], tracking_num: str) -> None:
    tracking_num = (tracking_num or "").strip().upper()
    if not tracking_num:
        return
    if not _EBAY_TRACKING_CANDIDATE_RE.fullmatch(tracking_num):
        _LOGGER.debug(f"[Ebay] Skipping candidate with unexpected format: {tracking_num}")
        return
    if sum(char.isdigit() for char in tracking_num) < _EBAY_MIN_DIGITS:
        _LOGGER.debug(f"[Ebay] Skipping candidate without enough digits: {tracking_num}")
        return
    if tracking_num in tracking_numbers:
        _LOGGER.debug(f"[Ebay] Skipping duplicate tracking number: {tracking_num}")
        return
    _LOGGER.debug(f"[Ebay] Found tracking number: {tracking_num}")
    tracking_numbers.append(tracking_num)


def _order_fallback(soup, body_text: str) -> list[dict]:
    """Fall back to the order number plus the order deep link.

    eBay Standard Delivery notices never print the carrier tracking number — it
    only exists behind the "Track package" button. We surface the order number
    and that button's link so the order still shows up as a package; clicking
    through lands on eBay's order details, which carries the live status.
    """
    order_numbers = []
    for match in _EBAY_ORDER_NUMBER_RE.finditer(body_text):
        order_number = match.group(1)
        if order_number not in order_numbers:
            order_numbers.append(order_number)

    if not order_numbers:
        _LOGGER.debug("[Ebay] No order number found")
        return []

    if len(order_numbers) > 1:
        _LOGGER.debug(f"[Ebay] Found {len(order_numbers)} order numbers, using the first: {order_numbers}")

    entry = {
        'tracking_number': order_numbers[0],
        'carrier': _EBAY_FALLBACK_CARRIER,
    }

    for link in soup.find_all('a', href=True):
        if _EBAY_ORDER_LINK_HINT.lower() in link['href'].lower():
            entry['link'] = link['href']
            break
    else:
        _LOGGER.debug("[Ebay] No order link found; carrier lookup will supply one")

    _LOGGER.debug(f"[Ebay] Falling back to order number: {entry['tracking_number']}")
    return [entry]


def parse_ebay(email):
    """Parse eBay tracking numbers.

    Falls back to the order number and order link when the email carries no
    tracking number, which is the case for eBay Standard Delivery notices.
    """
    tracking_numbers = []

    _LOGGER.debug("[Ebay] Starting parser")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    labels = soup.find_all(string=_EBAY_LABEL_TEXT_RE)
    _LOGGER.debug(f"[Ebay] Found {len(labels)} tracking number label(s)")

    for label in labels:
        parent = label.parent
        if parent is None or parent.name in _EBAY_SKIP_PARENTS:
            continue

        tracking_link = parent.find("a", recursive=False)
        if tracking_link:
            _add_tracking_number(tracking_numbers, tracking_link.get_text(strip=True))
        else:
            _LOGGER.debug(f"[Ebay] No tracking link found in <{parent.name}> label element")

    if not tracking_numbers:
        _LOGGER.debug("[Ebay] Checking body text for labeled tracking number")
        body_text = soup.get_text(separator=' ')
        for match in _EBAY_LABEL_RE.finditer(body_text):
            _add_tracking_number(tracking_numbers, match.group(1))

        if not tracking_numbers:
            _LOGGER.debug("[Ebay] No tracking number in email; checking for an order number")
            order_entries = _order_fallback(soup, body_text)
            if order_entries:
                _LOGGER.debug(f"[Ebay] Parser complete - Found {len(order_entries)} order reference(s)")
                return order_entries

    _LOGGER.debug(f"[Ebay] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
