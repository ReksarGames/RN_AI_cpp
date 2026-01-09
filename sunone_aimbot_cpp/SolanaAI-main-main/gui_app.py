"""PyQt6 GUI components for Solana AI (ConfigApp and helpers)."""

import time
import traceback
import win32api

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from detector import ConfigManager, AimbotController, CONFIG_PATH
from stream_proof import StreamProofManager
from widgets import NoScrollSlider, NoScrollComboBox, NoScrollSpinBox, NoScrollDoubleSpinBox
from icons import IconManager
from hotkeys import start_hotkey_listener
from tabs_general import build_general_tab
from tabs_target import build_target_tab
from tabs_display import build_display_tab
from tabs_performance import build_performance_tab
from tabs_antirecoil import build_antirecoil_tab
from tabs_models import build_models_tab
from tabs_advanced import build_advanced_tab
from tabs_triggerbot import build_triggerbot_tab
from tabs_flickbot import build_flickbot_tab
from tabs_controller import build_controller_tab
from tabs_hotkeys import build_hotkeys_tab
from tabs_about import build_about_tab

class ModelReloadThread(QThread):
    """Thread for reloading the model without blocking UI"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # progress updates
    
    def __init__(self, aimbot_controller, parent=None):
        super().__init__(parent)
        self.aimbot_controller = aimbot_controller
        
    def run(self):
        try:
            self.progress.emit("Stopping aimbot if running...")
            
            # Call the reload_model method which handles everything
            success = self.aimbot_controller.reload_model()
            
            if success:
                model_info = self.aimbot_controller.get_current_model_info()
                self.finished.emit(True, f"Model loaded: {model_info['name']}")
            else:
                self.finished.emit(False, "Failed to reload model")
                
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


import os
from PyQt6.QtCore import Qt, QSize, QEvent, QObject
from PyQt6.QtWidgets import QLabel, QScrollArea, QSlider, QComboBox, QSpinBox, QDoubleSpinBox


class ConfigApp(QMainWindow):
    def __init__(self):

        super().__init__()
        # Initialize icon manager FIRST
        self.icon_manager = IconManager("icons")  # Assumes icons folder in same directory

        self.setWindowTitle("Solana AI")
        self.setGeometry(100, 100, 920, 680)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.config_manager = ConfigManager(CONFIG_PATH)
        self.aimbot_controller = AimbotController(self.config_manager)
        self.config_data = self.config_manager.get_config()
        self.aimbot_controller.config_app_reference = self

        # Set application icon
        app_icon = self.icon_manager.get_icon('app_icon')
        if app_icon:
            self.setWindowIcon(app_icon)

        # Add stream-proof manager
        self.stream_proof = StreamProofManager()

        # Register this window with stream-proof manager
        self.stream_proof.register_qt_window(self)

        # Add this for menu toggle
        self.is_hidden = False

        # Initialize status tracking
        self.stream_proof_enabled = False

        # Hotkey thread lifecycle flag
        self.hotkeys_running = True

        # Start hotkey listener
        self.hotkey_thread = start_hotkey_listener(self)

        # Model reload thread
        self.model_reload_thread = None

        # Main container with electron-style background
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Apply Electron-like styling without transparency issues
        self.central_widget.setStyleSheet("""
            QWidget#central_widget {
                background-color: #1e1e1e;
                border: none;
            }
        """)

        # Add this line right after setting the stylesheet:
        self.central_widget.setObjectName("central_widget")

        # Add drop shadow effect for depth
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_shadow_effect()

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create title bar
        self.create_title_bar(main_layout)

        # Create main content area
        content_container = QWidget()
        content_container.setStyleSheet("border: none;")
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create navigation
        self.create_navigation(content_layout)

        # Create content area
        self.content_area = QWidget()
        self.content_area.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
                border-left: 1px solid #2d2d2d;
            }
        """)
        content_layout.addWidget(self.content_area, 1)

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(32, 24, 32, 24)

        main_layout.addWidget(content_container)

        # Create tab contents
        self.create_tab_contents()
        self.show_tab(0)

        # Setup real-time updates
        self.setup_real_time_updates()

        # Disable scroll on all widgets
        self.disable_scroll_on_all_widgets()

    def setup_shadow_effect(self):
        """Add shadow effect to the main window"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 122, 204, 80))  # Accent color with transparency
        self.central_widget.setGraphicsEffect(shadow)

    def create_title_bar(self, main_layout):
        """Create custom title bar with Electron style"""
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2d2d2d, stop: 1 #252526);
                border: none;
                border-bottom: 2px solid #007acc;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)
        title_layout.setSpacing(8)

        # Window controls (macOS style)
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # Close button
        close_btn = QPushButton()
        close_btn.setFixedSize(12, 12)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5f57;
                border: 1px solid #e0443e;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #ff3b30;
                border: 1px solid #ff1500;
            }
        """)
        close_btn.clicked.connect(self.close_application)

        # Minimize button
        min_btn = QPushButton()
        min_btn.setFixedSize(12, 12)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffbd2e;
                border: 1px solid #dea123;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #ffaa00;
                border: 1px solid #ff9500;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)

        # Maximize button (disabled)
        max_btn = QPushButton()
        max_btn.setFixedSize(12, 12)
        max_btn.setStyleSheet("""
            QPushButton {
                background-color: #28ca42;
                border: 1px solid #1aad2f;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #1fb934;
                border: 1px solid #0fa020;
            }
        """)

        controls_layout.addWidget(close_btn)
        controls_layout.addWidget(min_btn)
        controls_layout.addWidget(max_btn)
        title_layout.addWidget(controls_widget)

        # Title
        title_label = QLabel("Solana AI")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label, 1)

        # Spacer for symmetry
        spacer = QWidget()
        spacer.setFixedWidth(36)
        title_layout.addWidget(spacer)

        main_layout.addWidget(title_bar)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    def create_navigation(self, layout):
        """Create VS Code style navigation sidebar with custom icons"""
        nav = QWidget()
        nav.setFixedWidth(240)
        nav.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
                border-right: 2px solid #3e3e3e;
            }
        """)
    
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        # Navigation header
        header = QLabel("CONFIGURATION")
        header.setStyleSheet("""
            padding: 16px 24px 8px 24px;
            color: #858585;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        nav_layout.addWidget(header)

        # Navigation items with icon keys (using icon keys instead of emojis)
        self.nav_buttons = []
        nav_items = [
            ("General", "general"),
            ("Target", "target"),
            ("Display", "display"),
            ("Performance", "performance"),
            ("Models", "models"),
            ("Advanced", "advanced"),
            ("RCS", "rcs"),
            ("Triggerbot", "triggerbot"),
            ("Flickbot", "flickbot"),
            ("Controller", "controller"),
            ("Hotkeys", "hotkeys"),
            ("About", "about")
        ]

        for i, (name, icon_key) in enumerate(nav_items):
            btn = self.create_nav_button_with_icon(name, icon_key)
            btn.clicked.connect(lambda checked, index=i: self.show_tab(index))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Set first button as active
        self.nav_buttons[0].setProperty("active", True)
        self.nav_buttons[0].style().unpolish(self.nav_buttons[0])
        self.nav_buttons[0].style().polish(self.nav_buttons[0])

        nav_layout.addStretch()

        # Bottom section
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(24, 16, 24, 24)
        bottom_layout.setSpacing(12)

        # Status indicator with custom icon or fallback to dot
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        # Try to use custom icon, fallback to dot if not available
        if hasattr(self, 'icon_manager'):
            status_icon_pixmap = self.icon_manager.get_pixmap('status_ready', (12, 12))
            if status_icon_pixmap:
                self.status_icon = QLabel()
                self.status_icon.setPixmap(status_icon_pixmap)
                self.status_icon.setFixedSize(12, 12)
                status_layout.addWidget(self.status_icon)
            else:
                # Fallback to dot
                self.status_dot = QLabel("●")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                status_layout.addWidget(self.status_dot)
        else:
            # Fallback to dot
            self.status_dot = QLabel("●")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        bottom_layout.addWidget(status_widget)

        # Action buttons with icons
        self.run_button = self.create_action_button_with_icon("Start", "#007acc", "#005a9e", "start")
        self.run_button.clicked.connect(self.toggle_aimbot)
        bottom_layout.addWidget(self.run_button)

        exit_button = self.create_action_button_with_icon("Exit", "#3e3e3e", "#2d2d2d", "exit")
        exit_button.clicked.connect(self.stop_and_exit)
        bottom_layout.addWidget(exit_button)

        nav_layout.addWidget(bottom_section)
        layout.addWidget(nav)

    def create_action_button_with_icon(self, text, bg_color, hover_color, icon_key=None):
        """Create action button with custom icon"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
        # Set icon if provided and icon manager exists
        if icon_key and hasattr(self, 'icon_manager'):
            icon = self.icon_manager.get_icon(icon_key, (16, 16))
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(16, 16))
    
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {bg_color}, stop: 0.5 {bg_color}, stop: 1 {hover_color});
                border: 2px solid {hover_color};
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {hover_color}, stop: 1 {bg_color});
                border: 2px solid #00d4ff;
            }}
            QPushButton:pressed {{
                background: {hover_color};
                border: 2px solid {bg_color};
                padding: 11px 18px 9px 18px;
            }}
        """)
        return btn

    def create_nav_button_with_icon(self, text, icon_key):
        """Create navigation button with custom icon"""
        btn = QPushButton()
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
        # Set icon
        icon = self.icon_manager.get_icon(icon_key, (16, 16))
        if icon:
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
            btn.setText(f"  {text}")  # Add spacing after icon
        else:
            btn.setText(text)  # Fallback to text only
    
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: #cccccc;
                text-align: left;
                padding: 10px 24px;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(42, 45, 46, 0.8);
                border-left: 3px solid #007acc;
                color: #ffffff;
            }
            QPushButton[active="true"] {
                background-color: #37373d;
                color: white;
                border-left: 3px solid #007acc;
            }
        """)
        return btn


    def create_navigation_with_icons(self, layout):
        """Modified navigation creation with custom icons"""
        nav = QWidget()
        nav.setFixedWidth(240)
        nav.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
            }
        """)
    
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
    
        # Navigation header
        header = QLabel("CONFIGURATION")
        header.setStyleSheet("""
            padding: 16px 24px 8px 24px;
            color: #858585;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        nav_layout.addWidget(header)
    
        # Navigation items with icon keys
        self.nav_buttons = []
        nav_items = [
            ("General", "general"),
            ("Target", "target"),
            ("Display", "display"),
            ("Performance", "performance"),
            ("Models", "models"),
            ("Advanced", "advanced"),
            ("RCS", "rcs"),
            ("Triggerbot", "triggerbot"),
            ("Flickbot", "flickbot"),
            ("Controller", "controller"),
            ("Hotkeys", "hotkeys"),
            ("About", "about")
        ]
    
        for i, (name, icon_key) in enumerate(nav_items):
            btn = self.create_nav_button_with_icon(name, icon_key)
            btn.clicked.connect(lambda checked, index=i: self.show_tab(index))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
    
        # Set first button as active
        self.nav_buttons[0].setProperty("active", True)
        self.nav_buttons[0].style().unpolish(self.nav_buttons[0])
        self.nav_buttons[0].style().polish(self.nav_buttons[0])
    
        nav_layout.addStretch()
    
        # Bottom section with status icon
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(24, 16, 24, 24)
        bottom_layout.setSpacing(12)
    
        # Status indicator with custom icon
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
    
        # Use custom status icon instead of dot
        self.status_icon = self.icon_manager.create_icon_label('status_ready', (12, 12))
        status_layout.addWidget(self.status_icon)
    
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
    
        bottom_layout.addWidget(status_widget)
    
        # Action buttons with icons
        self.run_button = self.create_action_button_with_icon("Start", "#007acc", "#005a9e", "start")
        self.run_button.clicked.connect(self.toggle_aimbot)
        bottom_layout.addWidget(self.run_button)
    
        exit_button = self.create_action_button_with_icon("Exit", "#3e3e3e", "#2d2d2d", "exit")
        exit_button.clicked.connect(self.stop_and_exit)
        bottom_layout.addWidget(exit_button)
    
        nav_layout.addWidget(bottom_section)
        layout.addWidget(nav)

    def create_nav_button(self, text, icon):
        """Create navigation button with hover effect"""
        btn = QPushButton(f"{icon}  {text}")
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                text-align: left;
                padding: 10px 24px;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: #2a2d2e;
            }
            QPushButton[active="true"] {
                background-color: #37373d;
                color: white;
                border-left: 2px solid #007acc;
            }
        """)
        return btn

    def create_action_button(self, text, bg_color, hover_color):
        """Create action button with modern styling"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {bg_color}, stop: 0.5 {bg_color}, stop: 1 {hover_color});
                border: 2px solid {hover_color};
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {hover_color}, stop: 1 {bg_color});
                border: 2px solid #00d4ff;
            }}
            QPushButton:pressed {{
                background: {hover_color};
                border: 2px solid {bg_color};
                padding: 11px 18px 9px 18px;
            }}
        """)
        return btn

    def create_tab_contents(self):
        """Create content for each tab"""
        self.tab_contents = []
        
        # Tab 0: General Settings
        general_widget = self.create_section_widget()
        self.create_general_content(general_widget.layout())
        self.tab_contents.append(general_widget)

        # Tab 1: Target Settings (NEW)
        target_widget = self.create_section_widget()
        self.create_target_content(target_widget.layout())
        self.tab_contents.append(target_widget)
        
        # Tab 1: Display Settings
        display_widget = self.create_section_widget()
        self.create_display_content(display_widget.layout())
        self.tab_contents.append(display_widget)
        
        # Tab 2: Performance Settings
        performance_widget = self.create_section_widget()
        self.create_performance_content(performance_widget.layout())
        self.tab_contents.append(performance_widget)

        models_widget = self.create_section_widget()
        self.create_models_content(models_widget.layout())
        self.tab_contents.append(models_widget)
        
        # Tab 3: Advanced Settings
        advanced_widget = self.create_section_widget()
        self.create_advanced_content(advanced_widget.layout())
        self.tab_contents.append(advanced_widget)

        # Tab 5: Anti-Recoil Settings (NEW)
        antirecoil_widget = self.create_section_widget()
        self.create_antirecoil_content(antirecoil_widget.layout())
        self.tab_contents.append(antirecoil_widget)

        # Tab 6: Triggerbot (NEW - Separate)
        triggerbot_widget = self.create_section_widget()
        self.create_triggerbot_content(triggerbot_widget.layout())
        self.tab_contents.append(triggerbot_widget)

        # Tab 7: Flickbot (NEW - Separate)
        flickbot_widget = self.create_section_widget()
        self.create_flickbot_content(flickbot_widget.layout())
        self.tab_contents.append(flickbot_widget)

        # Tab 8: Controller (NEW)
        controller_widget = self.create_section_widget()
        self.create_controller_content(controller_widget.layout())
        self.tab_contents.append(controller_widget)

        hotkeys_widget = self.create_section_widget()
        self.create_hotkeys_content(hotkeys_widget.layout())
        self.tab_contents.append(hotkeys_widget)
        
        # Tab 4: About
        about_widget = self.create_section_widget()
        self.create_about_content(about_widget.layout())
        self.tab_contents.append(about_widget)
        
        # Add all tabs to content layout
        for widget in self.tab_contents:
            widget.setVisible(False)
            self.content_layout.addWidget(widget)

    def create_antirecoil_content(self, layout):
        """Anti-Recoil settings tab with smart activation"""
        build_antirecoil_tab(self, layout)

    def apply_recoil_preset(self, preset):
        """Apply weapon-specific recoil presets"""
        presets = {
            'smg': {
                'strength': 4,
                'bloom': True,
                'description': 'SMG: Low recoil compensation (3-5 strength)'
            },
            'ar': {
                'strength': 7,
                'bloom': True,
                'description': 'Assault Rifle: Medium recoil compensation (5-8 strength)'
            },
            'lmg': {
                'strength': 10,
                'bloom': True,
                'description': 'LMG: High recoil compensation (8-12 strength)'
            },
            'sniper': {
                'strength': 2,
                'bloom': False,
                'description': 'Sniper: Minimal recoil compensation (1-3 strength)'
            }
        }
    
        if preset in presets:
            settings = presets[preset]
        
            # Apply settings to UI
            self.anti_recoil_strength_slider.setValue(settings['strength'])
            self.anti_recoil_bloom_cb.setChecked(settings['bloom'])
        
            # Update description
            self.recoil_preset_desc.setText(settings['description'])
        
            # Enable anti-recoil
            self.anti_recoil_enabled_cb.setChecked(True)
        
            # Visual feedback
            self.status_label.setText(f"Applied {preset.upper()} preset")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def create_target_content(self, layout):
        """Target settings tab - All targeting and locking configurations"""
        build_target_tab(self, layout)

    def create_controller_content(self, layout):
        """Controller settings tab with scroll area"""
        build_controller_tab(self, layout)

    def get_combo_style(self):
        """Get combo box style"""
        return """
            QComboBox {
                background-color: #3e3e3e;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border: 2px solid #007acc;
            }
            QComboBox:focus {
                border: 2px solid #00d4ff;
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
                border: 2px solid #007acc;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
        """

    def refresh_controller_status(self):
        """Refresh controller connection status"""
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                # Disable silent mode when user clicks refresh
                self.aimbot_controller.controller.silent_mode = False
            
                # Show messages if this is the first time
                if not self.aimbot_controller.controller.messages_shown:
                    self.aimbot_controller.controller.show_controller_messages()
            
                # Now check for controller
                if self.aimbot_controller.controller.find_controller():
                    if self.aimbot_controller.controller.physical_controller_connected:
                        controller_type = self.aimbot_controller.controller.controller_type
                        controller_index = self.aimbot_controller.controller.physical_controller_index
                    
                        self.controller_status_label.setText(f"Connected: {controller_type.upper()} Controller (Index: {controller_index})")
                        self.controller_status_label.setStyleSheet("""
                            color: #4caf50;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        """)
                        self.controller_icon.setStyleSheet("font-size: 24px; color: #4caf50;")
                    else:
                        self.controller_status_label.setText("No Controller Connected")
                        self.controller_status_label.setStyleSheet("""
                            color: #858585;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        """)
                        self.controller_icon.setStyleSheet("font-size: 24px; color: #858585;")
                else:
                    self.controller_status_label.setText("No Controller Connected")
                    self.controller_icon.setStyleSheet("font-size: 24px; color: #858585;")
            else:
                self.controller_status_label.setText("Controller System Not Initialized")
                self.controller_icon.setStyleSheet("font-size: 24px; color: #ff9800;")
            
        except Exception as e:
            print(f"[-] Error refreshing controller status: {e}")
            self.controller_status_label.setText("Error detecting controller")

    def test_controller_vibration(self):
        """Test controller vibration"""
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                # Check if physical controller is connected (updated check)
                if self.aimbot_controller.controller.physical_controller_connected:
                    self.aimbot_controller.controller.vibrate(0.5, 0.5, 0.3)
                    self.status_label.setText("Vibration test sent")
                    self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                    QTimer.singleShot(1000, self.reset_status_label)
                else:
                    self.status_label.setText("No controller connected")
                    self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
                    QTimer.singleShot(1000, self.reset_status_label)
            else:
                self.status_label.setText("Controller not initialized")
                self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
                QTimer.singleShot(1000, self.reset_status_label)
        except Exception as e:
            print(f"[-] Vibration test error: {e}")

    def update_controller_test(self):
        """Update controller test display"""
        if not hasattr(self, 'controller_input_label') or not hasattr(self, 'stick_visual'):
            return
    
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                if self.aimbot_controller.controller.physical_controller_connected:
                    # Update stick positions
                    left_x, left_y = self.aimbot_controller.controller.get_stick_input("left")
                    right_x, right_y = self.aimbot_controller.controller.get_stick_input("right")
                
                    self.stick_visual.setText(
                        f"Left Stick: ({left_x:+.2f}, {left_y:+.2f}) | "
                        f"Right Stick: ({right_x:+.2f}, {right_y:+.2f})"
                    )
                
                    # Check buttons
                    buttons_pressed = []
                
                    # Check standard buttons
                    button_checks = [
                        ('A', 'a'),
                        ('B', 'b'),
                        ('X', 'x'),
                        ('Y', 'y'),
                        ('LB', 'lb'),
                        ('RB', 'rb'),
                        ('Back', 'back'),
                        ('Start', 'start'),
                        ('LS', 'ls'),
                        ('RS', 'rs')
                    ]
                
                    for display_name, button_key in button_checks:
                        if self.aimbot_controller.controller.is_button_pressed(button_key):
                            buttons_pressed.append(display_name)
                
                    # Check triggers
                    left_trigger = self.aimbot_controller.controller.get_trigger_input("left")
                    right_trigger = self.aimbot_controller.controller.get_trigger_input("right")
                
                    if left_trigger > 0.1:
                        buttons_pressed.append(f"LT({left_trigger:.1f})")
                    if right_trigger > 0.1:
                        buttons_pressed.append(f"RT({right_trigger:.1f})")
                
                    # Update display
                    if buttons_pressed:
                        self.controller_input_label.setText("Pressed: " + ", ".join(buttons_pressed))
                        self.controller_input_label.setStyleSheet("""
                            color: #007acc;
                            font-size: 12px;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                        """)
                    else:
                        self.controller_input_label.setText("Press buttons or move sticks to test")
                        self.controller_input_label.setStyleSheet("""
                            color: #858585;
                            font-size: 12px;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                        """)
                else:
                    # No controller connected
                    self.controller_input_label.setText("No controller connected")
                    self.stick_visual.setText("Left Stick: (-.---, -.---) | Right Stick: (-.---, -.---)")
                
        except Exception as e:
            # Silently handle errors to avoid spam
            pass

    def create_triggerbot_content(self, layout):
        """Triggerbot settings tab"""
        build_triggerbot_tab(self, layout)

    def create_flickbot_content(self, layout):
        """Flickbot settings tab"""
        build_flickbot_tab(self, layout)

    def create_models_content(self, layout):
        """Models tab"""
        build_models_tab(self, layout)

    def create_small_button(self, text, bg_color):
        """Create small action button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """)
        return btn
    
    def create_info_label(self, title, value):
        """Create information label widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        
        # Store value label for updates
        widget.value_label = value_label
        
        return widget

    def toggle_stream_proof(self):
        """Toggle stream-proof mode"""
        #print("[DEBUG] toggle_stream_proof called")
        
        try:
            # Toggle the stream-proof state
            is_enabled = self.stream_proof.toggle()
            self.stream_proof_enabled = is_enabled
            
            # Update status label
            self.update_stream_proof_status(is_enabled)
            
            # Show notification
            self.status_label.setText(f"Stream-proof {'enabled' if is_enabled else 'disabled'}")
            self.status_dot.setStyleSheet(f"color: {'#4caf50' if is_enabled else '#858585'}; font-size: 10px;")
            
            # Reset status after delay
            QTimer.singleShot(2000, self.reset_status_label)
            
        except Exception as e:
            print(f"[-] Error in toggle_stream_proof: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error in UI
            self.status_label.setText("Stream-proof error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def update_stream_proof_status(self, is_enabled):
        """Update the stream-proof status label"""
        if hasattr(self, 'stream_proof_status'):
            status_text = "Stream-Proof: Enabled" if is_enabled else "Stream-Proof: Disabled"
            self.stream_proof_status.setText(status_text)
            
            # Change color based on status
            if is_enabled:
                self.stream_proof_status.setStyleSheet("""
                    color: #4caf50;
                    font-size: 13px;
                    padding: 8px;
                    background-color: #1e1e1e;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                """)
            else:
                self.stream_proof_status.setStyleSheet("""
                    color: #cccccc;
                    font-size: 13px;
                    padding: 8px;
                    background-color: #1e1e1e;
                    border: 1px solid #3e3e3e;
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                """)

    def reset_status_label(self):
        """Reset the status label to default"""
        if self.aimbot_controller.running:
            self.status_label.setText("Running")
        else:
            self.status_label.setText("Ready")

    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.is_hidden:
            self.show()
            self.raise_()
            self.activateWindow()
            self.is_hidden = False
            #rint("[+] Menu shown")
        else:
            self.hide()
            self.is_hidden = True
            #print("[+] Menu hidden")

    def closeEvent(self, event):
        """Override close event to hide instead of close when using X button"""
        if self.aimbot_controller.running:
            # Just hide the window instead of closing
            self.hide()
            self.is_hidden = True
            event.ignore()
        else:
            # Actually close if aimbot is not running
            event.accept()
    
    def refresh_models(self):
        """Refresh the list of available models"""
        models = self.config_manager.get_available_models()
        current_model = self.config_manager.get_selected_model()
        
        # Update combo box
        self.model_combo.clear()
        self.model_combo.addItem("Auto-detect", "auto")
        
        for model in models:
            self.model_combo.addItem(model["name"], model["path"])
        
        # Select current model
        index = self.model_combo.findData(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # Update models table
        self.models_table.setRowCount(len(models))
        for i, model in enumerate(models):
            self.models_table.setItem(i, 0, QTableWidgetItem(model["name"]))
            self.models_table.setItem(i, 1, QTableWidgetItem(model["type"]))
            self.models_table.setItem(i, 2, QTableWidgetItem(f"{model['size']:.1f}"))
            self.models_table.setItem(i, 3, QTableWidgetItem(str(model["priority"])))
        
        # Update model info
        self.update_model_info()

    def update_model_info(self):
        """Update the model information display"""
        current_path = self.model_combo.currentData()
        
        if current_path and current_path != "auto":
            # Find model info
            models = self.config_manager.get_available_models()
            model_info = next((m for m in models if m["path"] == current_path), None)
            
            if model_info:
                self.model_path_label.value_label.setText(model_info["path"])
                self.model_type_label.value_label.setText(model_info["type"])
                self.model_size_label.value_label.setText(f"{model_info['size']:.1f} MB")
                self.model_priority_label.value_label.setText(str(model_info["priority"]))
            else:
                self.clear_model_info()
        else:
            # Auto mode - show best model
            best_model = self.config_manager.get_best_available_model()
            if best_model:
                models = self.config_manager.get_available_models()
                model_info = next((m for m in models if m["path"] == best_model), None)
                if model_info:
                    self.model_path_label.value_label.setText(f"Auto: {model_info['name']}")
                    self.model_type_label.value_label.setText(model_info["type"])
                    self.model_size_label.value_label.setText(f"{model_info['size']:.1f} MB")
                    self.model_priority_label.value_label.setText(str(model_info["priority"]))
            else:
                self.clear_model_info()

    def clear_model_info(self):
        """Clear model information display"""
        self.model_path_label.value_label.setText("Not loaded")
        self.model_type_label.value_label.setText("N/A")
        self.model_size_label.value_label.setText("N/A")
        self.model_priority_label.value_label.setText("N/A")

    def browse_for_model(self):
        """Browse for a model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            "",
            "Model Files (*.engine *.pt *.onnx);;All Files (*.*)"
        )
        
        if file_path:
            # Add to combo box if not already there
            index = self.model_combo.findData(file_path)
            if index < 0:
                model_name = os.path.basename(file_path)
                self.model_combo.addItem(model_name, file_path)
                index = self.model_combo.count() - 1
            
            self.model_combo.setCurrentIndex(index)
            self.update_model_info()

    def apply_model_change(self):
        """Apply the selected model change"""
        selected_model = self.model_combo.currentData()
    
        if selected_model:
            # Update config first
            success = self.config_manager.set_selected_model(selected_model)
        
            if success:
                # Start model reload in background
                self.status_label.setText("Reloading model...")
                self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
            
                # Disable the apply button during reload
                self.apply_model_btn.setEnabled(False)
            
                self.model_reload_thread = ModelReloadThread(self.aimbot_controller)
                self.model_reload_thread.finished.connect(self.on_model_reload_finished)
                self.model_reload_thread.progress.connect(
                    lambda msg: self.status_label.setText(msg)
                )
                self.model_reload_thread.start()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to change model. Please check if the file exists."
                )

    def on_model_reload_finished(self, success, message):
        """Handle model reload completion"""
        # Re-enable the apply button
        self.apply_model_btn.setEnabled(True)
    
        if success:
            self.status_label.setText("Model loaded")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
        
            # Update model info display
            self.update_model_info()
        
            # Show success notification
            QMessageBox.information(
                self,
                "Success",
                message
            )
        else:
            self.status_label.setText("Error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            QMessageBox.critical(self, "Model Reload Error", message)

    def on_model_table_selected(self):
        """Handle model selection in the table"""
        selected_items = self.models_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            model_name = self.models_table.item(row, 0).text()
            
            # Find and select in combo box
            for i in range(self.model_combo.count()):
                if self.model_combo.itemText(i) == model_name:
                    self.model_combo.setCurrentIndex(i)
                    break

    def on_auto_detect_changed(self, state):
        """Handle auto-detect checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.config_manager.set_value("model.auto_detect", enabled)
        
        if enabled:
            self.model_combo.setCurrentIndex(0)  # Select "Auto-detect"

    def on_tensorrt_changed(self, state):
        """Handle TensorRT preference change"""
        enabled = state == Qt.CheckState.Checked.value
        self.config_manager.set_value("model.use_tensorrt", enabled)
        self.refresh_models()

    def on_conf_override_changed(self, state):
        """Handle confidence override checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.conf_override_slider.setEnabled(enabled)
        
        if enabled:
            value = self.conf_override_slider.value() / 100.0
            self.config_manager.set_model_overrides(confidence=value)
        else:
            self.config_manager.set_model_overrides(confidence=None)

    def on_iou_override_changed(self, state):
        """Handle IOU override checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.iou_override_slider.setEnabled(enabled)
        
        if enabled:
            value = self.iou_override_slider.value() / 100.0
            self.config_manager.set_model_overrides(iou=value)
        else:
            self.config_manager.set_model_overrides(iou=None)

    def create_section_widget(self):
        """Create a styled section widget"""
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        return widget

    def create_section_title(self, text):
        """Create section title with consistent styling"""
        title = QLabel(text)
        title.setStyleSheet("""
            color: #e7e7e7;
            font-size: 24px;
            font-weight: 300;
            margin-bottom: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return title

    def create_section_description(self, text):
        """Create section description"""
        desc = QLabel(text)
        desc.setWordWrap(True)
        desc.setStyleSheet("""
            color: #858585;
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return desc

    def create_general_content(self, layout):
        """General settings tab"""
        build_general_tab(self, layout)

    def create_display_content(self, layout):
        """Display settings tab"""
        build_display_tab(self, layout)

    def create_performance_content(self, layout):
        """Performance settings tab"""
        build_performance_tab(self, layout)

    def create_advanced_content(self, layout):
        """Advanced settings tab with fast movement curves"""
        build_advanced_tab(self, layout)

    def create_preset_button(self, text, color):
        """Create a preset button with custom color"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
        """)
        return btn
    
    def apply_curve_preset(self, preset):
        """Apply a curve speed preset"""
        presets = {
            'aimlock': {
                'humanization': 5,
                'movement_speed': 50,  # 5.0
                'curve_type': 'Exponential',
                'description': 'Aimlock: Fastest with minimal curves (5% humanization)'
            },
            'fast': {
                'humanization': 15,
                'movement_speed': 30,  # 3.0
                'curve_type': 'Bezier',
                'description': 'Fast: Quick response with subtle curves (15% humanization)'
            },
            'medium': {
                'humanization': 30,
                'movement_speed': 20,  # 2.0
                'curve_type': 'Sine',
                'description': 'Medium: Balanced speed and smoothness (30% humanization)'
            },
            'slow': {
                'humanization': 50,
                'movement_speed': 10,  # 1.0
                'curve_type': 'Catmull',
                'description': 'Slow: Smooth human-like movement (50% humanization)'
            }
        }
        
        if preset in presets:
            settings = presets[preset]
            
            # Apply settings to UI
            self.humanizer_slider.setValue(settings['humanization'])
            self.movement_speed_slider.setValue(settings['movement_speed'])
            
            # Find and set curve type
            index = self.movement_curve_combo.findData(settings['curve_type'])
            if index >= 0:
                self.movement_curve_combo.setCurrentIndex(index)
            
            # Update description
            self.preset_desc.setText(settings['description'])
            
            # Enable movement curves
            self.enable_movement_curves_checkbox.setChecked(True)
            
            # Visual feedback
            self.status_label.setText(f"Applied {preset} preset")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def create_about_content(self, layout):
        """About tab"""
        build_about_tab(self, layout)

    def create_settings_group(self):
        """Create a settings group container"""
        group = QVBoxLayout()
        group.setSpacing(16)
        group.setContentsMargins(0, 0, 0, 24)
        return group

    def create_group_label(self, text):
        """Create a group label"""
        label = QLabel(text)
        label.setStyleSheet("""
            color: #cccccc;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return label

    def create_modern_slider(self, layout, label_text, value, min_val, max_val, suffix="", factor=1.0, decimals=1, step=1):
        """Create modern styled slider"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Label row
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        label_row.addWidget(label)
        
        value_label = QLabel(f"{value * factor:.{decimals}f}{suffix}" if factor != 1.0 else f"{value}{suffix}")
        value_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 14px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """)
        label_row.addWidget(value_label)
        
        container_layout.addLayout(label_row)
        
        # Slider
        slider = NoScrollSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setSingleStep(step)
        slider.setPageStep(step * 10)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2a2a2a, stop: 1 #3e3e3e);
                height: 6px;
                border-radius: 3px;
                border: 1px solid #555;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00d4ff, stop: 1 #007acc);
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
                border: 2px solid #005a9e;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1ae0ff, stop: 1 #0086d0);
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border: 2px solid #00a0e0;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #007acc, stop: 1 #00d4ff);
                border-radius: 3px;
                border: 1px solid #005a9e;
            }
        """)
        
        # Snap to step increments when dragging (for step > 1)
        if step > 1:
            # Update label during drag - use integer math to avoid floating point errors
            def update_label(val, s=step, f=factor, d=decimals, suf=suffix):
                snapped = int(round(val / s)) * s
                value_label.setText(f"{snapped * f:.{d}f}{suf}" if f != 1.0 else f"{snapped}{suf}")
            slider.valueChanged.connect(update_label)
            
            # Snap to nearest step when drag is released
            def snap_on_release(s=step):
                current = slider.value()
                snapped = int(round(current / s)) * s
                if snapped != current:
                    slider.setValue(snapped)
            
            slider.sliderReleased.connect(snap_on_release)
        else:
            slider.valueChanged.connect(lambda val: value_label.setText(f"{val * factor:.{decimals}f}{suffix}" if factor != 1.0 else f"{val}{suffix}"))
        
        container_layout.addWidget(slider)
        
        layout.addWidget(container)
        return slider

    def create_modern_checkbox(self, text, checked=False):
        """Create modern styled checkbox"""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
                spacing: 10px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #555;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2a2a2a, stop: 1 #1e1e1e);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00d4ff, stop: 1 #007acc);
                border: 2px solid #00a0e0;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #007acc;
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #00d4ff;
            }
        """)
        return checkbox

    def create_modern_input(self, placeholder, value):
        """Create modern styled input field"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        
        label = QLabel(placeholder)
        label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        input_layout.addWidget(label)
        
        entry = QLineEdit(value)
        entry.setStyleSheet("""
            QLineEdit {
                background-color: #3e3e3e;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            }
            QLineEdit:focus {
                border: 2px solid #00d4ff;
                outline: none;
            }
            QLineEdit:hover {
                border: 2px solid #007acc;
            }
        """)
        input_layout.addWidget(entry)
        
        return input_widget

    def create_keybind_selector(self, layout):
        """Create keybind selector"""
        layout.addWidget(self.create_group_label("Activation Key"))
        
        self.keybind_combo = QComboBox()
        self.keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keybind_combo.setStyleSheet("""
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
        """)
        
        # Keybind options with corresponding icon keys
        keybind_options = [
            ("Left Mouse Button", 0x01, "mouse_left"),     # Add mouse_left.png to icons folder
            ("Right Mouse Button", 0x02, "mouse_right"),   # Add mouse_right.png to icons folder
            ("Middle Mouse Button", 0x04, "mouse_scroll"), # Add mouse_middle.png to icons folder
            ("Mouse Button 4", 0x05, "mouse_4"),          # Add mouse_4.png to icons folder
            ("Mouse Button 5", 0x06, "mouse_5"),          # Add mouse_5.png to icons folder
            ("Left Shift", 0xA0, "left_shift"),             # Uses keyboard.png (hotkeys icon)
            ("Tab", 0x09, "tab_key"),                     # Uses keyboard.png (hotkeys icon)
            ("Left Control", 0xA2, "left_ctrl"),           # Uses keyboard.png (hotkeys icon)
            ("Left Alt", 0xA4, "left_alt"),               # Uses keyboard.png (hotkeys icon)
        ]
        
        # Add items with icons
        for label, hex_value, icon_key in keybind_options:
            icon = self.icon_manager.get_icon(icon_key, size=(16, 16))
            if icon:
                self.keybind_combo.addItem(icon, label, hex_value)
            else:
                # Fallback: add without icon if icon not found
                self.keybind_combo.addItem(label, hex_value)
        
        try:
            if isinstance(self.config_data["keybind"], str):
                initial_value = int(self.config_data["keybind"], 16)
            else:
                initial_value = self.config_data["keybind"]
            
            index = self.keybind_combo.findData(initial_value)
            if index >= 0:
                self.keybind_combo.setCurrentIndex(index)
        except (ValueError, KeyError):
            self.keybind_combo.setCurrentIndex(0)
        
        layout.addWidget(self.keybind_combo)

    def create_shape_selector(self, layout):
        """Create overlay shape selector"""
        layout.addWidget(self.create_group_label("Overlay Shape"))
        
        self.overlay_shape_combo = QComboBox()
        self.overlay_shape_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.overlay_shape_combo.setStyleSheet("""
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
        """)
        
        overlay_shape_options = [
            ("Circle", "circle"),
            ("Square", "square"),
        ]
        
        for label, value in overlay_shape_options:
            self.overlay_shape_combo.addItem(label, value)
        
        current_shape = self.config_data.get("overlay_shape", "circle")
        index = self.overlay_shape_combo.findData(current_shape)
        if index >= 0:
            self.overlay_shape_combo.setCurrentIndex(index)
        
        layout.addWidget(self.overlay_shape_combo)

    def create_curve_selector(self, layout, current_curve):
        """Create curve type selector"""
        #layout.addWidget(self.create_group_label("Curve Algorithm"))
        
        self.movement_curve_combo = QComboBox()
        self.movement_curve_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movement_curve_combo.setStyleSheet("""
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
        """)
        
        curve_options = [
            ("Bezier Curve", "Bezier"),
            ("B-Spline", "B-Spline"),
            ("Catmull-Rom", "Catmull"),
            ("Exponential", "Exponential"),
            ("Hermite", "Hermite"),
            ("Sinusoidal", "Sine")
        ]
        
        for label, value in curve_options:
            self.movement_curve_combo.addItem(label, value)
        
        index = self.movement_curve_combo.findData(current_curve)
        if index >= 0:
            self.movement_curve_combo.setCurrentIndex(index)
        
        layout.addWidget(self.movement_curve_combo)

    def create_hotkeys_content(self, layout):
        """Hotkeys settings tab"""
        build_hotkeys_tab(self, layout)

    def create_keybind_combo(self, label_text, current_value):
        """Create a keybind selector combo box with label"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
    
        label = QLabel(label_text)
        label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        container_layout.addWidget(label)
    
        combo = QComboBox()
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.setStyleSheet("""
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
        """)
    
        # Add common keybind options
        keybind_options = [
            ("F1", 0x70),
            ("F2", 0x71),
            ("F3", 0x72),
            ("F4", 0x73),
            ("F5", 0x74),
            ("F6", 0x75),
            ("F7", 0x76),
            ("F8", 0x77),
            ("F9", 0x78),
            ("F10", 0x79),
            ("F11", 0x7A),
            ("F12", 0x7B),
            ("Insert", 0x2D),
            ("Delete", 0x2E),
            ("Home", 0x24),
            ("End", 0x23),
            ("Page Up", 0x21),
            ("Page Down", 0x22),
        ]
    
        for label, hex_value in keybind_options:
            combo.addItem(label, hex_value)
    
        # Set current value
        try:
            if isinstance(current_value, str):
                initial_value = int(current_value, 16)
            else:
                initial_value = current_value
        
            index = combo.findData(initial_value)
            if index >= 0:
                combo.setCurrentIndex(index)
        except:
            combo.setCurrentIndex(5)  # Default to F6
    
        container_layout.addWidget(combo)
        return container

    def show_tab(self, index):
        """Show selected tab with animation"""
        # Update navigation
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Hide all tabs
        for widget in self.tab_contents:
            widget.setVisible(False)
        
        # Show selected tab
        if 0 <= index < len(self.tab_contents):
            self.tab_contents[index].setVisible(True)
            
        # If showing hotkeys tab, update stream-proof status
        if index == 5:  # Hotkeys tab index
            self.update_stream_proof_status(self.stream_proof_enabled)

    def setup_real_time_updates(self):
        """Set up real-time updates for all controls"""
        # Connect all controls to real-time update
        # General settings
        self.fov_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.sens_slider.valueChanged.connect(self.apply_settings_real_time)
        self.aim_height_slider.valueChanged.connect(self.apply_settings_real_time)
        self.confidence_slider.valueChanged.connect(self.apply_settings_real_time)
        self.keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)

        # Display settings
        self.show_overlay_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.overlay_shape_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.overlay_show_borders_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.circle_capture_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.show_debug_window_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.custom_res_checkbox.stateChanged.connect(self.apply_settings_real_time)

        # Performance settings
        self.use_kalman_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.kf_p_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kf_r_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kf_q_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kalman_frames_slider.valueChanged.connect(self.apply_settings_real_time)
        self.use_coupled_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.alpha_with_kalman_slider.valueChanged.connect(self.apply_settings_real_time)

        # Advanced settings
        self.enable_movement_curves_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.movement_curve_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.movement_speed_slider.valueChanged.connect(self.apply_settings_real_time)
        self.humanizer_slider.valueChanged.connect(self.apply_settings_real_time)
        self.random_curves_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.curve_smoothing_checkbox.stateChanged.connect(self.apply_settings_real_time)

        # Anti-recoil connections
        self.require_target_cb.stateChanged.connect(self.apply_settings_real_time)
        self.require_keybind_cb.stateChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_strength_slider.valueChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_bloom_cb.stateChanged.connect(self.apply_settings_real_time)

        # Triggerbot settings
        self.triggerbot_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.triggerbot_confidence_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_delay_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)

        # Flickbot settings
        self.flickbot_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.flickbot_keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.flickbot_speed_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_delay_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_autofire_cb.stateChanged.connect(self.apply_settings_real_time)
        self.flickbot_return_cb.stateChanged.connect(self.apply_settings_real_time)

        # Text field updates with delay
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.apply_settings_real_time)

        # Mouse FOV settings (NEW)
        self.use_separate_fov_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.mouse_fov_width_slider.valueChanged.connect(self.apply_settings_real_time)
        self.mouse_fov_height_slider.valueChanged.connect(self.apply_settings_real_time)
        self.dpi_slider.valueChanged.connect(self.apply_settings_real_time)
    
        # Enable/disable height slider based on checkbox
        self.use_separate_fov_checkbox.stateChanged.connect(
            lambda state: self.mouse_fov_height_slider.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        # Target lock settings
        if hasattr(self, 'target_lock_enabled_cb'):
            self.target_lock_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
            self.min_lock_slider.valueChanged.connect(self.apply_settings_real_time)
            self.max_lock_slider.valueChanged.connect(self.apply_settings_real_time)
            self.distance_threshold_slider.valueChanged.connect(self.apply_settings_real_time)
            self.reacquire_timeout_slider.valueChanged.connect(self.apply_settings_real_time)
            self.smart_switching_cb.stateChanged.connect(self.apply_settings_real_time)
            self.target_preference_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.multi_target_cb.stateChanged.connect(self.apply_settings_real_time)
            self.max_targets_slider.valueChanged.connect(self.apply_settings_real_time)
            self.switch_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        
        # Advanced options
        if hasattr(self, 'sticky_aim_cb'):
            self.sticky_aim_cb.stateChanged.connect(self.apply_settings_real_time)
            self.target_prediction_cb.stateChanged.connect(self.apply_settings_real_time)
            self.ignore_downed_cb.stateChanged.connect(self.apply_settings_real_time)

        # Controller settings
        if hasattr(self, 'controller_enabled_cb'):
            self.controller_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_activation_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.aim_stick_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.controller_sens_slider.valueChanged.connect(self.apply_settings_real_time)
            self.controller_deadzone_slider.valueChanged.connect(self.apply_settings_real_time)
            self.trigger_threshold_slider.valueChanged.connect(self.apply_settings_real_time)
            self.controller_vibration_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_autoswitch_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_hold_aim_cb.stateChanged.connect(self.apply_settings_real_time)
    
            # Button mappings
            for combo in self.button_mapping_combos.values():
                combo.currentIndexChanged.connect(self.apply_settings_real_time)

        if hasattr(self, 'stream_proof_keybind_combo'):
            self.stream_proof_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        if hasattr(self, 'menu_toggle_keybind_combo'):
            self.menu_toggle_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)

        if hasattr(self, 'stream_proof_keybind_combo'):
            self.stream_proof_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        if hasattr(self, 'menu_toggle_keybind_combo'):
            self.menu_toggle_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        
        # Connect text fields to delayed update
        for entry in [self.res_x_entry, self.res_y_entry]:
            entry.findChild(QLineEdit).textChanged.connect(self.schedule_real_time_update)

    def schedule_real_time_update(self):
        """Schedule a real-time update with delay"""
        self.update_timer.stop()
        self.update_timer.start(500)

    def apply_settings_real_time(self):
        """Apply settings in real-time with optimized curve settings"""
        try:
            # Get resolution values
            res_x_val = int(self.res_x_entry.findChild(QLineEdit).text())
            res_y_val = int(self.res_y_entry.findChild(QLineEdit).text())

            # Calculate humanizer settings for FAST curves
            humanizer_value = self.humanizer_slider.value()
            smoothing_factor = humanizer_value / 100.0
            
            # Optimized values for speed
            curve_steps = min(5, max(3, int(5 + (humanizer_value * 0.1))))  # 3-5 steps max
            bezier_randomness = 0.05 + (humanizer_value * 0.001)  # Minimal randomness
            
            confidence_snapped = round(self.confidence_slider.value() / 10.0) * 10
            
            new_config = {
                "fov": self.fov_combo.currentData(),
                "sensitivity": round(self.sens_slider.value() * 0.1, 1),
                "aim_height": self.aim_height_slider.value(),
                "confidence": round(confidence_snapped * 0.001, 2),
                "keybind": hex(self.keybind_combo.currentData()),
                "custom_resolution": {
                    "use_custom_resolution": self.custom_res_checkbox.isChecked(),
                    "x": res_x_val,
                    "y": res_y_val
                },
                "show_overlay": self.show_overlay_checkbox.isChecked(),
                "overlay_shape": self.overlay_shape_combo.currentData(),
                "overlay_show_borders": self.overlay_show_borders_checkbox.isChecked(),
                "circle_capture": self.circle_capture_checkbox.isChecked(),
                "show_debug_window": self.show_debug_window_checkbox.isChecked(),
                "kalman": {
                    "use_kalman": self.use_kalman_checkbox.isChecked(),
                    "kf_p": round(self.kf_p_slider.value() * 0.01, 2),
                    "kf_r": round(self.kf_r_slider.value() * 0.01, 2),
                    "kf_q": round(self.kf_q_slider.value() * 0.01, 2),
                    "kalman_frames_to_predict": round(self.kalman_frames_slider.value() * 0.1, 1),
                    "use_coupled_xy": self.use_coupled_checkbox.isChecked(),
                    "alpha_with_kalman": round(self.alpha_with_kalman_slider.value() * 0.01, 2),
                },
                "movement": {
                    "use_curves": self.enable_movement_curves_checkbox.isChecked(),
                    "curve_type": self.movement_curve_combo.currentData(),
                    "movement_speed": round(self.movement_speed_slider.value() * 0.1, 1),
                    "smoothing_enabled": self.curve_smoothing_checkbox.isChecked(),
                    "smoothing_factor": round(smoothing_factor, 3),
                    "random_curves": self.random_curves_checkbox.isChecked(),
                    "curve_steps": curve_steps,  # Very few steps for speed
                    "bezier_control_randomness": round(bezier_randomness, 3),
                    "spline_smoothness": 0.1 + (humanizer_value * 0.002),  # Minimal smoothness
                    "catmull_tension": 0.1 + (humanizer_value * 0.003),  # Low tension
                    "exponential_decay": 2.0 + (humanizer_value * 0.02),  # Fast decay
                    "hermite_tangent_scale": 0.3 + (humanizer_value * 0.003),  # Small tangents
                    "sine_frequency": 1.5 + (humanizer_value * 0.01),  # Quick oscillation
                    "aimlock_mode": humanizer_value <= 20  # Enable aimlock mode for low humanization
                },
                "anti_recoil": {
                    "enabled": self.anti_recoil_enabled_cb.isChecked(),
                    "strength": float(self.anti_recoil_strength_slider.value()),
                    "reduce_bloom": self.anti_recoil_bloom_cb.isChecked(),
                    "require_target": self.require_target_cb.isChecked(),
                    "require_keybind": self.require_keybind_cb.isChecked()
                },
                "triggerbot": {
                    "enabled": self.triggerbot_enabled_cb.isChecked(),
                    "confidence": round(self.triggerbot_confidence_slider.value() * 0.01, 2),
                    "fire_delay": round(self.triggerbot_delay_slider.value() * 0.001, 3),
                    "cooldown": round(self.triggerbot_cooldown_slider.value() * 0.001, 3),
                    "keybind": self.triggerbot_keybind_combo.currentData(),
                    "rapid_fire": self.triggerbot_rapidfire_cb.isChecked(),
                    "shots_per_burst": self.triggerbot_burst_slider.value()
                },
                "flickbot": {
                    "enabled": self.flickbot_enabled_cb.isChecked(),
                    "keybind": self.flickbot_keybind_combo.currentData(),
                    "flick_speed": round(self.flickbot_speed_slider.value() * 0.01, 2),
                    "flick_delay": round(self.flickbot_delay_slider.value() * 0.001, 3),
                    "cooldown": round(self.flickbot_cooldown_slider.value() * 0.001, 3),
                    "auto_fire": self.flickbot_autofire_cb.isChecked(),
                    "return_to_origin": self.flickbot_return_cb.isChecked(),
                    "smooth_flick": self.flickbot_smooth_cb.isChecked()
                },
                "mouse_fov": {  # NEW
                    "mouse_fov_width": self.mouse_fov_width_slider.value(),
                    "mouse_fov_height": self.mouse_fov_height_slider.value(),
                    "use_separate_fov": self.use_separate_fov_checkbox.isChecked()
                },
                "dpi": self.dpi_slider.value(),  # NEW
            }

            if hasattr(self, 'menu_toggle_keybind_combo'):
                new_config["hotkeys"] = {
                    "stream_proof_key": hex(self.stream_proof_keybind_combo.findChild(QComboBox).currentData()),
                    "menu_toggle_key": hex(self.menu_toggle_keybind_combo.findChild(QComboBox).currentData()),
                    "stream_proof_enabled": False,
                    "menu_visible": True
                }

            # Controller settings
            if hasattr(self, 'controller_enabled_cb'):
                button_mappings = {}
                for action_key, combo in self.button_mapping_combos.items():
                    button_mappings[action_key] = combo.currentText()
    
                new_config["controller"] = {
                    "enabled": self.controller_enabled_cb.isChecked(),
                    "sensitivity": round(self.controller_sens_slider.value() * 0.1, 1),
                    "deadzone": self.controller_deadzone_slider.value() / 100.0,
                    "vibration": self.controller_vibration_cb.isChecked(),
                    "trigger_threshold": self.trigger_threshold_slider.value() / 100.0,
                    "aim_stick": self.aim_stick_combo.currentData(),
                    "activation_button": self.controller_activation_combo.currentData(),
                    "auto_switch": self.controller_autoswitch_cb.isChecked(),
                    "hold_to_aim": self.controller_hold_aim_cb.isChecked(),
                    "button_mappings": button_mappings
                }

            # Target lock configuration
            if hasattr(self, 'target_lock_enabled_cb'):
                new_config["target_lock"] = {
                    "enabled": self.target_lock_enabled_cb.isChecked(),
                    "min_lock_duration": round(self.min_lock_slider.value() * 0.001, 3),
                    "max_lock_duration": round(self.max_lock_slider.value() * 0.001, 3),
                    "distance_threshold": self.distance_threshold_slider.value(),
                    "reacquire_timeout": round(self.reacquire_timeout_slider.value() * 0.001, 3),
                    "smart_switching": self.smart_switching_cb.isChecked(),
                    "preference": self.target_preference_combo.currentData(),
                    "multi_target": self.multi_target_cb.isChecked(),
                    "max_targets": self.max_targets_slider.value(),
                    "sticky_aim": self.sticky_aim_cb.isChecked(),
                    "prediction": self.target_prediction_cb.isChecked(),
                    "ignore_downed": self.ignore_downed_cb.isChecked(),
                    "switch_cooldown": round(self.switch_cooldown_slider.value() * 0.001, 3),
                }
            
            # Update config
            if self.config_manager.update_config(new_config):
                self.status_label.setText("Settings applied")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
            else:
                self.status_label.setText("Failed to apply")
                self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
                
        except ValueError:
            self.status_label.setText("Invalid input")
            self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
        except Exception as e:
            self.status_label.setText("Error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            print(f"[-] Error: {e}")

    def toggle_aimbot(self):
        """Toggle aimbot on/off"""
        if self.aimbot_controller.running:
            self.aimbot_controller.stop()
            self.run_button.setText("Start")
            self.status_label.setText("Stopped")
            self.status_dot.setStyleSheet("color: #858585; font-size: 10px;")
        else:
            if self.aimbot_controller.start():
                self.run_button.setText("Stop")
                self.status_label.setText("Running")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")

    @pyqtSlot()
    def toggle_aimbot_pause(self):
        """Toggle global aimbot pause/unpause (used by F3 hotkey)."""
        # Only meaningful when aimbot is running
        if not self.aimbot_controller.running:
            return

        self.aimbot_controller.toggle_pause()

        if self.aimbot_controller.paused:
            self.status_label.setText("Paused")
            self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
        else:
            self.status_label.setText("Running")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")

    @pyqtSlot()
    def apply_visual_config_from_backend(self):
        """Apply overlay/debug visual changes requested by backend.

        This is invoked via QMetaObject.invokeMethod from AimbotController
        so that heavy visual reconfiguration happens on the Qt main thread.
        """
        try:
            import threading as _threading
            thread_name = _threading.current_thread().name
            print(f"[VISUAL] apply_visual_config_from_backend on thread={thread_name}")
        except Exception:
            pass

        if hasattr(self, "aimbot_controller") and self.aimbot_controller:
            try:
                self.aimbot_controller.apply_visual_config_changes()
            except Exception as e:
                print(f"[-] Error applying visual config from backend: {e}")

    def stop_and_exit(self):
        """Stop and exit application"""
        if self.aimbot_controller.running:
            self.aimbot_controller.stop()
        self.close_application()

    def emergency_stop(self):
        """Emergency stop"""
        self.status_label.setText("Emergency stop")
        self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
        
        if self.aimbot_controller.running:
            self.aimbot_controller.force_stop()
        
        self.run_button.setText("Start")
        
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
        QTimer.singleShot(2000, lambda: self.status_dot.setStyleSheet("color: #858585; font-size: 10px;"))

    def close_application(self):
        """Close application"""
        # Signal hotkey listener thread to exit cleanly
        self.hotkeys_running = False
        if self.aimbot_controller.running:
            self.aimbot_controller.force_stop()
        self.close()
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only start dragging if click is in title bar area (top 36 pixels)
            if event.position().y() <= 36:
                self.drag_pos = event.globalPosition().toPoint()
                self.is_dragging = True
            else:
                self.is_dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'is_dragging') and self.is_dragging:
                if hasattr(self, 'drag_pos'):
                    self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
                    self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def disable_scroll_on_all_widgets(self):
        """Disable scroll on all interactive widgets"""
        # Disable on all sliders
        for slider in self.findChildren(QSlider):
            slider.wheelEvent = lambda event: event.ignore()
    
        # Disable on all combo boxes
        for combo in self.findChildren(QComboBox):
            combo.wheelEvent = lambda event: event.ignore()
    
        # Disable on any spin boxes if you have them
        for spinbox in self.findChildren(QSpinBox):
            spinbox.wheelEvent = lambda event: event.ignore()

