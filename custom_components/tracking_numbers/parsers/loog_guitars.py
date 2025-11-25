import logging
import re

from bs4 import BeautifulSoup

from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_LOOG_GUITARS = 'loog_guitars'
EMAIL_DOMAIN_LOOG_GUITARS = 'loogguitars.com'

_TRACKING_TEXT_REGEX = re.compile(r'Other tracking number:\s*([A-Z0-9]+)', re.IGNORECASE)
_VEHO_LINK_REGEX = re.compile(r'trackingId[/=]([A-Z0-9]+)', re.IGNORECASE)


def parse_loog_guitars(email):
    """Parse Loog Guitars tracking numbers (Veho)."""
    tracking_numbers = []

    _LOGGER.debug("[Loog Guitars] Starting parser")

    body = email.get(EMAIL_ATTR_BODY, '') or ''
    soup = BeautifulSoup(body, 'html.parser')
    text_content = soup.get_text(" ", strip=True)

    def _add_tracking(tracking_number: str | None, link: str | None = None) -> None:
        """Add a normalized tracking entry if new."""
        normalized = (tracking_number or '').strip().upper()
        if not normalized:
            return

        entry = {
            'tracking_number': normalized,
            'carrier': 'Veho',
            'origin': EMAIL_DOMAIN_LOOG_GUITARS,
            'link': link or f'https://track.shipveho.com/#/trackingId/{normalized}',
        }

        for existing in tracking_numbers:
            if existing.get('tracking_number') == normalized:
                if not existing.get('link') and entry.get('link'):
                    existing['link'] = entry['link']
                return

        tracking_numbers.append(entry)

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        match = _VEHO_LINK_REGEX.search(href)
        if match:
            _add_tracking(match.group(1), link=href.strip())
            continue

        text = anchor.get_text(strip=True)
        if text and re.fullmatch(r'[A-Z0-9]{8,}', text):
            context = anchor.parent.get_text(" ", strip=True) if anchor.parent else ''
            if 'other tracking number' in context.lower():
                _add_tracking(text)

    for match in _TRACKING_TEXT_REGEX.findall(text_content or ''):
        _add_tracking(match)

    _LOGGER.debug(f"[Loog Guitars] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
