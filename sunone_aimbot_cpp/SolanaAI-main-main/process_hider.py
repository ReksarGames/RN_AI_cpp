import os
import ctypes


class ProcessHider:
    """Hide process from task manager and process lists.

    This is a direct extraction of the original ProcessHider implementation
    from detector.py. It is intentionally conservative: process-critical
    features are disabled for safety.
    """

    def __init__(self) -> None:
        self.hidden = False
        if os.name == "nt":
            self.kernel32 = ctypes.WinDLL("kernel32")
            self.user32 = ctypes.WinDLL("user32")

    def hide_from_taskbar(self, hwnd: int) -> None:
        """Hide window from taskbar and Alt+Tab on Windows."""

        if os.name != "nt":
            return

        try:
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080

            ex_style = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style & ~WS_EX_APPWINDOW | WS_EX_TOOLWINDOW
            self.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            # Hide from Alt+Tab
            self.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            self.user32.ShowWindow(hwnd, 1)  # SW_SHOW

        except Exception as e:  # pragma: no cover - best-effort only
            print(f"Warning: Could not hide from taskbar: {e}")

    def set_process_critical(self) -> None:
        """DISABLED - This function would cause BSOD when process exits.

        Left here only to keep API compatibility with the original code.
        """

        print("[!] Process critical mode disabled for safety")

    def hide_process(self) -> None:
        """Apply lightweight "hiding" techniques (currently just priority tweak)."""

        if self.hidden:
            return

        if os.name == "nt":
            try:
                import psutil

                p = psutil.Process()
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            except Exception:
                # psutil may not be installed; this is best-effort.
                pass

            self.hidden = True
