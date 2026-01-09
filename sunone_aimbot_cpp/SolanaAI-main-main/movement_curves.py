import math
import random
from enum import Enum
from typing import List, Tuple


class MovementCurveType(Enum):
    """Supported movement curve types"""

    BEZIER = "Bezier"
    B_SPLINE = "B-Spline"
    CATMULL = "Catmull"
    EXPONENTIAL = "Exponential"
    HERMITE = "Hermite"
    SINE = "Sine"


class MovementCurves:
    """Advanced movement curves for natural mouse movement simulation.

    This class is responsible only for generating and shaping paths and
    movement values. The actual mouse I/O (move_mouse, checking running
    flags, etc.) is handled by higher-level code (e.g. AimbotController).
    """

    def __init__(self) -> None:
        self.supported_curves = [curve.value for curve in MovementCurveType]
        self.current_curve = MovementCurveType.BEZIER

        # Optimized parameters for speed
        self.curve_params = {
            "bezier_control_randomness": 0.1,  # Less deviation
            "spline_smoothness": 0.2,  # Less smoothing
            "catmull_tension": 0.2,  # Less tension
            "exponential_decay": 3.0,  # Faster decay
            "hermite_tangent_scale": 0.5,  # Less curve
            "sine_frequency": 2.0,  # Faster oscillation
            "curve_steps": 5,  # Fewer steps
            "speed_multiplier": 1.0,  # Additional speed control
            "aimlock_mode": True,  # Enable aimlock-like behavior
        }

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def set_aimlock_mode(self, enabled: bool) -> None:
        """Toggle between aimlock mode (fast) and humanized mode (slower)."""

        self.curve_params["aimlock_mode"] = enabled

        if enabled:
            # Fast settings for aimlock
            self.curve_params["curve_steps"] = 3
            self.curve_params["bezier_control_randomness"] = 0.05
            self.curve_params["speed_multiplier"] = 2.0
        else:
            # Normal humanized settings
            self.curve_params["curve_steps"] = 20
            self.curve_params["bezier_control_randomness"] = 0.3
            self.curve_params["speed_multiplier"] = 1.0

    def set_curve_type(self, curve_type: str) -> bool:
        """Set the movement curve type by name or enum value."""

        try:
            if isinstance(curve_type, str):
                # Try to match by value
                for curve in MovementCurveType:
                    if curve.value == curve_type:
                        self.current_curve = curve
                        return True
                # If no match, try direct enum creation
                self.current_curve = MovementCurveType(curve_type)
            else:
                self.current_curve = curve_type
            return True
        except ValueError:
            print(f"[-] Invalid curve type: {curve_type}")
            # Default to Bezier if invalid
            self.current_curve = MovementCurveType.BEZIER
            return False

    def get_supported_curves(self) -> List[str]:
        """Get list of supported movement curves."""

        return self.supported_curves

    def update_curve_parameters(self, **kwargs) -> None:
        """Update curve generation parameters in-place."""

        for key, value in kwargs.items():
            if key in self.curve_params:
                self.curve_params[key] = value
                print(f"[+] Updated {key} to {value}")
            else:
                print(f"[-] Unknown parameter: {key}")

    def get_curve_parameters(self) -> dict:
        """Get a shallow copy of current curve parameters."""

        return self.curve_params.copy()

    def random_curve_type(self) -> str:
        """Pick and activate a random curve type, return its name."""

        curve_type = random.choice(list(MovementCurveType))
        self.current_curve = curve_type
        return curve_type.value

    # ------------------------------------------------------------------
    # Path generation
    # ------------------------------------------------------------------
    def generate_fast_movement_path(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        max_steps: int = 5,
    ) -> List[Tuple[float, float]]:
        """Generate a fast movement path with minimal steps.

        This is tuned for aimlock-like behaviour: very few interpolation
        steps and minimal curvature.
        """

        distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)

        # Very few steps for speed
        steps = min(max_steps, max(2, int(distance / 30)))

        path: List[Tuple[float, float]] = []

        for i in range(steps + 1):
            t = i / steps

            if self.current_curve == MovementCurveType.BEZIER:
                # Fast bezier with minimal deviation
                ctrl_offset = 0.1
                ctrl_x = start_x + (end_x - start_x) * 0.5 + (end_x - start_x) * ctrl_offset * 0.5
                ctrl_y = start_y + (end_y - start_y) * 0.5 + (end_y - start_y) * ctrl_offset * 0.5

                x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t**2 * end_x
                y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t**2 * end_y

            elif self.current_curve == MovementCurveType.SINE:
                # Fast sine interpolation
                sine_influence = 0.05 * math.sin(t * math.pi)
                sine_t = t + sine_influence

                x = start_x + (end_x - start_x) * sine_t
                y = start_y + (end_y - start_y) * sine_t

            elif self.current_curve == MovementCurveType.EXPONENTIAL:
                # Fast exponential
                exp_t = 1 - math.exp(-3 * t)
                x = start_x + (end_x - start_x) * exp_t
                y = start_y + (end_y - start_y) * exp_t

            else:
                # Nearly linear for other curves (fast)
                mod_t = t * 0.95 + 0.05 * t * t
                x = start_x + (end_x - start_x) * mod_t
                y = start_y + (end_y - start_y) * mod_t

            path.append((x, y))

        return path

    def calculate_movement_speed(self, path: List[Tuple[float, float]]) -> List[float]:
        """Calculate per-step speed profile for a movement path."""

        if len(path) < 2:
            return [0.0]

        speeds: List[float] = []
        for i in range(len(path) - 1):
            dx = path[i + 1][0] - path[i][0]
            dy = path[i + 1][1] - path[i][1]
            speed = math.sqrt(dx * dx + dy * dy)
            speeds.append(speed)

        # Add final speed (same as last)
        speeds.append(speeds[-1] if speeds else 0.0)
        return speeds

    def smooth_path(
        self,
        path: List[Tuple[float, float]],
        smoothing_factor: float = 0.3,
    ) -> List[Tuple[float, float]]:
        """Apply smoothing to reduce jitter in a movement path."""

        if len(path) < 3:
            return path

        smoothed: List[Tuple[float, float]] = [path[0]]  # Keep first point

        for i in range(1, len(path) - 1):
            prev_x, prev_y = path[i - 1]
            curr_x, curr_y = path[i]
            next_x, next_y = path[i + 1]

            smooth_x = curr_x + smoothing_factor * ((prev_x + next_x) / 2 - curr_x)
            smooth_y = curr_y + smoothing_factor * ((prev_y + next_y) / 2 - curr_y)

            smoothed.append((smooth_x, smooth_y))

        smoothed.append(path[-1])  # Keep last point
        return smoothed

    def apply_curve_to_movement(
        self,
        move_x: float,
        move_y: float,
        distance: float,
        max_distance: float = 100.0,
    ) -> Tuple[float, float]:
        """Apply curve interpolation directly to movement values.

        Used when you already have a single movement vector but want to
        modulate it based on distance and curve type.
        """

        if distance == 0:
            return move_x, move_y

        # Normalize distance for interpolation parameter
        t = min(1.0, distance / max_distance)

        if self.current_curve == MovementCurveType.BEZIER:
            # Simple quadratic ease-in-out
            if t < 0.5:
                mod = 2 * t * t
            else:
                mod = -1 + (4 - 2 * t) * t
            move_x *= mod
            move_y *= mod

        elif self.current_curve == MovementCurveType.SINE:
            # Sine wave modulation
            sine_mod = (math.sin((t - 0.5) * math.pi) + 1.0) / 2.0
            move_x *= sine_mod
            move_y *= sine_mod

        elif self.current_curve == MovementCurveType.EXPONENTIAL:
            # Exponential modulation
            if t < 0.5:
                exp_mod = math.pow(2 * t, self.curve_params["exponential_decay"]) / 2.0
            else:
                exp_mod = 1.0 - math.pow(2 * (1.0 - t), self.curve_params["exponential_decay"]) / 2.0
            move_x *= exp_mod
            move_y *= exp_mod

        # For other curves, return unmodified (they work better with full path generation)
        return move_x, move_y
