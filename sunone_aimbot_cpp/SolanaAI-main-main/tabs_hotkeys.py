"""Hotkeys tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel


def build_hotkeys_tab(app, layout):
    """Populate the Hotkeys tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Hotkeys"))
    layout.addWidget(app.create_section_description("Configure keyboard shortcuts"))

    hotkeys_config = app.config_data.get(
        "hotkeys",
        {
            "stream_proof_key": "0x75",  # F6
            "menu_toggle_key": "0x76",  # F7
            "stream_proof_enabled": False,
            "menu_visible": True,
        },
    )

    # Stream-proof settings
    stream_group = app.create_settings_group()
    stream_container = QWidget()
    stream_layout = QVBoxLayout(stream_container)
    stream_layout.setContentsMargins(0, 0, 0, 0)
    stream_layout.setSpacing(12)

    stream_layout.addWidget(app.create_group_label("Stream-Proof Mode"))

    # Stream-proof description
    stream_desc = QLabel(
        "Makes windows invisible to streaming/recording software (OBS, Discord, etc.)",
    )
    stream_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-bottom: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    stream_desc.setWordWrap(True)
    stream_layout.addWidget(stream_desc)

    # Stream-proof keybind selector
    app.stream_proof_keybind_combo = app.create_keybind_combo(
        "Stream-Proof Toggle",
        hotkeys_config.get("stream_proof_key", "0x75"),
    )
    stream_layout.addWidget(app.stream_proof_keybind_combo)

    layout.addWidget(stream_container)

    # Menu visibility settings
    menu_group = app.create_settings_group()
    menu_container = QWidget()
    menu_layout = QVBoxLayout(menu_container)
    menu_layout.setContentsMargins(0, 0, 0, 0)
    menu_layout.setSpacing(12)

    menu_layout.addWidget(app.create_group_label("Menu Visibility"))

    # Menu keybind selector
    app.menu_toggle_keybind_combo = app.create_keybind_combo(
        "Menu Toggle",
        hotkeys_config.get("menu_toggle_key", "0x76"),
    )
    menu_layout.addWidget(app.menu_toggle_keybind_combo)

    layout.addWidget(menu_container)

    # Status
    status_group = app.create_settings_group()
    status_container = QWidget()
    status_layout = QVBoxLayout(status_container)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(8)

    status_layout.addWidget(app.create_group_label("Current Status"))

    app.stream_proof_status = QLabel("Stream-Proof: Disabled")
    app.stream_proof_status.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        padding: 8px;
        background-color: #1e1e1e;
        border: 1px solid #3e3e3e;
        border-radius: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    status_layout.addWidget(app.stream_proof_status)

    layout.addWidget(status_container)
    layout.addStretch()
