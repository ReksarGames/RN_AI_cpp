import os
import time
import ctypes


class AdvancedAntiDetection:
    """Various anti-detection helpers.

    Extracted from detector.py. These helpers are not currently wired into
    the main loop, but keeping them modular makes it easier to integrate
    or adjust later.
    """

    @staticmethod
    def randomize_timing() -> None:
        """Add randomized micro-delays to avoid extremely regular timing."""

        import random

        time.sleep(random.uniform(0.001, 0.003))

    @staticmethod
    def jitter_movement(x: float, y: float) -> tuple[float, float]:
        """Add subtle jitter to movement for more human-like behavior."""

        import random

        jitter_x = random.uniform(-0.5, 0.5)
        jitter_y = random.uniform(-0.5, 0.5)
        return x + jitter_x, y + jitter_y

    @staticmethod
    def check_virtual_machine() -> bool:
        """Best-effort check if running in a virtual machine (Windows only)."""

        if os.name != "nt":
            return False

        vm_signs = [
            "VMware",
            "VirtualBox",
            "Virtual",
            "Xen",
            "QEMU",
            "Hyper-V",
            "Parallels",
            "innotek GmbH",
        ]

        try:
            import wmi

            c = wmi.WMI()

            for bios in c.Win32_BIOS():
                for sign in vm_signs:
                    if sign.lower() in str(bios.Manufacturer).lower():
                        return True
                    if sign.lower() in str(bios.SerialNumber).lower():
                        return True

            for cs in c.Win32_ComputerSystem():
                for sign in vm_signs:
                    if sign.lower() in str(cs.Manufacturer).lower():
                        return True
                    if sign.lower() in str(cs.Model).lower():
                        return True

        except Exception:
            pass

        return False

    @staticmethod
    def check_sandbox() -> bool:
        """Basic sandbox environment heuristics."""

        sandbox_users = [
            "sandbox",
            "virus",
            "malware",
            "test",
            "john doe",
            "currentuser",
            "admin",
        ]

        current_user = os.getenv("USERNAME", "").lower()
        for user in sandbox_users:
            if user in current_user:
                return True

        sandbox_paths = [
            r"C:\\agent",
            r"C:\\sandbox",
            r"C:\\iDEFENSE",
            r"C:\\cuckoo",
        ]

        for path in sandbox_paths:
            if os.path.exists(path):
                return True

        return False

    @staticmethod
    def anti_dump() -> None:
        """Apply basic anti-dump mitigations on Windows."""

        if os.name != "nt":
            return

        try:
            kernel32 = ctypes.WinDLL("kernel32")

            # Set DEP policy
            DEP_ENABLE = 0x00000001
            kernel32.SetProcessDEPPolicy(DEP_ENABLE)

            # Disable SetUnhandledExceptionFilter
            kernel32.SetUnhandledExceptionFilter(None)

        except Exception as e:  # pragma: no cover - best-effort only
            print(f"Warning: Anti-dump error: {e}")
