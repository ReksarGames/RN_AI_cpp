"""Icon management helpers for the Solana AI PyQt6 GUI."""

import os

from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QLabel


class IconManager:
    """Manages custom icons for the GUI.

    This is extracted from gui_app.ConfigApp so it can be reused by other
    GUI components without pulling in the full window implementation.
    """

    def __init__(self, icon_path: str = "icons") -> None:
        """Initialize the icon manager.

        Args:
            icon_path: Directory containing icon image files.
        """
        self.icon_path = icon_path
        self.icons: dict[str, QPixmap] = {}
        self.load_icons()

    def load_icons(self) -> None:
        """Load all known icons from the icons folder."""
        icon_files = {
            # Navigation icons
            "general": "general.png",
            "target": "target1.png",
            "display": "monitor.png",
            "performance": "chart.png",
            "models": "robot.png",
            "advanced": "settings.png",
            "rcs": "target.png",
            "triggerbot": "gun.png",
            "flickbot": "explosion.png",
            "controller": "gamepad.png",
            "hotkeys": "keyboard.png",
            "about": "info.png",

            # Keybind icons
            "mouse_left": "mouse_left.png",
            "mouse_right": "mouse_right.png",
            "mouse_4": "mouse_4.png",
            "mouse_5": "mouse_5.png",
            "mouse_scroll": "mouse_scroll.png",
            "left_shift": "left_shift.png",
            "tab_key": "tab_key.png",
            "left_ctrl": "left_ctrl.png",
            "left_alt": "left_alt.png",
        }

        for key, filename in icon_files.items():
            filepath = os.path.join(self.icon_path, filename)
            if os.path.exists(filepath):
                self.icons[key] = QPixmap(filepath)
            else:
                # Keep behaviour identical to original: warn but continue.
                print(f"Warning: Icon not found: {filepath}")

    def get_icon(self, key: str, size: QSize | tuple[int, int] | None = None) -> QIcon | None:
        """Return a QIcon for the given logical key, optionally scaled."""
        pixmap = self.get_pixmap(key, size)
        if pixmap is None:
            return None
        return QIcon(pixmap)

    def get_pixmap(self, key: str, size: QSize | tuple[int, int] | None = None) -> QPixmap | None:
        """Return a QPixmap for the given logical key, optionally scaled."""
        if key not in self.icons:
            return None

        pixmap = self.icons[key]
        if size:
            if isinstance(size, tuple):
                w, h = size
                pixmap = pixmap.scaled(
                    w,
                    h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            else:
                pixmap = pixmap.scaled(
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        return pixmap

    def create_icon_label(self, key: str, size: tuple[int, int] = (16, 16)) -> QLabel:
        """Create a QLabel showing the icon for *key* (or empty if missing)."""
        label = QLabel()
        pixmap = self.get_pixmap(key, size)
        if pixmap is not None:
            label.setPixmap(pixmap)
        label.setFixedSize(size[0], size[1])
        return label
