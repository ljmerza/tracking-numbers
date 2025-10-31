import logging
import re
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag
from ..const import EMAIL_ATTR_BODY, fedex_regex, ups_regex, usps_regex


_LOGGER = logging.getLogger(__name__)
ATTR_LITTER_ROBOT = 'litter_robot'
EMAIL_DOMAIN_LITTER_ROBOT = 'litter-robot.com'

TRACKING_LABEL_RE = re.compile(r'tracking\s*number', re.IGNORECASE)
TRACKING_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(ups_regex, re.IGNORECASE),
    re.compile(usps_regex, re.IGNORECASE),
    re.compile(fedex_regex, re.IGNORECASE),
)


def parse_litter_robot(email):
    """Parse Litter Robot tracking numbers."""
    body = email.get(EMAIL_ATTR_BODY, '')
    tracking_numbers: list[str] = []
    seen: set[str] = set()

    _LOGGER.debug("[Litter Robot] Starting parser")

    if not body:
        _LOGGER.debug("[Litter Robot] Empty email body received; skipping")
        return tracking_numbers

    soup = BeautifulSoup(body, 'html.parser')

    def _add_candidates_from_text(text: str) -> None:
        for candidate in _extract_tracking_numbers(text):
            clean_candidate = candidate.replace('\xa0', ' ').strip()
            if not clean_candidate or clean_candidate in seen:
                continue
            seen.add(clean_candidate)
            tracking_numbers.append(clean_candidate)

    # Gather tracking numbers from link text or href attributes
    for element in soup.find_all('a'):
        href = element.get('href') or ''
        anchor_text = element.get_text(' ', strip=True)
        search_space = ' '.join(part for part in (anchor_text, href) if part)
        if 'track' not in href.lower() and 'tracking' not in href.lower():
            # Avoid pulling unrelated numbers from generic links
            search_space = anchor_text
        if not search_space:
            continue
        _add_candidates_from_text(search_space)

    # Look for explicit "Tracking Number" labels and capture nearby values
    for label in soup.find_all(string=TRACKING_LABEL_RE):
        container: Tag | NavigableString = label
        parent = getattr(label, 'parent', None)
        if isinstance(parent, Tag):
            container = parent
            if isinstance(parent.parent, Tag):
                container = parent.parent
        container_text = container.get_text(" ", strip=True) if isinstance(container, Tag) else str(container)
        if container_text:
            _add_candidates_from_text(container_text)

    if not tracking_numbers:
        # Fallback: scan plain text for supported tracking formats
        plain_text = soup.get_text(" ", strip=True)
        _add_candidates_from_text(plain_text)

    _LOGGER.debug("[Litter Robot] Parser complete - Found %d tracking number(s)", len(tracking_numbers))
    return tracking_numbers


def _extract_tracking_numbers(text: str) -> Iterable[str]:
    """Yield tracking numbers that match known carrier formats from provided text."""
    if not text:
        return []

    matches: list[str] = []
    current_parts: list[str] = []

    tokens = text.split()

    def _flush_candidate() -> None:
        if not current_parts:
            return
        candidate = ''.join(current_parts)
        if _matches_tracking(candidate):
            matches.append(candidate)
        current_parts.clear()

    for token in tokens:
        cleaned = re.sub(r'[^A-Za-z0-9]', '', token)
        if not cleaned:
            _flush_candidate()
            continue

        cleaned_upper = cleaned.upper()
        has_digit = any(char.isdigit() for char in cleaned_upper)

        if has_digit:
            current_parts.append(cleaned_upper)
            continue

        if current_parts:
            candidate = ''.join(current_parts)
            candidate_with_suffix = candidate + cleaned_upper
            if _matches_tracking(candidate_with_suffix):
                current_parts.append(cleaned_upper)
                continue
            _flush_candidate()

    _flush_candidate()
    return matches


def _matches_tracking(candidate: str) -> bool:
    """Return True if candidate matches any known carrier regex."""
    if not candidate:
        return False
    for regex in TRACKING_REGEXES:
        if regex.fullmatch(candidate):
            return True
    return False
