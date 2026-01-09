# ============================================
# HIGH DPI SCALING SETUP - MUST BE FIRST
# ============================================
import os
import sys

os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'RoundPreferFloor'

from PyQt6.QtCore import Qt, QMetaObject
from PyQt6.QtWidgets import QApplication

QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor)

# ============================================
# STANDARD LIBRARY IMPORTS
# ============================================
import ctypes
import ctypes.wintypes as wintypes
import glob
import hashlib
import json
import math
import os
import platform
import queue
import random
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkFont
from ctypes import windll
from enum import Enum
from tkinter import Canvas
from typing import Any, Dict, List, Optional, Tuple
import binascii
import subprocess
from datetime import datetime, timezone, timedelta

# ============================================
# THIRD-PARTY IMPORTS
# ============================================
import cpuinfo
import cv2
import bettercam
import cupy as cp
import gpustat
import hid
import numpy as np
import requests
import torch
import torchvision
import torchvision.transforms as transforms
import urllib3
import win32api
import win32con
import win32gui
import win32security
from filterpy.kalman import KalmanFilter
from PIL import Image
from termcolor import colored
from ultralytics import YOLO
import qrcode
from discord_interactions import verify_key

# ============================================
# CONDITIONAL IMPORTS WITH ERROR HANDLING
# ============================================

if os.name == 'nt':
    try:
        import curses
        import wmi
    except ImportError:
        curses = None
        wmi = None

try:
    import pyfiglet
    import colorama
    from colorama import Fore
except ImportError:
    pyfiglet = None
    colorama = None
    Fore = None

# ============================================
# QT MESSAGE HANDLER - Define early
# ============================================
def qt_message_handler(mode, context, message):
    if "QPainter" in message:
        return
    print(message)

from PyQt6.QtCore import qInstallMessageHandler
qInstallMessageHandler(qt_message_handler)

# ============================================
# GLOBAL CONSTANTS AND CONFIGURATION
# ============================================
CONFIG_PATH = "lib/config/config.json"
DEV_MODE = True
CONTROLLER_MESSAGES_SHOWN = False
ENABLE_PROCESS_CRITICAL = False

# ============================================
# SECURITY CHECKS - MUST BE FIRST
# ============================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if is_admin():
    print("[!] Running as administrator")
    print("[!] Disabling critical process features for safety")
    ENABLE_PROCESS_CRITICAL = False
else:
    ENABLE_PROCESS_CRITICAL = False

def init_security():
    """Initialize all security measures at program start"""
    
    # 1. Anti-Debug Checks (Windows only)
    if os.name == 'nt':
        kernel32 = ctypes.WinDLL('kernel32')
        
        if kernel32.IsDebuggerPresent():
            print("Error code: 1")
            sys.exit(1)
        
        if 'pydevd' in sys.modules:
            print("Error code: 2")
            sys.exit(1)
        
        if sys.gettrace() is not None:
            print("Error code: 3")
            sys.exit(1)

init_security()

# ============================================
# UTILITY FUNCTIONS
# ============================================
def show_error_message(message: str) -> None:
    """Show Windows error message box"""
    MB_OK = 0
    MB_ICONERROR = 16
    ctypes.windll.user32.MessageBoxW(None, message, 'Error', MB_OK | MB_ICONERROR)

def make_request(url: str) -> bool:
    """Make HTTP request and handle errors"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as http_err:
        error_msg = f'HTTP error occurred: {http_err}'
        print(error_msg)
        show_error_message(error_msg)
        return False
    except requests.exceptions.ConnectionError as conn_err:
        error_msg = f'Connection error occurred: {conn_err}'
        return False
    except requests.exceptions.Timeout as timeout_err:
        error_msg = f'Timeout error occurred: {timeout_err}'
        print(error_msg)
        show_error_message(error_msg)
        return False
    except Exception as err:
        error_msg = f'Other error occurred: {err}'
        print(error_msg)
        show_error_message(error_msg)
        return False

def restart_program():
    print('Restarting, please wait...')
    executable = sys.executable
    os.execv(executable, ['python'] + sys.argv)

def check_installation_status():
    """Check if packages have been installed before"""
    marker_file = '.packages_installed'
    
    if os.path.exists(marker_file):
        try:
            with open(marker_file, 'r') as f:
                data = json.load(f)
                return data.get('installed', False)
        except:
            return False
    return False

def mark_installation_complete():
    """Mark that packages have been installed"""
    marker_file = '.packages_installed'
    
    data = {
        'installed': True,
        'installation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'python_version': sys.version
    }
    
    with open(marker_file, 'w') as f:
        json.dump(data, f, indent=2)

def check_critical_packages():
    """Quick check for critical packages to verify installation"""
    critical_packages = [
        'torch',
        'ultralytics',
        'cv2',
        'PyQt6',
        'bettercam'
    ]
    
    missing_packages = []
    for package in critical_packages:
        try:
            if package == 'cv2':
                import cv2
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def install_process():
    print('\nInstalling required packages, please wait...\n')
    
    requirements_content = """
matplotlib>=3.2.2
numpy==1.23.0
opencv-python>=4.1.2
Pillow
PyYAML>=5.3.1
scipy>=1.4.1
tqdm>=4.41.0
tensorboard>=2.4.1
seaborn>=0.11.0
pandas
PyQt5
PyQt6
filterpy
bettercam
dxcam
protobuf==4.21.0
ipython
ultralytics
pyserial

