"""Target tab builder for the Solana AI PyQt6 GUI.

This mirrors ConfigApp.create_target_content but lives in a separate
module to keep gui_app.py smaller.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea

from widgets import NoScrollComboBox


def build_target_tab(app, layout):
    """Populate the Target tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Target"))
    layout.addWidget(
        app.create_section_description(
            "Configure target detection, selection, and locking behavior",
        )
    )

    # Scroll area wrapper
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

    scroll_content = QWidget()
    scroll_content.setStyleSheet("background-color: transparent;")
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setContentsMargins(0, 0, 12, 0)
    scroll_layout.setSpacing(24)

    target_lock_config = app.config_data.get(
        "target_lock",
        {
            "enabled": True,
            "min_lock_duration": 0.5,
            "max_lock_duration": 3.0,
            "distance_threshold": 100,
            "reacquire_timeout": 0.3,
            "smart_switching": True,
            "preference": "closest",
        },
    )

    # ============= TARGET LOCKING =============
    lock_group = app.create_settings_group()
    lock_container = QWidget()
    lock_layout = QVBoxLayout(lock_container)
    lock_layout.setContentsMargins(0, 0, 0, 0)
    lock_layout.setSpacing(16)

    lock_layout.addWidget(app.create_group_label("Target Locking"))

    app.target_lock_enabled_cb = app.create_modern_checkbox(
        "Enable Target Locking",
        target_lock_config.get("enabled", True),
    )
    lock_layout.addWidget(app.target_lock_enabled_cb)

    lock_desc = QLabel(
        "Prevents rapid target switching by locking onto one target "
        "until eliminated or lost"
    )
    lock_desc.setStyleSheet(
        """
        color: #858585;
        font-size: 12px;
        margin-top: 4px;
        margin-left: 26px;
        margin-bottom: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    lock_desc.setWordWrap(True)
    lock_layout.addWidget(lock_desc)

    min_lock = int(target_lock_config.get("min_lock_duration", 0.5) * 1000)
    app.min_lock_slider = app.create_modern_slider(
        lock_layout,
        "Minimum Lock Duration",
        min_lock,
        100,
        2000,
        "ms",
        0.001,
    )

    max_lock = int(target_lock_config.get("max_lock_duration", 3.0) * 1000)
    app.max_lock_slider = app.create_modern_slider(
        lock_layout,
        "Maximum Lock Duration",
        max_lock,
        1000,
        8000,
        "ms",
        0.001,
    )

    distance_threshold = int(target_lock_config.get("distance_threshold", 100))
    app.distance_threshold_slider = app.create_modern_slider(
        lock_layout,
        "Lock Break Distance",
        distance_threshold,
        50,
        300,
        "px",
    )

    reacquire_timeout = int(target_lock_config.get("reacquire_timeout", 0.3) * 1000)
    app.reacquire_timeout_slider = app.create_modern_slider(
        lock_layout,
        "Target Lost Timeout",
        reacquire_timeout,
        100,
        8000,
        "ms",
        0.001,
    )

    scroll_layout.addWidget(lock_container)

    # ============= TARGET SELECTION =============
    selection_group = app.create_settings_group()
    selection_container = QWidget()
    selection_layout = QVBoxLayout(selection_container)
    selection_layout.setContentsMargins(0, 0, 0, 0)
    selection_layout.setSpacing(16)

    selection_layout.addWidget(app.create_group_label("Target Selection"))

    app.smart_switching_cb = app.create_modern_checkbox(
        "Smart Target Switching (Prioritize threats)",
        target_lock_config.get("smart_switching", True),
    )
    selection_layout.addWidget(app.smart_switching_cb)

    preference_label = QLabel("Target Priority:")
    preference_label.setStyleSheet(
        """
        color: #cccccc;
        font-size: 13px;
        margin-top: 12px;
        margin-bottom: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    selection_layout.addWidget(preference_label)

    app.target_preference_combo = NoScrollComboBox()
    app.target_preference_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.target_preference_combo.setStyleSheet(
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

    preference_options = [
        ("Closest Target", "closest"),
        ("Most Centered", "centered"),
        ("Largest Target", "largest"),
        ("Highest Confidence", "confidence"),
        ("Lowest Health (if visible)", "health"),
    ]
    for label, value in preference_options:
        app.target_preference_combo.addItem(label, value)

    current_preference = target_lock_config.get("preference", "closest")
    idx = app.target_preference_combo.findData(current_preference)
    if idx >= 0:
        app.target_preference_combo.setCurrentIndex(idx)

    selection_layout.addWidget(app.target_preference_combo)

    app.multi_target_cb = app.create_modern_checkbox(
        "Multi-Target Mode (Track multiple targets)",
        target_lock_config.get("multi_target", False),
    )
    selection_layout.addWidget(app.multi_target_cb)

    app.max_targets_slider = app.create_modern_slider(
        selection_layout,
        "Maximum Simultaneous Targets",
        target_lock_config.get("max_targets", 1),
        1,
        5,
        " targets",
    )
    app.max_targets_slider.setEnabled(app.multi_target_cb.isChecked())

    app.multi_target_cb.stateChanged.connect(
        lambda state: app.max_targets_slider.setEnabled(
            state == Qt.CheckState.Checked.value
        )
    )

    scroll_layout.addWidget(selection_container)

    # ============= ADVANCED OPTIONS =============
    advanced_group = app.create_settings_group()
    advanced_container = QWidget()
    advanced_layout = QVBoxLayout(advanced_container)
    advanced_layout.setContentsMargins(0, 0, 0, 0)
    advanced_layout.setSpacing(12)

    advanced_layout.addWidget(app.create_group_label("Advanced Options"))

    app.sticky_aim_cb = app.create_modern_checkbox(
        "Sticky Aim (Slow down when near target)",
        target_lock_config.get("sticky_aim", False),
    )
    advanced_layout.addWidget(app.sticky_aim_cb)

    app.target_prediction_cb = app.create_modern_checkbox(
        "Enable Target Movement Prediction",
        target_lock_config.get("prediction", True),
    )
    advanced_layout.addWidget(app.target_prediction_cb)

    app.ignore_downed_cb = app.create_modern_checkbox(
        "Ignore Downed/Eliminated Targets",
        target_lock_config.get("ignore_downed", True),
    )
    advanced_layout.addWidget(app.ignore_downed_cb)

    switch_cooldown = int(target_lock_config.get("switch_cooldown", 0.2) * 1000)
    app.switch_cooldown_slider = app.create_modern_slider(
        advanced_layout,
        "Target Switch Cooldown",
        switch_cooldown,
        0,
        8000,
        "ms",
        0.001,
    )

    scroll_layout.addWidget(advanced_container)
    scroll_layout.addSpacing(20)

    scroll_area.setWidget(scroll_content)
    layout.addWidget(scroll_area)
