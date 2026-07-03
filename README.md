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

## Live Delivery Status (TrackingMore)

Optionally supply a [TrackingMore](https://www.trackingmore.com/) API key (in the initial setup or later via **Configure**) to enrich packages with live delivery status. When set, packages shipped by recognized carriers (USPS, UPS, FedEx, DHL) gain `status`, `delivery_status`, `estimated_delivery`, and `status_updated` attributes. Retailer order numbers (Amazon, Chewy, etc.) are skipped.

TrackingMore charges **one credit per tracking number registered**, so each number is registered only once and then re-read for free on later refreshes. New registrations are capped per refresh cycle to protect small credit budgets. With no key configured, the integration behaves exactly as before (email extraction only).

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

