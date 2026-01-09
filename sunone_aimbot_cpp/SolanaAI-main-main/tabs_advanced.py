"""Advanced movement/curves tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel


def build_advanced_tab(app, layout):
    """Populate the Advanced tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Advanced"))
    layout.addWidget(
        app.create_section_description("Movement curves and humanization settings")
    )

    movement_config = app.config_data.get(
        "movement",
        {
            "use_curves": False,
            "curve_type": "Exponential",  # Default to fastest
            "movement_speed": 3.0,  # Higher default speed
            "smoothing_enabled": True,
            "smoothing_factor": 0.1,  # Lower for faster response
            "random_curves": False,
        },
    )

    # Humanizer section
    humanizer_group = app.create_settings_group()
    humanizer_container = QWidget()
    humanizer_layout = QVBoxLayout(humanizer_container)
    humanizer_layout.setContentsMargins(0, 0, 0, 0)
    humanizer_layout.setSpacing(20)

    humanizer_layout.addWidget(app.create_group_label("Movement Curves"))

    app.enable_movement_curves_checkbox = app.create_modern_checkbox(
        "Enable Movement Curves", movement_config.get("use_curves", False)
    )
    humanizer_layout.addWidget(app.enable_movement_curves_checkbox)

    # Description
    curves_desc = QLabel(
        "Adds subtle natural movement while maintaining aimlock speed",
    )
    curves_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 4px;
        margin-left: 26px;
        margin-bottom: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    curves_desc.setWordWrap(True)
    humanizer_layout.addWidget(curves_desc)

    # Humanization slider (lower values for faster curves)
    smoothing_factor = movement_config.get("smoothing_factor", 0.1)
    humanizer_value = int(smoothing_factor * 100)
    app.humanizer_slider = app.create_modern_slider(
        humanizer_layout,
        "Humanization Level (Lower = Faster)",
        humanizer_value,
        0,
        100,
        "%",
    )

    layout.addWidget(humanizer_container)

    # Speed Preset Buttons
    preset_group = app.create_settings_group()
    preset_container = QWidget()
    preset_layout = QVBoxLayout(preset_container)
    preset_layout.setContentsMargins(0, 0, 0, 0)
    preset_layout.setSpacing(12)

    preset_layout.addWidget(app.create_group_label("Speed Presets"))

    # Preset buttons layout
    preset_buttons_layout = QHBoxLayout()
    preset_buttons_layout.setSpacing(8)

    # Create preset buttons
    app.aimlock_btn = app.create_preset_button("Aimlock", "#e91e63")
    app.aimlock_btn.clicked.connect(lambda: app.apply_curve_preset("aimlock"))
    preset_buttons_layout.addWidget(app.aimlock_btn)

    app.fast_btn = app.create_preset_button("Fast", "#ff9800")
    app.fast_btn.clicked.connect(lambda: app.apply_curve_preset("fast"))
    preset_buttons_layout.addWidget(app.fast_btn)

    app.medium_btn = app.create_preset_button("Medium", "#4caf50")
    app.medium_btn.clicked.connect(lambda: app.apply_curve_preset("medium"))
    preset_buttons_layout.addWidget(app.medium_btn)

    app.slow_btn = app.create_preset_button("Slow", "#2196f3")
    app.slow_btn.clicked.connect(lambda: app.apply_curve_preset("slow"))
    preset_buttons_layout.addWidget(app.slow_btn)

    preset_layout.addLayout(preset_buttons_layout)

    # Preset description
    app.preset_desc = QLabel(
        "Aimlock: Fastest with minimal curves (5% humanization)",
    )
    app.preset_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    app.preset_desc.setWordWrap(True)
    preset_layout.addWidget(app.preset_desc)

    layout.addWidget(preset_container)

    # Curve settings
    curve_group = app.create_settings_group()
    curve_container = QWidget()
    curve_layout = QVBoxLayout(curve_container)
    curve_layout.setContentsMargins(0, 0, 0, 0)
    curve_layout.setSpacing(20)

    curve_layout.addWidget(app.create_group_label("Curve Settings"))

    app.create_curve_selector(
        curve_layout,
        movement_config.get("curve_type", "Exponential"),
    )

    # Movement speed slider with higher default
    movement_speed = int(movement_config.get("movement_speed", 3.0) * 10)
    app.movement_speed_slider = app.create_modern_slider(
        curve_layout,
        "Movement Speed (Higher = Faster)",
        movement_speed,
        10,
        50,
        "",
        0.1,
    )

    # Additional options
    options_widget = QWidget()
    options_layout = QVBoxLayout(options_widget)
    options_layout.setContentsMargins(0, 12, 0, 0)
    options_layout.setSpacing(12)

    app.random_curves_checkbox = app.create_modern_checkbox(
        "Randomize Curve Types", movement_config.get("random_curves", False)
    )
    options_layout.addWidget(app.random_curves_checkbox)

    app.curve_smoothing_checkbox = app.create_modern_checkbox(
        "Enable Curve Smoothing", movement_config.get("smoothing_enabled", True)
    )
    options_layout.addWidget(app.curve_smoothing_checkbox)

    curve_layout.addWidget(options_widget)
    layout.addWidget(curve_container)

    layout.addStretch()
