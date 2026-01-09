import math
import threading
import time
from typing import Optional

import win32api

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except Exception:
    vg = None
    VGAMEPAD_AVAILABLE = False

try:
    import XInput
    XINPUT_AVAILABLE = True
except ImportError:
    try:
        import subprocess

        subprocess.run(
            ["python", "-m", "pip", "install", "XInput-Python"],
            capture_output=True,
            text=True,
        )
        import XInput  # type: ignore[redefined-builtin]

        XINPUT_AVAILABLE = True
    except Exception:
        XInput = None  # type: ignore[assignment]
        XINPUT_AVAILABLE = False


CONTROLLER_MESSAGES_SHOWN = False


class ControllerHandler:
    """Universal controller handler using vgamepad for virtual controller output.

    Extracted from detector.py; behaviour is preserved.
    """

    def __init__(self, aimbot_controller) -> None:
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Physical controller input
        self.physical_controller_index: Optional[int] = None
        self.physical_controller_connected = False

        # Virtual controller output
        self.virtual_gamepad = None
        self.virtual_controller_initialized = False
        self.vgamepad_available = VGAMEPAD_AVAILABLE

        # Controller settings
        self.deadzone = 0.15
        self.aim_stick = "right"
        self.trigger_threshold = 0.5
        self.sensitivity_multiplier = 1.0
        self.activation_button = "right_trigger"
        self.hold_to_aim = True

        # Controller type detection
        self.controller_type = "xbox"

        # State tracking
        self.is_aiming = False
        self.last_aim_state = False
        self.last_button_states: dict[str, bool] = {}

        # Silent mode flag
        self.silent_mode = True
        self.messages_shown = False

        # Lazy virtual controller init
        self.virtual_controller_attempted = False

    def show_controller_messages(self) -> None:
        """Show controller status messages only when needed."""
        global CONTROLLER_MESSAGES_SHOWN

        if not CONTROLLER_MESSAGES_SHOWN:
            CONTROLLER_MESSAGES_SHOWN = True

            if not VGAMEPAD_AVAILABLE:
                print("\n" + "=" * 60)
                print("[!] Virtual controller features disabled")
                print("[!] To enable virtual controller support:")
                print("    1. Download: https://github.com/ViGEm/ViGEmBus/releases")
                print("    2. Install ViGEmBusSetup_x64.msi")
                print("    3. Restart your computer")
                print("=" * 60 + "\n")
            else:
                print("[+] Virtual controller support available")

            if XINPUT_AVAILABLE:
                print("[+] XInput controller support ready")
            else:
                print("[-] XInput not available - controller input disabled")

    def initialize_virtual_controller(self) -> bool:
        """Initialize vgamepad virtual controller only when needed."""
        if self.virtual_controller_attempted:
            return self.virtual_controller_initialized

        self.virtual_controller_attempted = True

        if not VGAMEPAD_AVAILABLE or vg is None:
            self.virtual_controller_initialized = False
            return False

        try:
            self.virtual_gamepad = vg.VX360Gamepad()
            self.virtual_controller_initialized = True
            if not self.silent_mode:
                print("[+] Virtual controller initialized")
            return True
        except Exception:
            self.virtual_controller_initialized = False
            return False

    def find_controller(self) -> bool:
        """Find and connect to a physical controller via XInput."""
        if not XINPUT_AVAILABLE or XInput is None:  # type: ignore[truthy-function]
            if not self.silent_mode and not self.messages_shown:
                print("[-] XInput not available - cannot detect controllers")
                self.messages_shown = True
            return False

        try:
            for i in range(4):
                state = XInput.State()
                result = XInput.XInputGetState(i, state)

                if result == 0:  # ERROR_SUCCESS
                    self.physical_controller_index = i
                    self.physical_controller_connected = True
                    self.controller_type = "xbox"

                    if not self.silent_mode:
                        print(f"[+] Controller connected (Index: {i})")
                        if not self.virtual_controller_initialized and VGAMEPAD_AVAILABLE:
                            self.initialize_virtual_controller()

                    return True

            if self.physical_controller_connected:
                if not self.silent_mode:
                    print("[-] Controller disconnected")
                self.physical_controller_connected = False
                self.physical_controller_index = None

            return False

        except Exception as e:
            if not self.silent_mode:
                print(f"[-] Controller detection error: {e}")
            return False

    def detect_controller_type(self, controller_name: str = "") -> str:
        """Detect controller type (currently always 'xbox')."""
        return "xbox"

    def get_physical_controller_state(self):
        """Return a normalized gamepad state or None.

        This handles differences between XInput wrappers:
        - Some expose state.Gamepad
        - Others expose state.gamepad
        We normalize to an object with attributes used elsewhere:
        right_thumb_x, right_thumb_y, left_thumb_x, left_thumb_y,
        right_trigger, left_trigger, buttons.
        """
        if not self.physical_controller_connected or self.physical_controller_index is None:
            return None

        try:
            state = XInput.State()
            result = XInput.XInputGetState(self.physical_controller_index, state)
            if result != 0:
                self.physical_controller_connected = False
                return None

            # Try common attribute names first
            gamepad = getattr(state, "gamepad", None)
            if gamepad is None:
                gamepad = getattr(state, "Gamepad", None)

            if gamepad is None:
                # Unknown layout
                raise AttributeError("XINPUT_STATE has no 'Gamepad' or 'gamepad' field")

            # If the gamepad already exposes the attributes we expect, use it directly
            if all(
                hasattr(gamepad, attr)
                for attr in (
                    "right_thumb_x",
                    "right_thumb_y",
                    "left_thumb_x",
                    "left_thumb_y",
                    "right_trigger",
                    "left_trigger",
                    "buttons",
                )
            ):
                return gamepad

            # Otherwise, adapt the typical XInput-Python struct (wButtons, bLeftTrigger, etc.)
            class _NormalizedGamepad:
                __slots__ = (
                    "left_thumb_x",
                    "left_thumb_y",
                    "right_thumb_x",
                    "right_thumb_y",
                    "left_trigger",
                    "right_trigger",
                    "buttons",
                )

                def __init__(self, gp):
                    # Standard XInput fields: wButtons, bLeftTrigger, bRightTrigger,
                    # sThumbLX, sThumbLY, sThumbRX, sThumbRY
                    self.left_thumb_x = getattr(gp, "sThumbLX", 0)
                    self.left_thumb_y = getattr(gp, "sThumbLY", 0)
                    self.right_thumb_x = getattr(gp, "sThumbRX", 0)
                    self.right_thumb_y = getattr(gp, "sThumbRY", 0)
                    self.left_trigger = getattr(gp, "bLeftTrigger", 0)
                    self.right_trigger = getattr(gp, "bRightTrigger", 0)
                    self.buttons = getattr(gp, "wButtons", 0)

            return _NormalizedGamepad(gamepad)
        except Exception as e:
            print(f"[-] Error reading controller state: {e}")
            return None

    def get_stick_input(self, stick: str = "right") -> tuple[float, float]:
        if not self.physical_controller_connected:
            return 0.0, 0.0

        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return 0.0, 0.0

        try:
            if stick == "right":
                x = gamepad.right_thumb_x / 32768.0
                y = -gamepad.right_thumb_y / 32768.0
            else:
                x = gamepad.left_thumb_x / 32768.0
                y = -gamepad.left_thumb_y / 32768.0

            magnitude = math.sqrt(x * x + y * y)
            if magnitude < self.deadzone:
                return 0.0, 0.0

            if magnitude > 1.0:
                magnitude = 1.0

            normalized_magnitude = (magnitude - self.deadzone) / (1.0 - self.deadzone)
            x = (x / magnitude) * normalized_magnitude if magnitude > 0 else 0.0
            y = (y / magnitude) * normalized_magnitude if magnitude > 0 else 0.0

            return x, y
        except Exception:
            return 0.0, 0.0

    def get_trigger_input(self, trigger: str = "right") -> float:
        if not self.physical_controller_connected:
            return 0.0

        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return 0.0

        try:
            if trigger == "right":
                return gamepad.right_trigger / 255.0
            else:
                return gamepad.left_trigger / 255.0
        except Exception:
            return 0.0

    def is_button_pressed(self, button) -> bool:
        if not self.physical_controller_connected:
            return False

        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return False

        try:
            button_map = {
                "a": 0x1000,
                "b": 0x2000,
                "x": 0x4000,
                "y": 0x8000,
                "lb": 0x0100,
                "rb": 0x0200,
                "back": 0x0020,
                "start": 0x0010,
                "ls": 0x0040,
                "rs": 0x0080,
                "up": 0x0001,
                "down": 0x0002,
                "left": 0x0004,
                "right": 0x0008,
            }

            if isinstance(button, str):
                button_flag = button_map.get(button.lower(), 0)
            else:
                button_flag = button

            return bool(gamepad.buttons & button_flag)
        except Exception:
            return False

    def send_virtual_input(self, stick_x: float = 0.0, stick_y: float = 0.0, trigger_value: float = 0.0) -> None:
        if not self.virtual_controller_initialized or not self.virtual_gamepad:
            return

        try:
            if self.aim_stick == "right":
                self.virtual_gamepad.right_joystick(
                    x_value=int(stick_x * 32767),
                    y_value=int(stick_y * 32767),
                )
            else:
                self.virtual_gamepad.left_joystick(
                    x_value=int(stick_x * 32767),
                    y_value=int(stick_y * 32767),
                )

            if trigger_value > 0:
                if self.activation_button == "right_trigger":
                    self.virtual_gamepad.right_trigger(value=int(trigger_value * 255))
                elif self.activation_button == "left_trigger":
                    self.virtual_gamepad.left_trigger(value=int(trigger_value * 255))

            self.virtual_gamepad.update()
        except Exception:
            pass

    def check_activation(self) -> bool:
        if not self.physical_controller_connected or not self.enabled:
            return False

        if self.activation_button == "right_trigger":
            return self.get_trigger_input("right") > self.trigger_threshold
        if self.activation_button == "left_trigger":
            return self.get_trigger_input("left") > self.trigger_threshold
        if self.activation_button == "right_bumper":
            return self.is_button_pressed("rb")
        if self.activation_button == "left_bumper":
            return self.is_button_pressed("lb")
        if self.activation_button == "right_stick":
            return self.is_button_pressed("rs")
        if self.activation_button == "a_button":
            return self.is_button_pressed("a")
        if self.activation_button == "x_button":
            return self.is_button_pressed("x")
        return False

    def controller_loop(self) -> None:
        last_controller_check = 0.0
        controller_check_interval = 2.0

        while self.running:
            try:
                if self.enabled:
                    current_time = time.time()
                    if (
                        not self.physical_controller_connected
                        and current_time - last_controller_check > controller_check_interval
                    ):
                        old_silent = self.silent_mode
                        self.silent_mode = True
                        self.find_controller()
                        self.silent_mode = old_silent
                        last_controller_check = current_time

                    if self.physical_controller_connected:
                        self.is_aiming = self.check_activation()

                        if self.is_aiming != self.last_aim_state:
                            if self.is_aiming and not self.silent_mode:
                                print("[Controller] Aimbot activated")
                            self.last_aim_state = self.is_aiming

                        if self.is_aiming:
                            stick_x, stick_y = self.get_stick_input(self.aim_stick)
                            if abs(stick_x) > 0.1 or abs(stick_y) > 0.1:
                                move_x = stick_x * 15 * self.sensitivity_multiplier
                                move_y = stick_y * 15 * self.sensitivity_multiplier
                                if self.aimbot_controller.mouse_method.lower() == "hid":
                                    from hid_mouse import move_mouse

                                    move_mouse(int(move_x), int(move_y))

                        self.process_button_actions()

                time.sleep(0.01)

            except Exception as e:
                if not self.silent_mode:
                    print(f"[-] Controller loop error: {e}")
                time.sleep(0.1)

    def process_button_actions(self) -> None:
        config = self.aimbot_controller.config_manager.get_config()
        mappings = config.get("controller", {}).get("button_mappings", {})

        current_states = {
            "y": self.is_button_pressed("y"),
            "x": self.is_button_pressed("x"),
            "b": self.is_button_pressed("b"),
            "combo": self.is_button_pressed("back") and self.is_button_pressed("start"),
        }

        if current_states["y"] and not self.last_button_states.get("y", False):
            action = mappings.get("y_action", "None")
            self.execute_action(action)

        if current_states["x"] and not self.last_button_states.get("x", False):
            action = mappings.get("x_action", "None")
            self.execute_action(action)

        if current_states["b"] and not self.last_button_states.get("b", False):
            action = mappings.get("b_action", "None")
            self.execute_action(action)

        if current_states["combo"] and not self.last_button_states.get("combo", False):
            action = mappings.get("combo_action", "None")
            self.execute_action(action)

        self.last_button_states = current_states

    def execute_action(self, action: str) -> None:
        if action == "Toggle Overlay":
            current = self.aimbot_controller.config_manager.get_value("show_overlay", True)
            self.aimbot_controller.config_manager.set_value("show_overlay", not current)
            print(f"[Controller] Overlay {'enabled' if not current else 'disabled'}")

        elif action == "Toggle Debug Window":
            self.aimbot_controller.toggle_debug_window()

        elif action == "Toggle Triggerbot":
            current = self.aimbot_controller.triggerbot.enabled
            self.aimbot_controller.triggerbot.enabled = not current
            print(f"[Controller] Triggerbot {'enabled' if not current else 'disabled'}")

        elif action == "Toggle Flickbot":
            current = self.aimbot_controller.flickbot.enabled
            self.aimbot_controller.flickbot.enabled = not current
            print(f"[Controller] Flickbot {'enabled' if not current else 'disabled'}")

        elif action == "Emergency Stop":
            self.aimbot_controller.force_stop()

        elif action == "Toggle Movement Curves":
            self.aimbot_controller.toggle_movement_curves()

        elif action == "Switch Overlay Shape":
            self.aimbot_controller.toggle_overlay_shape()

        elif action == "Toggle Aimbot":
            if self.aimbot_controller.running:
                self.aimbot_controller.stop()
            else:
                self.aimbot_controller.start()

        elif action == "Increase Sensitivity":
            current = self.aimbot_controller.sensitivity
            new_sens = min(10.0, current + 0.1)
            self.aimbot_controller.config_manager.set_value("sensitivity", new_sens)
            print(f"[Controller] Sensitivity: {new_sens:.1f}")

        elif action == "Decrease Sensitivity":
            current = self.aimbot_controller.sensitivity
            new_sens = max(0.1, current - 0.1)
            self.aimbot_controller.config_manager.set_value("sensitivity", new_sens)
            print(f"[Controller] Sensitivity: {new_sens:.1f}")

    def vibrate(self, left_motor: float = 0.5, right_motor: float = 0.5, duration: float = 0.1) -> None:
        if self.physical_controller_connected and self.physical_controller_index is not None and XInput is not None:
            try:
                vibration = XInput.XINPUT_VIBRATION()
                vibration.wLeftMotorSpeed = int(left_motor * 65535)
                vibration.wRightMotorSpeed = int(right_motor * 65535)
                XInput.XInputSetState(self.physical_controller_index, vibration)

                def stop_vibration() -> None:
                    stop_vib = XInput.XINPUT_VIBRATION()
                    stop_vib.wLeftMotorSpeed = 0
                    stop_vib.wRightMotorSpeed = 0
                    XInput.XInputSetState(self.physical_controller_index, stop_vib)

                threading.Timer(duration, stop_vibration).start()
            except Exception:
                pass

    def stop(self) -> None:
        self.running = False
        # Avoid joining from within the controller loop thread itself
        if self.thread and self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=1)

        if self.virtual_gamepad:
            try:
                self.virtual_gamepad.reset()
                self.virtual_gamepad.update()
            except Exception:
                pass

        if self.physical_controller_connected and self.physical_controller_index is not None and XInput is not None:
            try:
                stop_vib = XInput.XINPUT_VIBRATION()
                stop_vib.wLeftMotorSpeed = 0
                stop_vib.wRightMotorSpeed = 0
                XInput.XInputSetState(self.physical_controller_index, stop_vib)
            except Exception:
                pass

        print("[+] Controller support stopped")

    def start(self) -> bool:
        if not self.running:
            if self.enabled and not self.messages_shown:
                self.silent_mode = False
                self.show_controller_messages()

            self.running = True
            self.thread = threading.Thread(target=self.controller_loop, daemon=True)
            self.thread.start()

            if self.enabled and not self.silent_mode:
                print("[+] Controller support started")
            return True
        return False


def check_vgamepad_requirements() -> bool:
    """Check if vgamepad requirements are met."""
    try:
        import vgamepad as vg_test

        test_controller = vg_test.VX360Gamepad()
        test_controller.reset()
        test_controller.update()
        print("[+] vgamepad is working correctly")
        return True
    except Exception as e:
        if "VIGEM_ERROR_BUS_NOT_FOUND" in str(e):
            print("\n" + "=" * 60)
            print("[-] ViGEmBus driver not installed!")
            print("[!] Virtual controller features will be disabled")
            print("[!] To enable virtual controller support:")
            print("    1. Download: https://github.com/ViGEm/ViGEmBus/releases")
            print("    2. Install ViGEmBusSetup_x64.msi")
            print("    3. Restart your computer")
            print("=" * 60 + "\n")
        else:
            print(f"[-] vgamepad error: {e}")
        return False
