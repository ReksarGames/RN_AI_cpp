"""Custom reusable PyQt6 widget classes for the Solana AI GUI."""

from PyQt6.QtWidgets import QSlider, QComboBox, QSpinBox, QDoubleSpinBox


class NoScrollSlider(QSlider):
    """QSlider that ignores mouse wheel events to prevent accidental changes."""

    def wheelEvent(self, event):  # type: ignore[override]
        event.ignore()


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events to prevent accidental changes."""

    def wheelEvent(self, event):  # type: ignore[override]
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events to prevent accidental changes."""

    def wheelEvent(self, event):  # type: ignore[override]
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel events to prevent accidental changes."""

    def wheelEvent(self, event):  # type: ignore[override]
        event.ignore()
