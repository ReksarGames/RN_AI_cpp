"""General tab builder for the Solana AI PyQt6 GUI.

This module contains the implementation that used to live inside
ConfigApp.create_general_content. It is factored out so that the
main gui_app.py is smaller and easier to navigate, while behaviour
remains identical.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)

from widgets import NoScrollComboBox


def build_general_tab(app, layout):
    """Populate the General tab into the given *layout*.

    The *app* argument is the ConfigApp instance; this function mutates
    its attributes (e.g. fov_combo, sens_slider, etc.) exactly as the
    original method did so that the rest of ConfigApp continues to work
    unchanged.
    """
    layout.addWidget(app.create_section_title("General"))

    # Main settings group
    settings_group = app.create_settings_group()
    settings_container = QWidget()
    settings_layout = QVBoxLayout(settings_container)
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(20)

    fov_label = QLabel("Field of View")
    fov_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    settings_layout.addWidget(fov_label)

    app.fov_combo = NoScrollComboBox()
    app.fov_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.fov_combo.setStyleSheet(
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

    # Add FOV options
    fov_values = [120, 160, 180, 240, 320, 360, 480, 640]
    for value in fov_values:
        app.fov_combo.addItem(f"{value}px", value)

    # Set current FOV value
    current_fov = app.config_data.get("fov", 320)
    index = app.fov_combo.findData(current_fov)
    if index >= 0:
        app.fov_combo.setCurrentIndex(index)
    else:
        # If current value not in list, find closest
        closest_index = min(range(len(fov_values)), key=lambda i: abs(fov_values[i] - current_fov))
        app.fov_combo.setCurrentIndex(closest_index)

    settings_layout.addWidget(app.fov_combo)

    # Sensitivity, aim height, and confidence sliders
    app.sens_slider = app.create_modern_slider(
        settings_layout,
        "Sensitivity (Higher is Faster)",
        int(app.config_data["sensitivity"] * 10),
        1,
        100,
        "",
        0.1,
    )
    app.aim_height_slider = app.create_modern_slider(
        settings_layout,
        "Aim Height Offset",
        app.config_data["aim_height"],
        1,
        100,
        "%",
    )
    # Round to nearest 10 to ensure 0.01 precision alignment
    confidence_value = round(app.config_data["confidence"] * 100) * 10
    app.confidence_slider = app.create_modern_slider(
        settings_layout,
        "Ai Confidence",
        confidence_value,
        100,
        990,
        "%%",
        0.001,
        2,
        10,
    )

    layout.addWidget(settings_container)

    # Mouse FOV Settings (NEW)
    mouse_fov_group = app.create_settings_group()
    mouse_fov_container = QWidget()
    mouse_fov_layout = QVBoxLayout(mouse_fov_container)
    mouse_fov_layout.setContentsMargins(0, 0, 0, 0)
    mouse_fov_layout.setSpacing(16)

    mouse_fov_config = app.config_data.get(
        "mouse_fov",
        {
            "mouse_fov_width": 40,
            "mouse_fov_height": 40,
            "use_separate_fov": False,
        },
    )

    app.use_separate_fov_checkbox = app.create_modern_checkbox(
        "Use Separate X/Y FOV",
        mouse_fov_config.get("use_separate_fov", False),
    )
    mouse_fov_layout.addWidget(app.use_separate_fov_checkbox)

    app.mouse_fov_width_slider = app.create_modern_slider(
        mouse_fov_layout,
        "Mouse FOV Width (Horizontal)",
        mouse_fov_config.get("mouse_fov_width", 40),
        10,
        180,
        "°",
    )

    app.mouse_fov_height_slider = app.create_modern_slider(
        mouse_fov_layout,
        "Mouse FOV Height (Vertical)",
        mouse_fov_config.get("mouse_fov_height", 40),
        10,
        180,
        "°",
    )

    app.dpi_slider = app.create_modern_slider(
        mouse_fov_layout,
        "Mouse DPI",
        app.config_data.get("dpi", 800),
        400,
        3200,
        " DPI",
    )

    layout.addWidget(mouse_fov_container)

    # Keybind section
    keybind_section = app.create_settings_group()
    app.create_keybind_selector(keybind_section)
    layout.addLayout(keybind_section)

    layout.addStretch()
