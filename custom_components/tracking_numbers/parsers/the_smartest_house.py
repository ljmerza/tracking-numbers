import logging
import quopri
import re

from bs4 import BeautifulSoup
from ..const import (
    EMAIL_ATTR_BODY,
    FEDEX_TRACKING_NUMBER_REGEX,
    UPS_TRACKING_NUMBER_REGEX,
    USPS_TRACKING_NUMBER_REGEX,
)


_LOGGER = logging.getLogger(__name__)
ATTR_SMARTEST_HOUSE = 'smartesthouse'
EMAIL_DOMAIN_SMARTEST_HOUSE = 'thesmartesthouse.com'

TRACKING_REGEXES = (
    re.compile(USPS_TRACKING_NUMBER_REGEX),
    re.compile(UPS_TRACKING_NUMBER_REGEX),
    re.compile(FEDEX_TRACKING_NUMBER_REGEX),
)
LEGACY_QUERY_REGEX = re.compile(r'tracking_number=([0-9]+)')
FLEX_USPS_REGEX = re.compile(r'94[\d\s-]{20,}')


def parse_smartest_house(email):
    """Parse the smartest house tracking numbers."""
    raw_body = email.get(EMAIL_ATTR_BODY, '')
    if not raw_body:
        _LOGGER.debug("[Smartest House] Empty email body received; skipping")
        return []

    decoded_body = raw_body
    if '=\r' in raw_body or '=\n' in raw_body:
        decoded = quopri.decodestring(raw_body)
        decoded_body = decoded.decode('utf-8', errors='ignore') if isinstance(decoded, bytes) else decoded

    tracking_numbers: list[str] = []
    seen: set[str] = set()

    def _normalize_candidate(number: str) -> str:
        return re.sub(r'[\s-]+', '', number or '').strip()

    def _add_tracking_number(number: str) -> None:
        normalized = _normalize_candidate(number)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        tracking_numbers.append(normalized)

    def _collect_targets(html: str) -> list[str]:
        soup = BeautifulSoup(html, 'html.parser')
        targets = [soup.get_text(" ", strip=True)]
        for element in soup.find_all('a'):
            link_text = element.get_text(" ", strip=True)
            if link_text:
                targets.append(link_text)
            href = element.get('href')
            if href:
                href = href.strip()
                if href.startswith('3D"') and href.endswith('"'):
                    href = href[3:-1]
                href = href.replace('=\r\n', '').replace('=\n', '')
                targets.append(href)
        return targets

    text_targets = _collect_targets(raw_body)
    if decoded_body != raw_body:
        text_targets.extend(_collect_targets(decoded_body))

    for target in text_targets:
        if not target:
            continue

        for match in LEGACY_QUERY_REGEX.findall(target):
            _add_tracking_number(match)

        for regex in TRACKING_REGEXES:
            for match in regex.findall(target):
                _add_tracking_number(match)

        for match in FLEX_USPS_REGEX.findall(target):
            _add_tracking_number(match)

    # Keep scanning the raw body for legacy tracking_number parameters that might
    # only exist in encoded links.
    for match in LEGACY_QUERY_REGEX.findall(raw_body):
        _add_tracking_number(match)

    _LOGGER.debug(
        "[Smartest House] Parser complete - Found %d tracking number(s)",
        len(tracking_numbers),
    )
    return tracking_numbers
