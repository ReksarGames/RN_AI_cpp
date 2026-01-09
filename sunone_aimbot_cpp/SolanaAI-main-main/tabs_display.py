"""Display tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


def build_display_tab(app, layout):
    """Populate the Display tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Display"))
    layout.addWidget(
        app.create_section_description("Customize overlay appearance and behavior")
    )

    # Overlay settings
    overlay_group = app.create_settings_group()
    overlay_container = QWidget()
    overlay_layout = QVBoxLayout(overlay_container)
    overlay_layout.setContentsMargins(0, 0, 0, 0)
    overlay_layout.setSpacing(12)

    app.show_overlay_checkbox = app.create_modern_checkbox(
        "Enable Overlay", app.config_data.get("show_overlay", True)
    )
    overlay_layout.addWidget(app.show_overlay_checkbox)

    app.overlay_show_borders_checkbox = app.create_modern_checkbox(
        "Show Overlay Borders", app.config_data.get("overlay_show_borders", True)
    )
    overlay_layout.addWidget(app.overlay_show_borders_checkbox)

    app.circle_capture_checkbox = app.create_modern_checkbox(
        "Circular Capture Region", app.config_data.get("circle_capture", True)
    )
    overlay_layout.addWidget(app.circle_capture_checkbox)

    layout.addWidget(overlay_container)

    # Shape selector
    shape_group = app.create_settings_group()
    app.create_shape_selector(shape_group)
    layout.addLayout(shape_group)

    # Debug settings
    debug_group = app.create_settings_group()
    debug_container = QWidget()
    debug_layout = QVBoxLayout(debug_container)
    debug_layout.setContentsMargins(0, 0, 0, 0)
    debug_layout.setSpacing(12)

    debug_layout.addWidget(app.create_group_label("Debug Options"))

    app.show_debug_window_checkbox = app.create_modern_checkbox(
        "Show Debug Window (320x320)",
        app.config_data.get("show_debug_window", False),
    )
    debug_layout.addWidget(app.show_debug_window_checkbox)

    debug_desc = QLabel("Small window showing real-time FPS and CUDA GPU acceleration status")
    debug_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 4px;
        margin-left: 26px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    debug_desc.setWordWrap(True)
    debug_layout.addWidget(debug_desc)

    layout.addWidget(debug_container)

    # Resolution settings
    res_group = app.create_settings_group()
    res_container = QWidget()
    res_layout = QVBoxLayout(res_container)
    res_layout.setContentsMargins(0, 0, 0, 0)
    res_layout.setSpacing(12)

    res_layout.addWidget(app.create_group_label("Resolution"))

    app.custom_res_checkbox = app.create_modern_checkbox(
        "Use Custom Resolution",
        app.config_data["custom_resolution"]["use_custom_resolution"],
    )
    res_layout.addWidget(app.custom_res_checkbox)

    res_inputs = QWidget()
    res_inputs_layout = QVBoxLayout(res_inputs)
    res_inputs_layout.setContentsMargins(0, 8, 0, 0)
    res_inputs_layout.setSpacing(12)

    app.res_x_entry = app.create_modern_input(
        "Width", str(app.config_data["custom_resolution"]["x"])
    )
    app.res_y_entry = app.create_modern_input(
        "Height", str(app.config_data["custom_resolution"]["y"])
    )

    # Keep inner layout horizontal as in the original code
    from PyQt6.QtWidgets import QHBoxLayout  # local import to avoid polluting module

    h_layout = QHBoxLayout()
    h_layout.setContentsMargins(0, 8, 0, 0)
    h_layout.setSpacing(12)
    h_layout.addWidget(app.res_x_entry)
    h_layout.addWidget(app.res_y_entry)
    h_layout.addStretch()

    res_layout.addLayout(h_layout)

    res_layout.addWidget(res_inputs)
    layout.addWidget(res_container)

    layout.addStretch()
