"""The Tracking Numbers integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVICE_ADD_MANUAL_TRACKING_NUMBER,
    SERVICE_REMOVE_TRACKING_NUMBER,
)
from .coordinator import TrackingNumbersCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# This integration can only be set up from config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tracking Numbers component."""
    # This is required even for config flow only integrations
    hass.data.setdefault(DOMAIN, {})
    return True

SERVICE_REFRESH = "refresh"

SERVICE_ADD_MANUAL_SCHEMA = vol.Schema({
    vol.Required("tracking_number"): vol.Coerce(str),
    vol.Required("entity_id"): str,
    vol.Optional("link"): vol.Coerce(str),
    vol.Optional("carrier"): vol.Coerce(str),
    vol.Optional("origin"): vol.Coerce(str),
    vol.Optional("status"): vol.Coerce(str),
})

SERVICE_REMOVE_TRACKING_SCHEMA = vol.Schema({
    vol.Required("tracking_number"): vol.Coerce(str),
    vol.Required("entity_id"): str,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tracking Numbers from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator
    coordinator = TrackingNumbersCoordinator(
        hass,
        entry.entry_id,
        entry.data,
        entry.options,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services (only once)
    if not hass.services.has_service(DOMAIN, SERVICE_ADD_MANUAL_TRACKING_NUMBER):
        await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Tracking Numbers integration."""

    def _resolve_coordinator(entity_id: str | None) -> TrackingNumbersCoordinator | None:
        if not hass.data.get(DOMAIN):
            return None

        if entity_id:
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, TrackingNumbersCoordinator):
                    return coord
            return None

        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, TrackingNumbersCoordinator):
                return coord

        return None

    async def add_manual_tracking_number(call: ServiceCall) -> None:
        """Service to add a manual tracking number."""
        entity_id = call.data.get("entity_id")
        coordinator = _resolve_coordinator(entity_id)

        if not coordinator:
            _LOGGER.error("No coordinator found to add manual tracking number")
            return

        tracking_number = call.data["tracking_number"]
        link = call.data.get("link")
        carrier = call.data.get("carrier")
        origin = call.data.get("origin")
        status = call.data.get("status")

        try:
            await coordinator.async_add_manual_package(
                tracking_number,
                link=link,
                carrier=carrier,
                origin=origin,
                status=status,
            )
            _LOGGER.info("Added manual tracking number: %s", tracking_number)
        except ValueError as err:
            _LOGGER.error("Failed to add manual tracking number: %s", err)

    async def remove_tracking_number(call: ServiceCall) -> None:
        """Service to remove or hide a tracking number."""
        entity_id = call.data.get("entity_id")
        coordinator = _resolve_coordinator(entity_id)

        if not coordinator:
            _LOGGER.error("No coordinator found to remove tracking number")
            return

        tracking_number = call.data["tracking_number"]

        try:
            await coordinator.async_remove_tracking_number(tracking_number)
            _LOGGER.info("Removed tracking number: %s", tracking_number)
        except ValueError as err:
            _LOGGER.error("Failed to remove tracking number: %s", err)

    async def refresh(call: ServiceCall) -> None:
        """Service to force refresh."""
        entity_id = call.data.get("entity_id")

        # Refresh all coordinators or specific one
        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, TrackingNumbersCoordinator):
                await coord.async_request_refresh()
                _LOGGER.info("Forced refresh for tracking numbers")

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_MANUAL_TRACKING_NUMBER,
        add_manual_tracking_number,
        schema=SERVICE_ADD_MANUAL_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_TRACKING_NUMBER,
        remove_tracking_number,
        schema=SERVICE_REMOVE_TRACKING_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        refresh,
        schema=vol.Schema({vol.Optional("entity_id"): str}),
    )
