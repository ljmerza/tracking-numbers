"""DataUpdateCoordinator for Tracking Numbers integration."""
from __future__ import annotations

from datetime import timedelta, date, datetime, timezone
import logging
from typing import Any
from email.utils import parsedate_to_datetime

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
    EMAIL_ATTR_DATE,
    TRACKING_NUMBER_URLS,
    MANUAL_RETAILER_CODE,
    MANUAL_ORIGIN_FALLBACK,
    MANUAL_CARRIER_FALLBACK,
    STORE_KEY_MANUAL_PACKAGES,
    STORE_KEY_HIDDEN_TRACKING_NUMBERS,
    LEGACY_STORE_KEY_IGNORED,
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
        self._ensure_storage_defaults()
        _LOGGER.debug("Loaded stored data: %s packages", len(self.stored_data.get("packages", {})))

        try:
            # Fetch emails and parse tracking numbers
            _LOGGER.debug("Fetching emails from IMAP server")
            auto_packages = await self.hass.async_add_executor_job(
                self._fetch_and_parse_emails
            )
            _LOGGER.debug("Fetched %d packages", len(auto_packages))

            packages = self._merge_manual_packages(auto_packages)

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

                    delivered_at = self._extract_email_timestamp(mail)

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
                        EMAIL_ATTR_BODY: body,
                        EMAIL_ATTR_DATE: delivered_at,
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
            delivered_at = email.get(EMAIL_ATTR_DATE)

            if isinstance(email_from, (list, tuple)):
                email_from = ''.join(list(email_from[0]))

            # Run matching parsers
            for ATTR, EMAIL_DOMAIN, parser in parsers:
                try:
                    if EMAIL_DOMAIN in email_from:
                        tracking_nums = parser(email=email)
                        if tracking_nums:
                            enriched = self._enrich_tracking_results(tracking_nums, delivered_at)
                            if enriched:
                                _LOGGER.debug(
                                    "Parser %s found %d tracking numbers from %s",
                                    ATTR,
                                    len(enriched),
                                    email_from,
                                )
                                all_tracking_numbers[ATTR].extend(enriched)
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
        hidden_numbers = set(self.stored_data.get(STORE_KEY_HIDDEN_TRACKING_NUMBERS, []))
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
                if tracking_number in hidden_numbers:
                    continue

                # Get carrier info
                pkg_info = find_carrier(item, EMAIL_DOMAIN)

                delivered_iso = item.get('email_timestamp')
                delivered_dt = self._parse_iso_datetime(delivered_iso)

                # Check if we've seen this before
                if tracking_number in known_packages:
                    existing = known_packages[tracking_number]
                    existing_first_iso = existing.get('first_seen')
                    existing_first_dt = self._parse_iso_datetime(existing_first_iso)

                    candidate_dt = existing_first_dt
                    if delivered_dt and (candidate_dt is None or delivered_dt < candidate_dt):
                        candidate_dt = delivered_dt

                    if candidate_dt:
                        pkg_info['first_seen'] = candidate_dt.isoformat()
                    elif existing_first_iso:
                        pkg_info['first_seen'] = existing_first_iso
                    elif delivered_iso:
                        pkg_info['first_seen'] = delivered_iso
                    else:
                        pkg_info['first_seen'] = now
                    pkg_info['last_updated'] = now
                else:
                    # New package
                    if delivered_dt:
                        pkg_info['first_seen'] = delivered_dt.isoformat()
                    elif delivered_iso:
                        pkg_info['first_seen'] = delivered_iso
                    else:
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

    def _merge_manual_packages(self, auto_packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge auto and manual packages with manual overrides."""
        manual_packages = self.stored_data.get(STORE_KEY_MANUAL_PACKAGES, {})
        hidden_numbers = set(self.stored_data.get(STORE_KEY_HIDDEN_TRACKING_NUMBERS, []))
        merged: dict[str, dict[str, Any]] = {}

        for pkg in auto_packages:
            tracking_number = pkg.get('tracking_number')
            if not tracking_number:
                continue
            merged[tracking_number] = pkg

        for tracking_number, manual_pkg in manual_packages.items():
            if not tracking_number or tracking_number in hidden_numbers:
                continue
            merged[tracking_number] = manual_pkg

        packages = list(merged.values())
        packages.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        return packages

    def _ensure_storage_defaults(self) -> None:
        """Ensure store has expected structures."""
        if not isinstance(self.stored_data.get('packages'), dict):
            self.stored_data['packages'] = {}
        manual = self.stored_data.get(STORE_KEY_MANUAL_PACKAGES)
        if not isinstance(manual, dict):
            self.stored_data[STORE_KEY_MANUAL_PACKAGES] = {}
        hidden = self.stored_data.get(STORE_KEY_HIDDEN_TRACKING_NUMBERS)
        if isinstance(hidden, list):
            self.stored_data[STORE_KEY_HIDDEN_TRACKING_NUMBERS] = hidden
        else:
            legacy = self.stored_data.get(LEGACY_STORE_KEY_IGNORED)
            if isinstance(legacy, list):
                self.stored_data[STORE_KEY_HIDDEN_TRACKING_NUMBERS] = legacy
            else:
                self.stored_data[STORE_KEY_HIDDEN_TRACKING_NUMBERS] = []

    @staticmethod
    def _normalize_datetime(dt: datetime | None) -> datetime | None:
        """Normalize datetimes to naive UTC for consistent storage."""
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    def _extract_email_timestamp(self, mail) -> str | None:
        """Extract delivery timestamp from a parsed email."""
        mail_date = getattr(mail, 'date', None)
        delivered: datetime | None = None

        if isinstance(mail_date, datetime):
            delivered = mail_date
        elif isinstance(mail_date, str):
            try:
                delivered = parsedate_to_datetime(mail_date)
            except (TypeError, ValueError):
                delivered = None

        if delivered is None:
            return None

        normalized = self._normalize_datetime(delivered)
        if normalized is None:
            return None

        return normalized.isoformat()

    @staticmethod
    def _parse_iso_datetime(value: str | None) -> datetime | None:
        """Parse isoformat strings (with optional Z suffix) into naive UTC datetimes."""
        if not value:
            return None

        if value.endswith('Z'):
            value = value.replace('Z', '+00:00')

        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError, AttributeError):
            return None

        return TrackingNumbersCoordinator._normalize_datetime(parsed)

    @staticmethod
    def _enrich_tracking_results(results, delivered_at: str | None) -> list[dict[str, Any]]:
        """Ensure parser results carry the source email timestamp."""
        if results is None:
            return []

        if isinstance(results, (str, bytes, int)):
            iterable = [results]
        else:
            try:
                iterable = list(results)
            except TypeError:
                iterable = [results]

        enriched: list[dict[str, Any]] = []
        for item in iterable:
            if isinstance(item, dict):
                enriched_item = dict(item)
                if delivered_at and 'email_timestamp' not in enriched_item:
                    enriched_item['email_timestamp'] = delivered_at
            else:
                enriched_item = {'tracking_number': str(item)}
                if delivered_at:
                    enriched_item['email_timestamp'] = delivered_at
            enriched.append(enriched_item)

        return enriched

    def _default_tracking_link(self, carrier: str, tracking_number: str) -> str:
        """Return a best-effort tracking link for manual entries."""
        key = (carrier or '').lower().replace(' ', '_')
        base = TRACKING_NUMBER_URLS.get(key, TRACKING_NUMBER_URLS['unknown'])
        return f"{base}{tracking_number}"

    async def async_add_manual_package(
        self,
        tracking_number: str,
        *,
        link: str | None = None,
        carrier: str | None = None,
        origin: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Persist a manual tracking number and update coordinator data."""
        tracking_number = str(tracking_number or '').strip()
        if not tracking_number:
            raise ValueError("Tracking number is required")

        self.stored_data = await self.store.async_load() or {}
        self._ensure_storage_defaults()

        manual_packages = self.stored_data.get(STORE_KEY_MANUAL_PACKAGES, {})

        now = datetime.now().isoformat()
        existing = manual_packages.get(tracking_number, {})

        final_carrier = (carrier or existing.get('carrier') or MANUAL_CARRIER_FALLBACK).strip()
        final_origin = (origin or existing.get('origin') or MANUAL_ORIGIN_FALLBACK).strip()

        if link:
            final_link = link.strip()
        elif existing.get('link'):
            final_link = existing['link']
        else:
            final_link = self._default_tracking_link(final_carrier, tracking_number)

        package: dict[str, Any] = {
            'tracking_number': tracking_number,
            'carrier': final_carrier,
            'origin': final_origin,
            'link': final_link,
            'first_seen': existing.get('first_seen', now),
            'last_updated': now,
            'retailer_code': MANUAL_RETAILER_CODE,
            'carrier_code': final_carrier.lower().replace(' ', '_') or 'unknown',
            'source': 'manual',
        }

        if status or existing.get('status'):
            package['status'] = status or existing.get('status')

        hidden_numbers = set(self.stored_data.get(STORE_KEY_HIDDEN_TRACKING_NUMBERS, []))
        if tracking_number in hidden_numbers:
            hidden_numbers.remove(tracking_number)
            self.stored_data[STORE_KEY_HIDDEN_TRACKING_NUMBERS] = list(hidden_numbers)

        manual_packages[tracking_number] = package
        self.stored_data[STORE_KEY_MANUAL_PACKAGES] = manual_packages

        await self.store.async_save(self.stored_data)

        packages = self._merge_manual_packages(list(self.stored_data.get('packages', {}).values()))
        summary = self._build_summary(packages)

        self.async_set_updated_data(
            {
                'packages': packages,
                'summary': summary,
                'count': len(packages),
                'last_update': now,
            }
        )

        return package

    async def async_remove_tracking_number(self, tracking_number: str) -> None:
        """Remove a manual package or hide an email-derived package."""
        tracking_number = str(tracking_number or '').strip()
        if not tracking_number:
            raise ValueError("Tracking number is required")

        self.stored_data = await self.store.async_load() or {}
        self._ensure_storage_defaults()

        manual_packages = self.stored_data.get(STORE_KEY_MANUAL_PACKAGES, {})
        hidden_numbers = set(self.stored_data.get(STORE_KEY_HIDDEN_TRACKING_NUMBERS, []))
        packages_store = self.stored_data.get('packages', {})

        removed = False

        if tracking_number in manual_packages:
            manual_packages.pop(tracking_number)
            self.stored_data[STORE_KEY_MANUAL_PACKAGES] = manual_packages
            removed = True
        else:
            if tracking_number not in hidden_numbers:
                hidden_numbers.add(tracking_number)
                removed = True
            self.stored_data[STORE_KEY_HIDDEN_TRACKING_NUMBERS] = list(hidden_numbers)

        if tracking_number in packages_store:
            packages_store.pop(tracking_number)
            self.stored_data['packages'] = packages_store

        if removed:
            await self.store.async_save(self.stored_data)

        packages = self._merge_manual_packages(list(self.stored_data.get('packages', {}).values()))
        summary = self._build_summary(packages)

        self.async_set_updated_data(
            {
                'packages': packages,
                'summary': summary,
                'count': len(packages),
                'last_update': datetime.now().isoformat(),
            }
        )

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
