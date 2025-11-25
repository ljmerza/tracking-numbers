"""Parsers list and carrier detection for Tracking Numbers integration."""
import logging
import re
from urllib.parse import urlparse

from .const import (
    EMAIL_ATTR_FROM,
    EMAIL_ATTR_SUBJECT,
    EMAIL_ATTR_BODY,
    TRACKING_NUMBER_URLS,
    CARRIER_LINK_HINTS,
    usps_regex,
    fedex_regex,
    ups_regex,
)

# Parser imports
from .parsers.ups import ATTR_UPS, EMAIL_DOMAIN_UPS, parse_ups
from .parsers.amazon import ATTR_AMAZON, EMAIL_DOMAIN_AMAZON, parse_amazon
from .parsers.amazon_de import ATTR_AMAZON_DE, EMAIL_DOMAIN_AMAZON_DE, parse_amazon_de
from .parsers.fedex import ATTR_FEDEX, EMAIL_DOMAIN_FEDEX, parse_fedex
from .parsers.paypal import ATTR_PAYPAL, EMAIL_DOMAIN_PAYPAL, parse_paypal
from .parsers.usps import ATTR_USPS, EMAIL_DOMAIN_USPS, parse_usps
from .parsers.ali_express import ATTR_ALI_EXPRESS, EMAIL_DOMAIN_ALI_EXPRESS, parse_ali_express
from .parsers.newegg import ATTR_NEWEGG, EMAIL_DOMAIN_NEWEGG, parse_newegg
from .parsers.rockauto import ATTR_ROCKAUTO, EMAIL_DOMAIN_ROCKAUTO, parse_rockauto
from .parsers.bh_photo import ATTR_BH_PHOTO, EMAIL_DOMAIN_BH_PHOTO, parse_bh_photo
from .parsers.ebay import ATTR_EBAY, EMAIL_DOMAIN_EBAY, parse_ebay
from .parsers.dhl import ATTR_DHL, EMAIL_DOMAIN_DHL, parse_dhl
from .parsers.hue import ATTR_HUE, EMAIL_DOMAIN_HUE, parse_hue
from .parsers.google_express import ATTR_GOOGLE_EXPRESS, EMAIL_DOMAIN_GOOGLE_EXPRESS, parse_google_express
from .parsers.western_digital import ATTR_WESTERN_DIGITAL, EMAIL_DOMAIN_WESTERN_DIGITAL, parse_western_digital
from .parsers.monoprice import ATTR_MONOPRICE, EMAIL_DOMAIN_MONOPRICE, parse_monoprice
from .parsers.georgia_power import ATTR_GEORGIA_POWER, EMAIL_DOMAIN_GEORGIA_POWER, parse_georgia_power
from .parsers.best_buy import ATTR_BEST_BUY, EMAIL_DOMAIN_BEST_BUY, parse_best_buy
from .parsers.dollar_shave_club import ATTR_DOLLAR_SHAVE_CLUB, EMAIL_DOMAIN_DOLLAR_SHAVE_CLUB, parse_dollar_shave_club
from .parsers.nuleaf import ATTR_NULEAF, EMAIL_DOMAIN_NULEAF, parse_nuleaf
from .parsers.timeless import ATTR_TIMELESS, EMAIL_DOMAIN_TIMLESS, parse_timeless
from .parsers.dsw import ATTR_DSW, EMAIL_DOMAIN_DSW, parse_dsw
from .parsers.wyze import ATTR_WYZE, EMAIL_DOMAIN_WYZE, parse_wyze
from .parsers.reolink import ATTR_REOLINK, EMAIL_DOMAIN_REOLINK, parse_reolink
from .parsers.chewy import ATTR_CHEWY, EMAIL_DOMAIN_CHEWY, parse_chewy
from .parsers.groupon import ATTR_GROUPON, EMAIL_DOMAIN_GROUPON, parse_groupon
from .parsers.zazzle import ATTR_ZAZZLE, EMAIL_DOMAIN_ZAZZLE, parse_zazzle
from .parsers.home_depot import ATTR_HOME_DEPOT, EMAIL_DOMAIN_HOME_DEPOT, parse_home_depot
from .parsers.house_of_noa import ATTR_HOUSE_OF_NOA, EMAIL_DOMAIN_HOUSE_OF_NOA, parse_house_of_noa
from .parsers.swiss_post import ATTR_SWISS_POST, EMAIL_DOMAIN_SWISS_POST, parse_swiss_post
from .parsers.bespoke_post import ATTR_DSW as ATTR_BESPOKE, EMAIL_DOMAIN_DSW as EMAIL_DOMAIN_BESPOKE, parse_bespoke_post
from .parsers.manta_sleep import ATTR_MANTA_SLEEP, EMAIL_DOMAIN_MANTA_SLEEP, parse_manta_sleep
from .parsers.prusa import ATTR_PRUSA, EMAIL_DOMAIN_PRUSA, parse_prusa
from .parsers.adam_eve import ATTR_ADAM_AND_EVE, EMAIL_DOMAIN_ADAM_AND_EVE, parse_adam_and_eve
from .parsers.target import ATTR_TARGET, EMAIL_DOMAIN_TARGET, parse_target
from .parsers.gamestop import ATTR_GAMESTOP, EMAIL_DOMAIN_GAMESTOP, parse_gamestop
from .parsers.litter_robot import ATTR_LITTER_ROBOT, EMAIL_DOMAIN_LITTER_ROBOT, parse_litter_robot
from .parsers.the_smartest_house import ATTR_SMARTEST_HOUSE, EMAIL_DOMAIN_SMARTEST_HOUSE, parse_smartest_house
from .parsers.ubiquiti import ATTR_UBIQUITI, EMAIL_DOMAIN_UBIQUITI, parse_ubiquiti
from .parsers.nintendo import ATTR_NINTENDO, EMAIL_DOMAIN_NINTENDO, parse_nintendo
from .parsers.pledgebox import ATTR_PLEDGEBOX, EMAIL_DOMAIN_PLEDGEBOX, parse_pledgebox
from .parsers.guitar_center import ATTR_GUITAR_CENTER, EMAIL_DOMAIN_GUITAR_CENTER, parse_guitar_center
from .parsers.sony import ATTR_SONY, EMAIL_DOMAIN_SONY, parse_sony
from .parsers.sylvane import ATTR_SYLVANE, EMAIL_DOMAIN_SYLVANE, parse_sylvane
from .parsers.loog_guitars import ATTR_LOOG_GUITARS, EMAIL_DOMAIN_LOOG_GUITARS, parse_loog_guitars
from .parsers.adafruit import ATTR_ADAFRUIT, EMAIL_DOMAIN_ADAFRUIT, parse_adafruit
from .parsers.thriftbooks import ATTR_THRIFT_BOOKS, EMAIL_DOMAIN_THRIFT_BOOKS, parse_thrift_books
from .parsers.etsy import ATTR_ETSY, EMAIL_DOMAIN_ETSY, parse_etsy
from .parsers.moen import ATTR_MOEN, EMAIL_DOMAIN_MOEN, parse_moen
from .parsers.lowes import ATTR_LOWES, EMAIL_DOMAIN_LOWES, parse_lowes
from .parsers.wayfair import ATTR_WAYFAIR, EMAIL_DOMAIN_WAYFAIR, parse_wayfair
from .parsers.generic import ATTR_GENERIC, EMAIL_DOMAIN_GENERIC, parse_generic

