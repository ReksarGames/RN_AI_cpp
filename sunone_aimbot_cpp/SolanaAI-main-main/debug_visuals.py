import threading
import queue
import time

import cv2
import numpy as np
import win32gui
import win32con


class CompactVisuals(threading.Thread):
    """Compact OpenCV debug window used for visualizing detections.

    Extracted from detector.py. This class is responsible only for
    displaying frames and handling GPU/CPU acceleration choices.
    """

    def __init__(self, cfg) -> None:
        super().__init__()

        self.cfg = cfg
        self.queue: "queue.Queue[np.ndarray | None]" = queue.Queue(maxsize=1)
        self.daemon = True
        self.name = "CompactVisuals"
        self.image = None
        self.running = False

        # Window settings
        self.window_width = getattr(cfg, "detection_window_width", 320)
        self.window_height = getattr(cfg, "detection_window_height", 320)
        self.window_name = getattr(cfg, "debug_window_name", "Solana Debug")
        self.scale_percent = getattr(cfg, "debug_window_scale_percent", 100)

        # GPU acceleration flags
        self.cuda_available = False
        self.opencl_available = False
        self.directx_available = False
        self.quicksync_available = False
        self.gpu_backend = "cpu"
        self.gpu_frame = None

        if getattr(cfg, "show_window", False):
            self.interpolation = cv2.INTER_NEAREST

    # ------------------------------------------------------------------
    # Public control API
    # ------------------------------------------------------------------
    def start_visuals(self) -> None:
        if getattr(self.cfg, "show_window", False) and not self.running:
            self.running = True
            if not self.is_alive():
                self.start()

    def stop_visuals(self) -> None:
        if self.running:
            self.running = False
            try:
                self.queue.put_nowait(None)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Thread loop
    # ------------------------------------------------------------------
    def run(self) -> None:  # type: ignore[override]
        try:
            if getattr(self.cfg, "show_window", False):
                self.spawn_debug_window()
                prev_frame_time = 0.0

            while self.running:
                try:
                    try:
                        self.image = self.queue.get(timeout=0.001)
                    except queue.Empty:
                        if getattr(self.cfg, "show_window", False):
                            key = cv2.pollKey() & 0xFF
                            if key == ord("q"):
                                self.running = False
                                break
                        continue

                    if self.image is None:
                        self.destroy()
                        break

                    if getattr(self.cfg, "show_window_fps", True):
                        new_frame_time = time.time()
                        if prev_frame_time > 0:
                            fps = 1.0 / (new_frame_time - prev_frame_time)
                            display_image = self.image.copy()
                            cv2.putText(
                                display_image,
                                f"FPS: {int(fps)}",
                                (10, 20),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 255, 0),
                                1,
                                cv2.LINE_AA,
                            )
                            self.image = display_image
                        prev_frame_time = new_frame_time

                    if getattr(self.cfg, "show_window", False):
                        self.display_frame_optimized()

                        key = cv2.pollKey() & 0xFF
                        if key == ord("q"):
                            self.running = False
                            break

                except Exception:
                    time.sleep(0.01)

        except Exception as e:
            print(f"Fatal error in compact visuals: {e}")
        finally:
            self.destroy()

    # ------------------------------------------------------------------
    # Window / GPU setup
    # ------------------------------------------------------------------
    def spawn_debug_window(self) -> None:
        cv2.namedWindow(self.window_name)
        print(f"[+] Debug window '{self.window_name}' created")
        self.setup_gpu_acceleration()
        self.set_window_properties()

    def setup_gpu_acceleration(self) -> None:
        try:
            gpu_backend_found = False

            # CUDA via CuPy + OpenCV
            try:
                import cupy as cp

                try:
                    device_count = cp.cuda.runtime.getDeviceCount()
                    if device_count > 0:
                        try:
                            cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
                            if cuda_devices > 0:
                                print(f"[+] CUDA devices detected: {cuda_devices}")
                                cv2.cuda.setDevice(0)

                                test_gpu_mat = cv2.cuda_GpuMat()
                                test_data = np.zeros((10, 10), dtype=np.uint8)
                                test_gpu_mat.upload(test_data)
                                _ = test_gpu_mat.download()

                                print("[+] CUDA acceleration enabled")
                                self.cuda_available = True
                                self.gpu_backend = "cuda"
                                gpu_backend_found = True
                            else:
                                print("[-] OpenCV CUDA support not available (no CUDA backend)")
                        except (AttributeError, Exception) as e:
                            print(f"[-] OpenCV CUDA not available: {e}")
                except Exception as e:
                    print(f"[-] CuPy CUDA check failed: {e}")
            except Exception:
                pass

            # OpenCL
            if not gpu_backend_found:
                try:
                    if cv2.ocl.haveOpenCL():
                        cv2.ocl.setUseOpenCL(True)
                        if cv2.ocl.useOpenCL():
                            test_mat = np.zeros((100, 100), dtype=np.uint8)
                            test_umat = cv2.UMat(test_mat)
                            _ = cv2.resize(test_umat, (50, 50))

                            self.cuda_available = False
                            self.opencl_available = True
                            self.gpu_backend = "opencl"
                            gpu_backend_found = True
                        else:
                            print("[-] OpenCL available but failed to enable")
                    else:
                        print("[-] OpenCL not available")
                except Exception as e:
                    print(f"[-] OpenCL setup error: {e}")

            # DirectX
            if not gpu_backend_found:
                try:
                    backends = cv2.videoio_registry.getBackends()
                    if cv2.CAP_DSHOW in backends or cv2.CAP_MSMF in backends:
                        print("[+] DirectX/DXVA acceleration available")
                        self.directx_available = True
                        self.gpu_backend = "directx"
                        gpu_backend_found = True
                except Exception as e:
                    print(f"[-] DirectX detection error: {e}")

            # Intel Quick Sync
            if not gpu_backend_found:
                try:
                    if hasattr(cv2, "videoio_registry"):
                        backends = cv2.videoio_registry.getBackends()
                        if cv2.CAP_INTEL_MFX in backends:
                            print("[+] Intel Quick Sync acceleration available")
                            self.quicksync_available = True
                            self.gpu_backend = "quicksync"
                            gpu_backend_found = True
                except Exception as e:
                    print(f"[-] Intel Quick Sync detection error: {e}")

            if not gpu_backend_found:
                print("[-] No GPU acceleration found, using optimized CPU")
                self.cuda_available = False
                self.opencl_available = False
                self.directx_available = False
                self.quicksync_available = False
                self.gpu_backend = "cpu"

                try:
                    cv2.setNumThreads(0)
                    cv2.setUseOptimized(True)
                    print("[+] Enhanced CPU optimizations enabled")
                except Exception:
                    pass
            else:
                print(f"[+] GPU acceleration active: {self.gpu_backend.upper()}")

        except Exception as e:
            print(f"[-] GPU setup error: {e}")
            self.cuda_available = False
            self.opencl_available = False
            self.directx_available = False
            self.quicksync_available = False
            self.gpu_backend = "cpu"

    def set_window_properties(self) -> None:
        if getattr(self.cfg, "debug_window_always_on_top", True):
            try:
                x = getattr(self.cfg, "spawn_window_pos_x", 100)
                y = getattr(self.cfg, "spawn_window_pos_y", 100)

                if x <= -1:
                    x = 0
                if y <= -1:
                    y = 0

                def set_window_properties_inner() -> None:
                    time.sleep(0.1)
                    try:
                        debug_window_hwnd = win32gui.FindWindow(None, self.window_name)
                        if debug_window_hwnd:
                            win32gui.SetWindowPos(
                                debug_window_hwnd,
                                win32con.HWND_TOPMOST,
                                x,
                                y,
                                self.window_width,
                                self.window_height,
                                0,
                            )
                    except Exception as e:
                        print(f"Window positioning error: {e}")

                threading.Thread(target=set_window_properties_inner, daemon=True).start()

            except Exception as e:
                print(f"Debug window setup error: {e}")

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def display_frame_optimized(self) -> None:
        try:
            if self.gpu_backend == "cuda" and self.cuda_available:
                self.display_with_cuda()
            elif self.gpu_backend == "opencl" and getattr(self, "opencl_available", False):
                self.display_with_opencl()
            elif self.gpu_backend == "directx" and getattr(self, "directx_available", False):
                self.display_with_directx()
            else:
                self.display_with_cpu_optimized()
        except Exception as e:
            print(f"Display error: {e}")
            self.display_with_cpu_optimized()

    def display_with_cuda(self) -> None:
        try:
            if self.gpu_frame is None:
                self.gpu_frame = cv2.cuda_GpuMat()

            self.gpu_frame.upload(self.image)

            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                gpu_resized = cv2.cuda_GpuMat()
                cv2.cuda.resize(self.gpu_frame, (width, height), gpu_resized, interpolation=cv2.INTER_LINEAR)
                resized_frame = gpu_resized.download()
                cv2.imshow(self.window_name, resized_frame)
            else:
                cpu_frame = self.gpu_frame.download()
                cv2.imshow(self.window_name, cpu_frame)

        except Exception as e:
            print(f"CUDA display error: {e}")
            self.cuda_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()

    def display_with_opencl(self) -> None:
        try:
            umat_image = cv2.UMat(self.image)

            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                umat_resized = cv2.resize(umat_image, (width, height), interpolation=cv2.INTER_LINEAR)
                resized_frame = umat_resized.get()
                cv2.imshow(self.window_name, resized_frame)
            else:
                cpu_frame = umat_image.get()
                cv2.imshow(self.window_name, cpu_frame)

        except Exception as e:
            print(f"OpenCL display error: {e}")
            self.opencl_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()

    def display_with_directx(self) -> None:
        try:
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                resized = cv2.resize(self.image, (width, height), interpolation=cv2.INTER_LINEAR_EXACT)
                cv2.imshow(self.window_name, resized)
            else:
                cv2.imshow(self.window_name, self.image)
        except Exception as e:
            print(f"DirectX display error: {e}")
            self.directx_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()

    def display_with_cpu_optimized(self) -> None:
        try:
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                resized = cv2.resize(self.image, (width, height), interpolation=cv2.INTER_NEAREST)
                cv2.imshow(self.window_name, resized)
            else:
                cv2.imshow(self.window_name, self.image)
        except Exception as e:
            print(f"CPU display error: {e}")
            self.running = False

    # ------------------------------------------------------------------
    # Frame update / teardown
    # ------------------------------------------------------------------
    def update_frame(self, frame) -> None:
        if self.running and frame is not None:
            try:
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                    except queue.Empty:
                        break

                try:
                    self.queue.put_nowait(frame.copy())
                except queue.Full:
                    pass
            except Exception:
                pass

    def destroy(self) -> None:
        cv2.destroyAllWindows()
        self.running = False
