import logging
import re
from html import unescape
from urllib.parse import unquote

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY
from ..const import EMAIL_ATTR_SUBJECT

_LOGGER = logging.getLogger(__name__)
ATTR_FEDEX = 'fedex'
EMAIL_DOMAIN_FEDEX = 'fedex.com'

_FEDEX_TRACKING_CANDIDATE_RE = re.compile(r"^(?:\d{12}|\d{15}|\d{20}|\d{22})$")
_FEDEX_TRACKING_IN_TEXT_RE = re.compile(r"\b(?:\d{12}|\d{15}|\d{20}|\d{22})\b")


def _add_tracking_number(tracking_numbers: list[str], tracking_num: str) -> None:
    tracking_num = (tracking_num or "").strip()
    if not tracking_num:
        return
    if not _FEDEX_TRACKING_CANDIDATE_RE.fullmatch(tracking_num):
        return
    if tracking_num in tracking_numbers:
        return
    tracking_numbers.append(tracking_num)


def _extract_query_param_values(link: str, key: str) -> list[str]:
    match = re.search(rf"(?:\\?|&){re.escape(key)}=([^&#]+)", link)
    if not match:
        return []
    raw_value = unquote(unescape(match.group(1)))
    return [part.strip() for part in re.split(r"[,\s]+", raw_value) if part.strip()]


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
        link_str = str(link)

        match = re.search(r'tracknumbers=(.*?)&', link_str)
        if match:
            _add_tracking_number(tracking_numbers, match.group(1))

        for tracking_num in _extract_query_param_values(link_str, "tracknumbers"):
            _add_tracking_number(tracking_numbers, tracking_num)

        for tracking_num in _extract_query_param_values(link_str, "trknbr"):
            _add_tracking_number(tracking_numbers, tracking_num)

    _LOGGER.debug("[Fedex] Checking subject line for tracking number")
    match = re.search(r'FedEx Shipment (.*?): Your package is on its way', subject)
    if match:
        _add_tracking_number(tracking_numbers, match.group(1))

    for tracking_num in _FEDEX_TRACKING_IN_TEXT_RE.findall(subject):
        _add_tracking_number(tracking_numbers, tracking_num)

    if not tracking_numbers:
        body = email.get(EMAIL_ATTR_BODY, '') or ''
        for tracking_num in _FEDEX_TRACKING_IN_TEXT_RE.findall(body):
            _add_tracking_number(tracking_numbers, tracking_num)
    
    _LOGGER.debug(f"[Fedex] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
