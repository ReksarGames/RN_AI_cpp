import math
import queue
import threading
import tkinter as tk
from tkinter import Canvas
from typing import Any


class OverlayConfigBridge:
    """Bridge between config manager and overlay system.

    This wrapper expects a config_manager object exposing get_value,
    get_overlay_shape, and set_overlay_shape, matching the existing
    ConfigManager behavior in detector.py.
    """

    def __init__(self, config_manager: Any) -> None:
        self.config_manager = config_manager

    @property
    def show_overlay(self) -> bool:
        return self.config_manager.get_value("show_overlay", True)

    @property
    def overlay_show_borders(self) -> bool:
        return self.config_manager.get_value("overlay_show_borders", True)

    @property
    def overlay_shape(self) -> str:
        """Get overlay shape - 'circle' or 'square'."""

        return self.config_manager.get_overlay_shape()

    @property
    def circle_capture(self) -> bool:
        return self.config_manager.get_value("circle_capture", False)

    @property
    def fov(self) -> int:
        return self.config_manager.get_value("fov", 320)

    # Helper methods
    def is_circle_overlay(self) -> bool:
        return self.overlay_shape == "circle"

    def is_square_overlay(self) -> bool:
        return self.overlay_shape == "square"

    def set_overlay_shape(self, shape: str) -> bool:
        return self.config_manager.set_overlay_shape(shape)

    def get_all_overlay_settings(self) -> dict:
        return {
            "show_overlay": self.show_overlay,
            "overlay_show_borders": self.overlay_show_borders,
            "overlay_shape": self.overlay_shape,
            "circle_capture": self.circle_capture,
            "fov": self.fov,
        }