mss
pygame
pynput
pywin32
requests
wheel
termcolor
gpustat
py-cpuinfo
pyautogui
wmi
pyfiglet
hidapi
qrcode
discord_interactions
windows-curses
vgamepad
XInput-Python
customtkinter
tensorrt"""
    
    with open('temp_requirements.txt', 'w') as f:
        f.write(requirements_content)
    
    try:
        print('Installing packages from requirements...')
        os.system(f'{sys.executable} -m pip install -r temp_requirements.txt --no-cache-dir --disable-pip-version-check')
        
        os.remove('temp_requirements.txt')
        
        print('\nSuccessfully installed packages')
        
        mark_installation_complete()
        
        print('\nRestarting program...')
        time.sleep(1)
        restart_program()
        
    except Exception as e:
        print(f'Error during installation: {e}')
        if os.path.exists('temp_requirements.txt'):
            os.remove('temp_requirements.txt')

def initialize_packages():
    """Main function to handle package installation check"""
    if check_installation_status():
        packages_ok, missing = check_critical_packages()
        
        if packages_ok:
            return True
        else:
            print(f'Missing packages detected: {", ".join(missing)}')
            print('Reinstalling...')
            if os.path.exists('.packages_installed'):
                os.remove('.packages_installed')
            install_process()
            return False
    else:
        print('First time setup detected')
        install_process()
        return False

if not initialize_packages():
    sys.exit(0)

def qt_message_handler(mode, context, message):
    if "QPainter" in message:
        return
    print(message)

# ============================================
# PROCESS HIDING / ANTI-DETECTION / STREAM-PROOF / VISUALS IMPORTS
# ============================================
from process_hider import ProcessHider
from anti_detection import AdvancedAntiDetection
from stream_proof import StreamProofManager
from debug_visuals import CompactVisuals

from movement_curves import MovementCurveType, MovementCurves

import hid_mouse
from hid_mouse import move_mouse, click_mouse, rapid_click, ensure_mouse_connected, move_and_click, get_mouse
from anti_recoil import SmartArduinoAntiRecoil
from controller_handler import ControllerHandler
from triggerbot import Triggerbot
from flickbot import Flickbot

from overlay import OverlayConfigBridge, Overlay

class ConfigManager:
    """Manages configuration with real-time updates"""
    
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config_data = {}
        self.callbacks = []
        self.lock = threading.Lock()
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config_data = json.load(f)
                
                # Ensure kalman config exists
                if "kalman" not in self.config_data:
                    self.config_data["kalman"] = self.get_default_kalman_config()
                    self.save_config()

                # Ensure overlay_shape exists (for backward compatibility)
                if "overlay_shape" not in self.config_data:
                    self.config_data["overlay_shape"] = "circle"
                    self.save_config()

                # Ensure debug window config exists (for backward compatibility)
                if "show_debug_window" not in self.config_data:
                    self.config_data["show_debug_window"] = False
                    self.save_config()
            else:
                # Create default config if it doesn't exist
                self.config_data = self.get_default_config()
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config_data = self.get_default_config()
        return self.config_data
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "fov": 320,
            "sensitivity": 1.0,
            "aim_height": 50,
            "confidence": 0.3,
            "triggerbot": False,
            "keybind": "0x02",
            "mouse_method": "hid",
            "mouse_fov": {  # NEW: Add mouse FOV settings
                "mouse_fov_width": 40,
                "mouse_fov_height": 40,
                "use_separate_fov": False  # Toggle between unified FOV and separate X/Y
            },
            "custom_resolution": {
                "use_custom_resolution": False,
                "x": 1920,
                "y": 1080
            },
            "show_overlay": True,
            "overlay_show_borders": True,
            "overlay_shape": "circle",
            "circle_capture": False,
            "show_debug_window": False,
            "kalman": self.get_default_kalman_config(),
            "model": self.get_default_model_config(),
            "hotkeys": {
                "stream_proof_key": "0x75",  # F6
                "menu_toggle_key": "0x76",   # F7
                "stream_proof_enabled": False,
                "menu_visible": True
            },
            "anti_recoil": {
                "enabled": False,
                "strength": 5.0,
                "reduce_bloom": True,
                "require_target": True,
                "require_keybind": True
            },
            "triggerbot": {
                "enabled": False,
                "confidence": 0.5,
                "fire_delay": 0.05,
                "cooldown": 0.1,
                "require_aimbot_key": True
            },
            "flickbot": {
                "enabled": False,
                "flick_speed": 0.8,
                "flick_delay": 0.05,
                "cooldown": 1.0,
                "keybind": 0x05,
                "auto_fire": True,
                "return_to_origin": True
            },
            "target_lock": {
                "enabled": True,
                "min_lock_duration": 0.5,
                "max_lock_duration": 3.0,
                "distance_threshold": 100,
                "reacquire_timeout": 0.3,
                "smart_switching": True,
                "prefer_closest": True,
                "prefer_centered": False
        }
    }
    
    def get_default_model_config(self) -> Dict[str, Any]:
        """Return default model configuration"""
        return {
            "selected_model": "auto",  # auto, or specific model path
            "model_path": "",  # Path to currently loaded model
            "available_models": [],  # List of available models
            "auto_detect": True,  # Auto-detect best available model
            "model_size": "medium",  # small, medium, large
            "use_tensorrt": True,  # Prefer TensorRT models if available
            "model_confidence_override": None,  # Model-specific confidence threshold
            "model_iou_override": None  # Model-specific IOU threshold
        }
    
    def scan_for_models(self, models_dir: str = ".") -> List[Dict[str, Any]]:
        """Scan directory for available YOLO models"""
        models = []
        
        # Define model patterns to search for
        patterns = [
            "*.engine",  # TensorRT models
            "*.pt",      # PyTorch models
            "*.onnx",    # ONNX models
        ]
        
        for pattern in patterns:
            for model_path in glob.glob(os.path.join(models_dir, pattern)):
                model_info = {
                    "path": model_path,
                    "name": os.path.basename(model_path),
                    "type": os.path.splitext(model_path)[1][1:],  # Remove the dot
                    "size": os.path.getsize(model_path) / (1024 * 1024),  # Size in MB
                    "priority": self._get_model_priority(model_path)
                }
                models.append(model_info)
        
        # Sort by priority (higher is better)
        models.sort(key=lambda x: x["priority"], reverse=True)
        
        return models
    
    def _get_model_priority(self, model_path: str) -> int:
        """Get model priority for auto-selection"""
        priority = 0
        
        # TensorRT models have highest priority
        if model_path.endswith(".engine"):
            priority += 100
        
        # Solana models have high priority
        if "solana" in model_path.lower():
            priority += 50
        
        # Larger models typically have better accuracy
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        if size_mb > 100:
            priority += 30
        elif size_mb > 50:
            priority += 20
        elif size_mb > 20:
            priority += 10
        
        return priority
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        with self.lock:
            return self.config_data.get("model", self.get_default_model_config()).copy()
    
    def update_model_config(self, updates: Dict[str, Any]) -> bool:
        """Update model configuration"""
        return self.update_config({"model": updates})
    
    def get_selected_model(self) -> str:
        """Get currently selected model"""
        return self.get_value("model.selected_model", "auto")
    
    def set_selected_model(self, model_path: str) -> bool:
        """Set selected model"""
        # Update available models list
        models = self.scan_for_models()
        self.set_value("model.available_models", models)
        
        # Validate model exists if not "auto"
        if model_path != "auto":
            if not os.path.exists(model_path):
                print(f"Model not found: {model_path}")
                return False
        
        return self.set_value("model.selected_model", model_path)
    
    def get_best_available_model(self) -> Optional[str]:
        """Get the best available model based on priority"""
        models = self.scan_for_models()
        if not models:
            return None
        
        # Update available models in config
        self.set_value("model.available_models", models)
        
        # Return highest priority model
        return models[0]["path"]
    
    def get_model_for_loading(self) -> Optional[str]:
        """Get the model path to load based on configuration"""
        selected = self.get_selected_model()
        
        if selected == "auto":
            # Auto-detect best model
            return self.get_best_available_model()
        else:
            # Use specific model
            if os.path.exists(selected):
                return selected
            else:
                print(f"Selected model not found: {selected}, falling back to auto")
                return self.get_best_available_model()
    
    def get_model_specific_confidence(self) -> Optional[float]:
        """Get model-specific confidence threshold if set"""
        return self.get_value("model.model_confidence_override", None)
    
    def get_model_specific_iou(self) -> Optional[float]:
        """Get model-specific IOU threshold if set"""
        return self.get_value("model.model_iou_override", None)
    
    def set_model_overrides(self, confidence: Optional[float] = None, iou: Optional[float] = None) -> bool:
        """Set model-specific overrides"""
        updates = {}
        if confidence is not None:
            updates["model_confidence_override"] = confidence
        if iou is not None:
            updates["model_iou_override"] = iou
        
        if updates:
            return self.update_model_config(updates)
        return True
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        # Refresh the list
        models = self.scan_for_models()
        self.set_value("model.available_models", models)
        return models
    
    def get_default_kalman_config(self) -> Dict[str, Any]:
        """Return default Kalman filter configuration"""
        return {
            "use_kalman": True,
            "kf_p": 38.17,  # Initial covariance
            "kf_r": 2.8,    # Measurement noise
            "kf_q": 28.11,  # Process noise
            "kalman_frames_to_predict": 1.5,
            "use_coupled_xy": False,
            "xy_correlation": 0.3,
            "process_correlation": 0.2,
            "measurement_correlation": 0.1,
            "alpha_with_kalman": 1.5  # ADD THIS LINE
        }
    
    def get_default_movement_config(self) -> Dict[str, Any]:
        """Return default movement curves configuration optimized for speed"""
        return {
            "use_curves": False,
            "curve_type": "Exponential",  # Fastest curve type
            "movement_speed": 3.0,  # Increased from 1.0
            "smoothing_enabled": True,
            "smoothing_factor": 0.1,  # Reduced from 0.3 for less smoothing
            "random_curves": False,
            "curve_steps": 5,  # Reduced from 50 for faster execution
            "bezier_control_randomness": 0.1,  # Reduced for more direct movement
            "spline_smoothness": 0.2,  # Reduced
            "catmull_tension": 0.2,  # Reduced
            "exponential_decay": 3.0,  # Increased for faster ramp
            "hermite_tangent_scale": 0.5,  # Reduced
            "sine_frequency": 2.0  # Increased for quicker cycles
        }
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with self.lock:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(self.config_data, f, indent=4)
            
            # Notify all callbacks about the config change
            self.notify_callbacks()
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            with self.lock:
                # Handle nested updates like custom_resolution and kalman
                for key, value in updates.items():
                    if isinstance(value, dict) and key in self.config_data and isinstance(self.config_data[key], dict):
                        self.config_data[key].update(value)
                    else:
                        self.config_data[key] = value
            return self.save_config()
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        with self.lock:
            return self.config_data.copy()
    
    def get_value(self, key: str, default=None):
        """Get a specific config value"""
        with self.lock:
            # Handle nested keys (e.g., "kalman.use_kalman")
            if '.' in key:
                keys = key.split('.')
                value = self.config_data
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value
            return self.config_data.get(key, default)
    
    def set_value(self, key: str, value: Any) -> bool:
        """Set a specific config value"""
        # Handle nested keys
        if '.' in key:
            keys = key.split('.')
            updates = {}
            current = updates
            for i, k in enumerate(keys[:-1]):
                current[k] = {}
                current = current[k]
            current[keys[-1]] = value
            return self.update_config(updates)
        return self.update_config({key: value})
    
    def get_kalman_config(self) -> Dict[str, Any]:
        """Get Kalman filter configuration"""
        with self.lock:
            return self.config_data.get("kalman", self.get_default_kalman_config()).copy()
    
    def update_kalman_config(self, updates: Dict[str, Any]) -> bool:
        """Update Kalman filter configuration"""
        return self.update_config({"kalman": updates})
    
    # *** NEW: Movement configuration methods ***
    def get_movement_config(self) -> Dict[str, Any]:
        """Get movement curves configuration"""
        with self.lock:
            return self.config_data.get("movement", self.get_default_movement_config()).copy()
    
    def update_movement_config(self, updates: Dict[str, Any]) -> bool:
        """Update movement curves configuration"""
        return self.update_config({"movement": updates})
    
    def get_movement_curves_enabled(self) -> bool:
        """Get movement curves enabled state"""
        return self.get_value("movement.use_curves", False)
    
    def set_movement_curves_enabled(self, enabled: bool) -> bool:
        """Set movement curves enabled state"""
        return self.set_value("movement.use_curves", enabled)
    
    def get_movement_curve_type(self) -> str:
        """Get current movement curve type"""
        return self.get_value("movement.curve_type", "Bezier")
    
    def set_movement_curve_type(self, curve_type: str) -> bool:
        """Set movement curve type"""
        supported_curves = ["Bezier", "B-Spline", "Catmull", "Exponential", "Hermite", "Sine"]
        if curve_type not in supported_curves:
            print(f"Invalid curve type: {curve_type}. Must be one of {supported_curves}")
            return False
        return self.set_value("movement.curve_type", curve_type)
    
    def get_movement_speed(self) -> float:
        """Get movement speed multiplier"""
        return self.get_value("movement.movement_speed", 1.0)
    
    def set_movement_speed(self, speed: float) -> bool:
        """Set movement speed multiplier"""
        if speed <= 0:
            print("Movement speed must be greater than 0")
            return False
        return self.set_value("movement.movement_speed", speed)
    
    def get_random_curves_enabled(self) -> bool:
        """Get random curves enabled state"""
        return self.get_value("movement.random_curves", False)
    
    def set_random_curves_enabled(self, enabled: bool) -> bool:
        """Set random curves enabled state"""
        return self.set_value("movement.random_curves", enabled)
    
    def toggle_movement_curves(self) -> bool:
        """Toggle movement curves on/off"""
        current_state = self.get_movement_curves_enabled()
        new_state = not current_state
        success = self.set_movement_curves_enabled(new_state)
        if success:
            print(f"[+] Movement curves {'enabled' if new_state else 'disabled'}")
        return success
    
    def get_supported_curve_types(self) -> list:
        """Get list of supported curve types"""
        return ["Bezier", "B-Spline", "Catmull", "Exponential", "Hermite", "Sine"]
    
    def get_overlay_shape(self) -> str:
        """Get overlay shape configuration"""
        with self.lock:
            return self.config_data.get("overlay_shape", "circle")
        
    def set_overlay_shape(self, shape: str) -> bool:
        """Set overlay shape configuration"""
        if shape not in ["circle", "square"]:
            print(f"Invalid overlay shape: {shape}. Must be 'circle' or 'square'")
            return False
        return self.set_value("overlay_shape", shape)
    
    def is_overlay_circle(self) -> bool:
        """Check if overlay is set to circle"""
        return self.get_overlay_shape() == "circle"
    
    def is_overlay_square(self) -> bool:
        """Check if overlay is set to square"""
        return self.get_overlay_shape() == "square"
    
    # NEW DEBUG WINDOW METHODS
    def get_debug_window_enabled(self) -> bool:
        """Get debug window enabled state"""
        with self.lock:
            return self.config_data.get("show_debug_window", False)
    
    def set_debug_window_enabled(self, enabled: bool) -> bool:
        """Set debug window enabled state"""
        return self.set_value("show_debug_window", enabled)
    
    def toggle_debug_window(self) -> bool:
        """Toggle debug window on/off"""
        current_state = self.get_debug_window_enabled()
        new_state = not current_state
        success = self.set_debug_window_enabled(new_state)
        if success:
            print(f"[+] Debug window {'enabled' if new_state else 'disabled'}")
    
    def register_callback(self, callback):
        """Register a callback to be called when config changes"""
        self.callbacks.append(callback)
    
    def notify_callbacks(self):
        """Notify all registered callbacks about config changes"""
        for callback in self.callbacks:
            try:
                callback(self.config_data)
            except Exception as e:
                print(f"Error in config callback: {e}")

class TargetTracker:
    """Advanced target tracking with motion prediction"""
    
    def __init__(self):
        self.tracked_targets = {}  # Store target history for prediction
        self.max_history = 10  # Keep last 10 frames of target data
        
    def update_target(self, target_id, position, timestamp):
        """Update target tracking history"""
        if target_id not in self.tracked_targets:
            self.tracked_targets[target_id] = []
        
        self.tracked_targets[target_id].append({
            'position': position,
            'timestamp': timestamp
        })
        
        # Keep only recent history
        if len(self.tracked_targets[target_id]) > self.max_history:
            self.tracked_targets[target_id].pop(0)
    
    def predict_position(self, target_id, current_time):
        """Predict where the target will be based on motion history"""
        if target_id not in self.tracked_targets or len(self.tracked_targets[target_id]) < 2:
            return None
        
        history = self.tracked_targets[target_id]
        
        # Calculate velocity from last two positions
        last = history[-1]
        prev = history[-2]
        
        dt = last['timestamp'] - prev['timestamp']
        if dt <= 0:
            return last['position']
        
        vx = (last['position'][0] - prev['position'][0]) / dt
        vy = (last['position'][1] - prev['position'][1]) / dt
        
        # Predict position
        time_delta = current_time - last['timestamp']
        predicted_x = last['position'][0] + vx * time_delta
        predicted_y = last['position'][1] + vy * time_delta
        
        return (predicted_x, predicted_y)
    
    def cleanup_old_targets(self, current_time, timeout=2.0):
        """Remove targets that haven't been seen recently"""
        to_remove = []
        for target_id, history in self.tracked_targets.items():
            if history and current_time - history[-1]['timestamp'] > timeout:
                to_remove.append(target_id)
        
        for target_id in to_remove:
            del self.tracked_targets[target_id]

