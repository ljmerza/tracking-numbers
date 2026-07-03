"""Thin async client for the TrackingMore v4 tracking API.

Optional: used only when the user configures a TrackingMore API key. Failures are
swallowed (logged, return ``None``) so a flaky/expired key never breaks the
coordinator's update loop. See const.py for endpoints, limits, and courier maps.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    TRACKINGMORE_BASE_URL,
    TRACKINGMORE_GET_BATCH,
    TRACKINGMORE_STATUS_LABELS,
    TRACKINGMORE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# TrackingMore meta.code returned when a tracking already exists for the
# account -> we treat it as "already registered" rather than an error.
_CODE_ALREADY_EXISTS = 4016


class TrackingMoreClient:
    """Minimal wrapper over the endpoints this integration needs."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Tracking-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Perform a request; return parsed JSON or None on any failure."""
        url = f"{TRACKINGMORE_BASE_URL}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=TRACKINGMORE_TIMEOUT),
                **kwargs,
            ) as resp:
                # TrackingMore encodes API-level errors in the JSON body, so parse
                # regardless of HTTP status (content_type=None tolerates odd types).
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("TrackingMore %s %s failed: %s", method, path, err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Unexpected TrackingMore error on %s %s: %s", method, path, err)
        return None

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        """Reduce a TrackingMore tracking object to the compact fields we store."""
        status_enum = (data.get("delivery_status") or "").lower() or None
        eta = (
            data.get("scheduled_delivery_date")
            or data.get("estimated_delivery_date")
            or data.get("expected_delivery")
            or None
        )
        label = TRACKINGMORE_STATUS_LABELS.get(status_enum) if status_enum else None
        return {
            "delivery_status": status_enum,
            "status": label or (status_enum.title() if status_enum else None),
            "estimated_delivery": eta,
        }

    async def create(
        self, tracking_number: str, courier_code: str
    ) -> dict[str, Any] | None:
        """Register a tracking number (costs 1 credit).

        Returns the normalized status dict on success, an empty dict when the
        number was already registered (still counts as registered, fetch status
        via ``get``), or None on failure. Distinguish with ``is not None``.
        """
        resp = await self._request(
            "POST",
            "/trackings/create",
            json={"tracking_number": tracking_number, "courier_code": courier_code},
        )
        if resp is None:
            return None

        meta = resp.get("meta", {})
        code = meta.get("code")
        if code in (200, 201):
            return self._normalize(resp.get("data") or {})

        message = str(meta.get("message", "")).lower()
        if code == _CODE_ALREADY_EXISTS or "exist" in message:
            return {}

        _LOGGER.warning(
            "TrackingMore create failed for %s/%s (code %s): %s",
            courier_code,
            tracking_number,
            code,
            meta.get("message"),
        )
        return None

    async def get(self, tracking_numbers: list[str]) -> dict[str, dict[str, Any]]:
        """Batch-read status for already-registered numbers (no credit cost).

        Returns ``{tracking_number: normalized_status_dict}``.
        """
        results: dict[str, dict[str, Any]] = {}
        for start in range(0, len(tracking_numbers), TRACKINGMORE_GET_BATCH):
            batch = tracking_numbers[start : start + TRACKINGMORE_GET_BATCH]
            resp = await self._request(
                "GET",
                "/trackings/get",
                params={"tracking_numbers": ",".join(batch)},
            )
            if resp is None:
                continue

            data = resp.get("data")
            if isinstance(data, dict):
                # Some responses wrap the list; fall back to any list-valued key.
                items = next(
                    (v for v in data.values() if isinstance(v, list)),
                    [data] if data.get("tracking_number") else [],
                )
            elif isinstance(data, list):
                items = data
            else:
                items = []

            for item in items:
                number = item.get("tracking_number")
                if number:
                    results[number] = self._normalize(item)

        return results
