import logging
import quopri
import re
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY, fedex_regex, ups_regex, usps_regex


_LOGGER = logging.getLogger(__name__)
ATTR_HOME_DEPOT = 'home_depot'
EMAIL_DOMAIN_HOME_DEPOT = 'homedepot.com'


TRACKING_LABEL_RE = re.compile(r'tracking\s*number', re.IGNORECASE)
TRACKING_LINE_RE = re.compile(r'(?:tracking\s*(?:number|#)\s*[:\-]?\s*)([A-Z0-9\s-]{8,})', re.IGNORECASE)
TRACKING_QUERY_KEYS = ('tracking', 'trackingnumber', 'tracking_number')
ORDER_NUMBER_RE = re.compile(r'order\s*#\s*([A-Za-z]{2}\d{8})', re.IGNORECASE)
TRACKING_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(ups_regex, re.IGNORECASE),
    re.compile(usps_regex, re.IGNORECASE),
    re.compile(fedex_regex, re.IGNORECASE),
)


def parse_home_depot(email):
    """Parse Home Depot tracking numbers."""
    body = email.get(EMAIL_ATTR_BODY, '')
    tracking_entries: list[dict] = []
    seen: set[str] = set()

    _LOGGER.debug("[Home Depot] Starting parser")

    if not body:
        _LOGGER.debug("[Home Depot] Empty email body received; skipping")
        return tracking_entries

    if '=\r' in body or '=\n' in body:
        decoded = quopri.decodestring(body)
        body = decoded.decode('utf-8', errors='ignore') if isinstance(decoded, bytes) else decoded

    soup = BeautifulSoup(body, 'html.parser')
    unified_text = soup.get_text(" ", strip=True)
    order_numbers = _extract_order_numbers(unified_text)

    def _add_entry(tracking_number: str, link: str | None = None) -> None:
        normalized = tracking_number.upper()
        if normalized in seen:
            return
        seen.add(normalized)

        entry: dict = {
            'tracking_number': normalized,
        }
        if link:
            entry['link'] = link
        if len(order_numbers) == 1:
            entry['order_number'] = next(iter(order_numbers))
        tracking_entries.append(entry)

    # Inspect anchor tags for tracking parameters and relevant text.
    for element in soup.find_all('a'):
        raw_href = element.get('href') or ''
        if not raw_href:
            continue

        href = _normalize_href(raw_href)
        tracking_from_link = _extract_from_link(href)
        if tracking_from_link:
            _add_entry(tracking_from_link, href)
            continue

        anchor_text = element.get_text(" ", strip=True)
        for candidate in _extract_tracking_candidates(anchor_text, require_label=False):
            _add_entry(candidate, href)

    # Scan for explicit "Tracking Number" labels within structured markup.
    for label in soup.find_all(string=TRACKING_LABEL_RE):
        container = getattr(label, 'parent', None)
        container_text = ''
        if container is not None:
            container_text = container.get_text(" ", strip=True)
        if container_text:
            for candidate in _extract_tracking_candidates(container_text, require_label=True):
                _add_entry(candidate)

    # Fallback to label-based search over entire body text.
    for candidate in _extract_tracking_candidates(unified_text, require_label=True):
        _add_entry(candidate)

    _LOGGER.debug("[Home Depot] Parser complete - Found %d tracking number(s)", len(tracking_entries))
    return tracking_entries


def _extract_order_numbers(text: str) -> set[str]:
    orders: set[str] = set()
    if not text:
        return orders
    for match in ORDER_NUMBER_RE.finditer(text):
        orders.add(match.group(1).upper())
    return orders


def _normalize_href(href: str) -> str:
    normalized = href.strip()
    if normalized.startswith('3D"') and normalized.endswith('"'):
        normalized = normalized[3:-1]
    normalized = normalized.replace('=\r\n', '').replace('=\n', '')
    if '=3D' in normalized:
        try:
            decoded = quopri.decodestring(normalized)
            normalized = decoded.decode('utf-8', errors='ignore') if isinstance(decoded, bytes) else decoded
        except Exception:  # pragma: no cover - best effort only
            normalized = normalized.replace('=3D', '=')
    return normalized


def _extract_from_link(link: str) -> str | None:
    parsed = urlparse(link)
    if 'link.order.homedepot.com' not in parsed.netloc.lower():
        return None

    params = parse_qs(parsed.query)
    for key in TRACKING_QUERY_KEYS:
        values = params.get(key)
        if not values:
            continue
        for value in values:
            candidate = _normalize_tracking_candidate(value)
            if candidate:
                return candidate
    return None


def _extract_tracking_candidates(text: str, require_label: bool) -> Iterable[str]:
    if not text:
        return ()

    matches: list[str] = []

    if require_label:
        for match in TRACKING_LINE_RE.finditer(text):
            candidate = _normalize_tracking_candidate(match.group(1))
            if candidate:
                matches.append(candidate)
        return matches

    tokens = text.split()
    current_parts: list[str] = []

    def flush_parts() -> None:
        if not current_parts:
            return
        candidate = ''.join(current_parts)
        normalized = _normalize_tracking_candidate(candidate)
        if normalized:
            matches.append(normalized)
        current_parts.clear()

    for token in tokens:
        cleaned = re.sub(r'[^A-Za-z0-9]', '', token)
        if not cleaned:
            flush_parts()
            continue

        cleaned_upper = cleaned.upper()
        if any(ch.isdigit() for ch in cleaned_upper):
            current_parts.append(cleaned_upper)
            continue

        if current_parts:
            candidate = ''.join(current_parts) + cleaned_upper
            normalized = _normalize_tracking_candidate(candidate)
            if normalized:
                current_parts.append(cleaned_upper)
                continue
            flush_parts()

    flush_parts()
    return matches


def _normalize_tracking_candidate(candidate: str) -> str | None:
    if not candidate:
        return None

    normalized = re.sub(r'[\s-]+', '', candidate).upper()
    if len(normalized) < 10:
        return None
    for regex in TRACKING_REGEXES:
        if regex.fullmatch(normalized):
            return normalized
    return None