class Overlay:
    """Tkinter overlay window for drawing simple FOV/crosshair shapes."""

    def __init__(self, cfg: OverlayConfigBridge) -> None:
        self.cfg = cfg
        self.queue: "queue.Queue[tuple]" = queue.Queue()
        self.thread: threading.Thread | None = None
        self.border_id: int | None = None
        self.root: tk.Tk | None = None
        self.canvas: Canvas | None = None
        self.running = False

        # Skip frames so that the figures do not interfere with the detector
        self.frame_skip_counter = 0

        # New option for overlay shape - can be 'circle' or 'square'
        self.overlay_shape = getattr(cfg, "overlay_shape", "circle")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self, width: int, height: int) -> None:
        if not self.cfg.show_overlay:
            return

        self.running = True
        self.root = tk.Tk()

        self.root.overrideredirect(True)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")

        self.canvas = Canvas(self.root, bg="black", highlightthickness=0, cursor="none")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create mask based on shape
        if self.overlay_shape == "circle":
            self._create_circular_mask(width, height)
        else:
            self._create_square_mask(width, height)

        self._bind_events()

        if self.cfg.overlay_show_borders:
            self._create_border(width, height)

        self.process_queue()
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _bind_events(self) -> None:
        """Bind events to prevent interaction with overlay."""

        if not self.root or not self.canvas:
            return

        events = [
            "<Button-1>",
            "<Button-2>",
            "<Button-3>",
            "<Motion>",
            "<Key>",
            "<Enter>",
            "<Leave>",
            "<FocusIn>",
            "<FocusOut>",
        ]

        for event in events:
            self.root.bind(event, lambda e: "break")
            self.canvas.bind(event, lambda e: "break")

    def _create_circular_mask(self, width: int, height: int) -> None:
        """Create a circular mask by filling areas outside the circle with black."""

        if self.canvas is None or not self.running:
            return

        radius = min(width, height) // 2
        center_x = width // 2
        center_y = height // 2

        self.canvas.create_rectangle(0, 0, width, height, fill="black", outline="black", tags="mask")

        step = 2

        for y in range(0, height, step):
            for x in range(0, width, step):
                if self.canvas is None or not self.running:
                    return

                distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

                if distance > radius:
                    self.canvas.create_rectangle(
                        x,
                        y,
                        x + step,
                        y + step,
                        fill="black",
                        outline="black",
                        tags="mask",
                    )

    def _create_square_mask(self, width: int, height: int) -> None:
        """Create a square mask - no masking needed for square."""

        # For square overlay we allow full rect to show, so nothing to do.
        return

    def _create_border(self, width: int, height: int) -> None:
        """Create border based on overlay shape."""

        if self.canvas is None or not self.running:
            return

        if self.overlay_shape == "circle":
            radius = min(width, height) // 2
            center_x = width // 2
            center_y = height // 2
            self.border_id = self.canvas.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                outline="#c8a2c8",
                width=1,
                fill="",
                tags="border",
            )
        else:
            border_size = min(width, height)
            center_x = width // 2
            center_y = height // 2
            half_size = border_size // 2
            self.border_id = self.canvas.create_rectangle(
                center_x - half_size,
                center_y - half_size,
                center_x + half_size,
                center_y + half_size,
                outline="#c8a2c8",
                width=1,
                fill="",
                tags="border",
            )

    def process_queue(self) -> None:
        if not self.running or self.canvas is None:
            return

        try:
            self.frame_skip_counter += 1
            if self.frame_skip_counter % 3 == 0:
                if not self.queue.empty():
                    self._clear_drawings()
                    while not self.queue.empty() and self.running:
                        command, args = self.queue.get()
                        if self.canvas is not None:
                            command(*args)
                else:
                    self._clear_drawings()

            if self.root and self.running:
                self.root.after(2, self.process_queue)

        except Exception as e:  # pragma: no cover - defensive
            print(f"[-] Error in overlay process_queue: {e}")
            if self.running and self.root:
                self.root.after(10, self.process_queue)

    def _clear_drawings(self) -> None:
        if self.canvas is None or not self.running:
            return

        try:
            items = self.canvas.find_all()
            for item in items:
                if self.canvas is None or not self.running:
                    break

                try:
                    tags = self.canvas.gettags(item)
                    if item != self.border_id and "mask" not in tags and "border" not in tags:
                        self.canvas.delete(item)
                except Exception:
                    continue

        except Exception as e:  # pragma: no cover - defensive
            print(f"[-] Error clearing overlay drawings: {e}")

    # Drawing API -------------------------------------------------------
    def draw_square(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.running:
            self.queue.put((self._draw_square, (x1, y1, x2, y2, color, size)))

    def _draw_square(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.canvas and self.running:
            try:
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
            except Exception:
                pass

    def draw_oval(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.running:
            self.queue.put((self._draw_oval, (x1, y1, x2, y2, color, size)))

    def _draw_oval(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.canvas and self.running:
            try:
                self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)
            except Exception:
                pass

    def draw_line(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.running:
            self.queue.put((self._draw_line, (x1, y1, x2, y2, color, size)))

    def _draw_line(self, x1, y1, x2, y2, color: str = "white", size: int = 1) -> None:
        if self.canvas and self.running:
            try:
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)
            except Exception:
                pass

    def draw_point(self, x, y, color: str = "white", size: int = 1) -> None:
        if self.running:
            self.queue.put((self._draw_point, (x, y, color, size)))

    def _draw_point(self, x, y, color: str = "white", size: int = 1) -> None:
        if self.canvas and self.running:
            try:
                self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)
            except Exception:
                pass

    def draw_text(self, x, y, text: str, size: int = 12, color: str = "white") -> None:
        if self.running:
            self.queue.put((self._draw_text, (x, y, text, size, color)))

    def _draw_text(self, x, y, text: str, size: int, color: str) -> None:
        if self.canvas and self.running:
            try:
                self.canvas.create_text(x, y, text=text, font=("Arial", size), fill=color)
            except Exception:
                pass

    # Lifecycle ---------------------------------------------------------
    def show(self, width: int, height: int) -> None:
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(
                target=self.run,
                args=(width, height),
                daemon=True,
                name="Overlay",
            )
            self.thread.start()

    def stop(self) -> None:
        """Properly stop the overlay and its Tk loop."""

        self.running = False

        try:
            while not self.queue.empty():
                self.queue.get_nowait()
        except Exception:
            pass

        if self.root:
            try:
                self.root.quit()
            except Exception:
                pass
            self.root = None

        self.canvas = None
        self.border_id = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.thread = None

    def set_shape(self, shape: str) -> None:
        """Set overlay shape - 'circle' or 'square'."""

        if shape in ["circle", "square"]:
            self.overlay_shape = shape
        else:
            raise ValueError("Shape must be 'circle' or 'square'")
