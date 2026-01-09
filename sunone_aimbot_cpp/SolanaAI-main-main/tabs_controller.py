"""Controller tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QGridLayout,
    QComboBox,
)


def build_controller_tab(app, layout):
    """Populate the Controller tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Controller"))
    layout.addWidget(
        app.create_section_description("Configure gamepad support for aimbot control"),
    )

    # Create scroll area
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setStyleSheet(
        """
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #3e3e3e;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4a4a4a;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        """
    )

    # Create container widget for scroll content
    scroll_content = QWidget()
    scroll_content.setStyleSheet("background-color: transparent;")
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setContentsMargins(0, 0, 12, 0)  # Right margin for scrollbar
    scroll_layout.setSpacing(24)

    # Get current controller config
    controller_config = app.config_data.get(
        "controller",
        {
            "enabled": False,
            "sensitivity": 1.0,
            "deadzone": 15,
            "vibration": True,
            "trigger_threshold": 50,
            "aim_stick": "right",
            "activation_button": "right_trigger",
            "button_mappings": {},
        },
    )

    # Connection Status Group
    status_container = QWidget()
    status_layout = QVBoxLayout(status_container)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(12)

    status_layout.addWidget(app.create_group_label("Controller Status"))

    # Status widget
    app.controller_status_widget = QWidget()
    app.controller_status_widget.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            padding: 12px;
        }
        """
    )
    status_info_layout = QHBoxLayout(app.controller_status_widget)

    # Controller icon and status
    app.controller_icon = QLabel("🎮")
    app.controller_icon.setStyleSheet("font-size: 24px;")
    status_info_layout.addWidget(app.controller_icon)

    app.controller_status_label = QLabel("No Controller Connected")
    app.controller_status_label.setStyleSheet(
        """
        color: #858585;
        font-size: 14px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    status_info_layout.addWidget(app.controller_status_label)
    status_info_layout.addStretch()

    # Refresh button
    app.refresh_controller_btn = app.create_small_button("Refresh", "#3e3e3e")
    app.refresh_controller_btn.clicked.connect(app.refresh_controller_status)
    status_info_layout.addWidget(app.refresh_controller_btn)

    status_layout.addWidget(app.controller_status_widget)

    # Enable checkbox
    app.controller_enabled_cb = app.create_modern_checkbox(
        "Enable Controller Support",
        controller_config.get("enabled", False),
    )
    status_layout.addWidget(app.controller_enabled_cb)

    scroll_layout.addWidget(status_container)

    # Input Settings Group
    input_container = QWidget()
    input_layout = QVBoxLayout(input_container)
    input_layout.setContentsMargins(0, 0, 0, 0)
    input_layout.setSpacing(20)

    input_layout.addWidget(app.create_group_label("Input Configuration"))

    # Activation method
    activation_label = QLabel("Activation Method:")
    activation_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        margin-bottom: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    input_layout.addWidget(activation_label)

    app.controller_activation_combo = QComboBox()
    app.controller_activation_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.controller_activation_combo.setStyleSheet(app.get_combo_style())
    app.controller_activation_combo.setStyleSheet(
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

    activation_options = [
        ("Right Trigger (RT)", "right_trigger"),
        ("Left Trigger (LT)", "left_trigger"),
        ("Right Bumper (RB)", "right_bumper"),
        ("Left Bumper (LB)", "left_bumper"),
        ("Right Stick Click (RS)", "right_stick"),
        ("A Button", "a_button"),
        ("X Button", "x_button"),
    ]
    for label, value in activation_options:
        app.controller_activation_combo.addItem(label, value)

    current_activation = controller_config.get("activation_button", "right_trigger")
    idx = app.controller_activation_combo.findData(current_activation)
    if idx >= 0:
        app.controller_activation_combo.setCurrentIndex(idx)

    input_layout.addWidget(app.controller_activation_combo)

    # Aim stick selector
    aim_stick_label = QLabel("Aim Control Stick:")
    aim_stick_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        margin-top: 12px;
        margin-bottom: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    input_layout.addWidget(aim_stick_label)

    app.aim_stick_combo = QComboBox()
    app.aim_stick_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.aim_stick_combo.setStyleSheet(app.get_combo_style())
    app.aim_stick_combo.setStyleSheet(
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

    app.aim_stick_combo.addItem("Right Stick", "right")
    app.aim_stick_combo.addItem("Left Stick", "left")
    app.aim_stick_combo.addItem("Both Sticks", "both")

    current_stick = controller_config.get("aim_stick", "right")
    idx = app.aim_stick_combo.findData(current_stick)
    if idx >= 0:
        app.aim_stick_combo.setCurrentIndex(idx)

    input_layout.addWidget(app.aim_stick_combo)

    # Sensitivity slider
    controller_sens = int(controller_config.get("sensitivity", 1.0) * 10)
    app.controller_sens_slider = app.create_modern_slider(
        input_layout,
        "Controller Sensitivity",
        controller_sens,
        1,
        50,
        "",
        0.1,
    )

    # Deadzone slider
    deadzone = int(controller_config.get("deadzone", 15))
    app.controller_deadzone_slider = app.create_modern_slider(
        input_layout,
        "Analog Stick Deadzone",
        deadzone,
        5,
        40,
        "%",
    )

    # Trigger threshold slider
    trigger_threshold = int(controller_config.get("trigger_threshold", 50))
    app.trigger_threshold_slider = app.create_modern_slider(
        input_layout,
        "Trigger Activation Threshold",
        trigger_threshold,
        10,
        90,
        "%",
    )

    scroll_layout.addWidget(input_container)

    # Features Group
    features_container = QWidget()
    features_layout = QVBoxLayout(features_container)
    features_layout.setContentsMargins(0, 0, 0, 0)
    features_layout.setSpacing(12)

    features_layout.addWidget(app.create_group_label("Controller Features"))

    # Vibration feedback
    app.controller_vibration_cb = app.create_modern_checkbox(
        "Enable Vibration Feedback",
        controller_config.get("vibration", True),
    )
    features_layout.addWidget(app.controller_vibration_cb)

    # Auto-switch to controller
    app.controller_autoswitch_cb = app.create_modern_checkbox(
        "Auto-switch to controller when connected",
        controller_config.get("auto_switch", False),
    )
    features_layout.addWidget(app.controller_autoswitch_cb)

    # Hold to aim option
    app.controller_hold_aim_cb = app.create_modern_checkbox(
        "Hold button to aim (release to stop)",
        controller_config.get("hold_to_aim", True),
    )
    features_layout.addWidget(app.controller_hold_aim_cb)

    scroll_layout.addWidget(features_container)

    # Button Mappings Group
    mappings_container = QWidget()
    mappings_layout = QVBoxLayout(mappings_container)
    mappings_layout.setContentsMargins(0, 0, 0, 0)
    mappings_layout.setSpacing(8)

    mappings_layout.addWidget(app.create_group_label("Quick Actions"))

    # Create button mapping grid
    mappings_grid = QGridLayout()
    mappings_grid.setSpacing(12)

    button_actions = [
        (
            "Y Button",
            "y_action",
            [
                "None",
                "Toggle Overlay",
                "Toggle Debug Window",
                "Increase Sensitivity",
                "Decrease Sensitivity",
            ],
        ),
        (
            "X Button",
            "x_action",
            [
                "None",
                "Toggle Overlay",
                "Toggle Debug Window",
                "Toggle Triggerbot",
                "Toggle Flickbot",
            ],
        ),
        (
            "B Button",
            "b_action",
            [
                "None",
                "Emergency Stop",
                "Toggle Movement Curves",
                "Switch Overlay Shape",
            ],
        ),
        (
            "Back + Start",
            "combo_action",
            ["None", "Toggle Aimbot", "Open Menu", "Reset Settings"],
        ),
    ]

    app.button_mapping_combos = {}

    for row, (button_label, action_key, actions) in enumerate(button_actions):
        label = QLabel(f"{button_label}:")
        label.setStyleSheet(
            """
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """
        )
        mappings_grid.addWidget(label, row, 0)

        combo = QComboBox()
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.setStyleSheet(app.get_combo_style())
        combo.setMinimumWidth(200)

        for action in actions:
            combo.addItem(action)

        # Set current value
        current_action = controller_config.get("button_mappings", {}).get(
            action_key,
            "None",
        )
        idx = combo.findText(current_action)
        if idx >= 0:
            combo.setCurrentIndex(idx)

        mappings_grid.addWidget(combo, row, 1)
        app.button_mapping_combos[action_key] = combo

    mappings_layout.addLayout(mappings_grid)
    scroll_layout.addWidget(mappings_container)

    # Controller Test Area
    test_container = QWidget()
    test_layout = QVBoxLayout(test_container)
    test_layout.setContentsMargins(0, 0, 0, 0)
    test_layout.setSpacing(12)

    test_layout.addWidget(app.create_group_label("Controller Test"))

    # Test area widget
    app.controller_test_widget = QWidget()
    app.controller_test_widget.setMinimumHeight(120)
    app.controller_test_widget.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            padding: 12px;
        }
        """
    )

    test_widget_layout = QVBoxLayout(app.controller_test_widget)

    # Input display
    app.controller_input_label = QLabel("Press buttons or move sticks to test")
    app.controller_input_label.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """
    )
    app.controller_input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    test_widget_layout.addWidget(app.controller_input_label)

    # Stick visualization
    app.stick_visual = QLabel(
        "Left Stick: (0.00, 0.00) | Right Stick: (0.00, 0.00)",
    )
    app.stick_visual.setStyleSheet(
        """
        color: #007acc;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """
    )
    app.stick_visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
    test_widget_layout.addWidget(app.stick_visual)

    test_layout.addWidget(app.controller_test_widget)

    # Test vibration button
    app.test_vibration_btn = app.create_action_button(
        "Test Vibration",
        "#4caf50",
        "#45a049",
    )
    app.test_vibration_btn.clicked.connect(app.test_controller_vibration)
    test_layout.addWidget(app.test_vibration_btn)

    scroll_layout.addWidget(test_container)

    # Add some padding at the bottom
    scroll_layout.addSpacing(20)

    # Set the scroll content
    scroll_area.setWidget(scroll_content)

    # Add scroll area to main layout
    layout.addWidget(scroll_area)

    # Start controller test timer
    app.controller_test_timer = QTimer()
    app.controller_test_timer.timeout.connect(app.update_controller_test)
    app.controller_test_timer.start(50)