_LOGGER = logging.getLogger(__name__)

# Parsers list - used by coordinator and sensor
parsers = [
    (ATTR_UPS, EMAIL_DOMAIN_UPS, parse_ups),
    (ATTR_FEDEX, EMAIL_DOMAIN_FEDEX, parse_fedex),
    (ATTR_AMAZON, EMAIL_DOMAIN_AMAZON, parse_amazon),
    (ATTR_AMAZON_DE, EMAIL_DOMAIN_AMAZON_DE, parse_amazon_de),
    (ATTR_PAYPAL, EMAIL_DOMAIN_PAYPAL, parse_paypal),
    (ATTR_USPS, EMAIL_DOMAIN_USPS, parse_usps),
    (ATTR_ALI_EXPRESS, EMAIL_DOMAIN_ALI_EXPRESS, parse_ali_express),
    (ATTR_NEWEGG, EMAIL_DOMAIN_NEWEGG, parse_newegg),
    (ATTR_ROCKAUTO, EMAIL_DOMAIN_ROCKAUTO, parse_rockauto),
    (ATTR_BH_PHOTO, EMAIL_DOMAIN_BH_PHOTO, parse_bh_photo),
    (ATTR_EBAY, EMAIL_DOMAIN_EBAY, parse_ebay),
    (ATTR_DHL, EMAIL_DOMAIN_DHL, parse_dhl),
    (ATTR_HUE, EMAIL_DOMAIN_HUE, parse_hue),
    (ATTR_GOOGLE_EXPRESS, EMAIL_DOMAIN_GOOGLE_EXPRESS, parse_google_express),
    (ATTR_WESTERN_DIGITAL, EMAIL_DOMAIN_WESTERN_DIGITAL, parse_western_digital),
    (ATTR_MONOPRICE, EMAIL_DOMAIN_MONOPRICE, parse_monoprice),
    (ATTR_GEORGIA_POWER, EMAIL_DOMAIN_GEORGIA_POWER, parse_georgia_power),
    (ATTR_BEST_BUY, EMAIL_DOMAIN_BEST_BUY, parse_best_buy),
    (ATTR_DOLLAR_SHAVE_CLUB, EMAIL_DOMAIN_DOLLAR_SHAVE_CLUB, parse_dollar_shave_club),
    (ATTR_NULEAF, EMAIL_DOMAIN_NULEAF, parse_nuleaf),
    (ATTR_TIMELESS, EMAIL_DOMAIN_TIMLESS, parse_timeless),
    (ATTR_DSW, EMAIL_DOMAIN_DSW, parse_dsw),
    (ATTR_WYZE, EMAIL_DOMAIN_WYZE, parse_wyze),
    (ATTR_REOLINK, EMAIL_DOMAIN_REOLINK, parse_reolink),
    (ATTR_CHEWY, EMAIL_DOMAIN_CHEWY, parse_chewy),
    (ATTR_GROUPON, EMAIL_DOMAIN_GROUPON, parse_groupon),
    (ATTR_ZAZZLE, EMAIL_DOMAIN_ZAZZLE, parse_zazzle),
    (ATTR_HOME_DEPOT, EMAIL_DOMAIN_HOME_DEPOT, parse_home_depot),
    (ATTR_HOUSE_OF_NOA, EMAIL_DOMAIN_HOUSE_OF_NOA, parse_house_of_noa),
    (ATTR_SWISS_POST, EMAIL_DOMAIN_SWISS_POST, parse_swiss_post),
    (ATTR_BESPOKE, EMAIL_DOMAIN_BESPOKE, parse_bespoke_post),
    (ATTR_MANTA_SLEEP, EMAIL_DOMAIN_MANTA_SLEEP, parse_manta_sleep),
    (ATTR_PRUSA, EMAIL_DOMAIN_PRUSA, parse_prusa),
    (ATTR_ADAM_AND_EVE, EMAIL_DOMAIN_ADAM_AND_EVE, parse_adam_and_eve),
    (ATTR_TARGET, EMAIL_DOMAIN_TARGET, parse_target),
    (ATTR_GAMESTOP, EMAIL_DOMAIN_GAMESTOP, parse_gamestop),
    (ATTR_LITTER_ROBOT, EMAIL_DOMAIN_LITTER_ROBOT, parse_litter_robot),
    (ATTR_SMARTEST_HOUSE, EMAIL_DOMAIN_SMARTEST_HOUSE, parse_smartest_house),
    (ATTR_UBIQUITI, EMAIL_DOMAIN_UBIQUITI, parse_ubiquiti),
    (ATTR_NINTENDO, EMAIL_DOMAIN_NINTENDO, parse_nintendo),
    (ATTR_PLEDGEBOX, EMAIL_DOMAIN_PLEDGEBOX, parse_pledgebox),
    (ATTR_GUITAR_CENTER, EMAIL_DOMAIN_GUITAR_CENTER, parse_guitar_center),
    (ATTR_SONY, EMAIL_DOMAIN_SONY, parse_sony),
    (ATTR_SYLVANE, EMAIL_DOMAIN_SYLVANE, parse_sylvane),
    (ATTR_LOOG_GUITARS, EMAIL_DOMAIN_LOOG_GUITARS, parse_loog_guitars),
    (ATTR_ADAFRUIT, EMAIL_DOMAIN_ADAFRUIT, parse_adafruit),
    (ATTR_THRIFT_BOOKS, EMAIL_DOMAIN_THRIFT_BOOKS, parse_thrift_books),
    (ATTR_ETSY, EMAIL_DOMAIN_ETSY, parse_etsy),
    (ATTR_MOEN, EMAIL_DOMAIN_MOEN, parse_moen),
    (ATTR_LOWES, EMAIL_DOMAIN_LOWES, parse_lowes),
    (ATTR_WAYFAIR, EMAIL_DOMAIN_WAYFAIR, parse_wayfair),
    (ATTR_GENERIC, EMAIL_DOMAIN_GENERIC, parse_generic),
]


