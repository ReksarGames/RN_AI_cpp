import time
from typing import Optional

import hid

# Shared HID mouse device and click timing state
mouse_dev: Optional[hid.device] = None
last_click_time: float = 0.0


def clamp_char(value: int) -> int:
    """Clamp integer to signed 8-bit range used by many HID mouse reports."""
    return max(-128, min(127, value))


def low_byte(x: int) -> int:
    return x & 0xFF


def high_byte(x: int) -> int:
    return (x >> 8) & 0xFF


def make_report(x: int, y: int) -> list[int]:
    """Create a simple HID report for mouse movement.

    This mirrors the original layout used in detector.py.
    """
    # Clamp values to signed 8-bit range
    x = max(-127, min(127, int(x)))
    y = max(-127, min(127, int(y)))

    # [report_id, buttons, x_low, x_high, y_low, y_high]
    return [1, 0, x & 0xFF, (x >> 8) & 0xFF, y & 0xFF, (y >> 8) & 0xFF]


def send_raw_report(report_data: list[int]) -> None:
    """Send a raw HID report if the mouse device is available."""
    global mouse_dev
    if mouse_dev:
        mouse_dev.write(report_data)


def move_mouse(x, y) -> bool:
    """Move the HID mouse by (x, y) units.

    Preserves the original behavior: lazy device reconnect via ensure_mouse_connected
    and clamping to the valid HID range.
    """
    global mouse_dev

    if not mouse_dev:
        if not ensure_mouse_connected():
            return False

    try:
        # Convert to integers and clamp to valid range for HID reports
        int_x = max(-127, min(127, int(round(x))))
        int_y = max(-127, min(127, int(round(y))))

        report = [1, 0, int_x & 0xFF, (int_x >> 8) & 0xFF, int_y & 0xFF, (int_y >> 8) & 0xFF]
        mouse_dev.write(report)
        return True
    except Exception as e:
        print(f"[-] Mouse move error: {e}")
        mouse_dev = None
        return False


def click_mouse(button: str = "left", duration: float = 0.05) -> bool:
    """Click mouse button using Arduino HID with minimal delay.

    Args:
        button: 'left' or 'right'.
        duration: How long to hold the button (seconds).
    """
    global mouse_dev, last_click_time

    try:
        if not mouse_dev:
            print("[-] Mouse device not initialized")
            return False

        # Minimal delay between clicks to avoid overwhelming the device
        current_time = time.time()
        time_since_last = current_time - last_click_time
        if time_since_last < 0.01:
            time.sleep(0.01 - time_since_last)

        if button == "left":
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(duration)
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
        elif button == "right":
            mouse_dev.write([1, 0x02, 0, 0, 0, 0])  # Button down
            time.sleep(duration)
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up

        last_click_time = time.time()
        return True
    except Exception as e:
        print(f"[-] Click error: {e}")
        return False


def rapid_click(clicks: int = 1, delay_between: float = 0.05) -> bool:
    """Perform rapid clicks for triggerbot behavior."""
    global mouse_dev

    if not mouse_dev:
        return False

    try:
        for i in range(clicks):
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(0.01)  # 10ms hold
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up

            if i < clicks - 1:
                time.sleep(delay_between)

        return True
    except Exception as e:
        print(f"[-] Rapid click error: {e}")
        return False


def ensure_mouse_connected() -> bool:
    """Ensure mouse device is connected, reconnect if needed.

    Uses the same fixed VID/PID as the original implementation.
    """
    global mouse_dev

    if mouse_dev is None:
        try:
            VENDOR_ID = 0x46D
            PRODUCT_ID = 0xC539
            get_mouse(VENDOR_ID, PRODUCT_ID)
            print("[+] Mouse device reconnected")
            return True
        except Exception as e:
            print(f"[-] Failed to reconnect mouse: {e}")
            return False
    return True


def move_and_click(x, y, button: str = "left", click_duration: float = 0.05) -> None:
    """Move mouse and click in one operation."""
    global mouse_dev
    try:
        if mouse_dev:
            move_mouse(x, y)
            time.sleep(0.01)
            click_mouse(button, click_duration)
    except Exception as e:
        print(f"[-] Move and click error: {e}")


def limit_xy(xy: int) -> int:
    if xy < -32767:
        return -32767
    if xy > 32767:
        return 32767
    return xy


def check_ping(dev: hid.device, ping_code: int) -> bool:
    dev.write([0, ping_code])
    resp = dev.read(max_length=1, timeout_ms=10)
    return bool(resp) and resp[0] == ping_code


def find_mouse_device(vid: int, pid: int, ping_code: int):
    """Enumerate HID devices and return the first matching, ping-responsive one."""
    global mouse_dev
    for dev_info in hid.enumerate(vid, pid):
        try:
            mouse_dev = hid.device()
            mouse_dev.open_path(dev_info["path"])
            if check_ping(mouse_dev, ping_code):
                return mouse_dev
            mouse_dev.close()
        except Exception as e:
            print(f"Error initializing device: {e}")
    return None


def get_mouse(vid: int, pid: int, ping_code: int = 249) -> None:
    """Initialize the global mouse_dev using VID/PID and optional ping code."""
    global mouse_dev
    mouse_dev = find_mouse_device(vid, pid, ping_code)
    if not mouse_dev:
        raise Exception(f"[-] Device Vendor ID: {hex(vid)}, Product ID: {hex(pid)} not found!")
    # Small no-op move to validate
    move_mouse(0, 0)
