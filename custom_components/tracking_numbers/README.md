# Tracking Numbers Integration v2.0

Modern Home Assistant integration for tracking package deliveries by parsing email notifications.

## Features

- 📦 **50+ Retailer Parsers** - Amazon, eBay, FedEx, UPS, USPS, and more
- 🔄 **Auto-Discovery** - Automatically detects tracking numbers in emails
- 📊 **Simple Data Structure** - Flat array for easy custom card development
- ⏱️ **Timestamp Tracking** - Know when packages were first/last seen
- 🚚 **Live Delivery Status** (optional) - Real-time status via TrackingMore when an API key is provided
- 🎛️ **Configurable Options** - Scan interval, days to search, max packages
- 🔧 **Services** - Ignore/unignore tracking numbers, force refresh

## Installation

1. Copy this folder to `/config/custom_components/tracking_numbers/`
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for "Tracking Numbers"
5. Enter your email credentials

### Gmail Setup

Gmail requires an **app-specific password**:

1. Enable 2-Step Verification on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Generate a new app password for "Home Assistant"
4. Use this password in the integration (not your regular password)

### Settings

- **IMAP Server:** `imap.gmail.com` (default)
- **IMAP Port:** `993` (default)
- **SSL:** Enabled (recommended)

## Configuration Options

After setup, click **Configure**. The options menu has three sections:

- **Scan settings** — Days to scan (1–90), Email folder (default INBOX), Scan interval (5–1440 min), Max packages (10–500).
- **Live status provider** — choose `None` (default), `TrackingMore`, or `Carrier-direct`; plus the TrackingMore API key.
- **Carrier API credentials** — free per-carrier credentials (used when the provider is Carrier-direct).

## Live Delivery Status (optional)

By default the integration only *extracts* tracking numbers from email. Optionally it can fetch **live
delivery status** for packages shipped by recognized carriers, via one of two providers selected under
**Configure → Live status provider**.

- **Scope:** only packages resolved to a real carrier (USPS, UPS, FedEx, DHL) are looked up. Retailer
  order numbers (Amazon, Chewy, etc.) are skipped — they aren't carrier-trackable.