EMAIL_DOMAIN_CARRIER_MAP = {
    EMAIL_DOMAIN_UPS: 'UPS',
    EMAIL_DOMAIN_FEDEX: 'FedEx',
    EMAIL_DOMAIN_USPS: 'USPS',
    EMAIL_DOMAIN_DHL: 'DHL',
    EMAIL_DOMAIN_SWISS_POST: 'Swiss Post',
}


def _carrier_from_link(link: str | None) -> str | None:
    """Infer carrier from tracking link."""
    if not link:
        return None
    link_str = str(link).strip()
    if not link_str:
        return None

    lower_link = link_str.lower()
    parsed = urlparse(lower_link if lower_link.startswith(('http://', 'https://')) else f'https://{lower_link}')
    for carrier, hints in CARRIER_LINK_HINTS.items():
        for hint in hints:
            if not hint:
                continue
            if hint in lower_link:
                return carrier
            if parsed.netloc and hint in parsed.netloc:
                return carrier
            if parsed.path and hint in parsed.path:
                return carrier
    return None


def _tracking_link_for(carrier: str, tracking_number: str) -> str:
    """Build a tracking URL for a carrier."""
    key = (carrier or '').lower().replace(' ', '_')
    base = TRACKING_NUMBER_URLS.get(key, TRACKING_NUMBER_URLS['unknown'])
    return f'{base}{tracking_number}'


