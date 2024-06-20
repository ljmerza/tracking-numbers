"""Support for Google - Calendar Event Devices."""
from datetime import timedelta, date
import logging
import re

from imapclient import IMAPClient
from mailparser import parse_from_bytes
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_EMAIL, CONF_PASSWORD, CONF_IMAP_SERVER,
    CONF_IMAP_PORT, CONF_SSL, CONF_EMAIL_FOLDER, CONF_DAYS_OLD,
    ATTR_TRACKING_NUMBERS, ATTR_COUNT,
    EMAIL_ATTR_FROM, EMAIL_ATTR_SUBJECT, EMAIL_ATTR_BODY,
    TRACKING_NUMBER_URLS, usps_regex, fedex_regex, ups_regex
)

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
from .parsers.swiss_post import ATTR_SWISS_POST, EMAIL_DOMAIN_SWISS_POST, parse_swiss_post
from .parsers.bespoke_post import ATTR_DSW, EMAIL_DOMAIN_DSW, parse_bespoke_post
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
from .parsers.adafruit import ATTR_ADAFRUIT, EMAIL_DOMAIN_ADAFRUIT, parse_adafruit
from .parsers.thriftbooks import ATTR_THRIFT_BOOKS, EMAIL_DOMAIN_THRIFT_BOOKS, parse_thrift_books
from .parsers.lowes import ATTR_LOWES, EMAIL_DOMAIN_LOWES, parse_lowes

from .parsers.generic import ATTR_GENERIC, EMAIL_DOMAIN_GENERIC, parse_generic

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
    (ATTR_SWISS_POST, EMAIL_DOMAIN_SWISS_POST, parse_swiss_post),
    (ATTR_DSW, EMAIL_DOMAIN_DSW, parse_bespoke_post),
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
    (ATTR_ADAFRUIT, EMAIL_DOMAIN_ADAFRUIT, parse_adafruit),
    (ATTR_THRIFT_BOOKS, EMAIL_DOMAIN_THRIFT_BOOKS, parse_thrift_books),
    (ATTR_LOWES, EMAIL_DOMAIN_LOWES, parse_lowes),
    
    (ATTR_GENERIC, EMAIL_DOMAIN_GENERIC, parse_generic),
]

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'tracking_numbers'

SCAN_INTERVAL = timedelta(seconds=30*60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_DAYS_OLD, default='30'): cv.positive_int,
    vol.Required(CONF_IMAP_SERVER, default='imap.gmail.com'): cv.string,
    vol.Required(CONF_IMAP_PORT, default=993): cv.positive_int,
    vol.Required(CONF_SSL, default=True): cv.boolean,
    vol.Required(CONF_EMAIL_FOLDER, default='INBOX'): cv.string,
})


def find_carrier(tracking_group, email_domain):
    _LOGGER.debug(f'find_carrier email_domain: {email_domain} {tracking_group}')

    link = ""
    carrier = ""

    tracking_number = tracking_group['tracking_number']

    # if tracking number is a url then use that
    if tracking_number.startswith('http'):
        link = tracking_number
        carrier = email_domain

    # if from carrier themself then use that
    elif email_domain == EMAIL_DOMAIN_UPS:
        link = TRACKING_NUMBER_URLS["ups"]
        carrier = "UPS"
    elif email_domain == EMAIL_DOMAIN_FEDEX:
        link = TRACKING_NUMBER_URLS["fedex"]
        carrier = "FedEx"
    elif email_domain == EMAIL_DOMAIN_USPS:
        link = TRACKING_NUMBER_URLS["usps"]
        carrier = "USPS"
    elif email_domain == EMAIL_DOMAIN_DHL:
        link = TRACKING_NUMBER_URLS["dhl"]
        carrier = "DHL"
    elif email_domain == EMAIL_DOMAIN_SWISS_POST:
        link = TRACKING_NUMBER_URLS["swiss_post"]
        carrier = "Swiss Post"
    
    # regex tracking number
    elif re.search(usps_regex, tracking_number) != None:
        link = TRACKING_NUMBER_URLS["usps"]
        carrier = 'USPS'
    elif re.search(ups_regex, tracking_number) != None:
        link = TRACKING_NUMBER_URLS["ups"]
        carrier = 'UPS'
    elif re.search(fedex_regex, tracking_number) != None:
        link = TRACKING_NUMBER_URLS["fedex"]
        carrier = 'FedEx'
        
    # try one more time
    else:
        isNumber = tracking_number.isnumeric()
        length = len(tracking_number)

        if (isNumber and (length == 12 or length == 15 or length == 20)):
            link = TRACKING_NUMBER_URLS["fedex"]
            carrier = "FedEx"
        elif (isNumber and length == 22):
            link = TRACKING_NUMBER_URLS["usps"]
            carrier = "USPS"
        elif (length > 25):
            link = TRACKING_NUMBER_URLS["dhl"]
            carrier = "DHL"
        else:
            link = TRACKING_NUMBER_URLS["unknown"]
            carrier = email_domain

    return {
        'tracking_number': tracking_number,
        'carrier': tracking_group.get('carrier') or carrier,
        'origin': tracking_group.get('origin') or email_domain or carrier,
        'link': tracking_group.get('link') or f'{link}{tracking_number}',
    }

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
):
    """Set up the Tracking Number platform."""
    data = hass.data.get(DOMAIN)
    
    if not data:
        hass.data[DOMAIN] = {
            "ignored_tracking_numbers": [],
        }

    def ignore_tracking_number(call: ServiceCall) -> None:
        _LOGGER.debug('Received ignore_tracking_number', call.data)
        hass.data[DOMAIN]["ignored_tracking_numbers"].append(call.data['tracking_number'])
        
    hass.services.register(DOMAIN, 'ignore_tracking_number', ignore_tracking_number)

    def unignore_tracking_number(call: ServiceCall) -> None:
        _LOGGER.debug('Received unignore_tracking_number', call.data)
        ignored_tracking_numbers = hass.data[DOMAIN]["ignored_tracking_numbers"]
        hass.data[DOMAIN]["ignored_tracking_numbers"] = [x for x in ignored_tracking_numbers if x not in call.data['tracking_number']]

    hass.services.register(DOMAIN, 'unignore_tracking_number', unignore_tracking_number)
    
    _LOGGER.error(config)
    add_entities([TrackingNumberEntity(config, hass)], True)

