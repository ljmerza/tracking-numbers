import logging
import re
from html import unescape
from urllib.parse import unquote

from bs4 import BeautifulSoup
from ..const import EMAIL_ATTR_BODY
from ..const import EMAIL_ATTR_SUBJECT

_LOGGER = logging.getLogger(__name__)
ATTR_CANADA_POST = 'canada_post'
EMAIL_DOMAIN_CANADA_POST = 'canadapost'

# 16-digit domestic PIN or 13-character international S10 id (e.g. RN123456789CA)
_CANADA_POST_TRACKING_CANDIDATE_RE = re.compile(r"^(?:\d{16}|[A-Z]{2}\d{9}[A-Z]{2})$")
# Tracking links carry the number as searchFor= (EN site), rechercher= (FR site)
# or p1= (notification redirect links)
_CANADA_POST_LINK_PARAM_RE = re.compile(r"(?:searchFor|rechercher|p1)=([A-Za-z0-9]+)")
# Bilingual subjects end with ": TRACKING <number>"
_CANADA_POST_SUBJECT_RE = re.compile(r"TRACKING\s+([A-Za-z0-9]+)", re.IGNORECASE)
# "Tracking number" / "Numéro de repérage" body labels; accented chars may
# arrive mangled depending on charset handling, so match them loosely
_CANADA_POST_BODY_LABEL_RE = re.compile(
    r"(?:Tracking number|Num.{1,2}ro de rep.{1,2}rage)\s*:?\s*(\d{16}|[A-Za-z]{2}\d{9}[A-Za-z]{2})",
    re.IGNORECASE,
)


def _add_tracking_number(tracking_numbers: list[str], tracking_num: str) -> None:
    tracking_num = (tracking_num or "").strip().upper()
    if not tracking_num:
        return
    if not _CANADA_POST_TRACKING_CANDIDATE_RE.fullmatch(tracking_num):
        return
    if tracking_num in tracking_numbers:
        return
    tracking_numbers.append(tracking_num)


def parse_canada_post(email):
    """Parse Canada Post tracking numbers."""
    tracking_numbers = []
    subject = email.get(EMAIL_ATTR_SUBJECT, 'N/A')

    _LOGGER.debug(f"[CanadaPost] Starting parser - Subject: {subject}")

    soup = BeautifulSoup(email[EMAIL_ATTR_BODY], 'html.parser')
    links = [link.get('href') for link in soup.find_all('a')]
    _LOGGER.debug(f"[CanadaPost] Found {len(links)} links in email body")

    for link in links:
        if not link:
            continue
        link_str = unquote(unescape(str(link)))
        for match in _CANADA_POST_LINK_PARAM_RE.finditer(link_str):
            _add_tracking_number(tracking_numbers, match.group(1))

    _LOGGER.debug("[CanadaPost] Checking subject line for tracking number")
    for match in _CANADA_POST_SUBJECT_RE.finditer(subject or ''):
        _add_tracking_number(tracking_numbers, match.group(1))

    if not tracking_numbers:
        _LOGGER.debug("[CanadaPost] Checking body text for labeled tracking number")
        body_text = soup.get_text(separator=' ')
        for match in _CANADA_POST_BODY_LABEL_RE.finditer(body_text):
            _add_tracking_number(tracking_numbers, match.group(1))

    _LOGGER.debug(f"[CanadaPost] Parser complete - Found {len(tracking_numbers)} tracking number(s)")
    return tracking_numbers
