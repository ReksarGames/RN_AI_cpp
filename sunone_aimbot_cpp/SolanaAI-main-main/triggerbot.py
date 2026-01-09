import time
from typing import Any

import win32api

import hid_mouse
from hid_mouse import ensure_mouse_connected


class Triggerbot:
    """Automatic firing when crosshair is on target - FAST SPRAY VERSION.

    Extracted from detector.py. Depends on an external aimbot_controller
    (for FOV, keybind, etc.) and uses hid_mouse for HID operations.
    """

    def __init__(self, aimbot_controller: Any) -> None:
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.confidence_threshold = 0.5
        self.fire_delay = 0.001  # Minimal initial delay (1ms)
        self.cooldown = 0.001   # Minimal cooldown between shots (1ms)
        self.last_fire_time = 0.0
        self.require_aimbot_key = False
        self.keybind = 0x02
        self.running = False
        self.consecutive_failures = 0
        self.rapid_fire = True
        self.shots_per_burst = 1
        self.trigger_in_progress = False

        # Spray mode settings
        self.spray_mode = True
        self.spray_active = False
        self.spray_start_time = 0.0
        self.max_spray_duration = 5.0
        self.spray_rate = 0.001

        # Grace period to prevent stopping on detection flicker
        self.last_target_time = 0.0
        self.grace_period = 0.15

    def is_keybind_pressed(self) -> bool:
        """Check if triggerbot keybind is pressed."""
        return win32api.GetAsyncKeyState(self.keybind) < 0

    def is_ready_to_fire(self) -> bool:
        """Check if triggerbot is ready to fire (special handling in spray mode)."""
        if self.spray_mode and self.spray_active:
            return time.time() - self.last_fire_time >= self.spray_rate
        return time.time() - self.last_fire_time > self.cooldown and not self.trigger_in_progress

    def find_best_target_from_results(self, results):
        """Find best target from YOLO results for triggerbot."""
        if not results or len(results[0].boxes) == 0:
            return None

        fov_center = self.aimbot_controller.fov // 2
        best_target = None
        best_score = float("inf")

        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            if hasattr(x1, "item"):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            confidence = box.conf[0].cpu().numpy() if hasattr(box.conf[0], "cpu") else box.conf[0]
            if confidence < self.confidence_threshold:
                continue

            padding = 20
            crosshair_in_box = (
                (x1 - padding) <= fov_center <= (x2 + padding)
                and (y1 - padding) <= fov_center <= (y2 + padding)
            )

            if crosshair_in_box:
                box_area = (x2 - x1) * (y2 - y1)
                if box_area < best_score:
                    best_score = box_area
                    best_target = {
                        "box": (x1, y1, x2, y2),
                        "confidence": confidence,
                        "crosshair_inside": True,
                    }

        return best_target

    def is_target_locked(self, target_x, target_y, fov_center, box=None) -> bool:
        """Check if we should fire (simplified)."""
        return True

    def should_fire(self) -> bool:
        if not self.enabled:
            return False

        if self.spray_mode and self.spray_active:
            return True

        if not self.is_ready_to_fire():
            return False

        if not self.is_keybind_pressed():
            return False

        if self.require_aimbot_key:
            aimbot_key = int(self.aimbot_controller.keybind, 16)
            if win32api.GetAsyncKeyState(aimbot_key) not in (-127, -128):
                return False

        return True

    def perform_trigger_with_results(self, results) -> bool:
        """Perform triggerbot using already computed YOLO results."""
        if not self.enabled:
            return False

        if not self.is_keybind_pressed():
            return False

        if not results or len(results[0].boxes) == 0:
            return False

        fov_center = self.aimbot_controller.fov // 2

        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            if hasattr(x1, "item"):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            confidence = box.conf[0].cpu().numpy() if hasattr(box.conf[0], "cpu") else box.conf[0]
            if confidence < self.confidence_threshold:
                continue

            if x1 <= fov_center <= x2 and y1 <= fov_center <= y2:
                self.execute_fire()
                return True

        return False

    def start_spray(self) -> None:
        self.spray_active = True
        self.spray_start_time = time.time()
        if ensure_mouse_connected():
            try:
                hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Left down
            except Exception:
                pass

    def stop_spray(self) -> None:
        self.spray_active = False
        if ensure_mouse_connected():
            try:
                hid_mouse.mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Left up
            except Exception:
                pass

    def execute_fast_fire(self) -> bool:
        if not hid_mouse.mouse_dev:
            return False

        try:
            if self.spray_mode and self.spray_active:
                hid_mouse.mouse_dev.write([1, 0x00, 0, 0, 0, 0])
                time.sleep(0.0001)
                hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])
                return True
            else:
                return self.execute_fire()
        except Exception:
            return False

    def execute_fire(self) -> bool:
        if not ensure_mouse_connected():
            self.consecutive_failures += 1
            return False

        try:
            if self.rapid_fire and self.shots_per_burst > 1:
                for _ in range(self.shots_per_burst):
                    hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])
                    hid_mouse.mouse_dev.write([1, 0x00, 0, 0, 0, 0])

                self.consecutive_failures = 0
                return True
            else:
                hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])
                time.sleep(0.001)
                hid_mouse.mouse_dev.write([1, 0x00, 0, 0, 0, 0])

                self.consecutive_failures = 0
                return True

        except Exception as e:
            print(f"[-] Triggerbot fire error: {e}")
            self.consecutive_failures += 1
            return False

    def fire(self) -> None:
        """Legacy fire method for compatibility - ULTRA FAST VERSION."""
        try:
            if not ensure_mouse_connected():
                self.consecutive_failures += 1
                return

            if self.rapid_fire and self.shots_per_burst > 1:
                for _ in range(self.shots_per_burst):
                    hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])
                    hid_mouse.mouse_dev.write([1, 0x00, 0, 0, 0, 0])

                self.last_fire_time = time.time()
                self.consecutive_failures = 0
            else:
                hid_mouse.mouse_dev.write([1, 0x01, 0, 0, 0, 0])
                time.sleep(0.001)
                hid_mouse.mouse_dev.write([1, 0, 0, 0, 0, 0])

                self.last_fire_time = time.time()
                self.consecutive_failures = 0

        except Exception as e:
            print(f"[-] Triggerbot fire error: {e}")
            self.consecutive_failures += 1
