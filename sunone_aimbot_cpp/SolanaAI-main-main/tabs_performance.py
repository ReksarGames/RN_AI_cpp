"""Performance tab builder for the Solana AI PyQt6 GUI."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout


def build_performance_tab(app, layout):
    """Populate the Performance tab into *layout* for the given ConfigApp *app*."""
    layout.addWidget(app.create_section_title("Performance"))
    layout.addWidget(
        app.create_section_description("Fine-tune smoothing and prediction algorithms")
    )

    kalman_config = app.config_data.get(
        "kalman",
        {
            "use_kalman": True,
            "kf_p": 20.0,
            "kf_r": 1.5,
            "kf_q": 15.0,
            "kalman_frames_to_predict": 0.5,
            "alpha_with_kalman": 1.5,
        },
    )

    kalman_group = app.create_settings_group()
    kalman_container = QWidget()
    kalman_layout = QVBoxLayout(kalman_container)
    kalman_layout.setContentsMargins(0, 0, 0, 0)
    kalman_layout.setSpacing(20)

    kalman_layout.addWidget(app.create_group_label("Smoothing Filter"))

    app.use_kalman_checkbox = app.create_modern_checkbox(
        "Enable Smoothing", kalman_config.get("use_kalman", True)
    )
    kalman_layout.addWidget(app.use_kalman_checkbox)

    app.use_coupled_checkbox = app.create_modern_checkbox(
        "Use Coupled XY Tracking", kalman_config.get("use_coupled_xy", False)
    )
    kalman_layout.addWidget(app.use_coupled_checkbox)

    spacer = QWidget()
    spacer.setFixedHeight(12)
    kalman_layout.addWidget(spacer)

    alpha_with_kalman = int(kalman_config.get("alpha_with_kalman", 1.5) * 100)
    app.alpha_with_kalman_slider = app.create_modern_slider(
        kalman_layout,
        "Alpha Smoothing",
        alpha_with_kalman,
        100,
        300,
        "",
        0.01,
    )

    app.kf_p_slider = app.create_modern_slider(
        kalman_layout,
        "Kf (P) - Trust in measurements",
        int(kalman_config.get("kf_p", 38.17) * 100),
        100,
        10000,
        "",
        0.01,
    )
    app.kf_r_slider = app.create_modern_slider(
        kalman_layout,
        "Kf (R) - Direct movement",
        int(kalman_config.get("kf_r", 2.8) * 100),
        10,
        1000,
        "",
        0.01,
    )
    app.kf_q_slider = app.create_modern_slider(
        kalman_layout,
        "Kf (Q) - Quick movement tracking",
        int(kalman_config.get("kf_q", 28.11) * 100),
        100,
        5000,
        "",
        0.01,
    )

    app.kalman_frames_slider = app.create_modern_slider(
        kalman_layout,
        "Prediction Frames (F) - Response time",
        int(kalman_config.get("kalman_frames_to_predict", 1.5) * 10),
        1,
        100,
        "",
        0.1,
    )

    layout.addWidget(kalman_container)
    layout.addStretch()
