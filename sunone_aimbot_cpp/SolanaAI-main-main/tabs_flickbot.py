"""Flickbot tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox


def build_flickbot_tab(app, layout):
    """Populate the Flickbot tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Flickbot"))
    layout.addWidget(
        app.create_section_description("Quick flick shots to targets"),
    )

    flickbot_config = app.config_data.get("flickbot", {})
    if not isinstance(flickbot_config, dict):
        flickbot_config = {
            "enabled": False,
            "flick_speed": 0.8,
            "flick_delay": 0.05,
            "cooldown": 1.0,
            "keybind": 0x05,
            "auto_fire": True,
            "return_to_origin": True,
        }

    # Main settings group
    flick_group = app.create_settings_group()
    flick_container = QWidget()
    flick_layout = QVBoxLayout(flick_container)
    flick_layout.setContentsMargins(0, 0, 0, 0)
    flick_layout.setSpacing(20)

    # Enable checkbox
    app.flickbot_enabled_cb = app.create_modern_checkbox(
        "Enable Flickbot",
        flickbot_config.get("enabled", False),
    )
    flick_layout.addWidget(app.flickbot_enabled_cb)

    # Keybind selector
    keybind_label = QLabel("Flickbot Activation Key:")
    keybind_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        margin-top: 12px;
        margin-bottom: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    flick_layout.addWidget(keybind_label)

    app.flickbot_keybind_combo = QComboBox()
    app.flickbot_keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.flickbot_keybind_combo.setStyleSheet(
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

    keybind_options = [
        ("Right Mouse Button", 0x02),
        ("Middle Mouse Button", 0x04),
        ("Mouse Button 4", 0x05),
        ("Mouse Button 5", 0x06),
        ("Left Shift", 0xA0),
        ("Left Control", 0xA2),
        ("Left Alt", 0xA4),
        ("Caps Lock", 0x14),
    ]
    for label, hex_value in keybind_options:
        app.flickbot_keybind_combo.addItem(label, hex_value)

    current_key = flickbot_config.get("keybind", 0x05)
    idx = app.flickbot_keybind_combo.findData(current_key)
    if idx >= 0:
        app.flickbot_keybind_combo.setCurrentIndex(idx)

    flick_layout.addWidget(app.flickbot_keybind_combo)

    # Smooth flick option
    app.flickbot_smooth_cb = app.create_modern_checkbox(
        "Smooth flick movement (slower but more stable)",
        flickbot_config.get("smooth_flick", False),
    )
    flick_layout.addWidget(app.flickbot_smooth_cb)

    # Flick speed
    flick_speed = int(flickbot_config.get("flick_speed", 0.8) * 100)
    app.flickbot_speed_slider = app.create_modern_slider(
        flick_layout,
        "Flick Speed",
        flick_speed,
        10,
        150,
        "%",
        0.01,
    )

    # Flick delay
    flick_delay = int(flickbot_config.get("flick_delay", 0.05) * 1000)
    app.flickbot_delay_slider = app.create_modern_slider(
        flick_layout,
        "Flick Delay (ms)",
        flick_delay,
        10,
        200,
        "ms",
        0.001,
    )

    # Cooldown
    flick_cooldown = int(flickbot_config.get("cooldown", 1.0) * 1000)
    app.flickbot_cooldown_slider = app.create_modern_slider(
        flick_layout,
        "Cooldown Between Flicks",
        flick_cooldown,
        100,
        3000,
        "ms",
        0.001,
    )

    # Options
    app.flickbot_autofire_cb = app.create_modern_checkbox(
        "Auto-fire after flick",
        flickbot_config.get("auto_fire", True),
    )
    flick_layout.addWidget(app.flickbot_autofire_cb)

    app.flickbot_return_cb = app.create_modern_checkbox(
        "Return to original position",
        flickbot_config.get("return_to_origin", True),
    )
    flick_layout.addWidget(app.flickbot_return_cb)

    layout.addWidget(flick_container)

    # Info box
    info_box = QWidget()
    info_box.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #e91e63;
            border-radius: 4px;
            padding: 12px;
        }
        """
    )
    info_layout = QVBoxLayout(info_box)

    info_text = QLabel(
        "Flickbot performs instant flick shots to targets. "
        "Hold the activation key and it will quickly flick to the nearest target.",
    )
    info_text.setStyleSheet(
        """
        color: #e91e63;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    info_text.setWordWrap(True)
    info_layout.addWidget(info_text)

    layout.addWidget(info_box)
    layout.addStretch()