- **Fields added** to each enriched package: `status` (readable label, e.g. "In Transit", "Out for
  Delivery"), `delivery_status` (enum: `pending`, `transit`, `out_for_delivery`, `delivered`,
  `exception`, `notfound`, plus TrackingMore's finer values), `estimated_delivery` (date), and
  `status_updated` (ISO timestamp).
- **Disabled by default:** with the provider set to `None`, behavior is unchanged (email extraction only).

### Provider: Carrier-direct (free)

Query each carrier's own free developer API — **zero cost**. Set the provider to *Carrier-direct* and enter
credentials under **Configure → Carrier API credentials** for the carriers you use (leave others blank):

| Carrier | Credentials | Get them at |
|---|---|---|
| USPS | OAuth consumer key + secret (add the *Tracking* API to your app) | https://developers.usps.com/ |
| UPS | OAuth client ID + secret | https://developer.ups.com/ |
| FedEx | API key + secret key (Track API) | https://developer.fedex.com/ |
| DHL | one API key (Shipment Tracking – Unified) | https://developer.dhl.com/ |

Already-delivered packages aren't re-queried, and calls are spaced/capped per carrier to respect the free
tiers (e.g. USPS ~60/hr, DHL 250/day, ~1 call/5s).

### Provider: TrackingMore (paid credits)

Supply a [TrackingMore](https://www.trackingmore.com/) API key. TrackingMore deducts **one credit per
unique tracking number + courier registered**; each number is registered only **once** (cached), then
re-read for free, with new registrations capped per cycle.

## Data Structure

The sensor provides a **flat packages array** optimized for custom cards:

```json
{
  "count": 3,
  "packages": [
    {
      "tracking_number": "1Z999AA10123456784",
      "carrier": "UPS",
      "carrier_code": "ups",
      "retailer": "Amazon",
      "retailer_code": "amazon_com",
      "link": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "first_seen": "2025-10-25T10:30:00Z",
      "last_updated": "2025-10-28T14:22:00Z",

      "status": "In Transit",
      "delivery_status": "transit",
      "estimated_delivery": "2025-10-30",
      "status_updated": "2025-10-28T14:22:00Z"
    }
  ],
  "summary": {
    "by_carrier": {"UPS": 2, "FedEx": 1},
    "by_retailer": {"Amazon": 2, "eBay": 1}
  },
  "last_update": "2025-10-28T14:22:00Z"
}
```

**Note on status fields:** `status`, `delivery_status`, `estimated_delivery`, and `status_updated` are
only present when a TrackingMore API key is configured (or `status` when set manually). See
[Live Delivery Status](#live-delivery-status-trackingmore).

**Note on `retailer`:** the retailer is derived from which parser matched the shipment email, i.e. who sent the notification. When the retailer emails you directly (e.g. Amazon's shipment notification), `retailer` is the retailer. When only the carrier emails you (e.g. a bare USPS Informed Delivery alert with no retailer context), `retailer` will be the carrier name — there's no way to recover the original store from the carrier's email alone. Use `retailer_code` for stable filtering (e.g. `amazon_com`, `usps_com`); use `retailer` for display.

### Custom Card Example

```javascript
const packages = this.hass.states['sensor.user_example_com_tracking_numbers'].attributes.packages || [];

// Simple iteration
packages.forEach(pkg => {
    console.log(`${pkg.carrier}: ${pkg.tracking_number}`);
});

// Filter by carrier
const upsPackages = packages.filter(p => p.carrier_code === 'ups');

// Sort by date (newest first)
packages.sort((a, b) => new Date(b.first_seen) - new Date(a.first_seen));
```

### Template Card Example

```yaml
type: markdown
content: |
  {% set pkgs = state_attr('sensor.user_example_com_tracking_numbers', 'packages') | default([]) %}
  ## Packages ({{ pkgs | length }})
  {% for pkg in pkgs | sort(attribute='first_seen', reverse=true) %}
  - **{{ pkg.carrier }}**: [{{ pkg.tracking_number }}]({{ pkg.link }})
    *from {{ pkg.retailer }}* - {{ pkg.first_seen | as_timestamp | timestamp_custom('%b %d') }}
  {% endfor %}
```

## Services

### Ignore Tracking Number

Hide a tracking number from the list:

```yaml
service: tracking_numbers.ignore_tracking_number
data:
  tracking_number: "1Z999AA10123456784"
```

### Unignore Tracking Number

Restore a previously ignored tracking number:

```yaml
service: tracking_numbers.unignore_tracking_number
data:
  tracking_number: "1Z999AA10123456784"
```

### Force Refresh

Immediately check for new packages:

```yaml
service: tracking_numbers.refresh
```

## Automations

### Notify on New Package

```yaml
automation:
  - alias: "Notify on new package"
    trigger:
      - platform: state
        entity_id: sensor.user_example_com_tracking_numbers
    action:
      - service: notify.mobile_app
        data:
          message: "New package detected! Total: {{ states('sensor.user_example_com_tracking_numbers') }}"
```

### Notify for Specific Carrier

```yaml
automation:
  - alias: "Notify UPS packages"
    trigger:
      - platform: template
        value_template: >
          {% set pkgs = state_attr('sensor.user_example_com_tracking_numbers', 'packages') | default([]) %}
          {{ pkgs | selectattr('carrier_code', 'eq', 'ups') | list | length > 0 }}
    action:
      - service: notify.mobile_app
        data:
          message: >
            {% set ups = state_attr('sensor.user_example_com_tracking_numbers', 'packages')
               | selectattr('carrier_code', 'eq', 'ups') | list %}
            You have {{ ups | length }} UPS package(s)
```

## Supported Retailers/Carriers

### Carriers
- UPS
- FedEx
- USPS
- DHL
- Swiss Post

### Retailers (50+)
Amazon, eBay, PayPal, AliExpress, Newegg, Best Buy, Home Depot, Inovelli, Lowe's, Target, Walmart, Chewy, Costway, Cradlewise, Groupon, GameStop, Nintendo, Sony, SwitchBot, Adafruit, Mixbook, Monoprice, B&H Photo, RockAuto, Wyze, Ubiquiti, Reolink, and many more...

## Troubleshooting

### Integration doesn't appear
- Restart Home Assistant
- Check logs for errors
- Verify folder structure is correct

### IMAP connection fails
- Verify email and password are correct
- For Gmail, use app-specific password
- Check IMAP server and port
- Ensure SSL is enabled
- Check if IMAP is enabled on your email account

### No packages detected
- Verify emails exist in the configured folder
- Check days_old setting (default: 30 days)
- Look for emails from known retailers
- Check logs for parser errors

### Packages not updating
- Check scan interval setting
- Manually trigger refresh service
- Verify IMAP connection is active
- Check Home Assistant logs

## Version History

### v2.0.0 (2025-10-28)
- ✨ Added UI configuration (config flow)
- ✨ Added options flow for settings
- ✨ Flat packages array structure
- ✨ DataUpdateCoordinator pattern
- ✨ Package persistence with timestamps
- ✨ Device grouping
- ⚠️ **BREAKING:** Removed YAML configuration
- ⚠️ **BREAKING:** Changed attribute structure

### v1.0.0
- Initial release with YAML configuration

## Credits

Original integration by @ljmerza
v2.0 modernization with config flow and flat structure

## License

See LICENSE file
