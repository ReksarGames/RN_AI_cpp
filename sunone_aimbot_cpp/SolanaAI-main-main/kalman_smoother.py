import numpy as np
import torch
from filterpy.kalman import KalmanFilter


class KalmanSmoother:
    """Kalman-based smoother for 2D mouse movement.

    This is extracted from the original detector logic. It depends only on a
    config_manager-like object that provides:
      - get_kalman_config()
      - register_callback(callback)
    and exposes the same public API as before:
      - update(dx, dy) -> (smoothed_x, smoothed_y)
      - get_motion_analysis() -> dict
      - predict_frames() -> list[dict]
    """

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.kalman_config = self.config_manager.get_kalman_config()
        self.config_manager.register_callback(self._on_config_update)

        # Check if we should use coupled mode
        self.use_coupled = self.kalman_config.get("use_coupled_xy", False)

        if self.use_coupled:
            # Use coupled filter
            self._init_coupled_filter()
        else:
            # Use original independent filters
            self.kf_x = KalmanFilter(dim_x=2, dim_z=1)
            self.kf_y = KalmanFilter(dim_x=2, dim_z=1)
            self._configure_filters()

    # ---------------------------------------------------------------------
    # Coupled XY filter configuration
    # ---------------------------------------------------------------------
    def _init_coupled_filter(self):
        """Initialize coupled XY filter"""
        # Single 4D filter for coupled motion
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self._configure_coupled_filter()

    def _configure_coupled_filter(self):
        """Configure the coupled Kalman filter"""
        if not self.kalman_config.get("use_kalman", True):
            return

        # State vector: [x, y, vx, vy]
        self.kf.x = np.array([[0.0], [0.0], [0.0], [0.0]])

        # State transition matrix
        dt = 1.0
        self.kf.F = np.array(
            [
                [1.0, 0.0, dt, 0.0],
                [0.0, 1.0, 0.0, dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )

        # Measurement matrix
        self.kf.H = np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
            ]
        )

        # Initial covariance with correlations
        p_pos = self.kalman_config.get("kf_p", 38.17)
        p_vel = p_pos * 2
        correlation_factor = self.kalman_config.get("xy_correlation", 0.3)

        self.kf.P = np.array(
            [
                [p_pos, p_pos * correlation_factor, 0.0, 0.0],
                [p_pos * correlation_factor, p_pos, 0.0, 0.0],
                [0.0, 0.0, p_vel, p_vel * correlation_factor],
                [0.0, 0.0, p_vel * correlation_factor, p_vel],
            ]
        )

        # Measurement noise
        r_val = self.kalman_config.get("kf_r", 2.8)
        measurement_correlation = self.kalman_config.get("measurement_correlation", 0.1)

        self.kf.R = np.array(
            [
                [r_val, r_val * measurement_correlation],
                [r_val * measurement_correlation, r_val],
            ]
        )

        # Process noise with coupling
        q = self.kalman_config.get("kf_q", 28.11)
        process_correlation = self.kalman_config.get("process_correlation", 0.2)
        q_pos = q / 3.0
        q_vel = q

        self.kf.Q = np.array(
            [
                [q_pos, q_pos * process_correlation, q_pos / 2.0, q_pos * process_correlation / 2.0],
                [q_pos * process_correlation, q_pos, q_pos * process_correlation / 2.0, q_pos / 2.0],
                [q_pos / 2.0, q_pos * process_correlation / 2.0, q_vel, q_vel * process_correlation],
                [q_pos * process_correlation / 2.0, q_pos / 2.0, q_vel * process_correlation, q_vel],
            ]
        )

    # ---------------------------------------------------------------------
    # Config updates
    # ---------------------------------------------------------------------
    def _on_config_update(self, new_config):
        """Handle configuration updates"""
        if "kalman" not in new_config:
            return

        self.kalman_config = new_config["kalman"]

        # Check if coupling mode changed
        new_use_coupled = self.kalman_config.get("use_coupled_xy", False)
        if new_use_coupled != self.use_coupled:
            self.use_coupled = new_use_coupled
            if self.use_coupled:
                self._init_coupled_filter()
            else:
                self.kf_x = KalmanFilter(dim_x=2, dim_z=1)
                self.kf_y = KalmanFilter(dim_x=2, dim_z=1)
                self._configure_filters()
        else:
            # Just reconfigure existing filter type
            if self.use_coupled:
                self._configure_coupled_filter()
            else:
                self._configure_filters()

    # ---------------------------------------------------------------------
    # Independent (per-axis) filters configuration
    # ---------------------------------------------------------------------
    def _configure_filters(self):
        """Configuration for independent X/Y filters"""
        if not self.kalman_config.get("use_kalman", True):
            return

        for kf in [self.kf_x, self.kf_y]:
            kf.x = np.array([[0.0], [0.0]])
            kf.F = np.array([[1.0, 1.0], [0.0, 1.0]])
            kf.H = np.array([[1.0, 0.0]])
            kf.P = np.eye(2) * self.kalman_config.get("kf_p", 38.17)
            kf.R = np.array([[self.kalman_config.get("kf_r", 2.8)]])
            q = self.kalman_config.get("kf_q", 28.11)
            kf.Q = np.array([[q / 3.0, q / 2.0], [q / 2.0, q]])

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def update(self, dx, dy):
        """Update the Kalman filter(s) with new measurements.

        Returns smoothed (dx, dy) as floats.
        """
        if not self.kalman_config.get("use_kalman", True):
            if isinstance(dx, torch.Tensor):
                dx = dx.cpu().item()
            if isinstance(dy, torch.Tensor):
                dy = dy.cpu().item()
            return float(dx), float(dy)

        # Convert tensors if needed
        if isinstance(dx, torch.Tensor):
            dx = dx.cpu().item()
        if isinstance(dy, torch.Tensor):
            dy = dy.cpu().item()

        if self.use_coupled:
            self.kf.predict()
            measurement = np.array([[dx], [dy]])
            self.kf.update(measurement)
            return float(self.kf.x[0, 0]), float(self.kf.x[1, 0])

        # Independent filters
        self.kf_x.predict()
        self.kf_y.predict()
        self.kf_x.update(np.array([[dx]]))
        self.kf_y.update(np.array([[dy]]))
        return float(self.kf_x.x[0, 0]), float(self.kf_y.x[0, 0])

    def get_motion_analysis(self):
        """Analyze current motion (only for coupled mode).

        Returns a dict with speed, heading, and turning information, or
        an empty dict if coupled mode is disabled.
        """
        if not self.use_coupled or not self.kalman_config.get("use_kalman", True):
            return {}

        vx = float(self.kf.x[2][0])
        vy = float(self.kf.x[3][0])
        speed = float(np.sqrt(vx ** 2 + vy ** 2))

        # Turning analysis via covariance
        velocity_covariance = self.kf.P[2:4, 2:4]
        turning_indicator = abs(velocity_covariance[0, 1]) / (
            float(np.sqrt(velocity_covariance[0, 0] * velocity_covariance[1, 1])) + 1e-10
        )

        heading_rad = float(np.arctan2(vy, vx))
        heading_deg = float(np.degrees(heading_rad))

        return {
            "speed": speed,
            "heading_rad": heading_rad,
            "heading_deg": heading_deg,
            "is_turning": bool(turning_indicator > 0.5),
            "turning_strength": float(turning_indicator),
        }

    def predict_frames(self):
        """Predict positions for configured number of frames ahead.

        Returns a list of prediction dicts.
        """
        if not self.kalman_config.get("use_kalman", True):
            return []

        frames_to_predict = self.kalman_config.get("kalman_frames_to_predict", 1.5)
        # Use at least 1 prediction frame
        num_predictions = max(1, int(frames_to_predict))
        predictions = []

        if self.use_coupled:
            # Backup current state
            state_backup = self.kf.x.copy()
            cov_backup = self.kf.P.copy()

            for i in range(num_predictions):
                self.kf.predict()
                predictions.append(
                    {
                        "frame": i + 1,
                        "x": int(self.kf.x[0][0]),
                        "y": int(self.kf.x[1][0]),
                        "vx": float(self.kf.x[2][0]),
                        "vy": float(self.kf.x[3][0]),
                        "uncertainty_x": float(np.sqrt(self.kf.P[0, 0])),
                        "uncertainty_y": float(np.sqrt(self.kf.P[1, 1])),
                    }
                )

            # Restore state
            self.kf.x = state_backup
            self.kf.P = cov_backup
            return predictions

        # Independent filters prediction
        x_state = self.kf_x.x.copy()
        y_state = self.kf_y.x.copy()
        x_cov = self.kf_x.P.copy()
        y_cov = self.kf_y.P.copy()

        for i in range(num_predictions):
            self.kf_x.predict()
            self.kf_y.predict()

            p_value = self.kalman_config.get("kf_p", 38.17) + i * 0.1

            predictions.append(
                {
                    "frame": i + 1,
                    "x": int(self.kf_x.x[0][0]),
                    "y": int(self.kf_y.x[0][0]),
                    "kf_p": float(p_value),
                    "uncertainty_x": float(np.sqrt(self.kf_x.P[0, 0])),
                    "uncertainty_y": float(np.sqrt(self.kf_y.P[0, 0])),
                }
            )

        # Restore state
        self.kf_x.x = x_state
        self.kf_y.x = y_state
        self.kf_x.P = x_cov
        self.kf_y.P = y_cov

        return predictions
