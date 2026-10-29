import logging
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    EMAIL_ATTR_SUBJECT,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
)


_LOGGER = logging.getLogger(__name__)
ATTR_ALIBABA = 'alibaba'
EMAIL_DOMAIN_ALIBABA = 'alibaba.com'

# Trade Assurance shipping email: "Your order is on its way (<order id>)" with a
# biz.alibaba.com/ta/detail.htm?orderId=<order id> link and no carrier tracking
# number, so it yields an order-only package (tracking_number == order_number).
# Carrier numbers usually arrive in a free-text seller message without the order,
# so those are matched by carrier pattern only and linked to an order only when
# the same email names one.
_ALIBABA_SHIPPED_RE = re.compile(r'on\s+its\s+way|has\s+shipped|shipped\s+your', re.IGNORECASE)
_ALIBABA_ORDER_HREF_RE = re.compile(r'biz\.alibaba\.com/ta/detail\.htm\?(?:[^"\s]*&)?orderId=(\d+)')
_ALIBABA_ORDER_TEXT_RE = re.compile(r'order\s+(?:no\.?\s*)?\(?(\d{12,})\)?', re.IGNORECASE)
_ALIBABA_ORDER_LINK = 'https://biz.alibaba.com/ta/detail.htm?orderId='
_ALIBABA_TEXT_RES = (
    re.compile(UPS_TRACKING_NUMBER_REGEX),
    re.compile(USPS_TRACKING_NUMBER_REGEX),
)


def parse_alibaba(email):
    """Parse Alibaba tracking numbers along with the order they belong to."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')
    body = email.get(EMAIL_ATTR_BODY, '')

    _LOGGER.debug(f"[Alibaba] Starting parser - Subject: {subject}")

    if not body:
        _LOGGER.debug("[Alibaba] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(' ', strip=True)

    order_number = None
    for link_element in soup.find_all('a'):
        match = _ALIBABA_ORDER_HREF_RE.search(link_element.get('href') or '')
        if match:
            order_number = match.group(1)
            break
    if not order_number:
        match = _ALIBABA_ORDER_TEXT_RE.search(subject or '') or _ALIBABA_ORDER_TEXT_RE.search(text)
        if match:
            order_number = match.group(1)
    # Clean order link: the email's hrefs carry click-tracking params and an as_token
    order_link = f'{_ALIBABA_ORDER_LINK}{order_number}' if order_number else None
    if order_number:
        _LOGGER.debug(f"[Alibaba] Found order number: {order_number}")

    def _add_tracking_number(number, link=None):
        number = number.strip().upper()
        if not number or number in [x['tracking_number'] for x in tracking_numbers]:
            return
        entry = {'tracking_number': number}
        if link:
            entry['link'] = link
        if order_number:
            entry['order_number'] = order_number
            entry['order_link'] = order_link
        tracking_numbers.append(entry)
        _LOGGER.debug(f"[Alibaba] Found tracking number: {number}")

    # Carrier numbers anywhere in the text (seller messages have no fixed format)
    for regex in _ALIBABA_TEXT_RES:
        for match in regex.findall(text):
            _add_tracking_number(match)

    # Shipping notice without a carrier number: track the order itself
    if not tracking_numbers and order_number and (
        _ALIBABA_SHIPPED_RE.search(subject or '') or _ALIBABA_SHIPPED_RE.search(text)
    ):
        _add_tracking_number(order_number, order_link)

    _LOGGER.debug(f"[Alibaba] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
