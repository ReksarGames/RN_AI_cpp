# 🎯 RN_AI_cpp — AI Aim Assistant

<div align="center">

![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?style=for-the-badge)
![CUDA](https://img.shields.io/badge/CUDA-12.8-76B900?style=for-the-badge)
![TensorRT](https://img.shields.io/badge/TensorRT-10.8-76B900?style=for-the-badge)

[🚀 Quick Start](#-quick-start) • [📚 Documentation](#-technical-details) * [📚Русская версия README](README_RU.md)


![RN_AI Demo](docs/demo.gif)

</div>

---

## ✨ Features

| | |
|---|---|
| **🎯 AI Detection** | Target detection using neural networks with high accuracy |
| **🎨 Color Detection** | Target identification through color-based filtering |
| **📈 Real-time Stats** | FPS counter and latency information |
| **🖱️ Aim Simulator** | Visualization of target movement prediction |
| **🎛️ ClassTable** | Real-time dynamic class management |
| **🔄 Kalman Filter** | Smooth movement without aim jitter |
| **⚡ Multiple Backends** | DirectML, CUDA+TensorRT, Color Detection |

---

## 🚀 Quick Start

### 1️⃣ Choose Your Build

<details open>
<summary><b>🟢 DirectML (Universal)</b></summary>

**For:** Any GPU (NVIDIA, AMD, Intel, integrated graphics)

```
✅ Windows 10/11 (x64)
✅ No CUDA required
✅ Recommended for older GPUs
```

**Recommended for:**
- GTX 10xx/9xx/7xx series
- AMD Radeon GPU
- Intel Iris/Xe GPU
- Laptops and office PCs

</details>

<details>
<summary><b>🟡 CUDA + TensorRT (Maximum Performance)</b></summary>

**For:** Latest generation NVIDIA GPUs

```
✅ RTX 2000/3000/4000 and newer
✅ GTX 1660
✅ CUDA 12.8 + TensorRT 10.8 (included)
❌ Does not support GTX 10xx/Pascal and older
```

**Features:**
- Switch between CUDA+TensorRT and DML in settings
- Maximum FPS and accuracy
- Professional-grade performance
Realese — https://mega.nz/file/T8IFHS7I#70_WjY_-3rDZ82U3yKS3meS8mk3bV29_RFrSCQRlFhg
</details>

---

## ⚙️ Configuration & Parameters

### 📦 ClassTable — Class Management

Dynamic management of target classes with:
- ✅ Add/switch classes in real-time
- ✅ Auto-detection of new classes
- ✅ Configure Y1/Y2 position for each class

---

### 🎨 Colorbot — Color Detection

Advanced color filtering system:

| Parameter | Range | Description |
|-----------|-------|-------------|
| `color_erode_iter` | 0-5 | Number of erosion iterations (reduces noise) |
| `color_dilate_iter` | 0-5 | Number of dilation iterations (restores size) |
| `color_min_area` | 1-1000 | Minimum object area |
| `color_target` | Yellow/Red/etc | Target color for tracking |
| `tinyArea` | 1-100 | Small element filtering threshold |
| `isOnlyTop` | true/false | Consider only top objects |
| `scanError` | 0-100 | Allowed search error (0=precise) |

**💡 Use:** Accurate color-based target selection while ignoring noise

---

### 🎯 Kalman Filter — Movement Prediction

Smoothing filter for target position prediction:

| Parameter | Description |
|-----------|-------------|
| `kalman_process_noise` | Accounts for random movement changes |
| `kalman_measurement_noise` | Accounts for sensor/camera errors |
| `kalman_speed_multiplier_x/y` | Speed multiplier per axis |
| `resetThreshold` | Filter reinitialization threshold |

**💡 Result:** Smooth aiming without jitter

---

## 🖥️ Interface & Controls

### 🎨 ImGui Menu

**Menu interface features:**

- 🧭 Vertical navbar with custom icons
- 🖼️ Custom background via `ui_bg.png`
- 🎨 Theming in `ui_theme.ini`
- ⚙️ `Components` tab for runtime configuration

#### 📸 Interface Screenshots

| Screen Capture | Target Status |
|---|---|
| ![Capture](docs/menu/сapture.jpg) | ![Status](docs/menu/status.jpg) |

#### 🎛️ Overlay Controls

- **Overlay Opacity** — Transparency (slider or ±)
- **UI Scale** — Interface scale (± or manual input)
- **Window Width/Height** — Window size (manual input)
- **Resize Handles** — Resize window from edges

### 🎮 Game Overlay — On-Screen Visualization

Information displayed directly on desktop over games and apps:

- 📊 **Stats** — FPS counter and latency info
- 🎯 **Aim Simulator** — Aiming prediction visualization
- 🔲 **Detection Boxes** — Detected target boxes
- 🎨 **Class Colors** — Auto-coloring (class 0 = green)
- 📝 **Text Size** — Adjustable in Components → Advanced

---

## 🔧 Technical Details

### 📁 File Structure

| File | Purpose |
|------|---------|
| **config.ini** | Main project configuration |
| **ui_theme.ini** | UI colors, sizes, and parameters |
| **ui_bg.png** | Menu background image (replaceable) |
| **imgui.ini** | Window state (local, not committed) |

### 📦 Core Modules

📹 **capture/** — Screen capture methods
- DirectX Duplication API — `duplication_api_capture`
- Windows Runtime capture — `winrt_capture`
- [📖 OBS Capture](docs/obs/obs_en.md) — `obs_capture`

🧠 **detector/** — Target detection system
- DirectML detector — `dml_detector`
- TensorRT detector (NVIDIA) — `trt_detector`
- Color-based detection — `color_detector`

🎨 **overlay/** — Visual interface
- ImGui implementation — `imgui_impl_*`
- 2D/3D rendering — `rendering`

### ⚡ Input Methods

- **WIN32 API** — Built-in Windows APIs  
  ⚠️ **Warning:** Don't use in games (instant detection)

- **Makcu/Kmbox/KmboxNet** — Specialized input devices  
  ✅ Recommended for games (low latency)

---

## 📚 Links & Resources

### 📖 Documentation

- 🔗 [TensorRT Docs](https://docs.nvidia.com/deeplearning/tensorrt/)
- 🔗 [OpenCV Docs](https://docs.opencv.org/4.x/d1/dfb/intro.html)
- 🔗 [CUDA 12.8](https://developer.nvidia.com/cuda-12-8-0-download-archive)
- 🔗 [Config](docs\config_en.md)

### 🛠️ Libraries Used

| Library | Purpose |
|---------|---------|
| [ImGui](https://github.com/ocornut/imgui) | User Interface |
| [OpenCV](https://opencv.org/) | Computer Vision |
| [TensorRT](https://developer.nvidia.com/tensorrt) | Neural network inference (NVIDIA) |
| [DirectML](https://github.com/microsoft/DirectML) | GPU computing (universal) |
| [CppWinRT](https://github.com/microsoft/cppwinrt) | Windows Runtime APIs |
| [GLFW](https://www.glfw.org/) | Window management |
| [nlohmann/JSON](https://github.com/nlohmann/json) | JSON processing |

### 💡 Methods & Inspiration

- 🔗 [WindMouse Algorithm](https://ben.land/post/2021/04/25/windmouse-human-mouse-movement/) — Natural mouse movement
- 🔗 [KMBOX](https://www.kmbox.top/) — Input device integration
- 🐍 [RN_AI (Python version)](https://github.com/ReksarGames/RN_AI)
- 🔀 [Original SunOne Aimbot](https://github.com/SunOner/sunone_aimbot_cpp) — RN_AI_cpp is a complete fork and rebuild

---

<div align="center">

**Made with ❤️ for the gaming community**

</div>
