# Tracking Numbers Integration v2.0

Modern Home Assistant integration for tracking package deliveries by parsing email notifications.

## Features

- 📦 **50+ Retailer Parsers** - Amazon, eBay, FedEx, UPS, USPS, and more
- 🔄 **Auto-Discovery** - Automatically detects tracking numbers in emails
- 📊 **Simple Data Structure** - Flat array for easy custom card development
- ⏱️ **Timestamp Tracking** - Know when packages were first/last seen
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

After setup, click **Configure** to modify:

- **Days to scan** (1-90): How far back to check emails
- **Email folder**: Which folder to monitor (default: INBOX)
- **Scan interval** (5-1440 minutes): How often to check for new packages
- **Max packages** (10-500): Maximum packages to store

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
      "retailer_code": "amazon",
      "link": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "first_seen": "2025-10-25T10:30:00Z",
      "last_updated": "2025-10-28T14:22:00Z"
    }
  ],
  "summary": {
    "by_carrier": {"UPS": 2, "FedEx": 1},
    "by_retailer": {"Amazon": 2, "eBay": 1}
  },
  "last_update": "2025-10-28T14:22:00Z"
}
```

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
Amazon, eBay, PayPal, AliExpress, Newegg, Best Buy, Home Depot, Lowe's, Target, Walmart, Chewy, Groupon, GameStop, Nintendo, Sony, Adafruit, Monoprice, B&H Photo, RockAuto, Wyze, Ubiquiti, Reolink, and many more...

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