class TrackingNumberEntity(Entity):
    def __init__(self, config, hass):
        self._attr = {
            ATTR_TRACKING_NUMBERS: {},
	        ATTR_COUNT: 0
        }

        self.hass = hass

        self.imap_server = config[CONF_IMAP_SERVER]
        self.imap_port = config[CONF_IMAP_PORT]
        self.email_address = config[CONF_EMAIL]
        self.password = config[CONF_PASSWORD]
        self.email_folder = config[CONF_EMAIL_FOLDER]
        self.ssl = config[CONF_SSL]
        self.days_old = int(config[CONF_DAYS_OLD])

        self.flag = [u'SINCE', date.today() - timedelta(days=self.days_old)]

    def update(self):
        self._attr = {
            ATTR_TRACKING_NUMBERS: {},
	        ATTR_COUNT: 0
        }

        ignored_tracking_numbers = self.hass.data.get(DOMAIN)["ignored_tracking_numbers"]

        # update to current day
        self.flag = [u'SINCE', date.today() - timedelta(days=self.days_old)]
        _LOGGER.debug(f'flag: {self.flag}')

        emails = []
        server = IMAPClient(self.imap_server, port=self.imap_port, use_uid=True, ssl=self.ssl)

        try:
            server.login(self.email_address, self.password)
            server.select_folder(self.email_folder, readonly=True)
        except Exception as err:
            _LOGGER.error('IMAPClient login error {}'.format(err))
            return False

        try:
            messages = server.search(self.flag)
            for uid, message_data in server.fetch(messages, 'RFC822').items():
                try:
                    mail = parse_from_bytes(message_data[b'RFC822'])
                    
                    emails.append({
                        EMAIL_ATTR_FROM: mail.from_,
                        EMAIL_ATTR_SUBJECT: mail.subject,
                        EMAIL_ATTR_BODY: mail.body
                    })
                except Exception as err:
                    _LOGGER.warning(
                        'mailparser parse_from_bytes error: {}'.format(err))

        except Exception as err:
            _LOGGER.error('IMAPClient update error: {}'.format(err))

        # empty out all parser arrays
        for ATTR, EMAIL_DOMAIN, parser in parsers:
            self._attr[ATTR_TRACKING_NUMBERS][ATTR] = []

        # for each email run each parser and save in the corresponding ATTR
        for email in emails:
            email_from = email[EMAIL_ATTR_FROM]
            _LOGGER.debug(f'parsing email from {email_from}')

            if isinstance(email_from, (list, tuple)):
                email_from = list(email_from)
                email_from = ''.join(list(email_from[0]))
            
            # run through all parsers for each email if email domain matches
            for ATTR, EMAIL_DOMAIN, parser in parsers:
                _LOGGER.debug(f'parsing email for parser {EMAIL_DOMAIN}')
                try:
                    if EMAIL_DOMAIN in email_from:
                        self._attr[ATTR_TRACKING_NUMBERS][ATTR] = self._attr[ATTR_TRACKING_NUMBERS][ATTR] + parser(email=email)
                except Exception as err:
                        _LOGGER.error('{} error: {}'.format(ATTR, err))

        _LOGGER.error(self._attr[ATTR_TRACKING_NUMBERS])

        # format and filter tracking numbers
        for ATTR, EMAIL_DOMAIN, parser in parsers:
            tracking_numbers = self._attr[ATTR_TRACKING_NUMBERS][ATTR]
            
            try:
                _LOGGER.error(f'parsing tracking numbers for {EMAIL_DOMAIN}: {tracking_numbers}')

                # normalize tracking numbers 
                if isinstance(tracking_numbers[0], str) or isinstance(tracking_numbers[0], int):
                    tracking_numbers = [{ 'tracking_number': x } for x in tracking_numbers]
                
                # dont add tracking numbers in ignored_tracking_numbers data
                tracking_numbers = [x for x in tracking_numbers if x['tracking_number'] not in ignored_tracking_numbers]
                
                # for each tracking_number, remove dup objects that have the same tracking_number value
                seen = set()
                unique_tracking_numbers = []
                for x in tracking_numbers:
                    tracking_number = x['tracking_number']
                    if tracking_number not in seen:
                        seen.add(tracking_number)
                        unique_tracking_numbers.append(x)
                tracking_numbers = unique_tracking_numbers
                
                # format tracking numbers to add carrier type
                _LOGGER.debug(f'parsing tracking numbers for {EMAIL_DOMAIN}')
                tracking_numbers = list(map(lambda x: find_carrier(x, EMAIL_DOMAIN), tracking_numbers))
            except Exception as err:
                _LOGGER.error('{} error format and filter: {}'.format(ATTR, err))

            self._attr[ATTR_TRACKING_NUMBERS][ATTR] = tracking_numbers
            self._attr[ATTR_COUNT] += len(tracking_numbers)

        server.logout()

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{}_tracking_numbers'.format(self.email_address)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attr[ATTR_COUNT]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attr

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return 'mdi:email'
