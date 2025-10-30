"""Support for Tracking Numbers sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_EMAIL
from .coordinator import TrackingNumbersCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tracking Numbers sensor from a config entry."""
    coordinator: TrackingNumbersCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([TrackingNumbersSensor(coordinator, entry)])


class TrackingNumbersSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tracking Numbers sensor."""

    def __init__(
        self,
        coordinator: TrackingNumbersCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_name = f"{entry.data[CONF_EMAIL]} Tracking Numbers"
        self._attr_unique_id = f"{entry.entry_id}_tracking_numbers"
        self._attr_icon = "mdi:package-variant-closed"

        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Tracking Numbers ({entry.data[CONF_EMAIL]})",
            "manufacturer": "Tracking Numbers Integration",
            "model": "Email Package Tracker",
        }

    @property
    def native_value(self) -> int:
        """Return the state of the sensor (package count)."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes with flat packages array."""
        if not self.coordinator.data:
            return {
                "packages": [],
                "summary": {},
                "count": 0,
            }

        return {
            "packages": self.coordinator.data.get("packages", []),
            "summary": self.coordinator.data.get("summary", {}),
            "count": self.coordinator.data.get("count", 0),
            "last_update": self.coordinator.data.get("last_update"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
