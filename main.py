"""
RV Monitor – application entry point.

Run with:
    python main.py

The app targets a 600 × 1024 vertical touchscreen.  On a desktop it will open
a window of the same size so the layout can be tested before deploying to the
Raspberry Pi.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from sensors.mqtt_flow_meter_client import MqttFlowMeterClient
from sensors.sensor_store import SensorStore
from ui.main_screen import MainScreen
from ui.navigation import Navigator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 1024


def _connect_flow_meters(store: SensorStore) -> MqttFlowMeterClient:
    """
    Attempt to connect to the MQTT broker for flow meter data.

    If the connection fails the app continues with zero flow data.
    Returns the client (kept alive for the application lifetime).
    """
    client = MqttFlowMeterClient(
        store.get_mqtt_broker(),
        store.get_mqtt_port(),
        store.get_all_modules(),
    )
    connected = client.connect()
    if connected:
        logger.info(
            "MQTT flow meter client connecting to broker %s:%s",
            store.get_mqtt_broker(),
            store.get_mqtt_port(),
        )
    else:
        logger.warning("MQTT broker not reachable – using placeholder tank levels")

    # Keep MQTT subscriptions in sync with sensor store changes
    def _on_sensor_change(event: str, sensor_id: str, config) -> None:
        if event == "add":
            client.add_sensor_module(sensor_id, config)
        elif event == "update":
            client.update_sensor_module(sensor_id, config)
        elif event == "remove":
            client.remove_sensor_module(sensor_id)

    store.subscribe(_on_sensor_change)
    return client


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    app.setStyleSheet(
        """
        QWidget { background-color: #0d1b2a; color: #eceff1; }
        QScrollBar:vertical {
            background: #0d1b2a; width: 8px; margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #1e3a5f; border-radius: 4px; min-height: 24px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """
    )

    # Load persistent sensor configuration
    store = SensorStore()

    # Flow meter MQTT client (non-blocking – app runs even without hardware)
    flow_client = _connect_flow_meters(store)  # noqa: F841  (kept alive)

    # Main window
    window = QMainWindow()
    window.setWindowTitle("RV Monitor")
    window.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

    stack = QStackedWidget()
    window.setCentralWidget(stack)

    navigator = Navigator(stack)

    main_screen = MainScreen(navigator, store=store)
    navigator.replace(main_screen)

    # Full-screen on Pi; windowed on desktop for development
    if "--fullscreen" in sys.argv:
        window.showFullScreen()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
