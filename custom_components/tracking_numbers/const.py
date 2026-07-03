"""Constants for Tracking Numbers integration."""

# Domain
DOMAIN = "tracking_numbers"

# Services
SERVICE_ADD_MANUAL_TRACKING_NUMBER = "add_manual_tracking_number"
SERVICE_REMOVE_TRACKING_NUMBER = "remove_tracking_number"

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
# Optional TrackingMore API key; when empty, live status lookups are disabled.
CONF_TRACKINGMORE_API_KEY = 'trackingmore_api_key'

# Defaults
DEFAULT_IMAP_SERVER = 'imap.gmail.com'
DEFAULT_IMAP_PORT = 993
DEFAULT_USE_SSL = True
DEFAULT_FOLDER = 'INBOX'
DEFAULT_DAYS_OLD = 30
DEFAULT_SCAN_INTERVAL = 30  # minutes
DEFAULT_MAX_PACKAGES = 100

# Seconds to wait for an IMAP server to respond on connect/login probes.
IMAP_CONNECTION_TIMEOUT = 10

ATTR_COUNT = 'count'
ATTR_TRACKING_NUMBERS = 'tracking_numbers'

EMAIL_ATTR_FROM = 'from'
EMAIL_ATTR_SUBJECT = 'subject'
EMAIL_ATTR_BODY = 'body'
EMAIL_ATTR_DATE = 'date'

USPS_TRACKING_NUMBER_REGEX = r"\b(94\d{20}|\d{4}\s\d{4}\s\d{4}\s\d{4}\s\d{4}\s\d{2})\b"
UPS_TRACKING_NUMBER_REGEX = r"\b(1Z[A-HJ-NP-Z0-9]{16})\b"
FEDEX_TRACKING_NUMBER_REGEX = r"\b(\d{12})\b"

EMAIL_DOMAIN_REGEX = r"@([\w.-]+)"

TRACKING_NUMBER_URLS = {
  'ups': "https://www.ups.com/track?loc=en_US&tracknum=",
  'usps': "https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1=",
  'fedex': "https://www.fedex.com/apps/fedextrack/?tracknumbers=",
  'dhl': 'https://www.logistics.dhl/us-en/home/tracking/tracking-parcel.html?submit=1&tracking-id=',
  'swiss_post': 'https://www.swisspost.ch/track?formattedParcelCodes=',
  'unknown': 'https://www.google.com/search?q=',
}

CARRIER_LINK_HINTS = {
  'UPS': ('ups.com',),
  'USPS': ('usps.com', 'postalpro.usps.com', 'mailviewrecipient.com'),
  'FedEx': ('fedex.com', 'fxtracking', 'fedexdeliverymanager'),
  'DHL': ('dhl.com', 'dhl.de', 'dhlparcel', 'dhlglobalmail'),
  'Swiss Post': ('swisspost.ch', 'swiss-post', 'post.ch'),
}

MANUAL_RETAILER_CODE = 'manual_entry'
MANUAL_RETAILER_NAME = 'Manual Entry'
MANUAL_ORIGIN_FALLBACK = 'Manual Entry'
MANUAL_CARRIER_FALLBACK = 'Custom'

# Human-readable names for parser ATTR slugs. Fallback is title-cased ATTR.
# Only entries that don't title-case cleanly need to be listed here.
RETAILER_DISPLAY_NAMES = {
    'ups': 'UPS',
    'usps': 'USPS',
    'fedex': 'FedEx',
    'dhl': 'DHL',
    'ebay': 'eBay',
    'paypal': 'PayPal',
    'ali_express': 'AliExpress',
    'amazon_de': 'Amazon DE',
    'bh_photo': 'B&H Photo',
    'dsw': 'DSW',
    'bespoke_post': 'Bespoke Post',
    'swiss_post': 'Swiss Post',
    'adam_and_eve': 'Adam & Eve',
    'gamestop': 'GameStop',
    'litter_robot': 'Litter-Robot',
    'smartesthouse': 'The Smartest House',
    'house_of_noa': 'House of Noa',
    'pledgebox': 'PledgeBox',
    'thrift_books': 'ThriftBooks',
    'switchbot': 'SwitchBot',
    'newegg': 'Newegg',
    'rockauto': 'RockAuto',
    'lowes': "Lowe's",
    'nuleaf': 'NuLeaf',
    'hue': 'Philips Hue',
    'generic': 'Generic',
}
STORE_KEY_MANUAL_PACKAGES = 'manual_packages'
STORE_KEY_HIDDEN_TRACKING_NUMBERS = 'hidden_tracking_numbers'
LEGACY_STORE_KEY_IGNORED = 'ignored_tracking_numbers'
# Persists {tracking_number: {courier_code, delivery_status, ...}} for numbers
# already registered with TrackingMore, so we don't re-register (re-spend credits).
STORE_KEY_TRACKINGMORE = 'trackingmore'

# --- TrackingMore live-status integration (optional) --------------------------
TRACKINGMORE_BASE_URL = 'https://api.trackingmore.com/v4'
# Seconds to wait for a TrackingMore API response.
TRACKINGMORE_TIMEOUT = 15
# TrackingMore allows ~3 create requests/second; pause between single creates.
TRACKINGMORE_CREATE_DELAY = 0.35
# Max tracking numbers per GET /trackings/get batch.
TRACKINGMORE_GET_BATCH = 40
# Cap on NEW registrations per poll cycle. A credit is spent per new number, and
# free plans are as small as ~50 credits/month, so a burst of new packages must
# not drain the whole budget in one cycle; remaining numbers register next cycle.
TRACKINGMORE_MAX_NEW_PER_CYCLE = 10

# Maps the integration's derived carrier_code (coordinator: carrier.lower()
# .replace(' ', '_')) to TrackingMore courier codes. Packages whose carrier_code
# is absent here are skipped (they're usually retailer order numbers, not
# carrier-trackable). usps/ups/fedex/dhl are standard TrackingMore codes.
TRACKINGMORE_COURIER_MAP = {
    'usps': 'usps',
    'ups': 'ups',
    'fedex': 'fedex',
    'dhl': 'dhl',
    # 'swiss_post': 'post-ch',  # UNVERIFIED code; confirm via GET /couriers/all
    #                             before enabling so we don't send a bad courier_code.
}

# TrackingMore delivery_status enum -> human-readable label written to `status`.
TRACKINGMORE_STATUS_LABELS = {
    'pending': 'Pending',
    'notfound': 'Not Found',
    'inforeceived': 'Info Received',
    'transit': 'In Transit',
    'pickup': 'Out for Pickup',
    'delivered': 'Delivered',
    'undelivered': 'Undelivered',
    'exception': 'Exception',
    'expired': 'Expired',
}

   
usps_pattern = [
    '^(94|93|92|94|95)[0-9]{20}$',
    '^(94|93|92|94|95)[0-9]{22}$',
    '^(70|14|23|03)[0-9]{14}$',
    '^(M0|82)[0-9]{8}$',
    '^([A-Z]{2})[0-9]{9}([A-Z]{2})$',
    '^(420)[0-9]{27}$'
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
