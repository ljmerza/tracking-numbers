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

# Live-status provider selection. 'none' disables status enrichment.
CONF_STATUS_PROVIDER = 'status_provider'
STATUS_PROVIDER_NONE = 'none'
STATUS_PROVIDER_TRACKINGMORE = 'trackingmore'
STATUS_PROVIDER_CARRIERS = 'carriers'
DEFAULT_STATUS_PROVIDER = STATUS_PROVIDER_NONE

# Carrier-direct (free) API credentials. USPS/UPS/FedEx use OAuth2 client
# credentials (id + secret); DHL uses a single API key. Each is optional — a
# carrier with no credentials configured is simply skipped.
CONF_USPS_CLIENT_ID = 'usps_client_id'
CONF_USPS_CLIENT_SECRET = 'usps_client_secret'
CONF_UPS_CLIENT_ID = 'ups_client_id'
CONF_UPS_CLIENT_SECRET = 'ups_client_secret'
CONF_FEDEX_CLIENT_ID = 'fedex_client_id'
CONF_FEDEX_CLIENT_SECRET = 'fedex_client_secret'
CONF_DHL_API_KEY = 'dhl_api_key'

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

# --- Carrier-direct (free) live-status integration (optional) -----------------
# Persists {tracking_number: {delivery_status, status, ...}} of last-known status
# so already-delivered packages aren't re-queried (respects tight carrier rate
# limits) and status survives restarts.
STORE_KEY_CARRIER_STATUS = 'carrier_status'

# Seconds to wait for a carrier API response.
CARRIER_TIMEOUT = 15
# Cap total carrier lookups per poll cycle (protects the tightest free tiers:
# USPS ~60/hr, DHL 250/day). Remaining packages are looked up on later cycles.
CARRIER_MAX_LOOKUPS_PER_CYCLE = 20
# Minimum seconds between successive calls to the SAME carrier (DHL enforces
# ~1 call / 5 s on its free tier; the others are far more generous).
CARRIER_MIN_CALL_SPACING = {
    'usps': 1.0,
    'ups': 0.5,
    'fedex': 0.2,
    'dhl': 5.0,
}

# Production hosts / endpoints (see plan for sources). Token lifetimes are read
# from each response rather than hardcoded.
USPS_TOKEN_URL = 'https://apis.usps.com/oauth2/v3/token'
USPS_TRACK_URL = 'https://apis.usps.com/tracking/v3/tracking/{number}'
UPS_TOKEN_URL = 'https://onlinetools.ups.com/security/v1/oauth/token'
UPS_TRACK_URL = 'https://onlinetools.ups.com/api/track/v1/details/{number}'
FEDEX_TOKEN_URL = 'https://apis.fedex.com/oauth/token'
FEDEX_TRACK_URL = 'https://apis.fedex.com/track/v1/trackingnumbers'
DHL_TRACK_URL = 'https://api-eu.dhl.com/track/shipments'

# Normalized delivery_status enum written to packages, aligned with the card's
# getStatusMeta(): delivered / out_for_delivery / transit / pending / exception /
# notfound. Cards on an older version that don't know `out_for_delivery` fall back
# to a neutral chip but still show the "Out for Delivery" label.
CARRIER_STATUS_LABELS = {
    'pending': 'Pending',
    'transit': 'In Transit',
    'out_for_delivery': 'Out for Delivery',
    'delivered': 'Delivered',
    'exception': 'Exception',
    'notfound': 'Not Found',
}

# DHL statusCode (stable 5-value enum) -> normalized status.
DHL_STATUS_MAP = {
    'pre-transit': 'pending',
    'transit': 'transit',
    'delivered': 'delivered',
    'failure': 'exception',
    'unknown': 'notfound',
}
# USPS statusCategory -> normalized status.
USPS_STATUS_MAP = {
    'pre-shipment': 'pending',
    'accepted': 'transit',
    'in transit': 'transit',
    'out for delivery': 'out_for_delivery',
    'delivered': 'delivered',
    'alert': 'exception',
    'delivery attempt': 'exception',
    'available for pickup': 'out_for_delivery',
}
# UPS currentStatus.type (single letter) -> normalized status. Within 'D', the
# description disambiguates delivered vs out-for-delivery (handled in code).
UPS_STATUS_MAP = {
    'M': 'pending',
    'I': 'transit',
    'U': 'transit',
    'D': 'delivered',
    'X': 'exception',
}
# FedEx latestStatusDetail.derivedCode (2-letter) -> normalized status. Unlisted
# codes default to 'transit' (see carriers.py).
FEDEX_STATUS_MAP = {
    'OC': 'pending',
    'DL': 'delivered',
    'OD': 'out_for_delivery',
    'AD': 'out_for_delivery',
    'DE': 'exception',
    'SE': 'exception',
    'DY': 'exception',
    'EA': 'exception',
    'CA': 'exception',
    'RS': 'exception',
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
