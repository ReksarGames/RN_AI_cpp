import random
import threading
import time

import win32api

from hid_mouse import ensure_mouse_connected, move_mouse


class SmartArduinoAntiRecoil:
    """Smart anti-recoil with rate limiting to prevent Arduino crashes.

    Extracted from detector.py. This class depends on an external
    aimbot_controller object and uses hid_mouse for HID operations.
    """

    def __init__(self, aimbot_controller) -> None:
        self.aimbot_controller = aimbot_controller
        self.enabled: bool = False
        self.strength: float = 5.0
        self.reduce_bloom: bool = True
        self.running: bool = False
        self.thread: threading.Thread | None = None

        # Smart activation flags
        self.require_target: bool = True
        self.require_keybind: bool = True

        # Rate limiting to prevent Arduino crashes
        self.last_recoil_time: float = 0.0
        self.min_recoil_interval: float = 0.008  # Minimum 8ms between commands (125Hz max)
        self.recoil_active: bool = False

        # Mutex for thread safety
        self.recoil_lock = threading.Lock()

    def start(self) -> bool:
        """Start anti-recoil system in a background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.recoil_loop, daemon=True)
            self.thread.start()
            return True
        return False

    def stop(self) -> None:
        """Stop anti-recoil system and join the worker thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        print("[+] Anti-recoil stopped")

    def check_mouse_button(self) -> bool:
        """Check if left mouse button is pressed using Windows API."""
        state = win32api.GetAsyncKeyState(0x01)  # VK_LBUTTON
        return (state & 0x8000) != 0

    def should_activate(self) -> bool:
        """Return True if anti-recoil should currently be active."""
        if not self.enabled:
            return False

        # Check mouse button state
        if not self.check_mouse_button():
            return False

        # Aimbot must be running
        if not self.aimbot_controller.running:
            return False

        # Check keybind if required
        if self.require_keybind:
            try:
                keybind_state = win32api.GetKeyState(int(self.aimbot_controller.keybind, 16))
                if keybind_state not in (-127, -128):
                    return False
            except Exception:
                return False

        # Require active target if configured
        if self.require_target:
            if hasattr(self.aimbot_controller, "has_target"):
                return bool(self.aimbot_controller.has_target)
            return False

        return True

    def recoil_loop(self) -> None:
        """Main anti-recoil loop with rate limiting and safety checks."""
        consecutive_errors = 0

        while self.running:
            try:
                current_time = time.time()

                # Rate limiting
                time_since_last = current_time - self.last_recoil_time
                if time_since_last < self.min_recoil_interval:
                    time.sleep(self.min_recoil_interval - time_since_last)
                    continue

                if self.should_activate():
                    with self.recoil_lock:
                        # Check if mouse device is healthy
                        if not ensure_mouse_connected():
                            consecutive_errors += 1
                            if consecutive_errors > 5:
                                print("[-] Anti-recoil disabled due to device errors")
                                self.enabled = False
                                break
                            time.sleep(0.1)
                            continue

                        # Reset error counter on successful connection
                        consecutive_errors = 0

                        # Apply recoil compensation with smaller, smoother movements
                        vertical_offset = self.calculate_vertical_offset()
                        horizontal_offset = self.calculate_horizontal_offset()

                        # Clamp values to prevent overflow
                        vertical_offset = max(-10, min(10, vertical_offset))
                        horizontal_offset = max(-5, min(5, horizontal_offset))

                        if abs(vertical_offset) > 0.5 or abs(horizontal_offset) > 0.5:
                            move_mouse(int(horizontal_offset), int(vertical_offset))
                            self.last_recoil_time = current_time

                    # Variable delay based on fire rate
                    time.sleep(random.uniform(0.010, 0.020))  # 10–20 ms
                else:
                    # Not active, idle with lower CPU usage
                    self.recoil_active = False
                    time.sleep(0.05)

            except Exception as e:
                print(f"[-] Anti-recoil error: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self.enabled = False
                    break
                time.sleep(0.1)

    def calculate_vertical_offset(self) -> float:
        """Calculate smoother vertical recoil compensation."""
        base_strength = self.strength * 0.7

        variation = random.uniform(0.8, 1.2)
        vertical_offset = base_strength * variation

        # Reduce when locked on a target
        if hasattr(self.aimbot_controller, "target_lock"):
            if self.aimbot_controller.target_lock.get("current_target_id"):
                vertical_offset *= 0.8

        return vertical_offset

    def calculate_horizontal_offset(self) -> float:
        """Calculate horizontal bloom compensation (small random sway)."""
        if not self.reduce_bloom:
            return 0.0

        return random.randrange(-2000, 2000, 1) / 1000.0

    def set_strength(self, strength: float) -> None:
        """Set anti-recoil strength (0–50, 0–20 recommended)."""
        self.strength = max(0.0, min(50.0, strength))
        print(f"[+] Anti-recoil strength set to: {self.strength}")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable anti-recoil."""
        self.enabled = enabled
        if enabled:
            print(f"[+] Anti-recoil enabled with strength: {self.strength}")
        else:
            print("[+] Anti-recoil disabled")
