"""Triggerbot tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox


def build_triggerbot_tab(app, layout):
    """Populate the Triggerbot tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Triggerbot"))
    layout.addWidget(
        app.create_section_description(
            "Automatic firing when crosshair is on target",
        )
    )

    triggerbot_config = app.config_data.get("triggerbot", {})
    if not isinstance(triggerbot_config, dict):
        triggerbot_config = {
            "enabled": False,
            "confidence": 0.5,
            "fire_delay": 0.05,
            "cooldown": 0.1,
            "require_aimbot_key": False,
            "keybind": 0x02,
        }

    # Main settings group
    trigger_group = app.create_settings_group()
    trigger_container = QWidget()
    trigger_layout = QVBoxLayout(trigger_container)
    trigger_layout.setContentsMargins(0, 0, 0, 0)
    trigger_layout.setSpacing(20)

    # Enable checkbox
    app.triggerbot_enabled_cb = app.create_modern_checkbox(
        "Enable Triggerbot",
        triggerbot_config.get("enabled", False),
    )
    trigger_layout.addWidget(app.triggerbot_enabled_cb)

    # Keybind selector
    trigger_keybind_label = QLabel("Triggerbot Activation Key:")
    trigger_keybind_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        margin-top: 12px;
        margin-bottom: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    trigger_layout.addWidget(trigger_keybind_label)

    app.triggerbot_keybind_combo = QComboBox()
    app.triggerbot_keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.triggerbot_keybind_combo.setStyleSheet(
        """
        QComboBox {
            background-color: #3e3e3e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            padding: 8px 12px;
            color: #cccccc;
            font-size: 13px;
            min-width: 200px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        QComboBox:hover {
            border-color: #555;
        }
        QComboBox:focus {
            border-color: #007acc;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #858585;
            margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            selection-background-color: #007acc;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            color: #cccccc;
            padding: 8px 12px;
            min-height: 30px;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #3e3e3e;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #007acc;
        }
        """
    )

    trigger_keybind_options = [
        ("Right Mouse Button", 0x02),
        ("Middle Mouse Button", 0x04),
        ("Mouse Button 4", 0x05),
        ("Mouse Button 5", 0x06),
        ("Left Shift", 0xA0),
        ("Left Control", 0xA2),
        ("Left Alt", 0xA4),
        ("Caps Lock", 0x14),
    ]
    for label, hex_value in trigger_keybind_options:
        app.triggerbot_keybind_combo.addItem(label, hex_value)

    current_trigger_key = triggerbot_config.get("keybind", 0x02)
    idx = app.triggerbot_keybind_combo.findData(current_trigger_key)
    if idx >= 0:
        app.triggerbot_keybind_combo.setCurrentIndex(idx)

    trigger_layout.addWidget(app.triggerbot_keybind_combo)

    # Confidence threshold
    trigger_confidence = int(triggerbot_config.get("confidence", 0.5) * 100)
    app.triggerbot_confidence_slider = app.create_modern_slider(
        trigger_layout,
        "Trigger Confidence Threshold",
        trigger_confidence,
        10,
        99,
        "%",
        0.01,
    )

    # Fire delay
    fire_delay = int(triggerbot_config.get("fire_delay", 0.05) * 1000)
    app.triggerbot_delay_slider = app.create_modern_slider(
        trigger_layout,
        "Fire Delay (ms)",
        fire_delay,
        10,
        200,
        "ms",
        0.001,
    )

    # Cooldown
    cooldown = int(triggerbot_config.get("cooldown", 0.1) * 1000)
    app.triggerbot_cooldown_slider = app.create_modern_slider(
        trigger_layout,
        "Cooldown Between Shots",
        cooldown,
        50,
        500,
        "ms",
        0.001,
    )

    # Rapid fire options
    app.triggerbot_rapidfire_cb = app.create_modern_checkbox(
        "Enable Rapid Fire",
        triggerbot_config.get("rapid_fire", True),
    )
    trigger_layout.addWidget(app.triggerbot_rapidfire_cb)

    # Shots per burst
    shots_per_burst = triggerbot_config.get("shots_per_burst", 1)
    app.triggerbot_burst_slider = app.create_modern_slider(
        trigger_layout,
        "Shots per Burst",
        shots_per_burst,
        1,
        5,
        " shots",
    )

    layout.addWidget(trigger_container)

    # Info box
    info_box = QWidget()
    info_box.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #007acc;
            border-radius: 4px;
            padding: 12px;
        }
        """
    )
    info_layout = QVBoxLayout(info_box)

    info_text = QLabel(
        "Triggerbot automatically fires when your crosshair is on an enemy. "
        "Hold the activation key to enable automatic firing.",
    )
    info_text.setStyleSheet(
        """
        color: #007acc;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    info_text.setWordWrap(True)
    info_layout.addWidget(info_text)

    layout.addWidget(info_box)
    layout.addStretch()
