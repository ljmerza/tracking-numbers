"""Constants for Tracking Numbers integration."""

# Domain
DOMAIN = "tracking_numbers"

# Configuration keys
CONF_EMAIL = 'email'
CONF_PASSWORD = 'password'
CONF_IMAP_SERVER = 'imap_server'
CONF_IMAP_PORT = 'imap_port'
CONF_EMAIL_FOLDER = 'folder'
CONF_SSL = 'ssl'
CONF_USE_SSL = 'use_ssl'  # New name for consistency
CONF_DAYS_OLD = 'days_old'
CONF_SCAN_INTERVAL = 'scan_interval'
CONF_MAX_PACKAGES = 'max_packages'

# Defaults
DEFAULT_IMAP_SERVER = 'imap.gmail.com'
DEFAULT_IMAP_PORT = 993
DEFAULT_USE_SSL = True
DEFAULT_FOLDER = 'INBOX'
DEFAULT_DAYS_OLD = 30
DEFAULT_SCAN_INTERVAL = 30  # minutes
DEFAULT_MAX_PACKAGES = 100

ATTR_COUNT = 'count'
ATTR_TRACKING_NUMBERS = 'tracking_numbers'

EMAIL_ATTR_FROM = 'from'
EMAIL_ATTR_SUBJECT = 'subject'
EMAIL_ATTR_BODY = 'body'

USPS_TRACKING_NUMBER_REGEX = r"\b(94\d{20}|\d{4}\s\d{4}\s\d{4}\s\d{4}\s\d{4}\s\d{2})\b"
UPS_TRACKING_NUMBER_REGEX = r"\b(1Z[A-HJ-NP-Z0-9]{16})\b"
FEDEX_TRACKING_NUMBER_REGEX = r"\b(\d{12})\b"

EMAIL_DOMAIN_REGEX = r"@([\w.-]+)"

TRACKING_NUMBER_URLS = {
  'ups': "https://www.ups.com/track?loc=en_US&tracknum=",
  'usps': "https://tools.usps.com/go/TrackConfirmAction?tLabels=",
  'fedex': "https://www.fedex.com/apps/fedextrack/?tracknumbers=",
  'dhl': 'https://www.logistics.dhl/us-en/home/tracking/tracking-parcel.html?submit=1&tracking-id=',
  'swiss_post': 'https://www.swisspost.ch/track?formattedParcelCodes=',
  'unknown': 'https://www.google.com/search?q=',
}

   
usps_pattern = [
    '^(94|93|92|94|95)[0-9]{20}$',
    '^(94|93|92|94|95)[0-9]{22}$',
    '^(70|14|23|03)[0-9]{14}$',
    '^(M0|82)[0-9]{8}$',
    '^([A-Z]{2})[0-9]{9}([A-Z]{2})$'
]

ups_pattern = [
    '^(1Z)[0-9A-Z]{16}$',
    '^(T)+[0-9A-Z]{10}$',
    '^[0-9]{9}$',
    '^[0-9]{26}$'
]

fedex_pattern = [
    '^[0-9]{20}$',
    '^[0-9]{15}$',
    '^[0-9]{12}$',
    '^[0-9]{22}$'
]

usps_regex = "(" + ")|(".join(usps_pattern) + ")"
fedex_regex = "(" + ")|(".join(fedex_pattern) + ")"
ups_regex = "(" + ")|(".join(ups_pattern) + ")"