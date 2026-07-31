"""
Sensor node configuration screens.

SensorListScreen
    Displays all configured ESP32 sensor modules.  The user can add a new
    module or edit / delete existing ones from this screen.

SensorEditScreen
    Full-screen form for creating or editing a sensor module.  Fields:
        • Sensor ID   (text, locked when editing)
        • Description (text)
        • Flow Meter routing fields (stream, inputs, policy, outputs, priority)
        • Flow Meter descriptions
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sensors.sensor_store import SensorStore

if TYPE_CHECKING:
    from ui.navigation import Navigator

# ── Shared style constants ────────────────────────────────────────────────────

_INPUT_STYLE = (
    "QLineEdit { background: #1f2937; color: #f8fafc; border: 1px solid #374151; "
    "border-radius: 6px; padding: 8px; font-size: 14px; }"
    "QLineEdit:focus { border-color: #3b82f6; }"
    "QLineEdit:disabled { color: #6b7280; }"
)
_COMBO_STYLE = (
    "QComboBox { background: #1f2937; color: #f8fafc; border: 1px solid #374151; "
    "border-radius: 6px; padding: 8px; font-size: 14px; }"
    "QComboBox::drop-down { border: none; width: 28px; }"
    "QComboBox QAbstractItemView { background: #1f2937; color: #f8fafc; "
    "selection-background-color: #3b82f6; }"
)
_BTN_SAVE = (
    "QPushButton { background: #2563eb; color: #dbeafe; border-radius: 8px; "
    "font-size: 15px; font-weight: bold; padding: 12px; border: none; }"
    "QPushButton:pressed { background: #1d4ed8; }"
    "QPushButton:disabled { background: #374151; color: #6b7280; }"
)
_BTN_DANGER = (
    "QPushButton { background: #7f1d1d; color: #fca5a5; border-radius: 8px; "
    "font-size: 13px; padding: 6px 14px; border: none; }"
    "QPushButton:pressed { background: #991b1b; }"
)
_BTN_SECONDARY = (
    "QPushButton { background: #1f2937; color: #93c5fd; border-radius: 8px; "
    "font-size: 13px; padding: 6px 14px; border: 1px solid #374151; }"
    "QPushButton:pressed { background: #374151; }"
)

_INPUT_POLICY_LABELS: dict[str, str] = {
    "weighted": "Weighted",
    "any_active": "Any Active Source",
}

_SENSOR_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Inter", 10, QFont.Bold))
    lbl.setStyleSheet("color: #4b5563; letter-spacing: 2px; padding: 14px 0 4px 0;")
    return lbl


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Inter", 12))
    lbl.setStyleSheet("color: #9ca3af; padding-bottom: 4px;")
    return lbl


def _build_header(
    navigator: "Navigator",
    title: str,
    parent_widget: QWidget,
    extra_widget: QWidget | None = None,
) -> QWidget:
    """Return a standard 56-px header bar with a back button and optional right widget."""
    header = QWidget(parent_widget)
    header.setFixedHeight(56)
    header.setStyleSheet("background: #08090e;")

    layout = QHBoxLayout(header)
    layout.setContentsMargins(8, 0, 16, 0)

    back_btn = QPushButton("‹ Back")
    back_btn.setFont(QFont("Inter", 14))
    back_btn.setStyleSheet(
        "QPushButton { color: #60a5fa; background: transparent; border: none; padding: 4px 8px; }"
        "QPushButton:pressed { color: #3b82f6; }"
    )
    back_btn.setCursor(Qt.PointingHandCursor)
    back_btn.clicked.connect(navigator.pop)
    layout.addWidget(back_btn)

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Inter", 16, QFont.Bold))
    title_lbl.setStyleSheet("color: #f8fafc;")
    title_lbl.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_lbl, stretch=1)

    if extra_widget is not None:
        layout.addWidget(extra_widget)

    return header


def _divider() -> QFrame:
    div = QFrame()
    div.setFrameShape(QFrame.HLine)
    div.setFixedHeight(1)
    div.setStyleSheet("background: #1f2937; border: none;")
    return div


class _ClickableSensorRow(QWidget):
    """Sensor list row container that emits click events."""

    clicked = Signal()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            target = self.childAt(event.position().toPoint())
            if not isinstance(target, QPushButton):
                self.clicked.emit()
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# SensorListScreen
# ---------------------------------------------------------------------------


class SensorListScreen(QWidget):
    """
    Full-screen list of all configured sensor modules.

    Displays each sensor ID and description with **Edit** and **Delete** buttons.
    An **+ Add Sensor** button at the top navigates to :class:`SensorEditScreen`.
    """

    def __init__(
        self,
        navigator: "Navigator",
        store: SensorStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._store = store
        self._edit_screens: dict[str, "SensorEditScreen"] = {}
        self._add_screen: "SensorEditScreen | None" = None

        self._build_ui()

        # Refresh the list whenever sensors change
        self._store.subscribe(self._on_sensors_changed)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._rebuild_list()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Add button for the header right side
        add_btn = QPushButton("+ Add")
        add_btn.setFont(QFont("Inter", 13, QFont.Bold))
        add_btn.setStyleSheet(
            "QPushButton { color: #60a5fa; background: transparent; border: none; padding: 4px 8px; }"
            "QPushButton:pressed { color: #3b82f6; }"
        )
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)

        root.addWidget(_build_header(self._navigator, "Sensor Nodes", self, add_btn))
        root.addWidget(_divider())

        # Scrollable sensor list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #08090e; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: #08090e;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(16, 12, 16, 12)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        root.addWidget(scroll, stretch=1)

        self._rebuild_list()

    def _rebuild_list(self) -> None:
        """Clear and repopulate the sensor list from the store."""
        layout = self._list_layout
        # Remove all widgets except the trailing stretch
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        modules = self._store.get_all_modules()

        if not modules:
            empty = QLabel("No sensor nodes configured.\nTap  + Add  to register one.")
            empty.setFont(QFont("Inter", 13))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #4b5563; padding: 40px 0;")
            layout.insertWidget(0, empty)
            return

        for i, (sensor_id, cfg) in enumerate(sorted(modules.items())):
            row = self._build_sensor_row(sensor_id, cfg)
            layout.insertWidget(i, row)
            layout.insertWidget(i + 1, _divider())

    def _build_sensor_row(self, sensor_id: str, cfg: dict) -> QWidget:
        row = _ClickableSensorRow()
        row.setStyleSheet("background: transparent;")
        row.setCursor(Qt.PointingHandCursor)
        row.clicked.connect(lambda sid=sensor_id: self._on_edit(sid))
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 14, 0, 14)
        h.setSpacing(10)

        # Info area
        info = QVBoxLayout()
        id_lbl = QLabel(sensor_id)
        id_lbl.setFont(QFont("Inter", 14, QFont.Bold))
        id_lbl.setStyleSheet("color: #f8fafc;")
        info.addWidget(id_lbl)

        desc = cfg.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setFont(QFont("Inter", 12))
            desc_lbl.setStyleSheet("color: #6b7280;")
            desc_lbl.setWordWrap(True)
            info.addWidget(desc_lbl)

        stream_summaries = []
        for meter in ("flow1", "flow2"):
            meter_cfg = cfg.get(meter, {})
            stream_id = meter_cfg.get("stream_id") or meter_cfg.get("role", "none")
            outputs = meter_cfg.get("routing", {}).get("outputs", [])
            if outputs:
                out_text = ", ".join(
                    f"{o.get('bank', '?')}:{int(round(float(o.get('proportion', 0.0)) * 100))}%"
                    for o in outputs
                )
            else:
                out_text = "no outputs"
            stream_summaries.append(f"{meter}: {stream_id} → {out_text}")
        role_lbl = QLabel(" · ".join(stream_summaries))
        role_lbl.setFont(QFont("Inter", 11))
        role_lbl.setStyleSheet("color: #374151;")
        info.addWidget(role_lbl)

        h.addLayout(info, stretch=1)

        # Action buttons
        edit_btn = QPushButton("Edit")
        edit_btn.setFont(QFont("Inter", 12))
        edit_btn.setFixedWidth(58)
        edit_btn.setStyleSheet(_BTN_SECONDARY)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda _, sid=sensor_id: self._on_edit(sid))
        h.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setFont(QFont("Inter", 12, QFont.Bold))
        del_btn.setFixedWidth(40)
        del_btn.setStyleSheet(_BTN_DANGER)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda _, sid=sensor_id: self._on_delete(sid))
        h.addWidget(del_btn)

        return row

    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        if self._add_screen is None:
            self._add_screen = SensorEditScreen(
                self._navigator, self._store, sensor_id=None
            )
        else:
            self._add_screen.reset_for_add()
        self._navigator.push(self._add_screen)

    def _on_edit(self, sensor_id: str) -> None:
        cfg = self._store.get_module(sensor_id)
        screen = SensorEditScreen(
            self._navigator, self._store, sensor_id=sensor_id, config=cfg
        )
        self._navigator.push(screen)

    def _on_delete(self, sensor_id: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete sensor",
            f"Remove «{sensor_id}» from the configuration?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._store.remove_module(sensor_id)

    def _on_sensors_changed(self, event: str, sensor_id: str, config) -> None:
        self._rebuild_list()


# ---------------------------------------------------------------------------
# SensorEditScreen
# ---------------------------------------------------------------------------


class SensorEditScreen(QWidget):
    """
    Full-screen form for creating or editing an ESP32 sensor module entry.

    When *sensor_id* is ``None`` the form is in **Add** mode and the ID field
    is editable.  When *sensor_id* is provided the form is in **Edit** mode and
    the ID field is locked to prevent accidental renames.
    """

    def __init__(
        self,
        navigator: "Navigator",
        store: SensorStore,
        sensor_id: str | None = None,
        config: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._store = store
        self._editing_id = sensor_id

        self._build_ui()
        self._populate(sensor_id, config or {})

    # ------------------------------------------------------------------

    def reset_for_add(self) -> None:
        """Reset all fields for a fresh Add operation."""
        self._editing_id = None
        self._populate(None, {})

    def _populate(self, sensor_id: str | None, config: dict) -> None:
        """Fill form fields from *sensor_id* and *config*."""
        self._id_field.setEnabled(sensor_id is None)
        self._id_field.setText(sensor_id or "")

        self._desc_field.setText(config.get("description", ""))

        for meter, combo, desc_field in (
            ("flow1", self._flow1_policy_combo, self._flow1_desc),
            ("flow2", self._flow2_policy_combo, self._flow2_desc),
        ):
            meter_cfg = config.get(meter, {})
            routing = meter_cfg.get("routing", {})
            policy = routing.get("input_policy", "weighted")
            idx = combo.findData(policy)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            desc_field.setText(meter_cfg.get("description", ""))

            stream_field = self._flow1_stream if meter == "flow1" else self._flow2_stream
            inputs_field = self._flow1_inputs if meter == "flow1" else self._flow2_inputs
            input_weights = self._flow1_input_weights if meter == "flow1" else self._flow2_input_weights
            outputs_field = self._flow1_outputs if meter == "flow1" else self._flow2_outputs
            source_field = self._flow1_source_bank if meter == "flow1" else self._flow2_source_bank
            priority_field = self._flow1_priority if meter == "flow1" else self._flow2_priority

            stream_field.setText(meter_cfg.get("stream_id", meter_cfg.get("role", "none")))
            inputs = routing.get("inputs", [])
            inputs_field.setText(
                ", ".join(
                    str(item.get("stream", "")).strip()
                    for item in inputs
                    if isinstance(item, dict) and str(item.get("stream", "")).strip()
                )
            )
            input_weights.setText(
                ", ".join(
                    f"{item.get('stream')}:{int(round(float(item.get('proportion')) * 100))}"
                    for item in inputs
                    if isinstance(item, dict) and item.get("proportion") is not None
                )
            )
            outputs = routing.get("outputs", [])
            outputs_field.setText(
                ", ".join(
                    f"{item.get('bank')}:{int(round(float(item.get('proportion', 0.0)) * 100))}"
                    for item in outputs
                    if isinstance(item, dict)
                )
            )
            source_bank = routing.get("source_bank")
            source_field.setText("" if source_bank is None else str(source_bank))
            priority_field.setText(str(routing.get("priority", 0)))

        self._error_label.setText("")
        self._save_btn.setText("Save" if sensor_id else "Add Sensor")

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_build_header(self._navigator, "Configure Sensor", self))
        root.addWidget(_divider())

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #08090e; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        form_widget = QWidget()
        form_widget.setStyleSheet("background: #08090e;")
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(20, 12, 20, 24)
        form.setSpacing(0)

        # ── Sensor identity ───────────────────────────────────────────
        form.addWidget(_section_label("SENSOR IDENTITY"))

        form.addWidget(_field_label("Sensor ID"))
        self._id_field = QLineEdit()
        self._id_field.setPlaceholderText("e.g. flow_module_01")
        self._id_field.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._id_field)
        form.addSpacing(12)

        form.addWidget(_field_label("Description"))
        self._desc_field = QLineEdit()
        self._desc_field.setPlaceholderText("e.g. Bay-area water meters")
        self._desc_field.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._desc_field)

        # ── Flow Meter 1 ──────────────────────────────────────────────
        form.addWidget(_section_label("FLOW METER 1"))

        form.addWidget(_field_label("Stream ID"))
        self._flow1_stream = QLineEdit()
        self._flow1_stream.setPlaceholderText("e.g. fresh_water_out")
        self._flow1_stream.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_stream)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Sources (comma-separated stream IDs)"))
        self._flow1_inputs = QLineEdit()
        self._flow1_inputs.setPlaceholderText("e.g. fresh_water_out, city_water_in")
        self._flow1_inputs.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_inputs)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Policy"))
        self._flow1_policy_combo = self._make_policy_combo()
        form.addWidget(self._flow1_policy_combo)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Weights % (stream:percent, optional)"))
        self._flow1_input_weights = QLineEdit()
        self._flow1_input_weights.setPlaceholderText("e.g. fresh_water_out:50, city_water_in:50")
        self._flow1_input_weights.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_input_weights)
        form.addSpacing(12)

        form.addWidget(_field_label("Output Splits % (bank:percent)"))
        self._flow1_outputs = QLineEdit()
        self._flow1_outputs.setPlaceholderText("e.g. grey:60, black:40")
        self._flow1_outputs.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_outputs)
        form.addSpacing(12)

        form.addWidget(_field_label("Source Bank (fresh/grey/black, optional)"))
        self._flow1_source_bank = QLineEdit()
        self._flow1_source_bank.setPlaceholderText("e.g. fresh")
        self._flow1_source_bank.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_source_bank)
        form.addSpacing(12)

        form.addWidget(_field_label("Priority"))
        self._flow1_priority = QLineEdit()
        self._flow1_priority.setPlaceholderText("0")
        self._flow1_priority.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_priority)
        form.addSpacing(12)

        form.addWidget(_field_label("Description"))
        self._flow1_desc = QLineEdit()
        self._flow1_desc.setPlaceholderText("e.g. Fresh water tank outflow")
        self._flow1_desc.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow1_desc)

        # ── Flow Meter 2 ──────────────────────────────────────────────
        form.addWidget(_section_label("FLOW METER 2"))

        form.addWidget(_field_label("Stream ID"))
        self._flow2_stream = QLineEdit()
        self._flow2_stream.setPlaceholderText("e.g. city_water_in")
        self._flow2_stream.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_stream)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Sources (comma-separated stream IDs)"))
        self._flow2_inputs = QLineEdit()
        self._flow2_inputs.setPlaceholderText("e.g. fresh_water_out, city_water_in")
        self._flow2_inputs.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_inputs)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Policy"))
        self._flow2_policy_combo = self._make_policy_combo()
        form.addWidget(self._flow2_policy_combo)
        form.addSpacing(12)

        form.addWidget(_field_label("Input Weights % (stream:percent, optional)"))
        self._flow2_input_weights = QLineEdit()
        self._flow2_input_weights.setPlaceholderText("e.g. fresh_water_out:50, city_water_in:50")
        self._flow2_input_weights.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_input_weights)
        form.addSpacing(12)

        form.addWidget(_field_label("Output Splits % (bank:percent)"))
        self._flow2_outputs = QLineEdit()
        self._flow2_outputs.setPlaceholderText("e.g. black:100")
        self._flow2_outputs.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_outputs)
        form.addSpacing(12)

        form.addWidget(_field_label("Source Bank (fresh/grey/black, optional)"))
        self._flow2_source_bank = QLineEdit()
        self._flow2_source_bank.setPlaceholderText("e.g. fresh")
        self._flow2_source_bank.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_source_bank)
        form.addSpacing(12)

        form.addWidget(_field_label("Priority"))
        self._flow2_priority = QLineEdit()
        self._flow2_priority.setPlaceholderText("0")
        self._flow2_priority.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_priority)
        form.addSpacing(12)

        form.addWidget(_field_label("Description"))
        self._flow2_desc = QLineEdit()
        self._flow2_desc.setPlaceholderText("e.g. City water hookup inflow")
        self._flow2_desc.setStyleSheet(_INPUT_STYLE)
        form.addWidget(self._flow2_desc)

        form.addSpacing(20)

        # Error label
        self._error_label = QLabel("")
        self._error_label.setFont(QFont("Inter", 12))
        self._error_label.setStyleSheet("color: #f87171; padding: 4px 0;")
        self._error_label.setWordWrap(True)
        form.addWidget(self._error_label)

        # Save button
        self._save_btn = QPushButton("Add Sensor")
        self._save_btn.setFont(QFont("Inter", 15, QFont.Bold))
        self._save_btn.setStyleSheet(_BTN_SAVE)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        form.addWidget(self._save_btn)
        form.addStretch()

        scroll.setWidget(form_widget)
        root.addWidget(scroll, stretch=1)

    @staticmethod
    def _make_policy_combo() -> QComboBox:
        combo = QComboBox()
        combo.setStyleSheet(_COMBO_STYLE)
        for policy in ("weighted", "any_active"):
            combo.addItem(_INPUT_POLICY_LABELS.get(policy, policy), userData=policy)
        return combo

    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        sensor_id = self._id_field.text().strip()
        description = self._desc_field.text().strip()

        # Validate
        if not sensor_id:
            self._error_label.setText("Sensor ID cannot be empty.")
            return
        if not _SENSOR_ID_RE.match(sensor_id):
            self._error_label.setText(
                "Sensor ID may only contain letters, digits, hyphens, and underscores (max 48 chars)."
            )
            return
        if self._editing_id is None and self._store.get_module(sensor_id) is not None:
            self._error_label.setText(f"A sensor with ID «{sensor_id}» already exists.")
            return

        try:
            flow1_cfg = self._build_meter_config(
                stream_id=self._flow1_stream.text().strip(),
                policy=self._flow1_policy_combo.currentData(),
                inputs_text=self._flow1_inputs.text().strip(),
                input_weights_text=self._flow1_input_weights.text().strip(),
                outputs_text=self._flow1_outputs.text().strip(),
                source_bank_text=self._flow1_source_bank.text().strip(),
                priority_text=self._flow1_priority.text().strip(),
                description_text=self._flow1_desc.text().strip(),
            )
            flow2_cfg = self._build_meter_config(
                stream_id=self._flow2_stream.text().strip(),
                policy=self._flow2_policy_combo.currentData(),
                inputs_text=self._flow2_inputs.text().strip(),
                input_weights_text=self._flow2_input_weights.text().strip(),
                outputs_text=self._flow2_outputs.text().strip(),
                source_bank_text=self._flow2_source_bank.text().strip(),
                priority_text=self._flow2_priority.text().strip(),
                description_text=self._flow2_desc.text().strip(),
            )
        except ValueError as exc:
            self._error_label.setText(str(exc))
            return

        config = {"description": description, "flow1": flow1_cfg, "flow2": flow2_cfg}

        self._store.add_or_update_module(sensor_id, config)
        self._navigator.pop()

    @staticmethod
    def _parse_split_pairs(text: str, *, allow_empty: bool) -> list[tuple[str, float]]:
        if not text:
            return []
        items = [part.strip() for part in text.split(",") if part.strip()]
        pairs: list[tuple[str, float]] = []
        for item in items:
            if ":" not in item:
                raise ValueError(f"Expected key:percent entry: '{item}'")
            key, raw_pct = item.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError("Split entry key cannot be empty")
            try:
                pct = float(raw_pct.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid percent in '{item}'") from exc
            if pct < 0:
                raise ValueError(f"Percent must be >= 0 in '{item}'")
            pairs.append((key, pct / 100.0))
        if not allow_empty and not pairs:
            raise ValueError("At least one split entry is required")
        return pairs

    @staticmethod
    def _build_meter_config(
        *,
        stream_id: str,
        policy: str,
        inputs_text: str,
        input_weights_text: str,
        outputs_text: str,
        source_bank_text: str,
        priority_text: str,
        description_text: str,
    ) -> dict:
        if not stream_id:
            stream_id = "none"

        source_names = [item.strip() for item in inputs_text.split(",") if item.strip()]
        input_weights = dict(
            SensorEditScreen._parse_split_pairs(input_weights_text, allow_empty=True)
        )
        inputs: list[dict] = []
        for src in source_names:
            inputs.append({"stream": src, "proportion": input_weights.get(src)})

        outputs = [
            {"bank": bank.lower(), "proportion": proportion}
            for bank, proportion in SensorEditScreen._parse_split_pairs(
                outputs_text, allow_empty=True
            )
        ]
        if outputs:
            total = sum(item["proportion"] for item in outputs)
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"Output percentages for stream '{stream_id}' must sum to 100"
                )

        try:
            priority = int(priority_text or "0")
        except ValueError as exc:
            raise ValueError(f"Priority must be an integer for stream '{stream_id}'") from exc

        source_bank = source_bank_text.lower() if source_bank_text else None
        if source_bank not in (None, "fresh", "grey", "black"):
            raise ValueError(
                f"Source bank must be fresh, grey, black, or empty for stream '{stream_id}'"
            )

        if policy not in ("weighted", "any_active"):
            raise ValueError(f"Invalid input policy for stream '{stream_id}'")

        if stream_id == "none" and outputs:
            raise ValueError("Not Assigned stream cannot have output splits")

        return {
            "stream_id": stream_id,
            "description": description_text,
            "routing": {
                "priority": priority,
                "input_policy": policy,
                "inputs": inputs,
                "outputs": outputs,
                "source_bank": source_bank,
            },
        }