class AimbotController:
    """Controls the aimbot with dynamic config updates"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.running = False
        self.thread = None
        self.smoother = None
        self.model = None
        self.camera = None
        self.mouse_dev = None
        self.mouse_lock = threading.Lock()
        self.initialize_target_tracker()

         # Mouse FOV settings (NEW)
        self.mouse_fov_width = 40
        self.mouse_fov_height = 40
        self.use_separate_fov = False
        
        # DPI settings for calculation (NEW)
        self.dpi = 800  # Default DPI
        self.mouse_sensitivity = 1.0  # Windows mouse sensitivity

        # Add stream-proof manager
        self.stream_proof = StreamProofManager()

        # Hotkey settings
        self.menu_toggle_key = 0x76  # F7 by default
    
        # Menu visibility state
        self.menu_visible = True
        self.config_app_reference = None

        # Overlay components
        self.overlay = None
        self.overlay_initialized = False

        # Compact debug window
        self.visuals = None
        self.visuals_enabled = False

        # *** NEW: Movement curves integration ***
        self.movement_curves = MovementCurves()
        self.current_mouse_position = (0, 0)

        # Anti-recoil system (pass self to it)
        self.anti_recoil = SmartArduinoAntiRecoil(self)
        self.load_anti_recoil_config()

        # Target tracking for anti-recoil
        self.has_target = False
        self.last_target_time = 0

        self.triggerbot = Triggerbot(self)
        self.flickbot = Flickbot(self)
    
        # Load their configurations
        self.load_triggerbot_config()
        self.load_flickbot_config()

        # Add controller support
        self.controller = ControllerHandler(self)
        self.controller_enabled = False
    
        # Load controller config
        self.load_controller_config()
        
        # Current runtime settings
        self.fov = 320
        self.sensitivity = 1.0
        self.aim_height = 50
        self.confidence = 0.3
        self.keybind = "0x02"
        self.mouse_method = "hid"
        self.custom_resolution = {}
        self.overlay_shape = "circle"  # Track current overlay shape


        # *** NEW: Movement curve settings ***
        self.use_movement_curves = False
        self.movement_curve_type = "Bezier"
        self.movement_speed = 1.0
        self.curve_smoothing = True
        self.random_curves = False
        
        # Kalman settings
        self.kalman_config = {}
        self.use_kalman = True
        self.kalman_frames_to_predict = 1.5
        
        # Screen dimensions
        self.full_x = 1920
        self.full_y = 1080
        self.center_x = self.full_x // 2
        self.center_y = self.full_y // 2

        # Create overlay config bridge
        self.overlay_cfg = OverlayConfigBridge(self.config_manager)
        
        # Initialize overlay
        self.overlay = Overlay(self.overlay_cfg)
        
        # Register for config updates
        self.config_manager.register_callback(self.on_config_updated)
        self.load_current_config()

        # Visual state tracking for safe, serialized reconfiguration
        self._visual_state_lock = threading.Lock()
        self._last_visual_fov = self.fov
        self._last_visual_mouse_method = self.mouse_method
        self._last_show_overlay = self.show_overlay
        self._last_visuals_enabled = self.visuals_enabled
        self._last_overlay_shape = self.overlay_shape

        # Setup debug window
        self.setup_debug_window()

        self.target_lock = {
            'enabled': True,
            'current_target_id': None,
            'lock_time': 0,
            'min_lock_duration': 0.5,  # Minimum time to lock onto a target
            'max_lock_duration': 3.0,  # Maximum time before forcing target switch
            'distance_threshold': 100,  # Max distance target can move before lock breaks
            'last_target_position': None,
            'target_lost_time': 0,
            'reacquire_timeout': 0.3  # Time to wait before switching targets after losing one
        }
        
        # Load target lock config
        self.load_target_lock_config()

    def load_anti_recoil_config(self):
        """Load anti-recoil settings from config"""
        config = self.config_manager.get_config()
        anti_recoil_config = config.get('anti_recoil', {})
    
        self.anti_recoil.enabled = anti_recoil_config.get('enabled', False)
        self.anti_recoil.strength = anti_recoil_config.get('strength', 5.0)
        self.anti_recoil.reduce_bloom = anti_recoil_config.get('reduce_bloom', True)
        self.anti_recoil.require_target = anti_recoil_config.get('require_target', True)
        self.anti_recoil.require_keybind = anti_recoil_config.get('require_keybind', True)

    def initialize_target_tracker(self):
        """Initialize the target tracker"""
        self.target_tracker = TargetTracker()
    
        # Enhanced target lock configuration
        self.target_lock = {
            'enabled': True,
            'current_target_id': None,
            'lock_time': 0,
            'min_lock_duration': 0.8,
            'max_lock_duration': 5.0,
            'distance_threshold': 150,
            'last_target_position': None,
            'target_lost_time': 0,
            'reacquire_timeout': 0.5,
            'switch_threshold': 0.7,  # Target must be 30% closer to switch
            'target_velocity': (0, 0),  # Track target velocity
            'lock_strength': 1.0,  # How strongly to maintain lock (1.0 = full lock)
            'prediction_enabled': True,
            'sticky_radius': 50,  # Pixels around target to maintain sticky aim
        }

    def load_target_lock_config(self):
        """Load target lock settings from config"""
        config = self.config_manager.get_config()
        target_lock_config = config.get('target_lock', {})
        
        self.target_lock['enabled'] = target_lock_config.get('enabled', True)
        self.target_lock['min_lock_duration'] = target_lock_config.get('min_lock_duration', 0.5)
        self.target_lock['max_lock_duration'] = target_lock_config.get('max_lock_duration', 3.0)
        self.target_lock['distance_threshold'] = target_lock_config.get('distance_threshold', 100)
        self.target_lock['reacquire_timeout'] = target_lock_config.get('reacquire_timeout', 0.3)

    def find_closest_target_with_enhanced_lock(self, results):
        """Enhanced target locking with prediction and sticky aim"""
        if not self.target_lock['enabled']:
            return self.find_closest_target(results)
    
        current_time = time.time()
        targets = []
        fov_half = self.fov // 2
    
        # Clean up old tracked targets
        self.target_tracker.cleanup_old_targets(current_time)
    
        # Process detected targets
        for i, box in enumerate(results[0].boxes):
            x1, y1, x2, y2 = box.xyxy[0]
            height = y2 - y1
            width = x2 - x1
            head_x = (x1 + x2) / 2
            head_y = y1 + (height * (100 - self.aim_height) / 100)
        
            if x1 < 15 or x1 < self.fov / 5 or y2 > self.fov / 1.2:
                continue
        
            # Create stable ID based on position and size
            target_id = self.generate_stable_target_id(x1, y1, x2, y2)
        
            # Update tracker
            self.target_tracker.update_target(target_id, (head_x, head_y), current_time)
        
            dist = math.sqrt((head_x - fov_half) ** 2 + (head_y - fov_half) ** 2)
        
            targets.append({
                'id': target_id,
                'index': i,
                'position': (head_x, head_y),
                'distance': dist,
                'box': box,
                'bbox': (x1, y1, x2, y2),
                'confidence': box.conf[0].cpu().numpy() if hasattr(box.conf[0], 'cpu') else box.conf[0],
                'area': width * height
            })
    
        # Handle locked target
        if self.target_lock['current_target_id']:
            locked_target = self.find_locked_target_match(targets, current_time)
        
            if locked_target:
                # Check if we should maintain lock
                if self.should_maintain_lock(locked_target, targets, current_time):
                    # Apply prediction if enabled
                    if self.target_lock['prediction_enabled']:
                        predicted_pos = self.target_tracker.predict_position(
                            locked_target['id'], 
                            current_time + 0.016  # Predict 1 frame ahead (60fps)
                        )
                        if predicted_pos:
                            return predicted_pos
                
                    return locked_target['position']
                else:
                    # Switch to better target
                    self.clear_target_lock()
    
        # Acquire new target if needed
        if targets and not self.target_lock['current_target_id']:
            selected = self.select_best_target(targets)
            if selected:
                self.lock_onto_target(selected, current_time)
                return selected['position']
    
        return None

    def set_smoother(self, smoother):
        """Set the Kalman smoother - called from main to ensure same instance is used"""
        self.smoother = smoother
        #print("[+] Kalman smoother linked to aimbot controller")

    def generate_stable_target_id(self, x1, y1, x2, y2):
        """Generate a stable ID for target tracking"""
        # Round positions to reduce jitter
        grid_size = 10
        x1_rounded = int(x1 / grid_size) * grid_size
        y1_rounded = int(y1 / grid_size) * grid_size
        x2_rounded = int(x2 / grid_size) * grid_size
        y2_rounded = int(y2 / grid_size) * grid_size
    
        return f"{x1_rounded}_{y1_rounded}_{x2_rounded}_{y2_rounded}"

    def find_locked_target_match(self, targets, current_time):
        """Find the locked target with improved matching"""
        if not self.target_lock['last_target_position']:
            return None
    
        last_x, last_y = self.target_lock['last_target_position']
    
        # Use prediction to estimate where target should be
        if self.target_lock['prediction_enabled']:
            predicted_pos = self.target_tracker.predict_position(
                self.target_lock['current_target_id'], 
                current_time
            )
            if predicted_pos:
                last_x, last_y = predicted_pos
    
        # Find best matching target
        best_match = None
        best_score = float('inf')
    
        for target in targets:
            curr_x, curr_y = target['position']
        
            # Calculate match score (lower is better)
            position_dist = math.sqrt((curr_x - last_x) ** 2 + (curr_y - last_y) ** 2)
        
            # Give bonus to targets with similar confidence
            confidence_diff = 0
            if hasattr(self.target_lock, 'last_confidence'):
                confidence_diff = abs(target['confidence'] - self.target_lock.get('last_confidence', 0.5)) * 50
        
            score = position_dist + confidence_diff
        
            # Must be within threshold to be considered
            if position_dist < self.target_lock['distance_threshold'] and score < best_score:
                best_match = target
                best_score = score
    
        if best_match:
            # Update lock with new target info
            self.target_lock['last_confidence'] = best_match['confidence']
    
        return best_match

    def should_maintain_lock(self, locked_target, all_targets, current_time):
        """Determine if we should maintain the current lock"""
        lock_duration = current_time - self.target_lock['lock_time']
    
        # Always maintain lock during minimum duration
        if lock_duration < self.target_lock['min_lock_duration']:
            return True
    
        # Check if exceeded maximum duration
        if lock_duration > self.target_lock['max_lock_duration']:
            # Find best alternative
            best_alternative = min(all_targets, key=lambda x: x['distance'])
        
            # Only switch if alternative is significantly better
            if best_alternative['distance'] < locked_target['distance'] * self.target_lock['switch_threshold']:
                return False
    
        # Check sticky aim radius
        if self.target_lock.get('sticky_radius', 50) > 0:
            fov_center = self.fov // 2
            dist_from_center = math.sqrt(
                (locked_target['position'][0] - fov_center) ** 2 + 
                (locked_target['position'][1] - fov_center) ** 2
            )
        
            # If target is very close to crosshair, maintain strong lock
            if dist_from_center < self.target_lock['sticky_radius']:
                self.target_lock['lock_strength'] = 1.0
                return True
    
        return True

    def select_best_target(self, targets):
        """Select the best target based on multiple factors"""
        if not targets:
            return None
    
        preference = self.config_manager.get_value('target_lock.preference', 'closest')
    
        # Score each target
        for target in targets:
            score = 0
        
            # Distance score (closer is better)
            max_dist = math.sqrt(self.fov ** 2 + self.fov ** 2)
            dist_score = 1.0 - (target['distance'] / max_dist)
            score += dist_score * 0.5
        
            # Confidence score
            score += target['confidence'] * 0.3
        
            # Size score (larger targets are easier to track)
            max_area = self.fov * self.fov
            size_score = target['area'] / max_area
            score += size_score * 0.2
        
            target['score'] = score
    
        # Apply preference weighting
        if preference == 'closest':
            return min(targets, key=lambda x: x['distance'])
        elif preference == 'confidence':
            return max(targets, key=lambda x: x['confidence'])
        elif preference == 'largest':
            return max(targets, key=lambda x: x['area'])
        else:
            # Use combined score
            return max(targets, key=lambda x: x['score'])

    def lock_onto_target(self, target, current_time):
        """Lock onto a new target"""
        self.target_lock['current_target_id'] = target['id']
        self.target_lock['lock_time'] = current_time
        self.target_lock['last_target_position'] = target['position']
        self.target_lock['last_confidence'] = target['confidence']
        self.target_lock['target_lost_time'] = 0
        self.target_lock['lock_strength'] = 1.0

    def find_closest_target_with_lock(self, results):
        """Find closest target with improved locking logic"""
        if not self.target_lock['enabled']:
            # Use original logic if locking is disabled
            return self.find_closest_target(results)
    
        current_time = time.time()
        targets = []
        fov_half = self.fov // 2
    
        # Collect all valid targets with their IDs
        for i, box in enumerate(results[0].boxes):
            x1, y1, x2, y2 = box.xyxy[0]

            # Convert tensors to float if needed
            if hasattr(x1, 'item'):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            height = y2 - y1
            width = x2 - x1
            head_x = (x1 + x2) / 2
            head_y = y1 + (height * (100 - self.aim_height) / 100)
        
            # Only skip if completely outside FOV
            if head_x < 0 or head_x > self.fov or head_y < 0 or head_y > self.fov:
                continue

            # Skip tiny detections
            if width < 5 or height < 5:
                continue
        
            dist = math.sqrt((head_x - fov_half) ** 2 + (head_y - fov_half) ** 2)
        
            # Calculate a unique ID based on position and size (more stable than index)
            # This helps track the same target even if detection order changes
            target_id = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"
        
            targets.append({
                'id': target_id,
                'index': i,
                'position': (head_x, head_y),
                'distance': dist,
                'box': box,
                'bbox': (x1, y1, x2, y2)
            })
    
        if not targets:
            # No targets found - but don't wait if we recently lost the target
            if self.target_lock['current_target_id'] is not None:
                if self.target_lock['target_lost_time'] == 0:
                    self.target_lock['target_lost_time'] = current_time
            
                # Instead of returning None during reacquire timeout,
                # immediately look for a new target if timeout is short
                if current_time - self.target_lock['target_lost_time'] > 0.1:  # Reduced from reacquire_timeout
                    self.clear_target_lock()
            return None
    
        # Check if we have a locked target
        if self.target_lock['current_target_id'] is not None:
            locked_target = None
        
            # Try to find the locked target by matching position/size
            if self.target_lock['last_target_position']:
                last_x, last_y = self.target_lock['last_target_position']
            
                # Find the target that's closest to the last known position
                best_match = None
                best_match_dist = float('inf')
            
                for target in targets:
                    curr_x, curr_y = target['position']
                    position_dist = math.sqrt((curr_x - last_x) ** 2 + (curr_y - last_y) ** 2)
                
                    # Consider this the same target if it's within the distance threshold
                    if position_dist < self.target_lock['distance_threshold']:
                        if position_dist < best_match_dist:
                            best_match = target
                            best_match_dist = position_dist
            
                # Use a more lenient distance threshold
                if best_match and best_match_dist < self.target_lock['distance_threshold']:
                    locked_target = best_match
                    self.target_lock['current_target_id'] = locked_target['id']
                    self.target_lock['target_lost_time'] = 0  # Reset lost time
        
            # If we found our locked target, stick with it
            if locked_target:
                lock_duration = current_time - self.target_lock['lock_time']
            
                # Only switch targets if:
                # 1. We've exceeded max lock duration
                # 2. AND there's a significantly closer target (at least 30% closer)
                if lock_duration > self.target_lock['max_lock_duration']:
                    # Check if there's a much better target
                    closest_target = min(targets, key=lambda x: x['distance'])
                
                    # Only switch if the new target is significantly closer
                    if closest_target['distance'] < locked_target['distance'] * 0.7:
                        # Switch to the closer target
                        self.target_lock['current_target_id'] = closest_target['id']
                        self.target_lock['lock_time'] = current_time
                        self.target_lock['last_target_position'] = closest_target['position']
                        self.target_lock['target_lost_time'] = 0
                        return closest_target['position']
                    else:
                        # Reset lock timer but keep the same target
                        self.target_lock['lock_time'] = current_time
            
                # Maintain lock on current target
                self.target_lock['last_target_position'] = locked_target['position']
                self.target_lock['target_lost_time'] = 0
                return locked_target['position']
            else:
                self.clear_target_lock()
    
        # Need to acquire new target (either no lock or lock was cleared)
        if targets:
            # Smart target selection based on preference
            preference = self.config_manager.get_value('target_lock.preference', 'closest')
        
            if preference == 'closest':
                # Sort by distance and get closest
                targets.sort(key=lambda x: x['distance'])
                selected = targets[0]
            elif preference == 'centered':
                # Get most centered target
                selected = min(targets, key=lambda x: x['distance'])
            elif preference == 'largest':
                # Get largest target (by bounding box area)
                def get_area(t):
                    x1, y1, x2, y2 = t['bbox']
                    return (x2 - x1) * (y2 - y1)
                selected = max(targets, key=get_area)
            elif preference == 'confidence':
                # Get highest confidence target
                selected = max(targets, key=lambda x: x['box'].conf[0])
            else:
                # Default to closest
                targets.sort(key=lambda x: x['distance'])
                selected = targets[0]
        
            # Lock onto new target
            self.target_lock['current_target_id'] = selected['id']
            self.target_lock['lock_time'] = current_time
            self.target_lock['last_target_position'] = selected['position']
            self.target_lock['target_lost_time'] = 0
        
            return selected['position']
    
        return None
    
    def clear_target_lock(self):
        """Clear the current target lock"""
        self.target_lock['current_target_id'] = None
        self.target_lock['lock_time'] = 0
        self.target_lock['last_target_position'] = None
        self.target_lock['target_lost_time'] = 0

    def load_target_lock_config(self):
        """Load target lock settings from config with improved defaults"""
        config = self.config_manager.get_config()
        target_lock_config = config.get('target_lock', {})
    
        # Use better defaults for more stable locking
        self.target_lock['enabled'] = target_lock_config.get('enabled', True)
        self.target_lock['min_lock_duration'] = target_lock_config.get('min_lock_duration', 0.8)  # Increased from 0.5
        self.target_lock['max_lock_duration'] = target_lock_config.get('max_lock_duration', 5.0)  # Increased from 3.0
        self.target_lock['distance_threshold'] = target_lock_config.get('distance_threshold', 150)  # Increased from 100
        self.target_lock['reacquire_timeout'] = target_lock_config.get('reacquire_timeout', 0.5)  # Increased from 0.3
        self.target_lock['preference'] = target_lock_config.get('preference', 'closest')
    
        # Add new settings for better control
        self.target_lock['sticky_aim'] = target_lock_config.get('sticky_aim', True)
        self.target_lock['require_visibility'] = target_lock_config.get('require_visibility', True)
        self.target_lock['switch_threshold'] = target_lock_config.get('switch_threshold', 0.7)  # How much closer a target needs to be to switch (0.7 = 30% closer)
    
    def load_current_config(self):
        """Load current configuration into runtime variables"""
        config = self.config_manager.get_config()
        self.fov = config.get('fov', 320)
        self.sensitivity = config.get('sensitivity', 1.0)
        self.aim_height = config.get('aim_height', 50)
        self.confidence = config.get('confidence', 0.3)
        self.keybind = config.get('keybind', "0x02")
        self.mouse_method = config.get('mouse_method', "hid")
        self.custom_resolution = config.get('custom_resolution', {})
        self.show_overlay = config.get('show_overlay', True)
        self.overlay_shape = config.get('overlay_shape', 'circle')
        self.visuals_enabled = config.get('show_debug_window', False)

        # Load mouse FOV settings (NEW)
        mouse_fov_config = config.get('mouse_fov', {})
        self.mouse_fov_width = mouse_fov_config.get('mouse_fov_width', 15)
        self.mouse_fov_height = mouse_fov_config.get('mouse_fov_height', 12)
        self.use_separate_fov = mouse_fov_config.get('use_separate_fov', False)
        self.dpi = config.get('dpi', 1100)
        self.mouse_sensitivity = config.get('mouse_sensitivity', 1.0)

        # *** NEW: Load movement curve settings ***
        movement_config = config.get('movement', {
            'use_curves': False,
            'curve_type': 'Bezier',
            'movement_speed': 1.0,
            'smoothing_enabled': True,
            'random_curves': False
        })
        
        self.use_movement_curves = movement_config.get('use_curves', False)
        self.movement_curve_type = movement_config.get('curve_type', 'Bezier')
        self.movement_speed = movement_config.get('movement_speed', 1.0)
        self.curve_smoothing = movement_config.get('smoothing_enabled', True)
        self.random_curves = movement_config.get('random_curves', False)
        
        # Update movement curves configuration
        self.movement_curves.set_curve_type(self.movement_curve_type)
        
        # Load Kalman configuration
        self.kalman_config = config.get('kalman', {
            "use_kalman": True,
            "kf_p": 38.17,
            "kf_r": 2.8,
            "kf_q": 28.11,
            "kalman_frames_to_predict": 1.5
        })
        self.use_kalman = self.kalman_config.get('use_kalman', True)
        self.kalman_frames_to_predict = self.kalman_config.get('kalman_frames_to_predict', 1.5)
        
        # Update screen dimensions
        if self.custom_resolution.get('use_custom_resolution', False):
            self.full_x = self.custom_resolution.get('x', 1920)
            self.full_y = self.custom_resolution.get('y', 1080)
        else:
            self.full_x = windll.user32.GetSystemMetrics(0)
            self.full_y = windll.user32.GetSystemMetrics(1)
        
        self.center_x = self.full_x // 2
        self.center_y = self.full_y // 2

        # Update overlay shape if overlay exists
        if self.overlay:
            self.overlay.set_shape(self.overlay_shape)

    def calc_movement(self, target_x, target_y):
        """Calculate movement with mouse FOV adjustments - FIXED Kalman prediction scaling"""

        # --- 1. Offsets from screen centre ---
        left = (self.full_x - self.fov) // 2
        top = (self.full_y - self.fov) // 2

        offset_x = target_x - (self.fov // 2)
        offset_y = target_y - (self.fov // 2)

        # --- 2. Degrees‑per‑pixel scale ---
        if self.use_separate_fov:
            degrees_per_pixel_x = self.mouse_fov_width / self.fov
            degrees_per_pixel_y = self.mouse_fov_height / self.fov
        else:
            degrees_per_pixel_x = self.mouse_fov_width / self.fov
            degrees_per_pixel_y = self.mouse_fov_width / self.fov  # Use width for both when unified

        # --- 3. Raw movement in "degrees" ---
        mouse_move_x = offset_x * degrees_per_pixel_x
        mouse_move_y = offset_y * degrees_per_pixel_y

        # --- 4. Optional pre‑smoothing with FIXED alpha calculation ---
        if self.use_kalman:
            # Use alpha_with_kalman as a gain but keep it within a stable range [0, 1]
            alpha = self.kalman_config.get("alpha_with_kalman", 0.5)
        else:
            # Use a reasonable default for non-Kalman mode
            alpha = 0.3

        # Clamp alpha to [0.05, 1.0] to avoid overshoot/oscillation
        alpha = max(0.05, min(alpha, 1.0))
        
        if not hasattr(self, 'last_move_x'):
            self.last_move_x, self.last_move_y = 0.0, 0.0

        move_x = alpha * mouse_move_x + (1 - alpha) * self.last_move_x
        move_y = alpha * mouse_move_y + (1 - alpha) * self.last_move_y

        self.last_move_x, self.last_move_y = move_x, move_y

        # --- 5. Convert to mouse movement units ---
        move_x = (move_x / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * self.sensitivity
        move_y = (move_y / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * self.sensitivity

        return move_x, move_y

    def load_controller_config(self):
        """Load controller settings from config"""
        config = self.config_manager.get_config()
        controller_config = config.get('controller', {})
    
        self.controller_enabled = controller_config.get('enabled', False)
        self.controller.enabled = self.controller_enabled
        self.controller.sensitivity_multiplier = controller_config.get('sensitivity', 1.0)
        self.controller.deadzone = controller_config.get('deadzone', 0.15)
        self.controller.trigger_threshold = controller_config.get('trigger_threshold', 0.5)
        self.controller.aim_stick = controller_config.get('aim_stick', 'right')
        self.controller.activation_button = controller_config.get('activation_button', 'right_trigger')
        self.controller.hold_to_aim = controller_config.get('hold_to_aim', True)

    def load_triggerbot_config(self):
        """Load triggerbot settings from config"""
        config = self.config_manager.get_config()
    
        # Ensure we get a dictionary, not a boolean
        triggerbot_config = config.get('triggerbot', {})
        if not isinstance(triggerbot_config, dict):
            triggerbot_config = {}
    
        self.triggerbot.enabled = triggerbot_config.get('enabled', False)
        self.triggerbot.confidence_threshold = triggerbot_config.get('confidence', 0.5)
        self.triggerbot.fire_delay = triggerbot_config.get('fire_delay', 0.05)
        self.triggerbot.cooldown = triggerbot_config.get('cooldown', 0.1)
        self.triggerbot.require_aimbot_key = triggerbot_config.get('require_aimbot_key', False)
        self.triggerbot.keybind = triggerbot_config.get('keybind', 0x02)
        self.triggerbot.rapid_fire = triggerbot_config.get('rapid_fire', True)
        self.triggerbot.shots_per_burst = triggerbot_config.get('shots_per_burst', 1)

    def load_flickbot_config(self):
        """Load flickbot settings from config"""
        config = self.config_manager.get_config()
    
        # Ensure we get a dictionary, not a boolean
        flickbot_config = config.get('flickbot', {})
        if not isinstance(flickbot_config, dict):
            flickbot_config = {}
    
        self.flickbot.enabled = flickbot_config.get('enabled', False)
        self.flickbot.smooth_flick = flickbot_config.get('smooth_flick', False)
        self.flickbot.flick_speed = flickbot_config.get('flick_speed', 0.8)
        self.flickbot.flick_delay = flickbot_config.get('flick_delay', 0.05)
        self.flickbot.cooldown = flickbot_config.get('cooldown', 1.0)
        self.flickbot.keybind = flickbot_config.get('keybind', 0x05)
        self.flickbot.auto_fire = flickbot_config.get('auto_fire', True)
        self.flickbot.return_to_origin = flickbot_config.get('return_to_origin', True)

    def set_config_app(self, config_app):
        """Set reference to ConfigApp for menu toggling"""
        self.config_app_reference = config_app

    def reload_model(self):
        """Reload the model with new settings"""
        try:
            print("[+] Reloading model...")
            
            # Store the current running state
            was_running = self.running
            
            # Stop if running
            if was_running:
                self.stop()
                # Wait for thread to fully stop
                time.sleep(0.5)
            
            # Clear old model
            if self.model:
                del self.model
                self.model = None
                # Force garbage collection to free memory
                import gc
                gc.collect()
            
            # Get new model path from config manager
            model_path = self.config_manager.get_model_for_loading()
            
            if not model_path:
                raise Exception("No models found in directory")
            
            # Load the new model
            print(f"[+] Loading model: {model_path}")
            self.model = YOLO(model_path, task="detect", verbose=False)
            
            # Update config with loaded model path
            self.config_manager.set_value("model.model_path", model_path)
            
            # Apply model-specific overrides
            confidence_override = self.config_manager.get_model_specific_confidence()
            if confidence_override is not None:
                self.confidence = confidence_override
                #print(f"[+] Using model-specific confidence: {confidence_override}")
            
            iou_override = self.config_manager.get_model_specific_iou()
            if iou_override is not None:
                self.iou = iou_override
                #print(f"[+] Using model-specific IOU: {iou_override}")
            
            # Warm up the model
            if self.camera:
                frame = self.camera.grab()
                if frame is not None:
                    self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            print(f"[+] Model reloaded successfully")
            
            # Restart if was running
            if was_running:
                self.start()
            
            return True
            
        except Exception as e:
            print(f"[-] Error reloading model: {e}")
            # Try to restore previous state if something went wrong
            if was_running and not self.running:
                try:
                    self.start()
                except:
                    pass
            return False

    def setup_debug_window(self):
        """Setup compact debug window"""
        # Create compact config for debug window
        debug_cfg = type('DebugConfig', (), {
            'show_window': self.visuals_enabled,
            'show_window_fps': True,
            'detection_window_width': 320,
            'detection_window_height': 320,
            'debug_window_name': 'Solana',
            'debug_window_scale_percent': 100,
            'debug_window_always_on_top': True,
            'spawn_window_pos_x': 100,
            'spawn_window_pos_y': 100
        })()
        
        if self.visuals_enabled:
            self.visuals = CompactVisuals(debug_cfg)
            print(f"[+] Debug window configured - visuals_enabled: {self.visuals_enabled}")
    
    def on_config_updated(self, new_config: Dict[str, Any]):
        """Called when configuration is updated.

        Heavy work (overlay/debug window/camera reinit) is deferred to
        :meth:`apply_visual_config_changes`, which is scheduled onto the
        Qt main thread where possible.
        """
        # Store old values for comparison
        old_kalman_config = self.kalman_config.copy()
        old_use_kalman = self.use_kalman

        old_movement_curves = getattr(self, "use_movement_curves", False)
        old_curve_type = getattr(self, "movement_curve_type", "Bezier")
        old_anti_recoil_enabled = self.anti_recoil.enabled
        old_controller_enabled = self.controller_enabled if hasattr(self, "controller_enabled") else False

        # Reload feature-specific configs (lightweight)
        self.load_anti_recoil_config()
        self.load_triggerbot_config()
        self.load_flickbot_config()
        self.load_controller_config()

        # Reload core runtime config snapshot
        self.load_current_config()

        # Confidence comes from the just-saved config
        self.confidence = new_config.get("confidence", 0.3)

        # Keep controller wiring in sync (no GUI operations here)
        if self.running:
            if old_controller_enabled != self.controller_enabled:
                if self.controller_enabled:
                    self.controller.enabled = True
                    self.controller.start()
                else:
                    self.controller.stop()
                    self.controller.enabled = False

        # Anti-recoil start/stop is also safe to do here
        if self.running and self.mouse_method.lower() == "hid":
            if old_anti_recoil_enabled != self.anti_recoil.enabled:
                if self.anti_recoil.enabled:
                    self.anti_recoil.start()
                else:
                    self.anti_recoil.stop()

        # Movement curve setting changes (informational)
        if old_movement_curves != self.use_movement_curves:
            print(f"[+] Movement curves {'enabled' if self.use_movement_curves else 'disabled'}")

        if old_curve_type != self.movement_curve_type:
            print(f"[+] Movement curve type changed to: {self.movement_curve_type}")

        # Kalman configuration changes (no heavy GUI work here)
        if old_kalman_config != self.kalman_config:
            print(f"[+] Kalman configuration changed:")
            print(f"    Old config: {old_kalman_config}")
            print(f"    New config: {self.kalman_config}")
            if self.smoother:
                print(f"    Smoother exists: {type(self.smoother)}")
                try:
                    smoother_config = self.smoother.kalman_config
                    print(f"    Smoother's config: {smoother_config}")
                except Exception:
                    pass
            else:
                print("    No smoother available!")

        if old_use_kalman != self.use_kalman:
            print(f"[+] Kalman filtering {'enabled' if self.use_kalman else 'disabled'}")

        # Schedule heavy visual/camera reconfiguration
        try:
            import threading as _threading
            print(f"[CFG] on_config_updated scheduling visual changes (thread={_threading.current_thread().name})")
        except Exception:
            pass

        if getattr(self, "config_app_reference", None) is not None:
            try:
                QMetaObject.invokeMethod(
                    self.config_app_reference,
                    "apply_visual_config_from_backend",
                    Qt.ConnectionType.QueuedConnection,
                )
            except Exception as e:
                print(f"[-] Failed to schedule visual config via Qt: {e}")
                self.apply_visual_config_changes()
        else:
            self.apply_visual_config_changes()

    def apply_visual_config_changes(self):
        """Apply overlay/debug/camera visual changes in a serialized, thread-safe way.

        Intended to run on the Qt main thread (via ConfigApp), but safe to
        call from any thread. It does not block with time.sleep.
        """
        try:
            import threading as _threading
            print(f"[VISUAL] apply_visual_config_changes on thread={_threading.current_thread().name}")
        except Exception:
            pass

        lock = getattr(self, "_visual_state_lock", None)
        if lock is None:
            import threading as _threading
            lock = _threading.Lock()
            self._visual_state_lock = lock

        with lock:
            old_fov = getattr(self, "_last_visual_fov", self.fov)
            old_method = getattr(self, "_last_visual_mouse_method", self.mouse_method)
            old_show_overlay = getattr(self, "_last_show_overlay", self.show_overlay)
            old_visuals_enabled = getattr(self, "_last_visuals_enabled", self.visuals_enabled)
            old_overlay_shape = getattr(self, "_last_overlay_shape", self.overlay_shape)

            new_fov = self.fov
            new_method = self.mouse_method
            new_show_overlay = self.show_overlay
            new_visuals_enabled = self.visuals_enabled
            new_overlay_shape = self.overlay_shape

            # Update stored state
            self._last_visual_fov = new_fov
            self._last_visual_mouse_method = new_method
            self._last_show_overlay = new_show_overlay
            self._last_visuals_enabled = new_visuals_enabled
            self._last_overlay_shape = new_overlay_shape

        # Gating: don't run overlay & debug window together
        if new_show_overlay and new_visuals_enabled:
            print("[VISUAL] Both overlay and debug window enabled; disabling debug window to avoid conflicts.")
            new_visuals_enabled = False
            self.visuals_enabled = False
            try:
                self.config_manager.set_value("show_debug_window", False)
            except Exception as e:
                print(f"[-] Failed to update show_debug_window in config: {e}")

        # Overlay shape change
        if old_overlay_shape != new_overlay_shape:
            print(f"[VISUAL] Overlay shape changed: {old_overlay_shape} -> {new_overlay_shape}")
            try:
                self.update_overlay_shape()
            except Exception as e:
                print(f"[-] Error updating overlay shape: {e}")

        # Overlay visibility toggle
        if old_show_overlay != new_show_overlay:
            print(f"[VISUAL] Overlay visibility changed: {old_show_overlay} -> {new_show_overlay}")
            try:
                if new_show_overlay:
                    self.start_overlay()
                else:
                    self.stop_overlay()
            except Exception as e:
                print(f"[-] Error toggling overlay: {e}")

        # Overlay FOV change
        if self.overlay_initialized and old_fov != new_fov:
            print(f"[VISUAL] FOV changed with overlay active: {old_fov} -> {new_fov}, restarting overlay")
            try:
                self.stop_overlay()
                self.start_overlay()
            except Exception as e:
                print(f"[-] Error restarting overlay after FOV change: {e}")

        # Debug window visibility
        if old_visuals_enabled != new_visuals_enabled:
            print(f"[VISUAL] Debug window changed: {old_visuals_enabled} -> {new_visuals_enabled}")
            try:
                if new_visuals_enabled:
                    self.start_debug_window()
                else:
                    self.stop_debug_window()
            except Exception as e:
                print(f"[-] Error toggling debug window: {e}")

        # Camera/mouse re-init on fov/method change
        if self.running and (old_fov != new_fov or old_method != new_method):
            print("[VISUAL] Reinitializing components due to FOV or mouse_method change")
            try:
                self.reinitialize_components()
            except Exception as e:
                print(f"[-] Error reinitializing components: {e}")

    def get_supported_curves(self):
        """Get list of supported movement curves"""
        return self.movement_curves.get_supported_curves()
    
    def set_movement_curve_type(self, curve_type: str):
        """Set the movement curve type"""
        if self.movement_curves.set_curve_type(curve_type):
            self.movement_curve_type = curve_type
            # Update config
            movement_config = self.config_manager.get_config().get('movement', {})
            movement_config['curve_type'] = curve_type
            self.config_manager.update_config({'movement': movement_config})
            print(f"[+] Movement curve set to: {curve_type}")
            return True
        return False
    
    def toggle_movement_curves(self):
        """Toggle movement curves on/off"""
        self.use_movement_curves = not self.use_movement_curves
        # Update config
        movement_config = self.config_manager.get_config().get('movement', {})
        movement_config['use_curves'] = self.use_movement_curves
        self.config_manager.update_config({'movement': movement_config})
        print(f"[+] Movement curves {'enabled' if self.use_movement_curves else 'disabled'}")

    def set_curve_speed_preset(self, preset: str):
        """Set curve speed preset: 'aimlock', 'fast', 'medium', 'slow'"""
        presets = {
            'aimlock': {
                'movement_speed': 5.0,
                'smoothing_factor': 0.05,
                'curve_steps': 3,
                'curve_type': 'Exponential'
            },
            'fast': {
                'movement_speed': 3.0,
                'smoothing_factor': 0.1,
                'curve_steps': 5,
                'curve_type': 'Bezier'
            },
            'medium': {
                'movement_speed': 1.5,
                'smoothing_factor': 0.2,
                'curve_steps': 10,
                'curve_type': 'Sine'
            },
            'slow': {
                'movement_speed': 0.8,
                'smoothing_factor': 0.3,
                'curve_steps': 20,
                'curve_type': 'Catmull'
            }
        }
    
        if preset in presets:
            settings = presets[preset]
            movement_config = self.config_manager.get_movement_config()
            movement_config.update(settings)
            self.config_manager.update_movement_config(movement_config)
            print(f"[+] Curve speed set to: {preset}")
        else:
            print(f"[-] Unknown preset: {preset}")


    def optimize_kalman_for_responsiveness(self):
        """Call this to make Kalman more responsive"""
        responsive_config = {
            "use_kalman": True,
            "kf_p": 15.0,  # Lower for more responsive
            "kf_r": 1.0,   # Lower for more direct
            "kf_q": 10.0,  # Lower for less prediction
            "kalman_frames_to_predict": 0.5,  # Minimal prediction
            "alpha_with_kalman": 0.8  # Lower alpha
        }
        self.config_manager.update_kalman_config(responsive_config)

    def optimize_for_speed(self):
        """Optimize all settings for maximum speed while using curves"""
        # Movement settings
        movement_config = {
            "use_curves": True,
            "curve_type": "Exponential",
            "movement_speed": 5.0,
            "smoothing_enabled": True,
            "smoothing_factor": 0.05,
            "random_curves": False,
            "curve_steps": 3,
            "bezier_control_randomness": 0.05,
            "exponential_decay": 4.0
        }
        self.config_manager.update_movement_config(movement_config)
    
        # Update sensitivity
        self.config_manager.set_value("sensitivity", 2.0)
    
        print("[+] Settings optimized for maximum speed with curves")

    def start_debug_window(self):
        """Start the debug window"""
        if not self.visuals_enabled:
            return
            
        # Always create a new instance to avoid thread reuse issues
        if self.visuals:
            self.visuals.stop_visuals()
            
        self.setup_debug_window()
        
        if self.visuals:
            print(f"[+] Starting debug window visuals thread...")
            self.visuals.start_visuals()
            print(f"[+] Debug window thread started: {self.visuals.is_alive()}")

    def stop_debug_window(self):
        """Stop the debug window"""
        if self.visuals:
            self.visuals.stop_visuals()

    def update_overlay_shape(self):
        """Update overlay shape without restarting the overlay"""
        if self.overlay:
            try:
                self.overlay.set_shape(self.overlay_shape)
                #print(f"[+] Overlay shape updated to: {self.overlay_shape}")
                
                # If overlay is currently running, restart it to apply the new shape
                if self.overlay_initialized:
                    #print("[+] Restarting overlay to apply new shape...")
                    self.stop_overlay()
                    time.sleep(0.2)  # Increased pause to ensure clean shutdown
                    self.start_overlay()
                    
            except Exception as e:
                print(f"[-] Error updating overlay shape: {e}")

    def get_overlay_dimensions(self):
        """Get overlay dimensions based on shape"""
        if self.overlay_shape == "circle":
            # For circle, use square dimensions
            return self.fov, self.fov
        else:  # square
            # For square, you might want different dimensions
            # or keep it square for consistency
            return self.fov, self.fov
        
    def reinitialize_components(self):
        """Reinitialize camera and mouse with new settings"""
        try:
            # Reinitialize camera with new FOV
            if self.camera:
                left = (self.full_x - self.fov) // 2
                top = (self.full_y - self.fov) // 2
                
                # Release old camera
                self.camera.release()
                
                # Create new camera with updated settings
                self.camera = StealthCapture(fov=self.fov, left=left, top=top)
                print(f"[+] Anti-cheat safe capture reinitialized with FOV: {self.fov}")
            
            # Reinitialize mouse if method changed
            if self.mouse_method.lower() == "hid":
                ensure_mouse_connected()
            
        except Exception as e:
            print(f"[-] Error reinitializing components: {e}")
    
    def initialize_components(self):
        """Initialize Solana components with model selection"""
        try:
            # DON'T create a new smoother here if one was already set
            if self.smoother is None:
                print("[!] No smoother provided, creating new one")
                self.smoother = KalmanSmoother(self.config_manager)
            else:
                print("[+] Using provided Kalman smoother")
        
            # Only initialize model if it hasn't been loaded yet
            if self.model is None:
                # Get model path from config manager
                model_path = self.config_manager.get_model_for_loading()
            
                if not model_path:
                    raise Exception("No models found in directory")
            
                # Load the selected model
                print(f"[+] Loading model: {model_path}")
                self.model = YOLO(model_path, task="detect", verbose=False)
            
                # Update config with loaded model path
                self.config_manager.set_value("model.model_path", model_path)
            
                # Get model-specific overrides
                confidence_override = self.config_manager.get_model_specific_confidence()
                if confidence_override is not None:
                    self.confidence = confidence_override
            
                iou_override = self.config_manager.get_model_specific_iou()
                if iou_override is not None:
                    self.iou = iou_override
        
            # Initialize anti-cheat safe camera
            left = (self.full_x - self.fov) // 2
            top = (self.full_y - self.fov) // 2
        
            self.camera = StealthCapture(fov=self.fov, left=left, top=top)
            print("[+] Anti-cheat safe capture started")
        
            # Initialize mouse if using HID
            if self.mouse_method.lower() == "hid":
                self.initialize_mouse()
        
            # Warm up the model
            frame = self.camera.grab()
            if frame is not None:
                self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
        
            print(f"[+] All components initialized successfully")
        
        except Exception as e:
            print(f"[-] Error initializing components: {e}")
            raise

    def get_current_model_info(self):
        """Get information about the currently loaded model"""
        model_path = self.config_manager.get_value("model.model_path", "Not loaded")
        
        if model_path != "Not loaded" and self.model is not None:
            return {
                "loaded": True,
                "path": model_path,
                "name": os.path.basename(model_path),
                "confidence": self.confidence,
                "iou": getattr(self, 'iou', 0.1)
            }
        else:
            return {
                "loaded": False,
                "path": "Not loaded",
                "name": "None",
                "confidence": self.confidence,
                "iou": 0.1
            }
    
    def initialize_mouse(self):
        """Initialize HID mouse"""
        try:
            VENDOR_ID = 0x46D
            PRODUCT_ID = 0xC539
            get_mouse(VENDOR_ID, PRODUCT_ID)
            print("[+] HID mouse initialized")
            return True
        except Exception as e:
            print(f"[-] Error initializing HID mouse: {e}")
            return False

    def start_overlay(self):
        """Start the overlay system"""
        if self.overlay_initialized or not self.show_overlay:
            return
        
        try:
            #print(f"[+] Starting {self.overlay_shape} overlay...")
            
            # Create new overlay instance to ensure clean state
            self.overlay = Overlay(self.overlay_cfg)
            
            # Ensure overlay has the correct shape before starting
            self.overlay.set_shape(self.overlay_shape)
            
            # Get dimensions based on overlay shape
            width, height = self.get_overlay_dimensions()
            
            self.overlay.show(width, height)
            self.overlay_initialized = True
            #print(f"[+] {self.overlay_shape.capitalize()} overlay started successfully")
        except Exception as e:
            print(f"[-] Error starting overlay: {e}")
            self.overlay_initialized = False

    def toggle_overlay_shape(self):
        """Toggle between circle and square overlay shapes"""
        new_shape = "square" if self.overlay_shape == "circle" else "circle"
        self.config_manager.set_overlay_shape(new_shape)
        print(f"[+] Overlay shape toggled to: {new_shape}")

    def stop_overlay(self):
        """Stop the overlay system"""
        if not self.overlay_initialized:
            return
        
        try:
            #print("[+] Stopping overlay...")
            self.overlay_initialized = False  # Set this first to prevent any new operations
            
            if self.overlay:
                self.overlay.stop()
                # Give it time to properly clean up
                time.sleep(0.1)
                
            #print("[+] Overlay stopped successfully")
        except Exception as e:
            print(f"[-] Error stopping overlay: {e}")
        finally:
            # Always mark as not initialized
            self.overlay_initialized = False
    
    def start(self):
        """Start the SolanaAi"""
        if self.running:
            print("[!] Solana Ai is already running!")
            return False
        
        self.running = True
        self.paused = False
        self.should_exit = False

        # Start controller if enabled
        if self.controller_enabled:
            self.controller.enabled = True
            self.controller.start()
        
        # Start overlay if enabled
        if self.show_overlay:
            self.start_overlay()

        # Start debug window if enabled
        if self.visuals_enabled:
            self.start_debug_window()

        # Start anti-recoil if enabled and using HID
        if self.anti_recoil.enabled and self.mouse_method.lower() == "hid":
            self.anti_recoil.start()

        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

        window_status = []
        if self.show_overlay:
            window_status.append(f"{self.overlay_shape} overlay")
        if self.visuals_enabled:
            window_status.append("debug window")
        if self.use_movement_curves:
            window_status.append(f"{self.movement_curve_type} curves")
        
        status_text = " and ".join(window_status) if window_status else "no visual components"
        #print(f"[+] Solana AI started with {status_text}")
        return True
    
    def stop(self):
        """Stop the Solana Ai"""
        if not self.running:
            print("[!] Solana Ai is not running!")
            return
        
        print("[+] Stopping Solana Ai...")
        self.running = False
        self.should_exit = True  # Set exit flag

        # Stop controller
        if self.controller:
            self.controller.stop()

        # Stop anti-recoil
        self.anti_recoil.stop()

        # Stop visual components
        self.stop_debug_window()

        # Stop overlay
        self.stop_overlay()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)  # Increased timeout
            if self.thread.is_alive():
                print("[!] Warning: Solana Ai thread did not stop cleanly")
        
        # Clean up resources
        self.cleanup_resources()
        
        print("[+] Solana Ai stopped successfully")

    def toggle_pause(self):
        """Toggle paused state for aiming/triggerbot while keeping capture running."""
        if not self.running:
            # Ignore pause toggles when not running
            return
        self.paused = not self.paused
        state = "paused" if self.paused else "unpaused"
        print(f"[+] Aimbot {state}")

    def cleanup_resources(self):
        """Clean up all resources"""
        if self.camera:
            try:
                self.camera.release()
                self.camera = None
            except Exception as e:
                print(f"[-] Error releasing camera: {e}")
        
        if self.model:
            try:
                # Clear model from memory if possible
                self.model = None
            except Exception as e:
                print(f"[-] Error clearing model: {e}")
        
        if self.smoother:
            self.smoother = None

    def force_stop(self):
        """Force stop everything - for emergency shutdown"""
        print("[!] Force stopping Solana Ai...")
        self.should_exit = True
        self.running = False
        self.stop_overlay()
        self.stop_debug_window()
        self.cleanup_resources()
        
        # Force terminate thread if it's still running
        if self.thread and self.thread.is_alive():
            print("[!] Force terminating Solana Ai thread...")
            # Note: There's no safe way to force kill a thread in Python
            # The thread should respect the should_exit flag

    def filter_detections(results, ignore_classes):
        """
        Returns a filtered list of boxes, removing any whose class name is in ignore_classes.
        """
        filtered_boxes = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            cls_name = results[0].names[cls_id]
            if cls_name not in ignore_classes:
                filtered_boxes.append(box)
        results[0].boxes = filtered_boxes
        return results


    def filter_and_prioritize(self, results):
        IGNORE_CLASSES = {"weapon", "dead_body", "smoke", "fire"}
        OPTIONAL_CLASSES = {"outline", "hideout_target_human", "hideout_target_balls", "third_person"}
        FOCUS_OPTIONAL = False

        boxes = results[0].boxes
        keep_indices = []

        for idx, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            cls_name = results[0].names[cls_id]

            if cls_name in IGNORE_CLASSES:
                continue
            if cls_name in OPTIONAL_CLASSES and not FOCUS_OPTIONAL:
                continue

            keep_indices.append(idx)

        # Keep only selected boxes (preserves Boxes type)
        results[0].boxes = boxes[keep_indices]
        return results

    def draw_detections_on_frame(self, frame, results):
        """Draw detection boxes on frame for debug window"""
        if not results or len(results[0].boxes) == 0:
            return frame
        
        try:
            import cv2
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                confidence = box.conf[0].cpu().numpy()
                cls_id = int(box.cls[0])
                cls_name = results[0].names[cls_id] if cls_id < len(results[0].names) else "unknown"
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label with confidence
                label = f"{cls_name}: {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                
        except Exception as e:
            print(f"Error drawing detections: {e}")
        
        return frame

    def run_loop(self):
        """Main Solana loop"""
        try:
            self.initialize_components()
        
            print(colored(f"Solana Ai is running. Hold your keybind to lock.", 'green'))
        
            # Frame skipping for optimal performance (like your test file)
            frame_count = 0
            processed_count = 0
            skipped_count = 0
            process_interval = 2  # Process every 2nd frame for 120 FPS analysis
            last_stats_time = time.time()
            last_results = None  # Cache last AI results for skipped frames
            
            while self.running:
                try:
                    # Always grab frame for debug window
                    frame = self.camera.grab()
                    if frame is not None:
                        frame_count += 1
                        
                        # Process at calculated interval (every 2nd frame) - ALWAYS
                        if frame_count % process_interval == 0:
                            processed_count += 1
                            # Run AI detection continuously
                            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
                            results = self.filter_and_prioritize(results)
                            last_results = results  # Cache results for skipped frames
                            
                            # Update debug window with detections
                            if self.visuals and self.visuals.running:
                                debug_frame = self.draw_detections_on_frame(frame.copy(), results)
                                self.visuals.update_frame(debug_frame)
                            
                            if not self.paused:
                                # Process triggerbot with AI results
                                if self.triggerbot.enabled:
                                    self.triggerbot.perform_trigger_with_results(results)
                                
                                # Only process aiming when keybind is pressed
                                if win32api.GetKeyState(int(self.keybind, 16)) in (-127, -128):
                                    self.process_frame(0, 0, results)
                        else:
                            skipped_count += 1
                            # Use cached results for skipped frames to maintain target tracking
                            if last_results is not None:
                                # Update debug window with cached detections
                                if self.visuals and self.visuals.running:
                                    debug_frame = self.draw_detections_on_frame(frame.copy(), last_results)
                                    self.visuals.update_frame(debug_frame)
                                
                                if not self.paused:
                                    # Process aiming with cached results if keybind pressed
                                    if win32api.GetKeyState(int(self.keybind, 16)) in (-127, -128):
                                        self.process_frame(0, 0, last_results)
                            else:
                                # No cached results, show raw frame
                                if self.visuals and self.visuals.running:
                                    self.visuals.update_frame(frame)
                    else:
                        # Small sleep when no frame available
                        time.sleep(0.001)  # 1ms sleep when idle
                
                except Exception as e:
                    print(f"[-] Error in Solana loop: {e}")
                    time.sleep(0.01)  # Reduced error sleep
    
        except Exception as e:
            print(f"[-] Fatal error in Solana Ai: {e}")
        finally:
            self.running = False

    
    def update_overlay_only(self):
        """Update overlay visuals without targeting"""
        if not self.overlay_initialized:
            return
        
        try:
            # Draw crosshair
            center = self.fov // 2
            if self.overlay_shape == "circle":
                self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                self.overlay.draw_oval(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
            else:  # square
                self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                self.overlay.draw_square(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
            
            # Optionally show detection boxes on overlay (without aiming)
            detected_objects = self.detect_objects_in_fov()
            for obj in detected_objects:
                x1, y1, x2, y2 = obj['bbox']
                confidence = obj['confidence']
                
                if confidence > self.confidence:
                    # Draw segmented corners (visual only)
                    box_width = x2 - x1
                    box_height = y2 - y1
                    corner_size = min(max(20, box_width // 3), max(20, box_height // 3))
                    line_thickness = 2
                    
                    # Draw segmented corners
                    self.overlay.draw_line(x1, y1, x1 + corner_size, y1, 'white', line_thickness)
                    self.overlay.draw_line(x1, y1, x1, y1 + corner_size, 'white', line_thickness)
                    self.overlay.draw_line(x2 - corner_size, y1, x2, y1, 'white', line_thickness)
                    self.overlay.draw_line(x2, y1, x2, y1 + corner_size, 'white', line_thickness)
                    self.overlay.draw_line(x1, y2 - corner_size, x1, y2, 'white', line_thickness)
                    self.overlay.draw_line(x1, y2, x1 + corner_size, y2, 'white', line_thickness)
                    self.overlay.draw_line(x2, y2 - corner_size, x2, y2, 'white', line_thickness)
                    self.overlay.draw_line(x2 - corner_size, y2, x2, y2, 'white', line_thickness)
                    
        except Exception as e:
            pass  # Silently handle overlay errors

    def process_frame_for_aiming(self, current_x, current_y):
        """Process frame for actual aiming - only when keybind is pressed"""
        if self.paused:
            return
        if not self.camera or not self.model:
            return
        
        try:
            frame = self.camera.grab()
            if frame is None:
                return
            
            # Update debug window (same frame used for aiming)
            if self.visuals and self.visuals.running:
                self.visuals.update_frame(frame)
            
            # Update overlay visuals
            self.update_overlay_only()
            
            # ACTUAL AIMING LOGIC - ONLY RUNS WHEN KEYBIND PRESSED
            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            # Find closest target
            closest = self.find_closest_target(results)
            if closest:
                self.aim_at_target(closest, current_x, current_y)
                
        except Exception as e:
            print(f"[-] Error processing frame for aiming: {e}")
    
    def initialize_components(self):
        """Initialize Solana components with model selection"""
        try:
            # Initialize Kalman smoother with config manager
            self.smoother = KalmanSmoother(self.config_manager)
        
            # Only initialize model if it hasn't been loaded yet
            if self.model is None:
                # Get model path from config manager
                model_path = self.config_manager.get_model_for_loading()
            
                if not model_path:
                    raise Exception("No models found in directory")
            
                # Load the selected model
                print(f"[+] Loading model: {model_path}")
                self.model = YOLO(model_path, task="detect", verbose=False)
            
                # Update config with loaded model path
                self.config_manager.set_value("model.model_path", model_path)
            
                # Get model-specific overrides
                confidence_override = self.config_manager.get_model_specific_confidence()
                if confidence_override is not None:
                    self.confidence = confidence_override
            
                iou_override = self.config_manager.get_model_specific_iou()
                if iou_override is not None:
                    self.iou = iou_override
        
            # Initialize anti-cheat safe camera
            left = (self.full_x - self.fov) // 2
            top = (self.full_y - self.fov) // 2
        
            self.camera = StealthCapture(fov=self.fov, left=left, top=top)
            print("[+] Anti-cheat safe capture started")
        
            # Initialize mouse if using HID
            if self.mouse_method.lower() == "hid":
                self.initialize_mouse()
        
            # Warm up the model
            frame = self.camera.grab()
            if frame is not None:
                self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
        
            print(f"[+] All components initialized successfully")
        
        except Exception as e:
            print(f"[-] Error initializing components: {e}")
            raise
    
    def process_frame(self, current_x, current_y, results):
        """Process a single frame for Solana"""
        if not self.camera or not self.model:
            return

        try:
            # Find target with locking logic
            closest = self.find_closest_target_with_lock(results)
        
            if closest:
                self.has_target = True
                self.last_target_time = time.time()
            
                # Convert to float values if they're tensors
                target_x = closest[0].item() if hasattr(closest[0], 'item') else closest[0]
                target_y = closest[1].item() if hasattr(closest[1], 'item') else closest[1]
            
                # Check if keybind is pressed OR controller is active
                keybind_active = win32api.GetKeyState(int(self.keybind, 16)) in (-127, -128)
                controller_active = False
            
                if hasattr(self, 'controller') and self.controller and self.controller.enabled:
                    # Consider controller active when a physical controller is connected;
                    # ControllerHandler.is_aiming is maintained by its own loop.
                    if self.controller.physical_controller_connected:
                        controller_active = self.controller.is_aiming
            
                # AIM IF EITHER IS ACTIVE
                if keybind_active or controller_active:
                    #print(f"[AIMING] Keybind: {keybind_active}, Controller: {controller_active}")
                    self.aim_at_target(closest, current_x, current_y)
                else:
                    #print(f"[NO AIM] Keybind: {keybind_active}, Controller: {controller_active}")
                    pass
            else:
                if time.time() - self.last_target_time > 0.5:
                    self.has_target = False
                
        except Exception as e:
            print(f"[-] Error processing frame: {e}")

    def detect_objects_in_fov(self):
        """Detect objects using the existing YOLO model"""
        detected_objects = []
        
        if not self.camera or not self.model:
            return detected_objects
        
        try:
            # Use the same frame capture as the main detection
            frame = self.camera.grab()
            if frame is None:
                return detected_objects
            
            # Run YOLO prediction with current settings
            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            # Convert YOLO results to detection format
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = box.conf[0].cpu().numpy()
                
                detected_objects.append({
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': float(confidence),
                    'class': 'target'
                })
                
        except Exception as e:
            print(f"[-] Error in YOLO detection: {e}")
        
        return detected_objects

    def find_best_target(self, results):
        """Find the best target from YOLO results"""
        if not results or len(results[0].boxes) == 0:
            return None
        
        try:
            fov_half = self.fov // 2
            valid_targets = []
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0]

                # Convert tensors to float if needed
                if hasattr(x1, 'item'):
                    x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

                height = y2 - y1
                width = x2 - x1
                head_x = (x1 + x2) / 2
                head_y = y1 + (height * (100 - self.aim_height) / 100)
                
                if head_x < 0 or head_x > self.fov or head_y < 0 or head_y > self.fov:
                    continue

                # Skip only very tiny detections (noise)
                if width < 5 or height < 5:
                    continue
                
                dist = (head_x - fov_half) ** 2 + (head_y - fov_half) ** 2
                confidence = box.conf[0].item() if hasattr(box.conf[0], 'item') else box.conf[0]
                
                valid_targets.append({
                    'pos': (head_x, head_y),
                    'dist': dist,
                    'confidence': confidence,
                    'size': width * height
                })
            
            if not valid_targets:
                return None
                
            # Sort by distance first, then by confidence for ties
            valid_targets.sort(key=lambda t: (t['dist'], -t['confidence']))
            
            # For moving targets, prefer the closest target immediately
            # No sticky targeting - always go for closest
            return valid_targets[0]['pos']
            
        except Exception as e:
            print(f"[-] Error finding best target: {e}")
            return None
    
    def aim_at_target(self, target, current_x, current_y):
        """Aim at target with IMPROVED sticky targeting to reduce shake"""
        try:
            # Calculate raw movement
            base_move_x, base_move_y = self.calc_movement(target[0], target[1])

            # Basic distance from centre (used only for deadzone logic)
            movement_magnitude = (base_move_x**2 + base_move_y**2)**0.5

            # For stability, treat all targets as stationary here by default.
            # We keep the variables so the deadzone logic below stays unchanged.
            target_is_moving = False
            speed_boost_threshold = 8.0  # default threshold used in deadzone logic

            # Do not apply any extra speed boosts or predictive leading here.
            # Just optionally run the Kalman smoother as a simple filter.
            move_x, move_y = base_move_x, base_move_y

            if self.use_kalman and self.smoother:
                try:
                    move_x, move_y = self.smoother.update(move_x, move_y)
                except Exception:
                    pass

            # Convert to integers and clamp
            final_x = max(-127, min(127, int(round(move_x))))
            final_y = max(-127, min(127, int(round(move_y))))

            # ADAPTIVE MOVEMENT THRESHOLDS: Different thresholds for moving vs stationary targets
            # NOTE: final_x/final_y are integer HID counts. Very tiny 1-count moves every frame
            # cause visible "shakiness", so we use a stronger deadzone around the center.
            if target_is_moving:
                # Moving targets: keep responsiveness but still suppress 1-count micro-jitter
                min_movement_threshold = 1.0 if movement_magnitude > speed_boost_threshold else 0.5
            else:
                # Stationary targets: be even more strict near center for a very steady lock
                min_movement_threshold = 1.5 if movement_magnitude > 3.0 else 1.0
            
            if abs(final_x) > min_movement_threshold or abs(final_y) > min_movement_threshold:
                with self.mouse_lock:
                    if self.mouse_method.lower() == "hid" and ensure_mouse_connected():
                        success = move_mouse(final_x, final_y)
                        if success:
                            #print(f"[MOVED] Applied movement: ({final_x}, {final_y})")
                            pass   
                        else:
                            print(f"[ERROR] Failed to move mouse")
                    else:
                        print(f"[ERROR] Mouse not connected or wrong method")
            else:
                # Very small movement - likely just noise/shake
                #print(f"[STICKY] Suppressed small movement: ({final_x}, {final_y})")
                pass

        except Exception as e:
            print(f"[-] Error aiming at target: {e}")

    def get_fast_curve_modifier(self, distance):
        """Get a fast curve modifier based on distance and curve type"""
        # Normalize distance (smaller values = less modification = faster)
        t = min(1.0, distance / 100.0)
    
        if self.movement_curve_type == "Bezier":
            # Fast bezier - minimal curve
            if t < 0.5:
                return 0.9 + (0.1 * (2 * t * t))
            else:
                return 0.9 + (0.1 * (-1 + (4 - 2 * t) * t))
            
        elif self.movement_curve_type == "Sine":
            # Fast sine - subtle wave
            return 0.95 + 0.05 * math.sin(t * math.pi)
        
        elif self.movement_curve_type == "Exponential":
            # Fast exponential - quick ramp
            return 0.9 + 0.1 * (1 - math.exp(-3 * t))
        
        elif self.movement_curve_type == "Catmull":
            # Fast catmull - minimal smoothing
            return 0.95 + 0.05 * t
        
        elif self.movement_curve_type == "Hermite":
            # Fast hermite - quick ease
            return 0.9 + 0.1 * (3 * t * t - 2 * t * t * t)
        
        elif self.movement_curve_type == "B-Spline":
            # Fast b-spline - minimal curve
            return 0.95 + 0.05 * t * t
        
        return 1.0  # No modification


    def execute_curve_movement_improved(self, path):
        """Execute the curved movement path with better timing"""
        if len(path) < 2 or self.mouse_method.lower() != "hid":
            return
    
        try:
            # Calculate total distance for timing
            total_distance = 0
            for i in range(1, len(path)):
                dx = path[i][0] - path[i-1][0]
                dy = path[i][1] - path[i-1][1]
                total_distance += math.sqrt(dx*dx + dy*dy)
        
            # Base movement time (in seconds) - adjust based on distance
            base_time = min(0.05, total_distance / 1000.0)  # Cap at 50ms total
            time_per_step = base_time / len(path) / self.movement_speed
        
            # Track cumulative movement
            cumulative_x = 0.0
            cumulative_y = 0.0
        
            for i in range(1, len(path)):
                if not self.running:  # Stop if aimbot is stopped
                    break
            
                # Calculate desired movement
                desired_x = path[i][0]
                desired_y = path[i][1]
            
                # Calculate actual movement needed (accounting for rounding errors)
                move_x = desired_x - cumulative_x
                move_y = desired_y - cumulative_y

                # CLAMP BEFORE ROUNDING
                clamped_move_x = max(-127, min(127, move_x))
                clamped_move_y = max(-127, min(127, move_y))
            
                # Round and move
                int_move_x = int(round(clamped_move_x))
                int_move_y = int(round(clamped_move_y))
            
                # Skip tiny movements
                if abs(int_move_x) > 0 or abs(int_move_y) > 0:
                    move_mouse(int_move_x, int_move_y)
                
                    # Update cumulative position
                    cumulative_x += int_move_x
                    cumulative_y += int_move_y
            
                # Small delay for smooth movement
                if time_per_step > 0:
                    time.sleep(time_per_step)
                
        except Exception as e:
            print(f"[-] Error executing curve movement: {e}")

    def toggle_debug_window(self):
        """Toggle debug window on/off during runtime.

        This flips the config flag; actual window start/stop is handled by
        :meth:`apply_visual_config_changes` via the normal config update
        flow, keeping all heavy work in one place.
        """
        try:
            import threading as _threading
            thread_name = _threading.current_thread().name
            print(f"[VISUAL] toggle_debug_window called (thread={thread_name}) current={self.visuals_enabled}")
        except Exception:
            pass

        # Flip the internal flag and persist to config; on_config_updated will
        # schedule apply_visual_config_changes for us.
        self.visuals_enabled = not self.visuals_enabled
        self.config_manager.set_value('show_debug_window', self.visuals_enabled)
        print(f"[+] Debug window {'enabled' if self.visuals_enabled else 'disabled'}")

    def get_debug_fps(self):
        """Get current FPS from debug window"""
        # Since FPS is calculated in the debug window, we can't easily retrieve it
        # This is a placeholder for future implementation
        return 0

    def get_status_info(self):
        """Get current status information including overlay shape"""
        model_info = self.get_current_model_info()

        return {
            "running": self.running,
            "overlay_active": self.overlay_initialized,
            "debug_window_active": self.visuals_enabled and self.visuals and self.visuals.running,
            "overlay_shape": self.overlay_shape,
            "fov": self.fov,
            "sensitivity": self.sensitivity,
            "kalman_enabled": self.use_kalman,
            "movement_curves_enabled": self.use_movement_curves,
            "current_curve_type": self.movement_curve_type,
            "supported_curves": self.get_supported_curves(),
            "model_loaded": model_info["loaded"],
            "model_name": model_info["name"],
            "model_confidence": model_info["confidence"]
        }

class LegacySmartArduinoAntiRecoil:
    """Smart anti-recoil with rate limiting to prevent Arduino crashes"""
    
    def __init__(self, aimbot_controller):
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.strength = 5.0
        self.reduce_bloom = True
        self.running = False
        self.thread = None
        
        # Smart activation flags
        self.require_target = True
        self.require_keybind = True
        
        # Rate limiting to prevent Arduino crashes
        self.last_recoil_time = 0
        self.min_recoil_interval = 0.008  # Minimum 8ms between commands (125Hz max)
        self.recoil_active = False
        
        # Add mutex for thread safety
        self.recoil_lock = threading.Lock()
    
    def start(self):
        """Start anti-recoil system"""
        if not self.running:
            self.running = True
            
            # Start recoil compensation thread
            self.thread = threading.Thread(target=self.recoil_loop, daemon=True)
            self.thread.start()
            
            #print("[+] Smart Arduino Anti-recoil started - only activates when aiming at targets")
            return True
        return False
    
    def stop(self):
        """Stop anti-recoil system"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
            
        print("[+] Anti-recoil stopped")
    
    def check_mouse_button(self):
        """Check if left mouse button is pressed using Windows API"""
        # VK_LBUTTON = 0x01 for left mouse button
        state = win32api.GetAsyncKeyState(0x01)
        # If high bit is set, button is pressed
        return state & 0x8000 != 0
    
    def should_activate(self):
        """Check if anti-recoil should activate"""
        if not self.enabled:
            return False
        
        # Check mouse button state using Windows API
        is_firing = self.check_mouse_button()
        
        if not is_firing:
            return False
        
        # Check if aimbot is running
        if not self.aimbot_controller.running:
            return False
        
        # Check if keybind is required and pressed
        if self.require_keybind:
            try:
                keybind_state = win32api.GetKeyState(int(self.aimbot_controller.keybind, 16))
                if keybind_state not in (-127, -128):
                    return False
            except:
                return False
        
        # Check if target is required and detected
        if self.require_target:
            if hasattr(self.aimbot_controller, 'has_target'):
                return self.aimbot_controller.has_target
            return False
        
        return True
    
    def recoil_loop(self):
        """Main anti-recoil loop with rate limiting"""
        consecutive_errors = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Rate limiting check
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
                        
                        # Clamp values to prevent Arduino overflow
                        vertical_offset = max(-10, min(10, vertical_offset))
                        horizontal_offset = max(-5, min(5, horizontal_offset))
                        
                        if abs(vertical_offset) > 0.5 or abs(horizontal_offset) > 0.5:
                            # Use existing move_mouse with rate limiting
                            move_mouse(int(horizontal_offset), int(vertical_offset))
                            self.last_recoil_time = current_time
                        
                    # Variable delay based on fire rate
                    time.sleep(random.uniform(0.010, 0.020))  # 10-20ms
                else:
                    # Not active, idle with lower CPU usage
                    self.recoil_active = False
                    time.sleep(0.05)  # 50ms idle check
                    
            except Exception as e:
                print(f"[-] Anti-recoil error: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self.enabled = False
                    break
                time.sleep(0.1)
    
    def calculate_vertical_offset(self):
        """Calculate smoother vertical recoil compensation"""
        # Use smoother, smaller values
        base_strength = self.strength * 0.7  # Reduce base strength
        
        # Add slight randomization for more natural movement
        variation = random.uniform(0.8, 1.2)
        vertical_offset = base_strength * variation
        
        # Apply smoothing if target is locked
        if hasattr(self.aimbot_controller, 'target_lock'):
            if self.aimbot_controller.target_lock.get('current_target_id'):
                vertical_offset *= 0.8  # Reduce when locked on target
        
        return vertical_offset
    
    def calculate_horizontal_offset(self):
        """Calculate horizontal bloom compensation"""
        if not self.reduce_bloom:
            return 0
        
        # Small random horizontal movement to counter bloom
        horizontal_offset = random.randrange(-2000, 2000, 1) / 1000.0
        return horizontal_offset
    
    def set_strength(self, strength):
        """Set anti-recoil strength (0-20 recommended)"""
        self.strength = max(0, min(50, strength))
        print(f"[+] Anti-recoil strength set to: {self.strength}")
    
    def set_enabled(self, enabled):
        """Enable/disable anti-recoil"""
        self.enabled = enabled
        if enabled:
            print(f"[+] Anti-recoil enabled with strength: {self.strength}")
        else:
            print("[+] Anti-recoil disabled")

# ============================================
# INTEGRATION WITH YOUR GUI
# ============================================
def integrate_with_pyqt(window):
    """Integrate hiding features with PyQt window"""
    
    # Get window handle
    hwnd = int(window.winId())
    
    # Create process hider
    hider = ProcessHider()
    
    # Hide from taskbar
    hider.hide_from_taskbar(hwnd)
    
    # Apply process hiding
    hider.hide_process()
    
    # Make window stay on top but hidden from Alt+Tab
    window.setWindowFlags(
        window.windowFlags() | 
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool
    )
    
    return hider

def setup_bettercam_with_patch():
    """Apply the patch and create a working BetterCam instance"""
    import bettercam.processor.base as base
    
    class ForcedNumpyProcessor:
        def __init__(self):
            from bettercam.processor.numpy_processor import NumpyProcessor
            self.backend = NumpyProcessor("BGRA")
        
        def process(self, *args, **kwargs):
            return self.backend.process(*args, **kwargs)
    
    original_create = bettercam.create
    
    def patched_create(*args, **kwargs):
        cam = original_create(*args, **kwargs)
        cam._processor = ForcedNumpyProcessor()
        return cam
    
    bettercam.create = patched_create
    return bettercam.create(output_idx=0, nvidia_gpu=True)

class StealthCapture:
    """Anti-cheat safe capture system with GPU acceleration"""
    
    def __init__(self, fov=320, left=0, top=0):
        self.fov = fov
        self.left = left
        self.top = top
        
        # Create camera exactly like test_bettercam_final.py
        self.cam = setup_bettercam_with_patch()
        print("✓ BetterCam initialized")
        
        self.gpu_code = self._get_gpu_code()
        print(f"[+] Anti-cheat safe capture initialized - {self.gpu_code}")
    
    def _get_gpu_code(self):
        """Get GPU identifier"""
        try:
            props = cp.cuda.runtime.getDeviceProperties(0)
            full_name = props['name'].decode('utf-8')
            clean_name = full_name.replace("NVIDIA ", "").replace("GeForce ", "")
            
            if "RTX" in clean_name:
                parts = clean_name.split()
                rtx_index = next(i for i, part in enumerate(parts) if "RTX" in part)
                if rtx_index + 1 < len(parts):
                    model = parts[rtx_index + 1]
                    if rtx_index + 2 < len(parts) and parts[rtx_index + 2] in ["Ti", "SUPER"]:
                        model += f" {parts[rtx_index + 2]}"
                    return f"RTX-{model.replace(' ', '')}"
            elif "GTX" in clean_name:
                parts = clean_name.split()
                gtx_index = next(i for i, part in enumerate(parts) if "GTX" in part)
                if gtx_index + 1 < len(parts):
                    model = parts[gtx_index + 1]
                    if gtx_index + 2 < len(parts) and parts[gtx_index + 2] in ["Ti", "SUPER"]:
                        model += f" {parts[gtx_index + 2]}"
                    return f"GTX-{model.replace(' ', '')}"
            
            return "NVIDIA-GPU"
        except:
            return "NVIDIA-GPU"
    
    def update_region(self, fov, left, top):
        """Update capture region"""
        self.fov = fov
        self.left = left
        self.top = top
    
    def grab(self):
        """Frame capture exactly like test_bettercam_final.py"""
        frame = self.cam.grab()
        
        if frame is not None:
            # Handle BGRA format from your test file
            if frame.shape[2] == 4:  # BGRA
                frame = frame[:, :, :3]  # Convert to BGR
            
            # Crop to FOV
            h, w = frame.shape[:2]
            if h == self.fov and w == self.fov:
                return frame
                
            if h > self.fov or w > self.fov:
                start_y = (h - self.fov) >> 1
                start_x = (w - self.fov) >> 1
                cropped = frame[start_y:start_y + self.fov, start_x:start_x + self.fov]
                
                if not cropped.flags['C_CONTIGUOUS']:
                    cropped = np.ascontiguousarray(cropped)
                
                return cropped
                
            return frame
            
        return None
    
    def release(self):
        """Release capture resources"""
        try:
            self.cam.stop()
            self.running = False
        except:
            pass



# Configuration update to include debug window option
def update_config_for_debug_window(config_manager):
    """Add debug window option to your existing config"""
    config = config_manager.get_config()
    
    # Add debug window setting if it doesn't exist
    if 'show_debug_window' not in config:
        config_manager.set_value('show_debug_window', False)  # Default to False
        print("[+] Added debug window option to config")

def listen_for_end_key():
    while True:
        if win32api.GetAsyncKeyState(0x23):  # 0x23 is VK_END
            print("\n[INFO] End key pressed. Exiting.")
            os._exit(0)  # Use os._exit to kill all threads instantly
        time.sleep(0.1)

def clear():
    if platform.system() == 'Windows':
        os.system('cls & title Solana Ai')
    elif platform.system() == 'Linux':
        os.system('clear')
        sys.stdout.write("\033]0;Solana Ai\007")
        sys.stdout.flush()
    elif platform.system() == 'Darwin':
        os.system("clear && printf '\033[3J'")
        os.system('echo -n -e "\033]0;Solana Ai\007"')

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def getchecksum():
    md5_hash = hashlib.md5()
    with open(''.join(sys.argv), "rb") as file:
        md5_hash.update(file.read())
    return md5_hash.hexdigest()

import os
import json as jsond  # json
import time  # sleep before exit
import binascii  # hex encoding
import platform  # check platform
import subprocess  # needed for mac device
import qrcode
from datetime import datetime, timezone, timedelta
from discord_interactions import verify_key # used for signature verification
from PIL import Image

try:
    if os.name == 'nt':
        import win32security  # get sid (WIN only)
    import requests  # https requests
except ModuleNotFoundError:
    print("Exception when importing modules")
    print("Installing necessary modules....")
    if os.path.isfile("requirements.txt"):
        os.system("pip install -r requirements.txt")
    else:
        if os.name == 'nt':
            os.system("pip install pywin32")
        os.system("pip install requests")
    print("Modules installed!")
    time.sleep(1.5)
    os._exit(1)
	
def legacy_clamp_char(value):
    return max(-128, min(127, value))

def legacy_is_locked(x1, x2, y1, y2):
    return x1 <= fov / 2 <= x2 and y1 <= fov / 2 <= y2

def legacy_low_byte(x):
    return x & 255

def legacy_high_byte(x):
    return x >> 8 & 255

def legacy_make_report(x, y):
    """Create HID report for mouse movement"""
    # Clamp values to signed 8-bit range
    x = max(-127, min(127, int(x)))
    y = max(-127, min(127, int(y)))
    
    # For most Arduino HID implementations, this format works:
    return [1, 0, x, 0, y, 0]  # [report_id, buttons, x, x_high, y, y_high]

def legacy_send_raw_report(report_data):
    global mouse_dev
    if mouse_dev:
        mouse_dev.write(report_data)

def legacy_move_mouse(x, y):
    """Fixed move_mouse with proper device checking and value conversion"""
    global mouse_dev
    
    if not mouse_dev:
        if not ensure_mouse_connected():
            return False
    
    try:
        # Convert to integers and clamp to valid range for HID reports
        # Arduino mouse expects signed 8-bit values (-128 to 127)
        int_x = max(-127, min(127, int(round(x))))
        int_y = max(-127, min(127, int(round(y))))
        
        # Create the HID report
        # Format: [report_id, buttons, x_low, x_high, y_low, y_high]
        report = [1, 0, int_x & 0xFF, (int_x >> 8) & 0xFF, int_y & 0xFF, (int_y >> 8) & 0xFF]
        
        mouse_dev.write(report)
        return True
    except Exception as e:
        print(f"[-] Mouse move error: {e}")
        mouse_dev = None
        return False

def legacy_click_mouse(button='left', duration=0.05):
    """Click mouse button using Arduino HID with minimal delay
    Args:
        button: 'left' or 'right'
        duration: How long to hold the button (in seconds)
    """
    global mouse_dev, last_click_time
    
    try:
        # Check if device exists
        if not mouse_dev:
            print("[-] Mouse device not initialized")
            return False
        
        # Minimal delay between clicks to prevent overwhelming the board
        current_time = time.time()
        time_since_last = current_time - last_click_time
        if time_since_last < 0.01:  # 10ms minimum between clicks
            time.sleep(0.01 - time_since_last)
        
        if button == 'left':
            # Send click as a single report with minimal delay
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(duration)  # Hold duration
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
        elif button == 'right':
            mouse_dev.write([1, 0x02, 0, 0, 0, 0])  # Button down
            time.sleep(duration)  # Hold duration
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
        
        last_click_time = time.time()
        return True
        
    except Exception as e:
        print(f"[-] Click error: {e}")
        return False

def legacy_rapid_click(clicks=1, delay_between=0.05):
    """Perform rapid clicks for triggerbot"""
    global mouse_dev
    
    if not mouse_dev:
        return False
    
    try:
        for i in range(clicks):
            # Very short click duration for rapid fire
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(0.01)  # 10ms hold
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
            
            if i < clicks - 1:  # Don't delay after last click
                time.sleep(delay_between)
        
        return True
    except Exception as e:
        print(f"[-] Rapid click error: {e}")
        return False
    
def legacy_ensure_mouse_connected():
    """Ensure mouse device is connected, reconnect if needed"""
    global mouse_dev
    
    if mouse_dev is None:
        try:
            # Try to reconnect using the same VID/PID as in initialization
            VENDOR_ID = 0x46D
            PRODUCT_ID = 0xC539
            get_mouse(VENDOR_ID, PRODUCT_ID)
            print("[+] Mouse device reconnected")
            return True
        except Exception as e:
            print(f"[-] Failed to reconnect mouse: {e}")
            return False
    return True

def legacy_move_and_click(x, y, button='left', click_duration=0.05):
    """Move mouse and click in one operation"""
    global mouse_dev
    try:
        if mouse_dev:
            # Move to position
            move_mouse(x, y)
            time.sleep(0.01)  # Small delay between move and click
            # Click
            click_mouse(button, click_duration)
    except Exception as e:
        print(f"[-] Move and click error: {e}")

def legacy_limit_xy(xy):
    if xy < -32767:
        return -32767
    if xy > 32767:
        return 32767
    return xy

def legacy_check_ping(dev, ping_code):
    dev.write([0, ping_code])
    resp = dev.read(max_length=1, timeout_ms=10)
    return resp and resp[0] == ping_code

def legacy_find_mouse_device(vid, pid, ping_code):
    global mouse_dev
    for dev_info in hid.enumerate(vid, pid):
        try:
            mouse_dev = hid.device()
            mouse_dev.open_path(dev_info['path'])
            if check_ping(mouse_dev, ping_code):
                return mouse_dev
            mouse_dev.close()
        except Exception as e:
            print(f'Error initializing device: {e}')
    return None

def legacy_get_mouse(vid, pid, ping_code=249):
    global mouse_dev
    mouse_dev = find_mouse_device(vid, pid, ping_code)
    if not mouse_dev:
        raise Exception(f'[-] Device Vendor ID: {hex(vid)}, Product ID: {hex(pid)} not found!')
    move_mouse(0, 0)

from kalman_smoother import KalmanSmoother

kernel32 = ctypes.WinDLL('kernel32')
user32 = windll.user32

class PROCESS_MITIGATION_DYNAMIC_CODE_POLICY(ctypes.Structure):
    _fields_ = [
        ('ProhibitDynamicCode', ctypes.c_uint, 1),
        ('AllowThreadOptOut', ctypes.c_uint, 1),
        ('AllowRemoteDowngrade', ctypes.c_uint, 1),
        ('AuditProhibitDynamicCode', ctypes.c_uint, 1),
        ('ReservedFlags', ctypes.c_uint, 28),
    ]

def send_coordinates(arduino, x, y):
    try:
        command = f"move {int(x)},{int(y)}\n"
        arduino.write(command.encode())
    except Exception as e:
        print(colored(f"Error sending coordinates to Arduino: {e}", 'red'))

if kernel32.IsDebuggerPresent():
    print("Error code: 1")
    sys.exit(1)
if 'pydevd' in sys.modules:
    print("Error code: 2")
    sys.exit(1)
if sys.gettrace() is not None:
    print("Error code: 3")
    sys.exit(1)

dynamic_code_policy = PROCESS_MITIGATION_DYNAMIC_CODE_POLICY()
dynamic_code_policy.ProhibitDynamicCode = 1
kernel32.SetProcessMitigationPolicy(11, ctypes.byref(dynamic_code_policy), ctypes.sizeof(dynamic_code_policy))

context = ctypes.create_string_buffer(716)
ctypes.memset(ctypes.addressof(context), 0, ctypes.sizeof(context))
context_ptr = ctypes.cast(ctypes.addressof(context), ctypes.POINTER(ctypes.c_long))
kernel32.GetThreadContext(kernel32.GetCurrentThread(), context_ptr)
if context_ptr[41] != 0 or context_ptr[42] != 0 or context_ptr[43] != 0 or context_ptr[44] != 0:
    print("Error code: 4")
    sys.exit(1)

urllib3.disable_warnings()
local_version = "1.4.3 BETA"
with open('lib/config/config.json', 'r') as file:
    config = json.load(file)
show_alerts = config.get('account_settings', {}).get('discord', {}).get('alerts', {}).get('visible', True)
if not isinstance(show_alerts, bool):
    print("You have an outdated config. Please add the new settings from  to your config.json ")
    print(colored("show_alerts must be a boolean (true or false)", 'red'))
    sys.exit(1)

cpu_info = cpuinfo.get_cpu_info()
cpu_name = cpu_info.get('brand_raw', 'Unknown CPU')
try:
    gpu_stats = gpustat.GPUStatCollection.new_query()
    gpu_name = gpu_stats.gpus[0].name if gpu_stats.gpus else "No GPU found"
except:
    gpu_name = "No GPU found"

try:
    fov = config['fov']
    sensitivity = config['sensitivity']
    aim_height = config['aim_height']
    confidence = config['confidence']
    triggerbot = config['triggerbot']
    keybind = config['keybind']
    mouse_method = config['mouse_method']
    custom_resolution = config['custom_resolution']
    use_custom_resolution = config['custom_resolution']['use_custom_resolution']
    custom_x = config['custom_resolution']['x']
    custom_y = config['custom_resolution']['y']
except KeyError as ke:
    print(f"Missing configuration field: {ke}. Please check your config.json file.")
    sys.exit(1)

                
def run_app():
    """Entry point to start the Solana AI Qt application."""
    # Import GUI lazily to avoid circular dependencies
    from gui_app import ConfigApp

    # Create QApplication (High DPI policy already set at module level)
    app = QApplication(sys.argv)
    
    config_manager = ConfigManager()
    update_config_for_debug_window(config_manager)
    
    # Create the main smoother that will be shared
    smoother = KalmanSmoother(config_manager)
    
    window = ConfigApp()
    
    # IMPORTANT: Pass the smoother to the aimbot controller so they use the same instance
    window.aimbot_controller.set_smoother(smoother)
    
    gui_hider = integrate_with_pyqt(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
