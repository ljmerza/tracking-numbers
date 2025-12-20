import logging
import re

from bs4 import BeautifulSoup

from ..const import EMAIL_ATTR_BODY, fedex_regex, ups_regex, usps_regex

_LOGGER = logging.getLogger(__name__)
ATTR_SWITCHBOT = 'switchbot'
EMAIL_DOMAIN_SWITCHBOT = 'switch-bot.com'


def _normalize_body(raw_body: str) -> str:
    """Normalize quoted-printable artifacts and whitespace for regex scanning."""
    body = raw_body or ''
    body = body.replace('=\r\n', '').replace('=\n', '')
    body = body.replace('=3D', '=')
    return body


def parse_switchbot(email):
    """Parse SwitchBot shipping emails for carrier tracking numbers."""
    tracking_numbers: list[dict] = []

    body = _normalize_body(email.get(EMAIL_ATTR_BODY, ''))
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text(" ", strip=True)

    # Prefer explicit "tracking number:" label (works for both plain and HTML).
    labeled_matches = re.findall(r'tracking number:\s*([A-Za-z0-9]+)', text, re.IGNORECASE)
    for match in labeled_matches:
        tracking_numbers.append({'tracking_number': match})

    # Fallback: scan for common carrier tracking patterns.
    for regex in (fedex_regex, ups_regex, usps_regex):
        for match in re.findall(regex, text):
            if isinstance(match, tuple):
                match = next((m for m in match if m), '')
            if match:
                tracking_numbers.append({'tracking_number': match})

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[dict] = []
    for entry in tracking_numbers:
        tn = str(entry.get('tracking_number', '') or '').strip()
        if not tn or tn in seen:
            continue
        seen.add(tn)
        deduped.append({'tracking_number': tn})

    _LOGGER.debug("[SwitchBot] Found %d tracking number(s)", len(deduped))
    return deduped

