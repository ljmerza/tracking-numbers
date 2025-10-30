"""The Tracking Numbers integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import DOMAIN
from .coordinator import TrackingNumbersCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tracking Numbers component."""
    # This is required even for config flow only integrations
    hass.data.setdefault(DOMAIN, {})
    return True

SERVICE_IGNORE_TRACKING_NUMBER = "ignore_tracking_number"
SERVICE_UNIGNORE_TRACKING_NUMBER = "unignore_tracking_number"
SERVICE_REFRESH = "refresh"

SERVICE_SCHEMA = vol.Schema({
    vol.Required("tracking_number"): str,
    vol.Optional("entity_id"): str,
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
    if not hass.services.has_service(DOMAIN, SERVICE_IGNORE_TRACKING_NUMBER):
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

    async def ignore_tracking_number(call: ServiceCall) -> None:
        """Service to ignore a tracking number."""
        tracking_number = call.data["tracking_number"]
        entity_id = call.data.get("entity_id")

        # Find the coordinator
        coordinator = None
        if entity_id:
            # Try to find coordinator by entity_id
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, TrackingNumbersCoordinator):
                    coordinator = coord
                    break
        else:
            # Use first coordinator if no entity_id specified
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, TrackingNumbersCoordinator):
                    coordinator = coord
                    break

        if coordinator:
            await coordinator.async_ignore_tracking_number(tracking_number)
            _LOGGER.info("Ignored tracking number: %s", tracking_number)
        else:
            _LOGGER.error("No coordinator found to ignore tracking number")

    async def unignore_tracking_number(call: ServiceCall) -> None:
        """Service to unignore a tracking number."""
        tracking_number = call.data["tracking_number"]
        entity_id = call.data.get("entity_id")

        # Find the coordinator
        coordinator = None
        if entity_id:
            # Try to find coordinator by entity_id
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, TrackingNumbersCoordinator):
                    coordinator = coord
                    break
        else:
            # Use first coordinator if no entity_id specified
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, TrackingNumbersCoordinator):
                    coordinator = coord
                    break

        if coordinator:
            await coordinator.async_unignore_tracking_number(tracking_number)
            _LOGGER.info("Unignored tracking number: %s", tracking_number)
        else:
            _LOGGER.error("No coordinator found to unignore tracking number")

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
        SERVICE_IGNORE_TRACKING_NUMBER,
        ignore_tracking_number,
        schema=SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UNIGNORE_TRACKING_NUMBER,
        unignore_tracking_number,
        schema=SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        refresh,
        schema=vol.Schema({vol.Optional("entity_id"): str}),
    )
