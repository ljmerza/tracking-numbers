"""Config flow for Tracking Numbers integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

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
    DEFAULT_IMAP_SERVER,
    DEFAULT_IMAP_PORT,
    DEFAULT_USE_SSL,
    DEFAULT_FOLDER,
    DEFAULT_DAYS_OLD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAX_PACKAGES,
)

_LOGGER = logging.getLogger(__name__)


async def validate_imap_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate IMAP connection credentials."""

    def _test_connection():
        """Test IMAP connection (blocking)."""
        try:
            server = IMAPClient(
                data[CONF_IMAP_SERVER],
                port=data[CONF_IMAP_PORT],
                use_uid=True,
                ssl=data[CONF_USE_SSL],
                timeout=10
            )
            server.login(data[CONF_EMAIL], data[CONF_PASSWORD])
            server.select_folder(data.get(CONF_EMAIL_FOLDER, DEFAULT_FOLDER), readonly=True)
            server.logout()
            return True
        except IMAPClientError as err:
            _LOGGER.error("IMAP connection error: %s", err)
            if "authentication" in str(err).lower() or "login" in str(err).lower():
                raise InvalidAuth from err
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.error("Unexpected error during IMAP connection: %s", err)
            raise CannotConnect from err

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
        return TrackingNumbersOptionsFlowHandler(config_entry)


class TrackingNumbersOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tracking Numbers."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current options or defaults
        options = {**self.config_entry.data, **self.config_entry.options}

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DAYS_OLD,
                    default=options.get(CONF_DAYS_OLD, DEFAULT_DAYS_OLD),
                ): vol.All(cv.positive_int, vol.Range(min=1)),
                vol.Optional(
                    CONF_EMAIL_FOLDER,
                    default=options.get(CONF_EMAIL_FOLDER, DEFAULT_FOLDER),
                ): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(cv.positive_int, vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_MAX_PACKAGES,
                    default=options.get(CONF_MAX_PACKAGES, DEFAULT_MAX_PACKAGES),
                ): vol.All(cv.positive_int, vol.Range(min=10, max=500)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
