import ctypes
import ctypes.wintypes as wintypes

import win32gui


class StreamProofManager:
    """Manages stream-proof functionality for Qt windows.

    Extracted from detector.py. Responsible only for marking windows as
    excluded from capture and restoring them.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.protected_windows: dict[int, dict] = {}
        self.qt_widgets = []  # Store Qt widget references

        # Windows constants
        self.WDA_NONE = 0x00000000
        self.WDA_EXCLUDEFROMCAPTURE = 0x00000011

        # Setup ctypes for SetWindowDisplayAffinity
        self.user32 = ctypes.windll.user32
        self.user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_qt_window(self, qt_widget) -> None:
        """Register a Qt window for stream-proof protection."""

        if qt_widget not in self.qt_widgets:
            self.qt_widgets.append(qt_widget)

    # ------------------------------------------------------------------
    # Public control API
    # ------------------------------------------------------------------
    def enable(self) -> bool:
        """Enable stream-proof mode."""

        if self.enabled:
            print("[!] Stream-proof already enabled")
            return True

        success = self._apply_stream_proof()
        if success:
            self.enabled = True
        else:
            print("[-] Failed to enable stream-proof mode")
            self.enabled = False
        return success

    def disable(self) -> None:
        """Disable stream-proof mode."""

        if not self.enabled:
            print("[!] Stream-proof already disabled")
            return

        self._remove_stream_proof()
        self.enabled = False

    def toggle(self) -> bool:
        """Toggle stream-proof mode and return new state."""

        try:
            import threading as _threading
            thread_name = _threading.current_thread().name
            print(f"[STREAM] toggle called (thread={thread_name}) enabled_before={self.enabled}")
        except Exception:
            pass

        if self.enabled:
            self.disable()
        else:
            self.enable()
        return self.enabled

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _apply_stream_proof(self) -> bool:
        """Apply stream-proof to registered windows."""

        try:
            found_windows = False

            # First, try Qt widget method
            for qt_widget in self.qt_widgets:
                if qt_widget and qt_widget.isVisible():
                    try:
                        hwnd = int(qt_widget.winId())
                        window_title = qt_widget.windowTitle()

                        result = self._apply_display_affinity(hwnd, window_title)
                        if result:
                            self.protected_windows[hwnd] = {
                                "title": window_title,
                                "qt_widget": qt_widget,
                                "method": "display_affinity",
                            }
                            found_windows = True
                        else:
                            # Try alternative Qt-specific protection
                            result = self.apply_qt_protection(qt_widget, window_title)
                            if result:
                                self.protected_windows[hwnd] = {
                                    "title": window_title,
                                    "qt_widget": qt_widget,
                                    "method": "qt_protection",
                                }
                                found_windows = True

                    except Exception as e:
                        print(f"[-] Error protecting Qt window: {e}")

            # Also search for Solana windows that might not be registered
            self._find_and_protect_additional_windows()

            return found_windows or len(self.protected_windows) > 0

        except Exception as e:  # pragma: no cover - defensive
            print(f"[-] Error in stream-proof application: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _apply_display_affinity(self, hwnd: int, title: str) -> bool:
        """Apply display affinity protection to a given window handle."""

        try:
            result = self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_EXCLUDEFROMCAPTURE)
            if result:
                return True

            # Fallback: WDA_MONITOR
            result = self.user32.SetWindowDisplayAffinity(hwnd, 0x00000001)
            if result:
                print(f"[+] Display affinity (monitor) applied to: {title}")
                return True

            error_code = ctypes.get_last_error()
            print(f"[-] SetWindowDisplayAffinity failed for {title}. Error: {error_code}")
            return False

        except Exception as e:
            print(f"[-] Display affinity error: {e}")
            return False

    def _apply_windows_display_affinity(self, w) -> None:
        try:
            import sys
            from ctypes import windll, wintypes as _wintypes

            if sys.platform != "win32":
                return

            hwnd = int(w.windowHandle().winId())
            WDA_EXCLUDEFROMCAPTURE = 0x11
            WDA_MONITOR = 0x01

            if not windll.user32.SetWindowDisplayAffinity(_wintypes.HWND(hwnd), WDA_EXCLUDEFROMCAPTURE):
                windll.user32.SetWindowDisplayAffinity(_wintypes.HWND(hwnd), WDA_MONITOR)
        except Exception:
            pass

    def _apply_on_gui(self, qt_widget, title: str) -> bool:
        from PyQt6.QtCore import Qt

        try:
            w = qt_widget.window()
            original_flags = w.windowFlags()
            w.setWindowFlags(original_flags | Qt.WindowType.Tool)
            w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

            was_visible = w.isVisible()
            if was_visible:
                w.hide()
            w.show()

            self._apply_windows_display_affinity(w)

            print(f"[+] Qt protection applied to: {title}")
            return True
        except Exception as e:
            print(f"[-] Qt protection error: {e}")
            return False

    def apply_qt_protection(self, qt_widget, title: str) -> bool:
        """Apply Qt-based stream-proof protection on the GUI thread."""

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt, QThread, QMetaObject

        app = QApplication.instance()
        if app is None:
            print("[-] Qt protection error: QApplication not yet created")
            return False

        if QThread.currentThread() != app.thread():
            from PyQt6.QtCore import Qt as QtCoreQt

            ok: list[bool] = []

            def _do() -> None:
                ok.append(self._apply_on_gui(qt_widget, title))

            QMetaObject.invokeMethod(app, _do, QtCoreQt.ConnectionType.QueuedConnection)
            app.processEvents()
            return bool(ok and ok[0])

        return self._apply_on_gui(qt_widget, title)

    def _find_and_protect_additional_windows(self) -> None:
        """Find and protect Solana windows not registered as Qt widgets."""

        try:
            protected_titles = [
                "Solana",  # Debug window
                "Solana Debug",  # Alternative debug window name
            ]

            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    try:
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title and hwnd not in self.protected_windows:
                            for title in protected_titles:
                                if title == window_title or title in window_title:
                                    print(
                                        f"[DEBUG] Found additional window: {window_title} (HWND: {hwnd})"
                                    )

                                    if self._apply_display_affinity(hwnd, window_title):
                                        self.protected_windows[hwnd] = {
                                            "title": window_title,
                                            "qt_widget": None,
                                            "method": "display_affinity",
                                        }
                                    break
                    except Exception:
                        pass
                return True

            win32gui.EnumWindows(enum_windows_callback, None)

        except Exception as e:
            print(f"[-] Error finding additional windows: {e}")

    def _remove_stream_proof(self) -> None:
        """Remove stream-proof from protected windows and restore Qt flags."""

        try:
            from PyQt6.QtCore import Qt

            for hwnd, info in list(self.protected_windows.items()):
                try:
                    if info["method"] == "display_affinity":
                        self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_NONE)

                    elif info["method"] == "qt_protection" and info["qt_widget"]:
                        qt_widget = info["qt_widget"]
                        if qt_widget:
                            flags = qt_widget.windowFlags()
                            qt_widget.setWindowFlags(flags & ~Qt.WindowType.Tool)
                            qt_widget.show()
                            print(f"[+] Qt protection removed from: {info['title']}")

                except Exception as e:
                    print(f"[-] Error removing protection from {info['title']}: {e}")

            self.protected_windows.clear()

        except Exception as e:  # pragma: no cover - defensive
            print(f"[-] Error removing stream-proof: {e}")
