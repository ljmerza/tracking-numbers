"""DataUpdateCoordinator for Tracking Numbers integration."""
from __future__ import annotations

from datetime import timedelta, date, datetime
import logging
from typing import Any

from imapclient import IMAPClient
from mailparser import parse_from_bytes

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_IMAP_SERVER,
    CONF_IMAP_PORT,
    CONF_USE_SSL,
    CONF_EMAIL_FOLDER,
    CONF_DAYS_OLD,
    CONF_SCAN_INTERVAL,
    CONF_MAX_PACKAGES,
    DEFAULT_FOLDER,
    DEFAULT_DAYS_OLD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAX_PACKAGES,
    EMAIL_ATTR_FROM,
    EMAIL_ATTR_SUBJECT,
    EMAIL_ATTR_BODY,
)

# Import parsers and find_carrier from shared module
from .parsers_list import parsers, find_carrier

_LOGGER = logging.getLogger(__name__)


class TrackingNumbersCoordinator(DataUpdateCoordinator):
    """Coordinator to manage tracking numbers data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        config: dict[str, Any],
        options: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        self.config = config
        self.options = options
        self.entry_id = entry_id

        # Storage for package persistence
        self.store = Store(hass, version=1, key=f"{DOMAIN}_{entry_id}")
        self.stored_data = {}

        # Get scan interval from options
        scan_interval_minutes = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        update_interval = timedelta(minutes=scan_interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config[CONF_EMAIL]}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch tracking numbers from email."""
        _LOGGER.debug("Starting tracking numbers update")

        # Load stored data
        self.stored_data = await self.store.async_load() or {}
        _LOGGER.debug("Loaded stored data: %s packages", len(self.stored_data.get("packages", {})))

        try:
            # Fetch emails and parse tracking numbers
            _LOGGER.debug("Fetching emails from IMAP server")
            packages = await self.hass.async_add_executor_job(
                self._fetch_and_parse_emails
            )
            _LOGGER.debug("Fetched %d packages", len(packages))

            # Build summary statistics
            summary = self._build_summary(packages)

            # Save updated data
            await self.store.async_save(self.stored_data)

            return {
                "packages": packages,
                "summary": summary,
                "count": len(packages),
                "last_update": datetime.now().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Error fetching tracking numbers: %s", err)
            raise UpdateFailed(f"Error communicating with email server: {err}") from err

    def _fetch_and_parse_emails(self) -> list[dict[str, Any]]:
        """Fetch emails and parse tracking numbers (blocking operation)."""
        # Get configuration
        imap_server = self.config[CONF_IMAP_SERVER]
        imap_port = self.config[CONF_IMAP_PORT]
        use_ssl = self.config.get(CONF_USE_SSL, True)
        email = self.config[CONF_EMAIL]
        password = self.config[CONF_PASSWORD]
        folder = self.options.get(CONF_EMAIL_FOLDER, DEFAULT_FOLDER)
        days_old = self.options.get(CONF_DAYS_OLD, DEFAULT_DAYS_OLD)

        # Date range for email search
        search_date = date.today() - timedelta(days=days_old)
        flag = [u'SINCE', search_date]

        _LOGGER.info("Connecting to IMAP server: %s:%s (SSL: %s)", imap_server, imap_port, use_ssl)
        _LOGGER.info("Email: %s, Folder: %s, Days: %s", email, folder, days_old)

        # Connect to IMAP server
        server = IMAPClient(imap_server, port=imap_port, use_uid=True, ssl=use_ssl)

        try:
            _LOGGER.debug("Attempting IMAP login...")
            server.login(email, password)
            _LOGGER.info("IMAP login successful")

            _LOGGER.debug("Selecting folder: %s", folder)
            server.select_folder(folder, readonly=True)
            _LOGGER.info("Folder selected successfully")
        except Exception as err:
            _LOGGER.error("IMAP login error: %s", err)
            server.logout()
            raise

        # Fetch emails
        emails = []
        try:
            _LOGGER.debug("Searching for emails with flag: %s", flag)
            messages = server.search(flag)
            _LOGGER.info("Found %d messages matching search criteria", len(messages))

            for uid, message_data in server.fetch(messages, 'RFC822').items():
                try:
                    mail = parse_from_bytes(message_data[b'RFC822'])

                    # Prefer HTML body for link parsing, fallback to plain text
                    body = mail.body
                    if hasattr(mail, 'text_html') and mail.text_html:
                        # text_html is a list, join all HTML parts
                        body = '\n'.join(mail.text_html)
                    elif hasattr(mail, 'text_plain') and mail.text_plain and not body:
                        # text_plain is a list, join all plain text parts
                        body = '\n'.join(mail.text_plain)

                    emails.append({
                        EMAIL_ATTR_FROM: mail.from_,
                        EMAIL_ATTR_SUBJECT: mail.subject,
                        EMAIL_ATTR_BODY: body
                    })
                except Exception as err:
                    _LOGGER.warning("Email parse error: %s", err)

        except Exception as err:
            _LOGGER.error("IMAP fetch error: %s", err)
        finally:
            server.logout()

        # Parse emails for tracking numbers
        all_tracking_numbers = {}
        for ATTR, EMAIL_DOMAIN, parser in parsers:
            all_tracking_numbers[ATTR] = []

        _LOGGER.info("Parsing %d emails for tracking numbers", len(emails))

        # Run parsers on each email
        for email in emails:
            email_from = email[EMAIL_ATTR_FROM]

            if isinstance(email_from, (list, tuple)):
                email_from = ''.join(list(email_from[0]))

            # Run matching parsers
            for ATTR, EMAIL_DOMAIN, parser in parsers:
                try:
                    if EMAIL_DOMAIN in email_from:
                        tracking_nums = parser(email=email)
                        if tracking_nums:
                            _LOGGER.debug("Parser %s found %d tracking numbers from %s", ATTR, len(tracking_nums), email_from)
                            all_tracking_numbers[ATTR].extend(tracking_nums)
                except Exception as err:
                    _LOGGER.error("Parser %s error: %s", ATTR, err)

        # Convert to flat packages array
        _LOGGER.info("Converting tracking numbers to packages")
        packages = self._convert_to_packages(all_tracking_numbers)
        _LOGGER.info("Converted to %d unique packages", len(packages))

        return packages

    def _convert_to_packages(
        self, all_tracking_numbers: dict[str, list]
    ) -> list[dict[str, Any]]:
        """Convert nested tracking numbers to flat packages array."""
        ignored_numbers = self.stored_data.get("ignored_tracking_numbers", [])
        known_packages = self.stored_data.get("packages", {})
        max_packages = self.options.get(CONF_MAX_PACKAGES, DEFAULT_MAX_PACKAGES)

        packages = []
        now = datetime.now().isoformat()

        for ATTR, EMAIL_DOMAIN, _ in parsers:
            tracking_numbers = all_tracking_numbers.get(ATTR, [])

            if not tracking_numbers:
                continue

            # Normalize to list of dicts
            if tracking_numbers and isinstance(tracking_numbers[0], (str, int)):
                tracking_numbers = [{'tracking_number': str(x)} for x in tracking_numbers]

            # Process each tracking number
            for item in tracking_numbers:
                tracking_number = item['tracking_number']

                # Skip ignored
                if tracking_number in ignored_numbers:
                    continue

                # Get carrier info
                pkg_info = find_carrier(item, EMAIL_DOMAIN)

                # Check if we've seen this before
                if tracking_number in known_packages:
                    # Update last_updated, keep first_seen
                    pkg_info['first_seen'] = known_packages[tracking_number].get(
                        'first_seen', now
                    )
                    pkg_info['last_updated'] = now
                else:
                    # New package
                    pkg_info['first_seen'] = now
                    pkg_info['last_updated'] = now

                # Add retailer_code and carrier_code for easy filtering
                pkg_info['retailer_code'] = EMAIL_DOMAIN.replace('@', '').replace('.', '_')
                pkg_info['carrier_code'] = pkg_info['carrier'].lower().replace(' ', '_')

                packages.append(pkg_info)

                # Update known packages
                known_packages[tracking_number] = pkg_info

        # Deduplicate by tracking_number (keep most recent)
        seen = {}
        for pkg in packages:
            tracking_number = pkg['tracking_number']
            if tracking_number not in seen:
                seen[tracking_number] = pkg

        packages = list(seen.values())

        # Sort by first_seen (newest first)
        packages.sort(key=lambda x: x.get('first_seen', ''), reverse=True)

        # Limit to max packages
        packages = packages[:max_packages]

        # Update stored data
        self.stored_data["packages"] = {
            pkg['tracking_number']: pkg for pkg in packages
        }

        return packages

    def _build_summary(self, packages: list[dict[str, Any]]) -> dict[str, Any]:
        """Build summary statistics."""
        by_carrier = {}
        by_retailer = {}

        for pkg in packages:
            carrier = pkg.get('carrier', 'Unknown')
            retailer = pkg.get('origin', 'Unknown')

            by_carrier[carrier] = by_carrier.get(carrier, 0) + 1
            by_retailer[retailer] = by_retailer.get(retailer, 0) + 1

        return {
            "by_carrier": by_carrier,
            "by_retailer": by_retailer,
        }

    async def async_ignore_tracking_number(self, tracking_number: str) -> None:
        """Add tracking number to ignore list."""
        self.stored_data = await self.store.async_load() or {}
        ignored = self.stored_data.get("ignored_tracking_numbers", [])

        if tracking_number not in ignored:
            ignored.append(tracking_number)
            self.stored_data["ignored_tracking_numbers"] = ignored
            await self.store.async_save(self.stored_data)
            await self.async_request_refresh()

    async def async_unignore_tracking_number(self, tracking_number: str) -> None:
        """Remove tracking number from ignore list."""
        self.stored_data = await self.store.async_load() or {}
        ignored = self.stored_data.get("ignored_tracking_numbers", [])

        if tracking_number in ignored:
            ignored.remove(tracking_number)
            self.stored_data["ignored_tracking_numbers"] = ignored
            await self.store.async_save(self.stored_data)
            await self.async_request_refresh()
