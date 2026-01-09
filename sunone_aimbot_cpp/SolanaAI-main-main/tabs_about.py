"""About tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel


def build_about_tab(app, layout):
    """Populate the About tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("About"))

    # Logo/Icon area (currently not added to layout, kept for future use)
    icon_widget = QWidget()
    icon_widget.setFixedHeight(80)
    icon_layout = QHBoxLayout(icon_widget)
    icon_layout.setContentsMargins(0, 0, 0, 0)

    icon_label = QLabel("⚡")
    icon_label.setStyleSheet(
        """
        font-size: 48px;
        color: #007acc;
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 16px;
        """
    )
    icon_label.setFixedSize(80, 80)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    icon_layout.addWidget(icon_label)
    icon_layout.addStretch()

    # Info card
    info_card = QWidget()
    info_card.setStyleSheet(
        """
        QWidget {
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 8px;
            padding: 24px;
        }
        """
    )
    info_layout = QVBoxLayout(info_card)

    version_label = QLabel("Solana Ai Version 1.0.0")
    version_label.setStyleSheet(
        """
        color: #858585;
        font-size: 13px;
        margin-bottom: 16px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    info_layout.addWidget(version_label)

    features = [
        "• Real-time configuration updates",
        "• Advanced Smoothing filtering",
        "• Customizable overlay system",
        "• Human-like movement patterns",
        "• GPU-accelerated processing",
    ]

    for feature in features:
        feature_label = QLabel(feature)
        feature_label.setStyleSheet(
            """
            color: #cccccc;
            font-size: 13px;
            padding: 4px 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """
        )
        info_layout.addWidget(feature_label)

    layout.addWidget(info_card)

    # Links
    links_widget = QWidget()
    links_layout = QHBoxLayout(links_widget)
    links_layout.setContentsMargins(0, 16, 0, 0)
    links_layout.setSpacing(24)

    discord_link = QLabel(
        "<a href='https://discord.gg/G7q8qgAMJy' style='color: #007acc; text-decoration: none;'>Discord</a>",
    )
    discord_link.setStyleSheet(
        """
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """
    )
    discord_link.setCursor(Qt.CursorShape.PointingHandCursor)
    discord_link.setOpenExternalLinks(True)
    links_layout.addWidget(discord_link)

    links_layout.addStretch()
    layout.addWidget(links_widget)

    layout.addStretch()
