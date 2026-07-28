"""
ESP32 Flow Meter client.

Connects to the ESP32 flow meter module over WiFi (HTTP or MQTT, TBD).
Currently returns mock values; swap out the method bodies when the real
hardware endpoint is known.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FlowMeterClient:
    """Client for the ESP32 fresh-water flow meter module."""

    def __init__(self, host: str = "192.168.1.100", port: int = 80) -> None:
        self._host = host
        self._port = port
        self._connected = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Establish a connection to the ESP32 flow meter.

        Returns True on success, False on failure.
        Replace the body with real HTTP/MQTT initialisation when ready.
        """
        logger.info("FlowMeterClient: connecting to %s:%s (mock)", self._host, self._port)
        # TODO: implement real connection (HTTP session or MQTT client)
        self._connected = True
        return self._connected

    def disconnect(self) -> None:
        """Close the connection to the flow meter."""
        logger.info("FlowMeterClient: disconnecting (mock)")
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_flow_rate(self) -> float:
        """
        Return the current flow rate in gallons per minute.

        Replace with a real HTTP GET / MQTT subscribe when hardware is ready.
        """
        if not self._connected:
            logger.warning("FlowMeterClient: not connected, returning 0.0 for flow rate")
            return 0.0
        # TODO: fetch from ESP32 endpoint
        return 0.0

    def get_total_gallons_used(self) -> float:
        """
        Return the cumulative gallons used since last reset.

        Replace with a real HTTP GET / MQTT subscribe when hardware is ready.
        """
        if not self._connected:
            logger.warning("FlowMeterClient: not connected, returning 0.0 for total gallons")
            return 0.0
        # TODO: fetch from ESP32 endpoint
        return 0.0
