"""Anti-recoil tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout


def build_antirecoil_tab(app, layout):
    """Populate the Anti-Recoil tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Anti-Recoil"))
    layout.addWidget(
        app.create_section_description(
            "Smart recoil compensation that activates only when aiming",
        )
    )

    anti_recoil_config = app.config_data.get(
        "anti_recoil",
        {
            "enabled": False,
            "strength": 5.0,
            "reduce_bloom": True,
            "require_target": True,
            "require_keybind": True,
        },
    )

    # Main settings group
    recoil_group = app.create_settings_group()
    recoil_container = QWidget()
    recoil_layout = QVBoxLayout(recoil_container)
    recoil_layout.setContentsMargins(0, 0, 0, 0)
    recoil_layout.setSpacing(20)

    recoil_layout.addWidget(app.create_group_label("Recoil Control"))

    # Enable checkbox
    app.anti_recoil_enabled_cb = app.create_modern_checkbox(
        "Enable Anti-Recoil",
        anti_recoil_config.get("enabled", False),
    )
    recoil_layout.addWidget(app.anti_recoil_enabled_cb)

    # Description
    recoil_desc = QLabel(
        "Smart anti-recoil that only activates when you're actually aiming at enemies",
    )
    recoil_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 4px;
        margin-left: 26px;
        margin-bottom: 16px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    recoil_desc.setWordWrap(True)
    recoil_layout.addWidget(recoil_desc)

    # Strength slider
    anti_recoil_strength = int(anti_recoil_config.get("strength", 5.0))
    app.anti_recoil_strength_slider = app.create_modern_slider(
        recoil_layout,
        "Recoil Compensation Strength",
        anti_recoil_strength,
        0,
        20,
        "",
    )

    # Reduce bloom checkbox
    app.anti_recoil_bloom_cb = app.create_modern_checkbox(
        "Reduce Horizontal Bloom",
        anti_recoil_config.get("reduce_bloom", True),
    )
    recoil_layout.addWidget(app.anti_recoil_bloom_cb)

    layout.addWidget(recoil_container)

    # Activation Settings Group
    activation_group = app.create_settings_group()
    activation_container = QWidget()
    activation_layout = QVBoxLayout(activation_container)
    activation_layout.setContentsMargins(0, 0, 0, 0)
    activation_layout.setSpacing(12)

    activation_layout.addWidget(app.create_group_label("Activation Requirements"))

    # Require target checkbox
    app.require_target_cb = app.create_modern_checkbox(
        "Only activate when target is detected",
        anti_recoil_config.get("require_target", True),
    )
    activation_layout.addWidget(app.require_target_cb)

    # Require keybind checkbox
    app.require_keybind_cb = app.create_modern_checkbox(
        "Only activate when aimbot key is pressed",
        anti_recoil_config.get("require_keybind", True),
    )
    activation_layout.addWidget(app.require_keybind_cb)

    # Activation info
    activation_info = QLabel(
        "With both options enabled, anti-recoil only works when:\n"
        "• A target is detected by the AI\n"
        "• Your aimbot keybind is pressed\n"
        "• You're firing (left mouse)",
    )
    activation_info.setStyleSheet(
        """
        color: #4caf50;
        font-size: 12px;
        margin-top: 8px;
        padding: 12px;
        background-color: #1e1e1e;
        border: 1px solid #4caf50;
        border-radius: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    activation_info.setWordWrap(True)
    activation_layout.addWidget(activation_info)

    layout.addWidget(activation_container)

    # Weapon Presets Group
    presets_group = app.create_settings_group()
    presets_container = QWidget()
    presets_layout = QVBoxLayout(presets_container)
    presets_layout.setContentsMargins(0, 0, 0, 0)
    presets_layout.setSpacing(12)

    presets_layout.addWidget(app.create_group_label("Weapon Presets"))

    # Preset buttons
    preset_buttons_layout = QHBoxLayout()
    preset_buttons_layout.setSpacing(8)

    # Create weapon preset buttons
    app.smg_preset_btn = app.create_preset_button("SMG", "#4caf50")
    app.smg_preset_btn.clicked.connect(lambda: app.apply_recoil_preset("smg"))
    preset_buttons_layout.addWidget(app.smg_preset_btn)

    app.ar_preset_btn = app.create_preset_button("Assault Rifle", "#2196f3")
    app.ar_preset_btn.clicked.connect(lambda: app.apply_recoil_preset("ar"))
    preset_buttons_layout.addWidget(app.ar_preset_btn)

    app.lmg_preset_btn = app.create_preset_button("LMG", "#ff9800")
    app.lmg_preset_btn.clicked.connect(lambda: app.apply_recoil_preset("lmg"))
    preset_buttons_layout.addWidget(app.lmg_preset_btn)

    app.sniper_preset_btn = app.create_preset_button("Sniper", "#9c27b0")
    app.sniper_preset_btn.clicked.connect(lambda: app.apply_recoil_preset("sniper"))
    preset_buttons_layout.addWidget(app.sniper_preset_btn)

    presets_layout.addLayout(preset_buttons_layout)

    # Preset description
    app.recoil_preset_desc = QLabel(
        "SMG: Low recoil compensation (3-5 strength)",
    )
    app.recoil_preset_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    app.recoil_preset_desc.setWordWrap(True)
    presets_layout.addWidget(app.recoil_preset_desc)

    layout.addWidget(presets_container)
    layout.addStretch()
