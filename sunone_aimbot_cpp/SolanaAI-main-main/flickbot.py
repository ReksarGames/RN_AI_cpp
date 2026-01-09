import math
import time
from typing import Any

import win32api

from hid_mouse import ensure_mouse_connected, move_mouse, click_mouse


class Flickbot:
    """Enhanced Flickbot with proper screen movement and aim height targeting.

    Extracted from detector.py. Depends on an external aimbot_controller
    and uses hid_mouse for movement and clicks.
    """

    def __init__(self, aimbot_controller: Any) -> None:
        self.aimbot_controller = aimbot_controller
        self.enabled = False

        # Flick settings
        self.flick_speed = 1.0  # Direct movement multiplier
        self.flick_delay = 0.01  # Minimal delay before fire
        self.cooldown = 0.3  # Cooldown between flicks
        self.last_flick_time = 0.0
        self.keybind = 0x05  # Mouse button 4

        # Behavior settings
        self.auto_fire = True
        self.return_to_origin = True
        self.smooth_flick = False
        self.instant_flick = True  # Instant movement

        # State tracking
        self.consecutive_failures = 0
        self.flick_in_progress = False

    def is_ready_to_flick(self) -> bool:
        return time.time() - self.last_flick_time > self.cooldown and not self.flick_in_progress

    def is_keybind_pressed(self) -> bool:
        return win32api.GetAsyncKeyState(self.keybind) < 0

    def find_best_target_from_results(self, results):
        if not results or len(results[0].boxes) == 0:
            return None

        targets = []
        fov_center = self.aimbot_controller.fov // 2

        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            if hasattr(x1, "item"):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            height = y2 - y1
            width = x2 - x1

            if width < 5 or height < 5:
                continue

            center_x = (x1 + x2) / 2
            target_y = y1 + (height * (100 - self.aimbot_controller.aim_height) / 100)

            fov_target_x = center_x
            fov_target_y = target_y

            dist_from_center = math.sqrt((fov_target_x - fov_center) ** 2 + (fov_target_y - fov_center) ** 2)

            confidence = box.conf[0].cpu().numpy() if hasattr(box.conf[0], "cpu") else box.conf[0]

            targets.append(
                {
                    "fov_position": (fov_target_x, fov_target_y),
                    "distance": dist_from_center,
                    "confidence": confidence,
                    "box": (x1, y1, x2, y2),
                }
            )

        if not targets:
            return None

        return min(targets, key=lambda t: t["distance"])

    def calculate_flick_movement(self, fov_target_x: float, fov_target_y: float) -> tuple[int, int]:
        screen_center_x = self.aimbot_controller.center_x
        screen_center_y = self.aimbot_controller.center_y
        fov_size = self.aimbot_controller.fov

        fov_left = screen_center_x - (fov_size // 2)
        fov_top = screen_center_y - (fov_size // 2)

        absolute_target_x = fov_left + fov_target_x
        absolute_target_y = fov_top + fov_target_y

        delta_x = absolute_target_x - screen_center_x
        delta_y = absolute_target_y - screen_center_y

        delta_x *= self.aimbot_controller.sensitivity
        delta_y *= self.aimbot_controller.sensitivity

        delta_x *= self.flick_speed
        delta_y *= self.flick_speed

        delta_x = int(round(delta_x))
        delta_y = int(round(delta_y))

        delta_x = max(-127, min(127, delta_x))
        delta_y = max(-127, min(127, delta_y))

        return delta_x, delta_y

    def execute_flick(self, target) -> bool:
        if not ensure_mouse_connected():
            self.consecutive_failures += 1
            return False

        try:
            fov_x, fov_y = target["fov_position"]
            delta_x, delta_y = self.calculate_flick_movement(fov_x, fov_y)

            if self.instant_flick:
                move_mouse(delta_x, delta_y)
                time.sleep(self.flick_delay)
                if self.auto_fire:
                    click_mouse("left", duration=0.01)
                if self.return_to_origin:
                    move_mouse(-delta_x, -delta_y)
            else:
                if self.smooth_flick:
                    steps = 3
                    for _ in range(steps):
                        move_mouse(delta_x // steps, delta_y // steps)
                        time.sleep(0.002)
                else:
                    move_mouse(delta_x, delta_y)

                time.sleep(self.flick_delay)

                if self.auto_fire:
                    click_mouse("left", duration=0.02)

                if self.return_to_origin:
                    time.sleep(0.01)
                    if self.smooth_flick:
                        steps = 3
                        for _ in range(steps):
                            move_mouse(-delta_x // steps, -delta_y // steps)
                            time.sleep(0.002)
                    else:
                        move_mouse(-delta_x, -delta_y)

            self.consecutive_failures = 0
            return True

        except Exception as e:
            print(f"[-] Flick execution error: {e}")
            self.consecutive_failures += 1
            return False

    def perform_flick_with_results(self, results) -> bool:
        if not self.enabled or not self.is_ready_to_flick():
            return False

        if not self.is_keybind_pressed():
            return False

        if self.consecutive_failures > 5:
            print("[-] Flickbot disabled due to repeated failures")
            self.enabled = False
            self.consecutive_failures = 0
            return False

        self.flick_in_progress = True

        try:
            target = self.find_best_target_from_results(results)
            if not target:
                return False

            success = self.execute_flick(target)
            if success:
                self.last_flick_time = time.time()

            return success
        finally:
            self.flick_in_progress = False
