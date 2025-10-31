import logging
import re
from html import unescape
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY


_LOGGER = logging.getLogger(__name__)
ATTR_CHEWY = 'chewy'
EMAIL_DOMAIN_CHEWY = 'chewy.com'

CHEWY_TRACK_LINK_RE = re.compile(
    r'https?://www\.chewy\.com/app/account/order-details/track\?[^"\'\s<>]+',
    re.IGNORECASE,
)
ORDER_NUMBER_RE = re.compile(r'Order\s*#\s*([0-9]+)', re.IGNORECASE)


def parse_chewy(email):
    """Parse Chewy tracking links and order identifiers."""
    body = email.get(EMAIL_ATTR_BODY, '') or ''

    if not body:
        _LOGGER.debug("[Chewy] Empty email body received; skipping")
        return []

    tracking_entries = []
    seen_ids: set[str] = set()

    for raw_link in CHEWY_TRACK_LINK_RE.findall(body):
        entry = _entry_from_link(raw_link)
        if not entry:
            continue

        tracking_id = entry['tracking_number']
        if tracking_id in seen_ids:
            continue

        seen_ids.add(tracking_id)
        tracking_entries.append(entry)

    if tracking_entries:
        _LOGGER.debug("[Chewy] Found %d tracking entries from links", len(tracking_entries))
        return tracking_entries

    # Fallback: extract order numbers from text if no direct links were found
    soup = BeautifulSoup(body, 'html.parser')
    text_content = soup.get_text(' ')
    for order_id in ORDER_NUMBER_RE.findall(text_content):
        tracking_id = order_id.strip()
        if not tracking_id or tracking_id in seen_ids:
            continue

        seen_ids.add(tracking_id)
        tracking_entries.append({
            'tracking_number': tracking_id,
            'carrier': 'Chewy',
            'link': f'https://www.chewy.com/app/account/order-details/track?orderId={tracking_id}',
        })

    if tracking_entries:
        _LOGGER.debug("[Chewy] Fallback matched %d order identifiers", len(tracking_entries))
    else:
        _LOGGER.debug("[Chewy] No tracking information found in email")

    return tracking_entries


def _entry_from_link(raw_link: str) -> dict | None:
    """Build a tracking entry from a Chewy tracking URL."""
    decoded_link = unescape(raw_link.strip())
    parsed = urlparse(decoded_link)

    if 'chewy.com' not in parsed.netloc:
        return None

    if not parsed.path.endswith('/track'):
        return None

    params = parse_qs(parsed.query)
    order_id = (params.get('orderId') or [''])[0].strip()
    package_id = (params.get('packageId') or [''])[0].strip()

    canonical_params = []
    if order_id:
        canonical_params.append(('orderId', order_id))
    if package_id:
        canonical_params.append(('packageId', package_id))

    canonical_url = decoded_link
    if canonical_params:
        canonical_query = urlencode(canonical_params)
        canonical_url = urlunparse((
            'https',
            'www.chewy.com',
            '/app/account/order-details/track',
            '',
            canonical_query,
            '',
        ))

    tracking_parts = [part for part in (order_id, package_id) if part]
    tracking_id = '-'.join(tracking_parts) or decoded_link

    return {
        'tracking_number': tracking_id,
        'carrier': 'Chewy',
        'link': canonical_url,
    }