def find_carrier(tracking_group, email_domain):
    """Determine carrier from tracking number and email domain."""
    _LOGGER.debug(f'find_carrier email_domain: {email_domain} {tracking_group}')

    tracking_number = str(tracking_group.get('tracking_number', '') or '').strip()
    tracking_upper = tracking_number.upper()
    tracking_lower = tracking_number.lower()

    link = tracking_group.get('link') or ''
    carrier = tracking_group.get('carrier') or ''

    if tracking_lower.startswith('http://') or tracking_lower.startswith('https://'):
        link = tracking_number
        if not carrier:
            carrier = _carrier_from_link(link)

    if not carrier and link:
        carrier = _carrier_from_link(link)

    if not carrier:
        carrier = EMAIL_DOMAIN_CARRIER_MAP.get(email_domain)

    if not carrier and not tracking_lower.startswith('http'):
        if re.search(usps_regex, tracking_upper):
            carrier = 'USPS'
        elif re.search(ups_regex, tracking_upper):
            carrier = 'UPS'
        elif re.search(fedex_regex, tracking_upper):
            carrier = 'FedEx'

    if not carrier and tracking_upper.isdigit():
        length = len(tracking_upper)
        if length in (12, 15, 20):
            carrier = 'FedEx'
        elif length in (22, 30):
            carrier = 'USPS'
        elif length >= 26:
            carrier = 'DHL'

    if not carrier:
        carrier = email_domain or 'Unknown'

    final_link = tracking_group.get('link') or link or _tracking_link_for(carrier, tracking_number)

    if final_link and 'qtc_tLabels1' in final_link and 'qtc_tLabels1=' not in final_link:
        prefix, _, remainder = final_link.partition('qtc_tLabels1')
        final_link = f"{prefix}qtc_tLabels1={tracking_number}"

    return {
        'tracking_number': tracking_number,
        'carrier': tracking_group.get('carrier') or carrier,
        'origin': tracking_group.get('origin') or email_domain or carrier,
        'link': final_link,
    }
