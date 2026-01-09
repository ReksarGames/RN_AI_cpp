"""Models tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
)


def build_models_tab(app, layout):
    """Populate the Models tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Models"))
    layout.addWidget(app.create_section_description("Manage and configure AI models"))

    # Model Selection Group
    model_group = app.create_settings_group()
    model_container = QWidget()
    model_layout = QVBoxLayout(model_container)
    model_layout.setContentsMargins(0, 0, 0, 0)
    model_layout.setSpacing(12)

    model_layout.addWidget(app.create_group_label("Model Selection"))

    # Model dropdown with buttons
    model_select_layout = QHBoxLayout()
    model_select_layout.setSpacing(8)

    app.model_combo = QComboBox()
    app.model_combo.setMinimumWidth(300)
    app.model_combo.setCursor(Qt.CursorShape.PointingHandCursor)
    app.model_combo.setStyleSheet(
        """
        QComboBox {
            background-color: #3e3e3e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            padding: 8px 12px;
            color: #cccccc;
            font-size: 13px;
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
    model_select_layout.addWidget(app.model_combo)

    # Buttons
    app.refresh_models_btn = app.create_small_button("Refresh", "#3e3e3e")
    app.refresh_models_btn.clicked.connect(app.refresh_models)
    model_select_layout.addWidget(app.refresh_models_btn)

    app.browse_model_btn = app.create_small_button("Browse...", "#3e3e3e")
    app.browse_model_btn.clicked.connect(app.browse_for_model)
    model_select_layout.addWidget(app.browse_model_btn)

    app.apply_model_btn = app.create_small_button("Apply", "#007acc")
    app.apply_model_btn.clicked.connect(app.apply_model_change)
    model_select_layout.addWidget(app.apply_model_btn)

    model_layout.addLayout(model_select_layout)

    # Model settings checkboxes
    app.auto_detect_model_cb = app.create_modern_checkbox(
        "Auto-detect best model",
        app.config_manager.get_value("model.auto_detect", True),
    )
    app.auto_detect_model_cb.stateChanged.connect(app.on_auto_detect_changed)
    model_layout.addWidget(app.auto_detect_model_cb)

    app.tensorrt_preference_cb = app.create_modern_checkbox(
        "Prefer TensorRT models (.engine)",
        app.config_manager.get_value("model.use_tensorrt", True),
    )
    app.tensorrt_preference_cb.stateChanged.connect(app.on_tensorrt_changed)
    model_layout.addWidget(app.tensorrt_preference_cb)

    layout.addWidget(model_container)

    # Model Information Group
    info_group = app.create_settings_group()
    info_container = QWidget()
    info_layout = QVBoxLayout(info_container)
    info_layout.setContentsMargins(0, 0, 0, 0)
    info_layout.setSpacing(12)

    info_layout.addWidget(app.create_group_label("Current Model Information"))

    # Model info display
    app.model_info_widget = QWidget()
    app.model_info_widget.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            padding: 12px;
        }
        """
    )
    info_grid = QHBoxLayout(app.model_info_widget)
    info_grid.setSpacing(24)

    # Create info labels
    app.model_path_label = app.create_info_label("Path", "Not loaded")
    app.model_type_label = app.create_info_label("Type", "N/A")
    app.model_size_label = app.create_info_label("Size", "N/A")
    app.model_priority_label = app.create_info_label("Priority", "N/A")

    info_grid.addWidget(app.model_path_label)
    info_grid.addWidget(app.model_type_label)
    info_grid.addWidget(app.model_size_label)
    info_grid.addWidget(app.model_priority_label)
    info_grid.addStretch()

    info_layout.addWidget(app.model_info_widget)
    layout.addWidget(info_container)

    # Model Overrides Group
    overrides_group = app.create_settings_group()
    overrides_container = QWidget()
    overrides_layout = QVBoxLayout(overrides_container)
    overrides_layout.setContentsMargins(0, 0, 0, 0)
    overrides_layout.setSpacing(16)

    overrides_layout.addWidget(app.create_group_label("Model-Specific Overrides"))

    # Confidence override
    conf_layout = QHBoxLayout()
    app.conf_override_cb = app.create_modern_checkbox("Override Confidence")
    conf_layout.addWidget(app.conf_override_cb)

    app.conf_override_slider = app.create_modern_slider(
        conf_layout,
        "",
        30,
        10,
        90,
        "%",
    )
    app.conf_override_slider.setEnabled(False)

    app.conf_override_cb.stateChanged.connect(app.on_conf_override_changed)
    overrides_layout.addLayout(conf_layout)

    # IOU override
    iou_layout = QHBoxLayout()
    app.iou_override_cb = app.create_modern_checkbox("Override IOU")
    iou_layout.addWidget(app.iou_override_cb)

    app.iou_override_slider = app.create_modern_slider(
        iou_layout,
        "",
        10,
        10,
        90,
        "%",
    )
    app.iou_override_slider.setEnabled(False)

    app.iou_override_cb.stateChanged.connect(app.on_iou_override_changed)
    overrides_layout.addLayout(iou_layout)

    layout.addWidget(overrides_container)

    # Models table
    app.models_table = QTableWidget()
    app.models_table.setColumnCount(4)
    app.models_table.setHorizontalHeaderLabels([
        "Name",
        "Type",
        "Size (MB)",
        "Priority",
    ])
    app.models_table.horizontalHeader().setStretchLastSection(True)
    app.models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    app.models_table.itemSelectionChanged.connect(app.on_model_table_selected)
    app.models_table.setMaximumHeight(200)
    app.models_table.setStyleSheet(
        """
        QTableWidget {
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            gridline-color: #3e3e3e;
        }
        QTableWidget::item {
            padding: 8px;
            color: #cccccc;
        }
        QTableWidget::item:selected {
            background-color: #007acc;
        }
        QHeaderView::section {
            background-color: #2d2d2d;
            color: #cccccc;
            padding: 8px;
            border: none;
            border-right: 1px solid #3e3e3e;
            border-bottom: 1px solid #3e3e3e;
        }
        """
    )

    layout.addWidget(app.models_table)

    # Initialize model list and info
    app.refresh_models()
