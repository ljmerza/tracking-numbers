"""Config flow for Tracking Numbers integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError, LoginError

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

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
    CONF_TRACKINGMORE_API_KEY,
    CONF_STATUS_PROVIDER,
    STATUS_PROVIDER_NONE,
    STATUS_PROVIDER_TRACKINGMORE,
    STATUS_PROVIDER_CARRIERS,
    DEFAULT_STATUS_PROVIDER,
    CONF_USPS_CLIENT_ID,
    CONF_USPS_CLIENT_SECRET,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_FEDEX_CLIENT_ID,
    CONF_FEDEX_CLIENT_SECRET,
    CONF_DHL_API_KEY,
    DEFAULT_IMAP_SERVER,
    DEFAULT_IMAP_PORT,
    DEFAULT_USE_SSL,
    DEFAULT_FOLDER,
    DEFAULT_DAYS_OLD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAX_PACKAGES,
    IMAP_CONNECTION_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def validate_imap_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate IMAP connection credentials."""

    def _test_connection():
        """Test IMAP connection (blocking)."""
        server = None
        try:
            server = IMAPClient(
                data[CONF_IMAP_SERVER],
                port=data[CONF_IMAP_PORT],
                use_uid=True,
                ssl=data[CONF_USE_SSL],
                timeout=IMAP_CONNECTION_TIMEOUT,
            )
            server.login(data[CONF_EMAIL], data[CONF_PASSWORD])
            server.select_folder(data.get(CONF_EMAIL_FOLDER, DEFAULT_FOLDER), readonly=True)
            return True
        except LoginError as err:
            _LOGGER.exception("IMAP authentication failed (%s)", type(err).__name__)
            raise InvalidAuth from err
        except IMAPClientError as err:
            _LOGGER.exception("IMAP connection error (%s)", type(err).__name__)
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error during IMAP connection (%s)", type(err).__name__
            )
            raise CannotConnect from err
        finally:
            if server is not None:
                try:
                    server.logout()
                except Exception:  # pylint: disable=broad-except
                    pass

    await hass.async_add_executor_job(_test_connection)

    return {"title": data[CONF_EMAIL]}


class TrackingNumbersConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tracking Numbers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            try:
                # Set default values
                user_input.setdefault(CONF_IMAP_SERVER, DEFAULT_IMAP_SERVER)
                user_input.setdefault(CONF_IMAP_PORT, DEFAULT_IMAP_PORT)
                user_input.setdefault(CONF_USE_SSL, DEFAULT_USE_SSL)
                user_input.setdefault(CONF_EMAIL_FOLDER, DEFAULT_FOLDER)
                user_input.setdefault(CONF_DAYS_OLD, DEFAULT_DAYS_OLD)
                user_input.setdefault(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                user_input.setdefault(CONF_MAX_PACKAGES, DEFAULT_MAX_PACKAGES)

                info = await validate_imap_connection(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_IMAP_SERVER, default=DEFAULT_IMAP_SERVER
                ): cv.string,
                vol.Optional(
                    CONF_IMAP_PORT, default=DEFAULT_IMAP_PORT
                ): cv.positive_int,
                vol.Optional(
                    CONF_USE_SSL, default=DEFAULT_USE_SSL
                ): cv.boolean,
                vol.Optional(
                    CONF_DAYS_OLD, default=DEFAULT_DAYS_OLD
                ): vol.All(cv.positive_int, vol.Range(min=1)),
                vol.Optional(
                    CONF_EMAIL_FOLDER, default=DEFAULT_FOLDER
                ): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(cv.positive_int, vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_MAX_PACKAGES, default=DEFAULT_MAX_PACKAGES
                ): vol.All(cv.positive_int, vol.Range(min=10, max=500)),
                vol.Optional(CONF_TRACKINGMORE_API_KEY): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TrackingNumbersOptionsFlowHandler:
        """Get the options flow for this handler."""
        return TrackingNumbersOptionsFlowHandler()


def _password_selector() -> TextSelector:
    """A masked text input for secrets/API keys."""
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class TrackingNumbersOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tracking Numbers."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "email_settings",
                "status_provider",
                "carrier_credentials",
            ],
        )

    def _current(self) -> dict[str, Any]:
        """Merged current values (data + options) for defaults."""
        return {**self.config_entry.data, **self.config_entry.options}

    def _save(self, updates: dict[str, Any]) -> FlowResult:
        """Merge a sub-step's values into the full options and finish."""
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **updates}
        )

    async def async_step_email_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Scan/window settings."""
        if user_input is not None:
            return self._save(user_input)

        current = self._current()
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DAYS_OLD,
                    default=current.get(CONF_DAYS_OLD, DEFAULT_DAYS_OLD),
                ): vol.All(cv.positive_int, vol.Range(min=1)),
                vol.Optional(
                    CONF_EMAIL_FOLDER,
                    default=current.get(CONF_EMAIL_FOLDER, DEFAULT_FOLDER),
                ): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(cv.positive_int, vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_MAX_PACKAGES,
                    default=current.get(CONF_MAX_PACKAGES, DEFAULT_MAX_PACKAGES),
                ): vol.All(cv.positive_int, vol.Range(min=10, max=500)),
            }
        )
        return self.async_show_form(step_id="email_settings", data_schema=data_schema)

    async def async_step_status_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose the live-status provider (and the TrackingMore key)."""
        if user_input is not None:
            return self._save(user_input)

        current = self._current()
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_STATUS_PROVIDER,
                    default=current.get(CONF_STATUS_PROVIDER, DEFAULT_STATUS_PROVIDER),
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN,
                        options=[
                            {"value": STATUS_PROVIDER_NONE, "label": "None (email only)"},
                            {"value": STATUS_PROVIDER_TRACKINGMORE, "label": "TrackingMore (API key)"},
                            {"value": STATUS_PROVIDER_CARRIERS, "label": "Carrier-direct (USPS/UPS/FedEx/DHL)"},
                        ],
                    )
                ),
                vol.Optional(
                    CONF_TRACKINGMORE_API_KEY,
                    default=current.get(CONF_TRACKINGMORE_API_KEY, ""),
                ): _password_selector(),
            }
        )
        return self.async_show_form(step_id="status_provider", data_schema=data_schema)

    async def async_step_carrier_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enter free carrier API credentials (all optional)."""
        if user_input is not None:
            return self._save(user_input)

        current = self._current()
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_USPS_CLIENT_ID,
                    default=current.get(CONF_USPS_CLIENT_ID, ""),
                ): cv.string,
                vol.Optional(
                    CONF_USPS_CLIENT_SECRET,
                    default=current.get(CONF_USPS_CLIENT_SECRET, ""),
                ): _password_selector(),
                vol.Optional(
                    CONF_UPS_CLIENT_ID,
                    default=current.get(CONF_UPS_CLIENT_ID, ""),
                ): cv.string,
                vol.Optional(
                    CONF_UPS_CLIENT_SECRET,
                    default=current.get(CONF_UPS_CLIENT_SECRET, ""),
                ): _password_selector(),
                vol.Optional(
                    CONF_FEDEX_CLIENT_ID,
                    default=current.get(CONF_FEDEX_CLIENT_ID, ""),
                ): cv.string,
                vol.Optional(
                    CONF_FEDEX_CLIENT_SECRET,
                    default=current.get(CONF_FEDEX_CLIENT_SECRET, ""),
                ): _password_selector(),
                vol.Optional(
                    CONF_DHL_API_KEY,
                    default=current.get(CONF_DHL_API_KEY, ""),
                ): _password_selector(),
            }
        )
        return self.async_show_form(
            step_id="carrier_credentials", data_schema=data_schema
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
