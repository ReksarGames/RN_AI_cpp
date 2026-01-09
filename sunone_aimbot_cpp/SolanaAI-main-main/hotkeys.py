"""Hotkey handling utilities for the Solana AI PyQt6 GUI.

This module provides a single helper function that starts a background
thread which polls the configured global hotkeys (menu toggle and
stream-proof toggle) and invokes the corresponding methods on the
ConfigApp instance. The logic is extracted from ConfigApp.start_hotkey_listener
so it can live outside gui_app.py.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import win32api
from PyQt6.QtCore import QTimer, QMetaObject, Qt


def start_hotkey_listener(config_app: Any) -> threading.Thread:
    """Start a daemon thread that polls global hotkeys for *config_app*.

    The behaviour matches the original ConfigApp.start_hotkey_listener
    implementation:
    - Reads hotkey definitions from config_app.config_manager.get_config()["hotkeys"].
    - Toggles menu visibility and stream-proof mode on key transitions.
    - Uses QTimer.singleShot to execute UI updates on the Qt main thread.
    """

    def hotkey_loop() -> None:
        last_menu_key_state = False
        last_stream_key_state = False

        last_pause_state = False

        # Run until the owning ConfigApp signals shutdown
        while getattr(config_app, "hotkeys_running", True):
            try:
                # Get current hotkey from config
                current_config = config_app.config_manager.get_config()
                hotkey_config = current_config.get("hotkeys", {})

                # Parse keys
                menu_key_str = hotkey_config.get("menu_toggle_key", "0x76")
                stream_key_str = hotkey_config.get("stream_proof_key", "0x75")

                try:
                    menu_key = int(menu_key_str, 16) if isinstance(menu_key_str, str) else menu_key_str
                    stream_key = int(stream_key_str, 16) if isinstance(stream_key_str, str) else stream_key_str
                except Exception:
                    menu_key = 0x76  # F7
                    stream_key = 0x75  # F6

                # Check menu toggle key with proper state tracking
                menu_key_state = bool(win32api.GetAsyncKeyState(menu_key) & 0x8000)
                if menu_key_state and not last_menu_key_state:
                    QTimer.singleShot(0, config_app.toggle_visibility)
                    time.sleep(0.2)  # Debounce
                last_menu_key_state = menu_key_state

                # Check stream-proof key with proper state tracking
                stream_key_state = bool(win32api.GetAsyncKeyState(stream_key) & 0x8000)
                if stream_key_state and not last_stream_key_state:
                    QTimer.singleShot(0, config_app.toggle_stream_proof)
                    time.sleep(0.2)  # Debounce
                last_stream_key_state = stream_key_state

                # Global F3 pause/unpause for aimbot (VK_F3 = 0x72)
                pause_key = 0x72
                pause_state = bool(win32api.GetAsyncKeyState(pause_key) & 0x8000)
                if pause_state and not last_pause_state:
                    # Use Qt's queued connection mechanism so the slot runs
                    # safely on the main GUI thread.
                    try:
                        QMetaObject.invokeMethod(
                            config_app,
                            "toggle_aimbot_pause",
                            Qt.ConnectionType.QueuedConnection,
                        )
                    except Exception as e:
                        print(f"Hotkey pause invoke error: {e}")
                    time.sleep(0.2)  # Debounce
                last_pause_state = pause_state

                time.sleep(0.05)  # Check every 50ms
            except Exception as e:  # pragma: no cover - defensive
                print(f"Hotkey error: {e}")
                time.sleep(1)

    thread = threading.Thread(target=hotkey_loop, daemon=True)
    thread.start()
    return thread
