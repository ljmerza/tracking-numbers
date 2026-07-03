# Home Assistant Email Sensor

Gets emails from IMAP and parses out any tracking numbers. Goes well with the [tracking-number-card](https://github.com/ljmerza/tracking-number-card) for lovelace!

Supported Emails

- Adafruit
- Adam & Eve
- Amazon
- Amazon DE
- Ali Express
- B&H Photo
- Bespoke Post
- Best Buy
- Chewy
- Costway
- Cradlewise
- DHL
- Dollar Shave Club
- DSW
- eBay
- Etsy
- FedEx
- Gamestop
- Georgia Power
- Giri Designs
- Google Express
- Groupon
- Guitar Center
- Home Depot
- House of Noa
- Inovelli
- Litter Robot
- Loog Guitars
- Lowes
- Manta Sleep
- Mixbook
- Moen
- Monoprice
- NewEgg
- Nintendo
- Nuleaf
- Paypal
- Pledge Box
- Philips Hue
- Prusa
- Reolink
- Rockauto
- Sylvane
- Sony
- Swiss Post
- SwitchBot
- Target
- Thriftbooks
- Timeless
- The Smartest House
- Ubiquiti
- UPS
- USPS
- Walmart
- Wayfair
- Western Digital
- Wyze
- Zazzle

If you want support for tracking, forward me the email (ljmerza at gmail) and open an issue.

---

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)

![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

## Options

| Name        | Type    | Requirement  | `default` Description                                                 |
| ----------- | ------- | ------------ | --------------------------------------------------------------------- |
| email       | string  | **Required** | email address                                                         |
| password    | string  | **Required** | email password                                                        |
| imap_server | string  | **Optional** | `imap.gmail.com`  IMAP server address>                                |
| imap_port   | number  | **Optional** | `993` IMAP port                                                       |
| folder      | string  | **Optional** | `INBOX` Which folder to pull emails from                              |
| ssl         | boolean | **Optional** | `true` enable or disable SSL when using IMAP                          |
| days_old    | number  | **Optional** | `30` how many days of emails to retrieve                              |
| trackingmore_api_key | string | **Optional** | Enables live delivery status via [TrackingMore](https://www.trackingmore.com/). Leave blank to disable. |

## Live Delivery Status (optional)

By default the integration only *extracts* tracking numbers from email. You can optionally enrich packages
shipped by recognized carriers (USPS, UPS, FedEx, DHL) with live delivery status — `status`,
`delivery_status`, `estimated_delivery`, and `status_updated` attributes. Retailer order numbers (Amazon,
Chewy, etc.) are skipped. Configure it under **Configure → Live status provider**; with the provider set to
**None** (the default) behavior is unchanged.

Two providers are available:

- **Carrier-direct (free):** query each carrier's own free developer API. Set the provider to
  *Carrier-direct* and enter credentials under **Configure → Carrier API credentials** for whichever
  carriers you use (leave the rest blank). Each carrier needs a free developer account:
  [USPS](https://developers.usps.com/) (OAuth key + secret), [UPS](https://developer.ups.com/) (client ID +
  secret), [FedEx](https://developer.fedex.com/) (API key + secret), [DHL](https://developer.dhl.com/)
  (one API key). Zero cost; delivered packages aren't re-queried and calls are rate-limited per carrier.
- **TrackingMore (paid credits):** supply a [TrackingMore](https://www.trackingmore.com/) API key. One
  credit per tracking number registered; each number is registered once and re-read for free afterward,
  with new registrations capped per cycle.

## Manual Tracking Numbers

If you have a package that is not captured via email, call the `tracking_numbers.add_manual_tracking_number` service (or use the lovelace card's add button) to save it alongside your parsed deliveries. Provide the target sensor's `entity_id`, the `tracking_number`, and optionally a `link`, `carrier`, `origin`, or `status` string. Use `tracking_numbers.remove_tracking_number` to delete a manual entry or hide a tracking number that was parsed from email.

---

Enjoy my card? Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/JMISm06AD)

[commits-shield]: https://img.shields.io/github/commit-activity/y/ljmerza/ha-email-sensor.svg?style=for-the-badge
[commits]: https://github.com/ljmerza/ha-email-sensor/commits/master
[license-shield]: https://img.shields.io/github/license/ljmerza/ha-email-sensor.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Leonardo%20Merza%20%40ljmerza-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ljmerza/ha-email-sensor.svg?style=for-the-badge
[releases]: https://github.com/ljmerza/ha-email-sensor/releases

