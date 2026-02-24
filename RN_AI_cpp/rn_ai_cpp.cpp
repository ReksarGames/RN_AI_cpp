#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

#include <iostream>
#include <thread>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <cstdint>
#include <sstream>
#include <cmath>
#include <filesystem>
#include <limits>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <random>
#include <cctype>
#include <algorithm>
#include <fstream>
#include <memory>
#include <cwchar>

#include "capture.h"
#include "mouse.h"
#include "rn_ai_cpp.h"
#include "keyboard_listener.h"
#include "overlay.h"
#include "Game_overlay.h"
#include "other_tools.h"
#include "virtual_camera.h"

std::condition_variable frameCV;
std::atomic<bool> shouldExit(false);
std::atomic<bool> aiming(false);
std::atomic<bool> detectionPaused(false);
std::mutex configMutex;

#ifdef USE_CUDA
TrtDetector trt_detector;
#endif


DirectMLDetector* dml_detector = nullptr;
MouseThread* globalMouseThread = nullptr;
Config config;

ColorDetector* color_detector = nullptr;
std::thread color_detThread;

SerialConnection* arduinoSerial = nullptr;
KmboxConnection* kmboxSerial = nullptr;
KmboxNetConnection* kmboxNetSerial = nullptr;
MakcuConnection* makcu_conn = nullptr;

std::atomic<bool> detection_resolution_changed(false);
std::atomic<bool> capture_method_changed(false);
std::atomic<bool> capture_cursor_changed(false);
std::atomic<bool> capture_borders_changed(false);
std::atomic<bool> capture_fps_changed(false);
std::atomic<bool> capture_window_changed(false);
std::atomic<bool> detector_model_changed(false);
std::atomic<bool> show_window_changed(false);
std::atomic<bool> input_method_changed(false);

std::atomic<bool> zooming(false);
std::atomic<bool> shooting(false);
std::atomic<bool> triggerbot_button(false);

Game_overlay* gameOverlayPtr = nullptr;

namespace
{
struct MonitorQueryContext
{
    int target_index = 0;
    int current_index = 0;
    RECT result{ 0, 0, 0, 0 };
    bool found = false;
};

BOOL CALLBACK EnumMonitorsProc(HMONITOR hMon, HDC, LPRECT, LPARAM lParam)
{
    auto* ctx = reinterpret_cast<MonitorQueryContext*>(lParam);
    if (!ctx)
        return TRUE;

    if (ctx->current_index == ctx->target_index)
    {
        MONITORINFO mi{};
        mi.cbSize = sizeof(mi);
        if (GetMonitorInfo(hMon, &mi))
        {
            ctx->result = mi.rcMonitor;
            ctx->found = true;
            return FALSE;
        }
    }
    ++ctx->current_index;
    return TRUE;
}

RECT GetMonitorRectByIndexOrPrimary(int monitorIndex)
{
    MonitorQueryContext ctx;
    ctx.target_index = std::max(0, monitorIndex);
    EnumDisplayMonitors(nullptr, nullptr, EnumMonitorsProc, reinterpret_cast<LPARAM>(&ctx));
    if (ctx.found)
        return ctx.result;

    MONITORINFO mi{};
    mi.cbSize = sizeof(mi);
    HMONITOR primary = MonitorFromPoint(POINT{ 0, 0 }, MONITOR_DEFAULTTOPRIMARY);
    if (primary && GetMonitorInfo(primary, &mi))
        return mi.rcMonitor;

    RECT fallback{ 0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN) };
    return fallback;
}

void StopGameOverlay()
{
    if (gameOverlayPtr)
    {
        gameOverlayPtr->Stop();
        delete gameOverlayPtr;
        gameOverlayPtr = nullptr;
    }
}

struct AimSimVec2
{
    double x = 0.0;
    double y = 0.0;
};

struct AimSimHistorySample
{
    double timeSec = 0.0;
    AimSimVec2 target;
    AimSimVec2 aim;
};

struct AimSimQueuedMove
{
    double executeAtSec = 0.0;
    int mx = 0;
    int my = 0;
};

struct AimSimulationState
{
    bool initialized = false;
    bool controllerInitialized = false;
    int panelW = 0;
    int panelH = 0;

    std::mt19937 rng{ std::random_device{}() };
    std::chrono::steady_clock::time_point lastWallTime{};

    double simTimeSec = 0.0;
    double accumulatorSec = 0.0;
    double currentFps = 100.0;
    double targetFps = 100.0;
    double fpsRetargetSec = 0.0;
    double targetMotionRetargetSec = 0.0;
    double lastFrameDtSec = 1.0 / 100.0;

    AimSimVec2 targetPos;
    AimSimVec2 targetVel;
    AimSimVec2 targetDesiredVel;
    AimSimVec2 aimPos;
    AimSimVec2 observedTarget;
    AimSimVec2 predictedTarget;

    double usedCaptureDelayMs = 0.0;
    double usedInferenceDelayMs = 0.0;
    double usedInputDelayMs = 0.0;
    double usedExtraDelayMs = 0.0;
    double usedTotalDelayMs = 0.0;
    double lastErrorPx = 0.0;
    int lastMoveX = 0;
    int lastMoveY = 0;

    double ctrlPrevX = 0.0;
    double ctrlPrevY = 0.0;
    double ctrlPrevVelocityX = 0.0;
    double ctrlPrevVelocityY = 0.0;
    double ctrlPrevTimeSec = 0.0;

    double windCarryX = 0.0;
    double windCarryY = 0.0;
    double windVelX = 0.0;
    double windVelY = 0.0;
    double windNoiseX = 0.0;
    double windNoiseY = 0.0;
    double windFracX = 0.0;
    double windFracY = 0.0;
    double windPatternX = 0.0;
    double windPatternY = 0.0;
    double windPatternPhaseA = 0.0;
    double windPatternPhaseB = 0.0;
    double windPatternRateA = 0.0;
    double windPatternRateB = 0.0;
    std::mt19937 windRng{ std::random_device{}() };
    bool windEnabledSnapshot = false;
    double windGSnapshot = 0.0;
    double windWSnapshot = 0.0;
    double windMSnapshot = 0.0;
    double windDSnapshot = 0.0;

    std::deque<AimSimHistorySample> history;
    std::deque<AimSimQueuedMove> queuedMoves;
    std::deque<AimSimVec2> targetTrail;
    std::deque<AimSimVec2> aimTrail;
};

static double aim_sim_random_range(AimSimulationState& s, double minV, double maxV)
{
    std::uniform_real_distribution<double> dist(minV, maxV);
    return dist(s.rng);
}

static double aim_sim_vec_len(const AimSimVec2& v)
{
    return std::hypot(v.x, v.y);
}

static void aim_sim_reset_wind_state(AimSimulationState& s)
{
    constexpr double twoPi = 6.28318530717958647692;
    std::uniform_real_distribution<double> phaseDist(0.0, twoPi);
    std::uniform_real_distribution<double> rateDist(0.04, 0.16);

    s.windCarryX = 0.0;
    s.windCarryY = 0.0;
    s.windVelX = 0.0;
    s.windVelY = 0.0;
    s.windNoiseX = 0.0;
    s.windNoiseY = 0.0;
    s.windFracX = 0.0;
    s.windFracY = 0.0;
    s.windPatternX = 0.0;
    s.windPatternY = 0.0;
    s.windPatternPhaseA = phaseDist(s.windRng);
    s.windPatternPhaseB = phaseDist(s.windRng);
    s.windPatternRateA = rateDist(s.windRng);
    s.windPatternRateB = rateDist(s.windRng);
}

static void aim_sim_sync_wind_config(AimSimulationState& s)
{
    const bool windEnabled = config.wind_mouse_enabled;
    const double windG = static_cast<double>(config.wind_G);
    const double windW = static_cast<double>(config.wind_W);
    const double windM = static_cast<double>(config.wind_M);
    const double windD = static_cast<double>(config.wind_D);

    const bool changed =
        (s.windEnabledSnapshot != windEnabled) ||
        (std::abs(s.windGSnapshot - windG) > 1e-6) ||
        (std::abs(s.windWSnapshot - windW) > 1e-6) ||
        (std::abs(s.windMSnapshot - windM) > 1e-6) ||
        (std::abs(s.windDSnapshot - windD) > 1e-6);

    if (!changed)
        return;

    aim_sim_reset_wind_state(s);
    s.windEnabledSnapshot = windEnabled;
    s.windGSnapshot = windG;
    s.windWSnapshot = windW;
    s.windMSnapshot = windM;
    s.windDSnapshot = windD;
}

static void aim_sim_choose_target_motion(AimSimulationState& s)
{
    const double stopChance = std::clamp(static_cast<double>(config.aim_sim_target_stop_chance), 0.0, 0.95);
    const double maxSpeed = std::max(20.0, static_cast<double>(config.aim_sim_target_max_speed));

    if (aim_sim_random_range(s, 0.0, 1.0) < stopChance)
    {
        s.targetDesiredVel = { 0.0, 0.0 };
        s.targetMotionRetargetSec = aim_sim_random_range(s, 0.25, 0.95);
        return;
    }

    const double angle = aim_sim_random_range(s, 0.0, 2.0 * 3.14159265358979323846);
    const double speed = aim_sim_random_range(s, maxSpeed * 0.25, maxSpeed);
    s.targetDesiredVel = { std::cos(angle) * speed, std::sin(angle) * speed };
    s.targetMotionRetargetSec = aim_sim_random_range(s, 0.35, 1.35);
}

static void aim_sim_reset(AimSimulationState& s, int panelW, int panelH)
{
    s.initialized = true;
    s.controllerInitialized = false;
    s.panelW = panelW;
    s.panelH = panelH;

    s.simTimeSec = 0.0;
    s.accumulatorSec = 0.0;
    s.currentFps = std::clamp((config.aim_sim_fps_min + config.aim_sim_fps_max) * 0.5, 15.0, 360.0);
    s.targetFps = s.currentFps;
    s.fpsRetargetSec = 0.0;
    s.targetMotionRetargetSec = 0.0;
    s.lastFrameDtSec = 1.0 / std::max(15.0, s.currentFps);

    s.targetPos = { panelW * 0.72, panelH * 0.38 };
    s.targetVel = { 0.0, 0.0 };
    s.targetDesiredVel = { 0.0, 0.0 };
    s.aimPos = { panelW * 0.50, panelH * 0.50 };
    s.observedTarget = s.targetPos;
    s.predictedTarget = s.targetPos;

    s.usedCaptureDelayMs = 0.0;
    s.usedInferenceDelayMs = 0.0;
    s.usedInputDelayMs = 0.0;
    s.usedExtraDelayMs = 0.0;
    s.usedTotalDelayMs = 0.0;
    s.lastErrorPx = 0.0;
    s.lastMoveX = 0;
    s.lastMoveY = 0;

    s.ctrlPrevX = 0.0;
    s.ctrlPrevY = 0.0;
    s.ctrlPrevVelocityX = 0.0;
    s.ctrlPrevVelocityY = 0.0;
    s.ctrlPrevTimeSec = 0.0;

    aim_sim_reset_wind_state(s);
    s.windEnabledSnapshot = config.wind_mouse_enabled;
    s.windGSnapshot = static_cast<double>(config.wind_G);
    s.windWSnapshot = static_cast<double>(config.wind_W);
    s.windMSnapshot = static_cast<double>(config.wind_M);
    s.windDSnapshot = static_cast<double>(config.wind_D);

    s.history.clear();
    s.queuedMoves.clear();
    s.targetTrail.clear();
    s.aimTrail.clear();

    s.lastWallTime = std::chrono::steady_clock::now();
    aim_sim_choose_target_motion(s);
}

static double aim_sim_get_live_inference_ms()
{
    double delayMs = static_cast<double>(config.aim_sim_inference_delay_ms);

    if (config.backend == "DML")
    {
        if (dml_detector)
            delayMs = dml_detector->lastInferenceTimeDML.count();
    }
#ifdef USE_CUDA
    else
    {
        delayMs = trt_detector.lastInferenceTime.count();
    }
#endif
    if (!std::isfinite(delayMs))
        delayMs = static_cast<double>(config.aim_sim_inference_delay_ms);

    return std::clamp(delayMs, 0.0, 120.0);
}

static AimSimHistorySample aim_sim_sample_history(const std::deque<AimSimHistorySample>& history, double sampleTime)
{
    if (history.empty())
        return {};

    if (sampleTime <= history.front().timeSec)
        return history.front();
    if (sampleTime >= history.back().timeSec)
        return history.back();

    for (size_t i = 1; i < history.size(); ++i)
    {
        const auto& b = history[i];
        if (b.timeSec < sampleTime)
            continue;

        const auto& a = history[i - 1];
        const double dt = std::max(1e-6, b.timeSec - a.timeSec);
        const double t = std::clamp((sampleTime - a.timeSec) / dt, 0.0, 1.0);

        AimSimHistorySample out;
        out.timeSec = sampleTime;
        out.target.x = a.target.x + (b.target.x - a.target.x) * t;
        out.target.y = a.target.y + (b.target.y - a.target.y) * t;
        out.aim.x = a.aim.x + (b.aim.x - a.aim.x) * t;
        out.aim.y = a.aim.y + (b.aim.y - a.aim.y) * t;
        return out;
    }

    return history.back();
}

static double aim_sim_calculate_speed_multiplier(double distance, double maxDistance)
{
    const double snapRadius = std::max(0.0, static_cast<double>(config.snapRadius));
    const double nearRadius = std::max(1e-3, static_cast<double>(config.nearRadius));
    const double curveExp = std::max(0.1, static_cast<double>(config.speedCurveExponent));
    const double minSpeed = static_cast<double>(config.minSpeedMultiplier);
    const double maxSpeed = static_cast<double>(config.maxSpeedMultiplier);

    if (distance < snapRadius)
        return minSpeed * config.snapBoostFactor;

    if (distance < nearRadius)
    {
        const double t = distance / nearRadius;
        const double curve = 1.0 - std::pow(1.0 - t, curveExp);
        return minSpeed + (maxSpeed - minSpeed) * curve;
    }

    const double norm = std::clamp(distance / std::max(1e-6, maxDistance), 0.0, 1.0);
    return minSpeed + (maxSpeed - minSpeed) * norm;
}

static void aim_sim_enqueue_move(AimSimulationState& s, double executeAtSec, int mx, int my)
{
    if (mx == 0 && my == 0)
        return;

    if (!s.queuedMoves.empty())
    {
        AimSimQueuedMove& back = s.queuedMoves.back();
        if (std::abs(back.executeAtSec - executeAtSec) <= 1e-6)
        {
            back.mx += mx;
            back.my += my;
            return;
        }
    }

    const double inputDelayMs = std::clamp(static_cast<double>(config.aim_sim_input_delay_ms), 0.0, 60.0);
    const double maxFps = std::clamp(
        static_cast<double>(std::max(config.aim_sim_fps_min, config.aim_sim_fps_max)),
        15.0, 360.0);
    const double minFrameMs = 1000.0 / std::max(1.0, maxFps);
    const double delayedFrames = inputDelayMs / std::max(0.1, minFrameMs);
    const double stepsPerFrame = config.wind_mouse_enabled ? 5.0 : 1.0;
    const int needed = static_cast<int>(std::ceil((delayedFrames + 2.0) * stepsPerFrame));
    const size_t queueLimit = static_cast<size_t>(std::clamp(needed, 32, 256));

    if (s.queuedMoves.size() >= queueLimit)
        s.queuedMoves.pop_front();

    s.queuedMoves.push_back({ executeAtSec, mx, my });
}

static void aim_sim_enqueue_relative_path(AimSimulationState& s, double executeAtSec, int dx, int dy)
{
    if (dx == 0 && dy == 0)
        return;

    if (!config.wind_mouse_enabled)
    {
        aim_sim_enqueue_move(s, executeAtSec, dx, dy);
        return;
    }

    s.windCarryX += static_cast<double>(dx);
    s.windCarryY += static_cast<double>(dy);

    const double baseG = std::clamp(static_cast<double>(config.wind_G), 0.05, 50.0);
    const double baseW = std::clamp(static_cast<double>(config.wind_W), 0.0, 80.0);
    const double baseM = std::max(1.0, static_cast<double>(config.wind_M));
    const double baseD = std::max(1.0, static_cast<double>(config.wind_D));

    std::uniform_real_distribution<double> noiseDist(-1.0, 1.0);
    std::uniform_real_distribution<double> clipDist(0.55, 1.0);
    constexpr double twoPi = 6.28318530717958647692;

    const double carryMag = std::hypot(s.windCarryX, s.windCarryY);
    const int maxSubsteps = std::clamp(static_cast<int>(carryMag * 0.24) + 1, 1, 5);

    for (int i = 0; i < maxSubsteps; ++i)
    {
        const double dist = std::hypot(s.windCarryX, s.windCarryY);
        const double velMag = std::hypot(s.windVelX, s.windVelY);
        if (dist < 0.20 && velMag < 0.12)
            break;

        const double normDist = std::clamp(dist / baseD, 0.0, 1.0);
        const double pullGain = baseG * (0.25 + 0.75 * normDist);
        const double noiseAmp = baseW * (0.15 + 0.85 * normDist);

        double pullX = 0.0;
        double pullY = 0.0;
        if (dist > 1e-8)
        {
            pullX = s.windCarryX / dist * pullGain;
            pullY = s.windCarryY / dist * pullGain;
        }

        s.windPatternRateA = std::clamp(s.windPatternRateA + noiseDist(s.windRng) * 0.004, 0.025, 0.280);
        s.windPatternRateB = std::clamp(s.windPatternRateB + noiseDist(s.windRng) * 0.004, 0.025, 0.280);

        const double stepTempo = 0.20 + 0.95 * normDist;
        s.windPatternPhaseA += s.windPatternRateA * stepTempo;
        s.windPatternPhaseB += s.windPatternRateB * stepTempo;
        if (s.windPatternPhaseA > twoPi) s.windPatternPhaseA = std::fmod(s.windPatternPhaseA, twoPi);
        if (s.windPatternPhaseB > twoPi) s.windPatternPhaseB = std::fmod(s.windPatternPhaseB, twoPi);

        const double oscAX = std::sin(s.windPatternPhaseA);
        const double oscBX = std::sin(s.windPatternPhaseB + 1.61803398875);
        const double oscAY = std::cos(s.windPatternPhaseA * 0.79 + 0.35);
        const double oscBY = std::cos(s.windPatternPhaseB * 1.17 - 0.48);

        const double patternAmp = baseW * (0.05 + 0.55 * normDist);
        const double patternTargetX = (oscAX + 0.58 * oscBX) * patternAmp;
        const double patternTargetY = (oscAY + 0.58 * oscBY) * patternAmp;
        const double patternBlend = 0.12 + 0.20 * normDist;
        s.windPatternX = s.windPatternX * (1.0 - patternBlend) + patternTargetX * patternBlend;
        s.windPatternY = s.windPatternY * (1.0 - patternBlend) + patternTargetY * patternBlend;

        s.windNoiseX = s.windNoiseX * 0.72 + noiseDist(s.windRng) * noiseAmp * 0.28;
        s.windNoiseY = s.windNoiseY * 0.72 + noiseDist(s.windRng) * noiseAmp * 0.28;

        const double windForceX = s.windNoiseX + s.windPatternX * 0.42;
        const double windForceY = s.windNoiseY + s.windPatternY * 0.42;

        const double drag = 0.82 + (1.0 - normDist) * 0.10;
        s.windVelX = s.windVelX * drag + pullX + windForceX;
        s.windVelY = s.windVelY * drag + pullY + windForceY;

        const double vCap = std::max(0.65, baseM * (0.30 + 0.70 * normDist));
        const double newVelMag = std::hypot(s.windVelX, s.windVelY);
        if (newVelMag > vCap)
        {
            const double clip = vCap * clipDist(s.windRng);
            s.windVelX = (s.windVelX / newVelMag) * clip;
            s.windVelY = (s.windVelY / newVelMag) * clip;
        }

        s.windFracX += s.windVelX;
        s.windFracY += s.windVelY;

        const int stepX = static_cast<int>(std::round(s.windFracX));
        const int stepY = static_cast<int>(std::round(s.windFracY));
        if (stepX == 0 && stepY == 0)
            continue;

        s.windFracX -= static_cast<double>(stepX);
        s.windFracY -= static_cast<double>(stepY);
        s.windCarryX -= static_cast<double>(stepX);
        s.windCarryY -= static_cast<double>(stepY);
        aim_sim_enqueue_move(s, executeAtSec, stepX, stepY);
    }

    const double carryCap = 120.0;
    const double finalCarryMag = std::hypot(s.windCarryX, s.windCarryY);
    if (finalCarryMag > carryCap)
    {
        const double scale = carryCap / finalCarryMag;
        s.windCarryX *= scale;
        s.windCarryY *= scale;
    }
}

static AimSimVec2 aim_sim_counts_to_world_delta(int mx, int my, int detRes, double scaleToCtrlX, double scaleToCtrlY)
{
    if (detRes <= 0 || scaleToCtrlX <= 1e-8 || scaleToCtrlY <= 1e-8)
        return {};

    const Config::GameProfile* gpPtr = nullptr;
    auto activeIt = config.game_profiles.find(config.active_game);
    if (activeIt != config.game_profiles.end())
        gpPtr = &activeIt->second;
    else
    {
        auto unifiedIt = config.game_profiles.find("UNIFIED");
        if (unifiedIt != config.game_profiles.end())
            gpPtr = &unifiedIt->second;
    }
    if (!gpPtr)
        return {};
    const auto& gp = *gpPtr;

    if (gp.sens == 0.0 || gp.yaw == 0.0 || gp.pitch == 0.0)
        return {};

    const double fovNow = std::max(1.0, static_cast<double>(config.fovX));
    const double fovScale = (gp.fovScaled && gp.baseFOV > 1.0) ? (fovNow / gp.baseFOV) : 1.0;
    const double degX = static_cast<double>(mx) * gp.sens * gp.yaw * fovScale;
    const double degY = static_cast<double>(my) * gp.sens * gp.pitch * fovScale;

    const double degPerPxX = fovNow / static_cast<double>(detRes);
    const double degPerPxY = std::max(1e-6, static_cast<double>(config.fovY) / static_cast<double>(detRes));

    const double controlPxX = degX / degPerPxX;
    const double controlPxY = degY / degPerPxY;

    AimSimVec2 deltaWorld;
    deltaWorld.x = controlPxX / scaleToCtrlX;
    deltaWorld.y = controlPxY / scaleToCtrlY;
    return deltaWorld;
}

static double aim_sim_next_frame_dt(AimSimulationState& s)
{
    const double fpsMin = std::clamp(static_cast<double>(std::min(config.aim_sim_fps_min, config.aim_sim_fps_max)), 15.0, 360.0);
    const double fpsMax = std::clamp(static_cast<double>(std::max(config.aim_sim_fps_min, config.aim_sim_fps_max)), 15.0, 360.0);

    s.fpsRetargetSec -= s.lastFrameDtSec;
    if (s.fpsRetargetSec <= 0.0)
    {
        s.targetFps = aim_sim_random_range(s, fpsMin, fpsMax);
        s.fpsRetargetSec = aim_sim_random_range(s, 0.12, 0.55);
    }

    const double alpha = 1.0 - std::exp(-s.lastFrameDtSec * 5.0);
    s.currentFps += (s.targetFps - s.currentFps) * alpha;

    const double range = std::max(0.0, fpsMax - fpsMin);
    const double jitter = range * std::clamp(static_cast<double>(config.aim_sim_fps_jitter), 0.0, 0.8);
    const double instantFps = std::clamp(
        s.currentFps + aim_sim_random_range(s, -jitter, jitter),
        fpsMin, fpsMax
    );

    s.lastFrameDtSec = 1.0 / std::max(15.0, instantFps);
    return s.lastFrameDtSec;
}

static void aim_sim_step(AimSimulationState& s, double dtSec, int panelW, int panelH)
{
    s.simTimeSec += dtSec;
    aim_sim_sync_wind_config(s);

    s.targetMotionRetargetSec -= dtSec;
    if (s.targetMotionRetargetSec <= 0.0)
        aim_sim_choose_target_motion(s);

    const double maxAccel = std::max(20.0, static_cast<double>(config.aim_sim_target_accel));
    const double dvX = s.targetDesiredVel.x - s.targetVel.x;
    const double dvY = s.targetDesiredVel.y - s.targetVel.y;
    const double dvLen = std::hypot(dvX, dvY);
    const double maxDv = maxAccel * dtSec;
    if (dvLen > maxDv && dvLen > 1e-8)
    {
        const double k = maxDv / dvLen;
        s.targetVel.x += dvX * k;
        s.targetVel.y += dvY * k;
    }
    else
    {
        s.targetVel.x = s.targetDesiredVel.x;
        s.targetVel.y = s.targetDesiredVel.y;
    }

    if (aim_sim_vec_len(s.targetDesiredVel) < 1.0)
    {
        const double damp = std::exp(-dtSec * 2.8);
        s.targetVel.x *= damp;
        s.targetVel.y *= damp;
    }

    s.targetPos.x += s.targetVel.x * dtSec;
    s.targetPos.y += s.targetVel.y * dtSec;

    const double margin = 10.0;
    const double maxX = std::max(margin, static_cast<double>(panelW) - margin);
    const double maxY = std::max(margin, static_cast<double>(panelH) - margin);

    if (s.targetPos.x < margin)
    {
        s.targetPos.x = margin;
        s.targetVel.x = std::abs(s.targetVel.x) * 0.65;
        s.targetDesiredVel.x = std::abs(s.targetDesiredVel.x);
    }
    else if (s.targetPos.x > maxX)
    {
        s.targetPos.x = maxX;
        s.targetVel.x = -std::abs(s.targetVel.x) * 0.65;
        s.targetDesiredVel.x = -std::abs(s.targetDesiredVel.x);
    }

    if (s.targetPos.y < margin)
    {
        s.targetPos.y = margin;
        s.targetVel.y = std::abs(s.targetVel.y) * 0.65;
        s.targetDesiredVel.y = std::abs(s.targetDesiredVel.y);
    }
    else if (s.targetPos.y > maxY)
    {
        s.targetPos.y = maxY;
        s.targetVel.y = -std::abs(s.targetVel.y) * 0.65;
        s.targetDesiredVel.y = -std::abs(s.targetDesiredVel.y);
    }

    s.history.push_back({ s.simTimeSec, s.targetPos, s.aimPos });
    while (!s.history.empty() && (s.simTimeSec - s.history.front().timeSec) > 3.0)
        s.history.pop_front();

    const double captureMs = std::clamp(static_cast<double>(config.aim_sim_capture_delay_ms), 0.0, 80.0);
    const double inferenceMs = config.aim_sim_use_live_inference
        ? aim_sim_get_live_inference_ms()
        : std::clamp(static_cast<double>(config.aim_sim_inference_delay_ms), 0.0, 120.0);
    const double inputMs = std::clamp(static_cast<double>(config.aim_sim_input_delay_ms), 0.0, 60.0);
    const double extraMs = std::clamp(static_cast<double>(config.aim_sim_extra_delay_ms), 0.0, 60.0);
    const double totalObsMs = captureMs + inferenceMs + extraMs;

    s.usedCaptureDelayMs = captureMs;
    s.usedInferenceDelayMs = inferenceMs;
    s.usedInputDelayMs = inputMs;
    s.usedExtraDelayMs = extraMs;
    s.usedTotalDelayMs = totalObsMs + inputMs;

    const double sampleTime = s.simTimeSec - (totalObsMs * 0.001);
    const AimSimHistorySample delayed = aim_sim_sample_history(s.history, sampleTime);
    s.observedTarget = delayed.target;

    const int detRes = std::max(32, config.detection_resolution);
    const double scaleToCtrlX = static_cast<double>(detRes) / std::max(1, panelW);
    const double scaleToCtrlY = static_cast<double>(detRes) / std::max(1, panelH);
    const double centerCtrlX = static_cast<double>(detRes) * 0.5;
    const double centerCtrlY = static_cast<double>(detRes) * 0.5;

    const double observedCtrlX = centerCtrlX + (delayed.target.x - delayed.aim.x) * scaleToCtrlX;
    const double observedCtrlY = centerCtrlY + (delayed.target.y - delayed.aim.y) * scaleToCtrlY;

    double predictedCtrlX = observedCtrlX;
    double predictedCtrlY = observedCtrlY;

    if (!s.controllerInitialized)
    {
        s.controllerInitialized = true;
        s.ctrlPrevX = observedCtrlX;
        s.ctrlPrevY = observedCtrlY;
        s.ctrlPrevVelocityX = 0.0;
        s.ctrlPrevVelocityY = 0.0;
        s.ctrlPrevTimeSec = s.simTimeSec;
    }
    else
    {
        const double obsDt = std::max(s.simTimeSec - s.ctrlPrevTimeSec, 1e-8);
        const double vx = std::clamp((observedCtrlX - s.ctrlPrevX) / obsDt, -20000.0, 20000.0);
        const double vy = std::clamp((observedCtrlY - s.ctrlPrevY) / obsDt, -20000.0, 20000.0);

        s.ctrlPrevX = observedCtrlX;
        s.ctrlPrevY = observedCtrlY;
        s.ctrlPrevVelocityX = vx;
        s.ctrlPrevVelocityY = vy;
        s.ctrlPrevTimeSec = s.simTimeSec;

        predictedCtrlX = observedCtrlX + vx * static_cast<double>(config.predictionInterval) + vx * 0.002;
        predictedCtrlY = observedCtrlY + vy * static_cast<double>(config.predictionInterval) + vy * 0.002;
    }

    if (!std::isfinite(predictedCtrlX))
        predictedCtrlX = observedCtrlX;
    if (!std::isfinite(predictedCtrlY))
        predictedCtrlY = observedCtrlY;

    const double offsetX = predictedCtrlX - centerCtrlX;
    const double offsetY = predictedCtrlY - centerCtrlY;
    const double distancePx = std::hypot(offsetX, offsetY);

    s.lastMoveX = 0;
    s.lastMoveY = 0;

    if (distancePx > 0.0)
    {
        const double degPerPxX = static_cast<double>(config.fovX) / static_cast<double>(detRes);
        const double degPerPxY = static_cast<double>(config.fovY) / static_cast<double>(detRes);
        const double maxDistanceCtrl = std::hypot(static_cast<double>(detRes), static_cast<double>(detRes)) * 0.5;
        const double speed = aim_sim_calculate_speed_multiplier(distancePx, maxDistanceCtrl);
        const auto countsPair = config.degToCounts(offsetX * degPerPxX, offsetY * degPerPxY, config.fovX);

        double corr = 1.0;
        const double fps = 1.0 / std::max(1e-8, dtSec);
        if (fps > 30.0)
            corr = 30.0 / fps;

        const double moveX = countsPair.first * speed * corr;
        const double moveY = countsPair.second * speed * corr;

        const int mx = static_cast<int>(moveX);
        const int my = static_cast<int>(moveY);
        aim_sim_enqueue_relative_path(s, s.simTimeSec + inputMs * 0.001, mx, my);
    }

    while (!s.queuedMoves.empty() && s.queuedMoves.front().executeAtSec <= s.simTimeSec)
    {
        const AimSimQueuedMove m = s.queuedMoves.front();
        s.queuedMoves.pop_front();

        const AimSimVec2 worldDelta = aim_sim_counts_to_world_delta(m.mx, m.my, detRes, scaleToCtrlX, scaleToCtrlY);
        s.aimPos.x += worldDelta.x;
        s.aimPos.y += worldDelta.y;
        s.lastMoveX += m.mx;
        s.lastMoveY += m.my;
    }

    const double aimMargin = 6.0;
    s.aimPos.x = std::clamp(s.aimPos.x, aimMargin, std::max(aimMargin, static_cast<double>(panelW) - aimMargin));
    s.aimPos.y = std::clamp(s.aimPos.y, aimMargin, std::max(aimMargin, static_cast<double>(panelH) - aimMargin));

    s.predictedTarget.x = s.aimPos.x + (predictedCtrlX - centerCtrlX) / scaleToCtrlX;
    s.predictedTarget.y = s.aimPos.y + (predictedCtrlY - centerCtrlY) / scaleToCtrlY;
    s.predictedTarget.x = std::clamp(s.predictedTarget.x, 0.0, static_cast<double>(panelW));
    s.predictedTarget.y = std::clamp(s.predictedTarget.y, 0.0, static_cast<double>(panelH));
    s.lastErrorPx = std::hypot(s.targetPos.x - s.aimPos.x, s.targetPos.y - s.aimPos.y);

    if (config.aim_sim_show_history)
    {
        s.targetTrail.push_back(s.targetPos);
        s.aimTrail.push_back(s.aimPos);
        const size_t maxTrail = 160;
        while (s.targetTrail.size() > maxTrail) s.targetTrail.pop_front();
        while (s.aimTrail.size() > maxTrail) s.aimTrail.pop_front();
    }
    else
    {
        s.targetTrail.clear();
        s.aimTrail.clear();
    }
}

static void draw_aim_sim_panel(
    Game_overlay* overlay,
    AimSimulationState& s,
    int screenW,
    int screenH,
    int originX,
    int originY)
{
    if (!overlay || !config.aim_sim_enabled)
        return;

    const int panelW = std::clamp(config.aim_sim_width, 220, 1920);
    const int panelH = std::clamp(config.aim_sim_height, 180, 1080);
    int panelX = std::max(0, config.aim_sim_x);
    int panelY = screenH - panelH - std::max(0, config.aim_sim_y);

    const int minX = -panelW + 20;
    const int minY = -panelH + 20;
    const int maxX = std::max(20, screenW - 20);
    const int maxY = std::max(20, screenH - 20);
    panelX = std::clamp(panelX, minX, maxX);
    panelY = std::clamp(panelY, minY, maxY);

    if (!s.initialized || s.panelW != panelW || s.panelH != panelH)
        aim_sim_reset(s, panelW, panelH);

    auto now = std::chrono::steady_clock::now();
    double dtReal = 1.0 / 120.0;
    if (s.lastWallTime.time_since_epoch().count() != 0)
    {
        dtReal = std::chrono::duration<double>(now - s.lastWallTime).count();
        dtReal = std::clamp(dtReal, 0.001, 0.08);
    }
    s.lastWallTime = now;
    s.accumulatorSec = std::min(0.15, s.accumulatorSec + dtReal);

    int loops = 0;
    while (loops < 20)
    {
        const double frameDt = aim_sim_next_frame_dt(s);
        if (s.accumulatorSec < frameDt)
            break;
        aim_sim_step(s, frameDt, panelW, panelH);
        s.accumulatorSec -= frameDt;
        ++loops;
    }
    if (loops >= 20)
        s.accumulatorSec = 0.0;

    const float fx = static_cast<float>(originX + panelX);
    const float fy = static_cast<float>(originY + panelY);
    const float fw = static_cast<float>(panelW);
    const float fh = static_cast<float>(panelH);

    overlay->FillRect({ fx, fy, fw, fh }, ARGB(155, 12, 16, 20));
    overlay->AddRect({ fx, fy, fw, fh }, ARGB(230, 185, 190, 200), 1.5f);

    const float cx = fx + fw * 0.5f;
    const float cy = fy + fh * 0.5f;
    overlay->AddLine({ fx, cy, fx + fw, cy }, ARGB(90, 255, 255, 255), 1.0f);
    overlay->AddLine({ cx, fy, cx, fy + fh }, ARGB(90, 255, 255, 255), 1.0f);

    if (config.aim_sim_show_history && s.targetTrail.size() > 1)
    {
        const size_t n = s.targetTrail.size();
        for (size_t i = 1; i < n; ++i)
        {
            const float alpha = static_cast<float>(50 + (180 * i) / n);
            const auto& p0 = s.targetTrail[i - 1];
            const auto& p1 = s.targetTrail[i];
            overlay->AddLine(
                { fx + static_cast<float>(p0.x), fy + static_cast<float>(p0.y),
                  fx + static_cast<float>(p1.x), fy + static_cast<float>(p1.y) },
                ARGB(static_cast<uint8_t>(alpha), 255, 120, 120), 1.2f);
        }
    }

    if (config.aim_sim_show_history && s.aimTrail.size() > 1)
    {
        const size_t n = s.aimTrail.size();
        for (size_t i = 1; i < n; ++i)
        {
            const float alpha = static_cast<float>(50 + (180 * i) / n);
            const auto& p0 = s.aimTrail[i - 1];
            const auto& p1 = s.aimTrail[i];
            overlay->AddLine(
                { fx + static_cast<float>(p0.x), fy + static_cast<float>(p0.y),
                  fx + static_cast<float>(p1.x), fy + static_cast<float>(p1.y) },
                ARGB(static_cast<uint8_t>(alpha), 120, 220, 255), 1.2f);
        }
    }

    if (config.aim_sim_show_observed)
    {
        overlay->FillCircle(
            { fx + static_cast<float>(s.observedTarget.x), fy + static_cast<float>(s.observedTarget.y), 4.0f },
            ARGB(230, 255, 205, 90));
    }

    overlay->AddCircle(
        { fx + static_cast<float>(s.predictedTarget.x), fy + static_cast<float>(s.predictedTarget.y), 6.0f },
        ARGB(210, 255, 245, 100), 1.5f);
    overlay->FillCircle(
        { fx + static_cast<float>(s.targetPos.x), fy + static_cast<float>(s.targetPos.y), 5.0f },
        ARGB(250, 255, 90, 90));
    overlay->FillCircle(
        { fx + static_cast<float>(s.aimPos.x), fy + static_cast<float>(s.aimPos.y), 4.0f },
        ARGB(255, 80, 200, 255));
    overlay->AddCircle(
        { fx + static_cast<float>(s.aimPos.x), fy + static_cast<float>(s.aimPos.y), 9.0f },
        ARGB(235, 80, 200, 255), 1.8f);
    overlay->AddLine(
        { fx + static_cast<float>(s.aimPos.x), fy + static_cast<float>(s.aimPos.y),
          fx + static_cast<float>(s.targetPos.x), fy + static_cast<float>(s.targetPos.y) },
        ARGB(160, 255, 255, 255), 1.0f);

    const float tx = fx + 12.0f;
    float ty = fy + 8.0f;
    const float step = 21.0f;
    overlay->AddText(tx, ty, L"Aim Simulation", 20.0f, ARGB(245, 230, 235, 245));
    ty += step;

    wchar_t line[256]{};
    const double simFps = 1.0 / std::max(1e-6, s.lastFrameDtSec);
    swprintf_s(line, L"FPS %.1f (range %d..%d)", simFps, config.aim_sim_fps_min, config.aim_sim_fps_max);
    overlay->AddText(tx, ty, line, 17.0f, ARGB(220, 210, 220, 230));
    ty += step;

    swprintf_s(line, L"Delay %.1f ms (cap %.1f + inf %.1f + in %.1f + extra %.1f)",
        s.usedTotalDelayMs, s.usedCaptureDelayMs, s.usedInferenceDelayMs, s.usedInputDelayMs, s.usedExtraDelayMs);
    overlay->AddText(tx, ty, line, 17.0f, ARGB(220, 210, 220, 230));
    ty += step;

    swprintf_s(line, L"Target speed %.0f px/s | Error %.1f px", aim_sim_vec_len(s.targetVel), s.lastErrorPx);
    overlay->AddText(tx, ty, line, 17.0f, ARGB(220, 210, 220, 230));
    ty += step;

    swprintf_s(line, L"Move counts dx=%d dy=%d", s.lastMoveX, s.lastMoveY);
    overlay->AddText(tx, ty, line, 17.0f, ARGB(220, 210, 220, 230));
}

void GameOverlayThreadFunction()
{
    AimSimulationState aimSimState;

    while (!shouldExit)
    {
        bool enabled = false;
        int detRes = 320;
        int monitorIdx = 0;
        int maxFps = 0;
        bool drawFrame = false;
        bool drawBoxes = true;
        bool drawFuture = true;
        bool showCorrection = true;
        int fa = 180, fr = 255, fg = 255, fb = 255;
        int ba = 255, br = 0, bg = 255, bb = 0;
        float frameThickness = 1.5f;
        float boxThickness = 2.0f;
        float futurePointRadius = 5.0f;

        {
            std::lock_guard<std::mutex> lock(configMutex);
            enabled = config.game_overlay_enabled;
            detRes = config.detection_resolution;
            monitorIdx = config.monitor_idx;
            maxFps = config.game_overlay_max_fps;
            drawFrame = config.game_overlay_draw_frame;
            drawBoxes = config.game_overlay_draw_boxes;
            drawFuture = config.game_overlay_draw_future;
            showCorrection = config.game_overlay_show_target_correction;
            fa = config.game_overlay_frame_a; fr = config.game_overlay_frame_r; fg = config.game_overlay_frame_g; fb = config.game_overlay_frame_b;
            ba = config.game_overlay_box_a; br = config.game_overlay_box_r; bg = config.game_overlay_box_g; bb = config.game_overlay_box_b;
            frameThickness = config.game_overlay_frame_thickness;
            boxThickness = config.game_overlay_box_thickness;
            futurePointRadius = config.game_overlay_future_point_radius;
        }

        if (!enabled)
        {
            StopGameOverlay();
            std::this_thread::sleep_for(std::chrono::milliseconds(80));
            continue;
        }

        if (!gameOverlayPtr)
        {
            gameOverlayPtr = new Game_overlay();
            if (!gameOverlayPtr->Start())
            {
                delete gameOverlayPtr;
                gameOverlayPtr = nullptr;
                std::cerr << "[GameOverlay] Failed to start overlay window." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
                continue;
            }
        }

        gameOverlayPtr->SetMaxFPS(maxFps > 0 ? static_cast<unsigned>(maxFps) : 0u);
        gameOverlayPtr->BeginFrame();

        const RECT monRect = GetMonitorRectByIndexOrPrimary(monitorIdx);
        const int monLeft = monRect.left;
        const int monTop = monRect.top;
        const int monW = static_cast<int>(monRect.right - monRect.left);
        const int monH = static_cast<int>(monRect.bottom - monRect.top);
        const int sw = std::max(1, monW);
        const int sh = std::max(1, monH);
        const float capW = static_cast<float>(std::max(1, detRes));
        const float capH = static_cast<float>(std::max(1, detRes));
        const float offX = static_cast<float>(monLeft) + (static_cast<float>(sw) - capW) * 0.5f;
        const float offY = static_cast<float>(monTop) + (static_cast<float>(sh) - capH) * 0.5f;

        if (drawFrame)
        {
            gameOverlayPtr->AddRect({ offX, offY, capW, capH }, ARGB((uint8_t)fa, (uint8_t)fr, (uint8_t)fg, (uint8_t)fb), frameThickness);
        }

        std::vector<cv::Rect> boxesCopy;
        {
            std::lock_guard<std::mutex> lk(detectionBuffer.mutex);
            boxesCopy = detectionBuffer.boxes;
        }

        if (drawBoxes)
        {
            const OverlayColor boxCol = ARGB((uint8_t)ba, (uint8_t)br, (uint8_t)bg, (uint8_t)bb);
            for (const auto& b : boxesCopy)
            {
                gameOverlayPtr->AddRect(
                    { offX + static_cast<float>(b.x), offY + static_cast<float>(b.y), static_cast<float>(b.width), static_cast<float>(b.height) },
                    boxCol,
                    boxThickness);
            }
        }

        if (drawFuture && globalMouseThread)
        {
            const auto pts = globalMouseThread->getFuturePositions();
            for (const auto& p : pts)
            {
                gameOverlayPtr->FillCircle(
                    { offX + static_cast<float>(p.first), offY + static_cast<float>(p.second), futurePointRadius },
                    ARGB(190, 120, 230, 120));
            }
        }

        if (showCorrection)
        {
            const float cx = static_cast<float>(monLeft) + static_cast<float>(sw) * 0.5f;
            const float cy = static_cast<float>(monTop) + static_cast<float>(sh) * 0.5f;
            const float scope = std::max(4.0f, static_cast<float>(config.aim_bot_scope));
            gameOverlayPtr->AddCircle({ cx, cy, scope }, ARGB(140, 80, 120, 255), 1.5f);
            gameOverlayPtr->AddLine({ cx - 8.0f, cy, cx + 8.0f, cy }, ARGB(200, 255, 255, 255), 1.0f);
            gameOverlayPtr->AddLine({ cx, cy - 8.0f, cx, cy + 8.0f }, ARGB(200, 255, 255, 255), 1.0f);
        }

        if (config.aim_sim_enabled)
        {
            draw_aim_sim_panel(gameOverlayPtr, aimSimState, sw, sh, monLeft, monTop);
        }

        gameOverlayPtr->EndFrame();
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }

    StopGameOverlay();
}
}

namespace
{
class TeeStreamBuf : public std::streambuf
{
public:
    TeeStreamBuf(std::streambuf* primary, std::streambuf* secondary)
        : primary_(primary), secondary_(secondary) {}

protected:
    int overflow(int ch) override
    {
        if (ch == EOF)
            return !EOF;

        std::lock_guard<std::mutex> lock(mutex_);
        const int p = primary_ ? primary_->sputc(static_cast<char>(ch)) : ch;
        const int s = secondary_ ? secondary_->sputc(static_cast<char>(ch)) : ch;
        return (p == EOF || s == EOF) ? EOF : ch;
    }

    std::streamsize xsputn(const char* s, std::streamsize n) override
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (primary_)
            primary_->sputn(s, n);
        if (secondary_)
            secondary_->sputn(s, n);
        return n;
    }

    int sync() override
    {
        std::lock_guard<std::mutex> lock(mutex_);
        int p = primary_ ? primary_->pubsync() : 0;
        int s = secondary_ ? secondary_->pubsync() : 0;
        return (p == 0 && s == 0) ? 0 : -1;
    }

private:
    std::streambuf* primary_;
    std::streambuf* secondary_;
    std::mutex mutex_;
};

std::mutex g_console_log_mutex;
std::ofstream g_console_log_file;
std::unique_ptr<TeeStreamBuf> g_cout_tee;
std::unique_ptr<TeeStreamBuf> g_cerr_tee;
std::streambuf* g_orig_cout = nullptr;
std::streambuf* g_orig_cerr = nullptr;
bool g_console_file_logging_enabled = false;
const char* k_console_log_path = "runtime_console.log";
}

void SetConsoleFileLoggingEnabled(bool enabled, bool clear_on_enable)
{
    std::lock_guard<std::mutex> lock(g_console_log_mutex);

    if (enabled)
    {
        if (g_console_file_logging_enabled)
            return;

        std::ios::openmode mode = std::ios::out | std::ios::binary;
        mode |= clear_on_enable ? std::ios::trunc : std::ios::app;
        g_console_log_file.open(k_console_log_path, mode);
        if (!g_console_log_file.is_open())
            return;

        g_orig_cout = std::cout.rdbuf();
        g_orig_cerr = std::cerr.rdbuf();
        g_cout_tee = std::make_unique<TeeStreamBuf>(g_orig_cout, g_console_log_file.rdbuf());
        g_cerr_tee = std::make_unique<TeeStreamBuf>(g_orig_cerr, g_console_log_file.rdbuf());
        std::cout.rdbuf(g_cout_tee.get());
        std::cerr.rdbuf(g_cerr_tee.get());
        g_console_file_logging_enabled = true;
        return;
    }

    if (!g_console_file_logging_enabled)
        return;

    if (g_orig_cout)
        std::cout.rdbuf(g_orig_cout);
    if (g_orig_cerr)
        std::cerr.rdbuf(g_orig_cerr);

    g_cout_tee.reset();
    g_cerr_tee.reset();
    if (g_console_log_file.is_open())
        g_console_log_file.close();

    g_console_file_logging_enabled = false;
}


//ERRORS: '(': illegal token on right side of '::'
//'exists': identifier not found
//'exists' : identifier not found
//'exists' : is not a member of 'std::filesystem'
//'exists' : is not a member of 'std::filesystem'
//'modelPath' uses undefined class 'std::filesystem::path'
// namespace "std::filesystem" has no member "exists"
//namespace "std::filesystem" has no member "exists"
//syntax error : ')'
//use of undefined type 'std::filesystem::path'
void createInputDevices()
{
    if (arduinoSerial)
    {
        delete arduinoSerial;
        arduinoSerial = nullptr;
    }

    if (kmboxSerial)
    {
        delete kmboxSerial;
        kmboxSerial = nullptr;
    }

    if (makcu_conn)
    {
        delete makcu_conn;
        makcu_conn = nullptr;
    }

    if (kmboxNetSerial)
    {
        delete kmboxNetSerial;
        kmboxNetSerial = nullptr;
    }

    if (config.input_method == "ARDUINO")
    {
        std::cout << "[Mouse] Using Arduino method input." << std::endl;
        arduinoSerial = new SerialConnection(config.arduino_port, config.arduino_baudrate);
    }
    else if (config.input_method == "KMBOX_B")
    {
        std::cout << "[Mouse] Using KMBOX_B method input." << std::endl;
        kmboxSerial = new KmboxConnection(config.kmbox_b_port, config.kmbox_b_baudrate);
        if (!kmboxSerial->isOpen())
        {
            std::cerr << "[Kmbox] Error connecting to Kmbox serial." << std::endl;
            delete kmboxSerial;
            kmboxSerial = nullptr;
        }
    }
    else if (config.input_method == "KMBOX_NET")
    {
        std::cout << "[Mouse] Using KMBOX_NET input." << std::endl;
        kmboxNetSerial = new KmboxNetConnection(config.kmbox_net_ip, config.kmbox_net_port, config.kmbox_net_uuid);
        if (!kmboxNetSerial->isOpen())
        {
            std::cerr << "[KmboxNet] Error connecting." << std::endl;
            delete kmboxNetSerial; kmboxNetSerial = nullptr;
        }
    }
    else if (config.input_method == "MAKCU")
    {
        std::cout << "[Mouse] Using Makcu method input." << std::endl;
        makcu_conn = new MakcuConnection(config.makcu_port, config.makcu_baudrate);
        if (!makcu_conn->isOpen())
        {
            std::cerr << "[Makcu] Error connecting to Makcu." << std::endl;
            delete makcu_conn;
            makcu_conn = nullptr;
        }
    }
    else
    {
        std::cout << "[Mouse] Using default Win32 method input." << std::endl;
    }
}


void assignInputDevices()
{
    if (globalMouseThread)
    {
        globalMouseThread->setSerialConnection(arduinoSerial);
        globalMouseThread->setKmboxConnection(kmboxSerial);
        globalMouseThread->setKmboxNetConnection(kmboxNetSerial);
        globalMouseThread->setMakcuConnection(makcu_conn);
    }
}

void handleEasyNoRecoil(MouseThread& mouseThread)
{
    if (config.easynorecoil && shooting.load() && zooming.load())
    {
        std::lock_guard<std::mutex> lock(mouseThread.input_method_mutex);
        int recoil_compensation = static_cast<int>(config.easynorecoilstrength);
        
        if (makcu_conn)
        {
            makcu_conn->move(0, recoil_compensation);
        }
        else if (arduinoSerial)
        {
            arduinoSerial->move(0, recoil_compensation);
        }
        else if (kmboxSerial)
        {
            kmboxSerial->move(0, recoil_compensation);
        }
        else if (kmboxNetSerial)
        {
            kmboxNetSerial->move(0, recoil_compensation);
        }
        else
        {
            INPUT input = { 0 };
            input.type = INPUT_MOUSE;
            input.mi.dx = 0;
            input.mi.dy = recoil_compensation;
            input.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK;
            SendInput(1, &input, sizeof(INPUT));
        }
    }
}

void mouseThreadFunction(MouseThread& mouseThread)
{
    int lastVersion = -1;
    struct TargetCandidate
    {
        cv::Rect box;
        int class_id{ -1 };
        double pivot_x{ 0.0 };
        double pivot_y{ 0.0 };
        double size{ 0.0 };
        double relative_size{ 0.0 };
        double distance_to_center{ 0.0 };
        double dx{ 0.0 };
        double dy{ 0.0 };
        uint64_t lock_id{ 0 };
        bool smoothed{ false };
    };

    struct SmartTargetState
    {
        bool lock_active{ false };
        uint64_t lock_id{ 0 };
        cv::Point2d lock_center{ 0.0, 0.0 };
        std::chrono::steady_clock::time_point lock_lost_time{};
        int lock_class{ -1 };
        int last_target_count{ 0 };
        std::unordered_map<int, int> last_target_count_by_class;
        bool is_waiting_for_switch{ false };
        std::chrono::steady_clock::time_point target_switch_time{};
    };

    struct TargetHistoryFrame
    {
        double x{ 0.0 };
        double y{ 0.0 };
        double size{ 0.0 };
        std::chrono::steady_clock::time_point time{};
    };

    static SmartTargetState smart_state;
    static std::unordered_map<uint64_t, std::deque<TargetHistoryFrame>> target_history;
    static std::mt19937 rng{ std::random_device{}() };

    auto clear_lock_state = [&]()
        {
            smart_state.lock_active = false;
            smart_state.lock_id = 0;
            smart_state.lock_center = { 0.0, 0.0 };
            smart_state.lock_lost_time = std::chrono::steady_clock::time_point{};
            smart_state.lock_class = -1;
        };

    auto make_lock_id = [](const cv::Rect& box, int grid) -> uint64_t
        {
            int x1 = (box.x / grid) * grid;
            int y1 = (box.y / grid) * grid;
            int x2 = ((box.x + box.width) / grid) * grid;
            int y2 = ((box.y + box.height) / grid) * grid;

            uint64_t id = 0;
            id |= (static_cast<uint64_t>(x1) & 0xFFFF);
            id |= (static_cast<uint64_t>(y1) & 0xFFFF) << 16;
            id |= (static_cast<uint64_t>(x2) & 0xFFFF) << 32;
            id |= (static_cast<uint64_t>(y2) & 0xFFFF) << 48;
            return id;
        };

    auto get_box_center = [](const cv::Rect& box) -> cv::Point2d
        {
            return cv::Point2d(box.x + box.width * 0.5, box.y + box.height * 0.5);
        };

    auto parse_int_list = [](const std::string& text) -> std::vector<int>
        {
            std::vector<int> values;
            std::string cleaned;
            cleaned.reserve(text.size());
            for (char c : text)
            {
                if (std::isdigit(static_cast<unsigned char>(c)))
                    cleaned.push_back(c);
                else
                    cleaned.push_back(' ');
            }
            std::stringstream ss(cleaned);
            int val = 0;
            while (ss >> val)
                values.push_back(val);
            return values;
        };

    auto get_aim_position_for_class = [&](int class_id) -> double
        {
            double pos1 = config.aim_bot_position;
            double pos2 = config.aim_bot_position2;

            auto it = config.class_aim_positions.find(class_id);
            if (it != config.class_aim_positions.end())
            {
                pos1 = it->second.first;
                pos2 = it->second.second;
            }
            else if (config.class_aim_positions.empty())
            {
                if (class_id == config.class_head)
                {
                    pos1 = config.head_y_offset;
                    pos2 = config.head_y_offset;
                }
                else
                {
                    pos1 = config.body_y_offset;
                    pos2 = config.body_y_offset;
                }
            }

            if (config.disable_headshot)
                return std::max(pos1, pos2);

            if (pos1 > pos2)
                std::swap(pos1, pos2);
            std::uniform_real_distribution<double> dist(pos1, pos2);
            return dist(rng);
        };

    auto make_target_id = [&](const TargetCandidate& target) -> uint64_t
        {
            uint64_t x = static_cast<uint32_t>(std::max(0, static_cast<int>(std::round(target.pivot_x))));
            uint64_t y = static_cast<uint32_t>(std::max(0, static_cast<int>(std::round(target.pivot_y))));
            uint64_t cls = static_cast<uint32_t>(std::max(0, target.class_id));
            return (cls << 48) ^ (x << 24) ^ y;
        };

    auto update_target_counts = [&](const std::vector<TargetCandidate>& targets, int reference_class)
        {
            smart_state.last_target_count = static_cast<int>(targets.size());
            int current_target_count = 0;
            for (const auto& t : targets)
            {
                if (t.class_id == reference_class)
                    ++current_target_count;
            }
            smart_state.last_target_count_by_class[reference_class] = current_target_count;
        };

    auto update_lock = [&](const TargetCandidate& target)
        {
            smart_state.lock_active = true;
            smart_state.lock_id = make_lock_id(target.box, 10);
            smart_state.lock_center = get_box_center(target.box);
            smart_state.lock_lost_time = std::chrono::steady_clock::time_point{};
            smart_state.lock_class = target.class_id;
        };

    auto apply_target_lock = [&](const std::vector<TargetCandidate>& targets,
        double lock_distance,
        double reacquire_time,
        int reference_class,
        int fallback_class,
        bool& lock_blocking) -> int
        {
            lock_blocking = false;
            if (!smart_state.lock_active)
                return -1;

            auto now = std::chrono::steady_clock::now();

            if (targets.empty())
            {
                if (smart_state.lock_lost_time.time_since_epoch().count() == 0)
                    smart_state.lock_lost_time = now;
                double lost_for = std::chrono::duration<double>(now - smart_state.lock_lost_time).count();
                if (lost_for >= reacquire_time)
                {
                    clear_lock_state();
                    return -1;
                }
                lock_blocking = true;
                return -1;
            }

            int locked_idx = -1;
            for (size_t i = 0; i < targets.size(); ++i)
            {
                if (make_lock_id(targets[i].box, 10) == smart_state.lock_id)
                {
                    locked_idx = static_cast<int>(i);
                    break;
                }
            }

            if (locked_idx == -1)
            {
                double best_dist = std::numeric_limits<double>::max();
                bool restrict_to_fallback = (fallback_class >= 0 &&
                    reference_class >= 0 &&
                    smart_state.lock_class == reference_class);
                for (size_t i = 0; i < targets.size(); ++i)
                {
                    if (restrict_to_fallback)
                    {
                        if (targets[i].class_id != fallback_class)
                            continue;
                    }
                    else if (smart_state.lock_class != -1 && targets[i].class_id != smart_state.lock_class)
                    {
                        continue;
                    }
                    cv::Point2d center = get_box_center(targets[i].box);
                    double dx = center.x - smart_state.lock_center.x;
                    double dy = center.y - smart_state.lock_center.y;
                    double dist = std::hypot(dx, dy);
                    if (dist < best_dist)
                    {
                        best_dist = dist;
                        locked_idx = static_cast<int>(i);
                    }
                }

                double reacquire_distance = std::max(10.0, std::min(lock_distance, lock_distance * 0.35));
                if (locked_idx != -1 && best_dist > reacquire_distance)
                    locked_idx = -1;
            }

            if (locked_idx != -1)
            {
                update_lock(targets[locked_idx]);
                return locked_idx;
            }

            if (smart_state.lock_lost_time.time_since_epoch().count() == 0)
                smart_state.lock_lost_time = now;
            double lost_for = std::chrono::duration<double>(now - smart_state.lock_lost_time).count();
            if (lost_for >= reacquire_time)
            {
                clear_lock_state();
                return -1;
            }
            lock_blocking = true;
            return -1;
        };

    auto choose_with_weights = [&](const std::vector<TargetCandidate*>& candidates,
        double aim_scope) -> TargetCandidate*
        {
            if (candidates.empty())
                return nullptr;
            if (candidates.size() == 1)
                return candidates[0];

            double tiebreak_ratio = std::max(0.0, static_cast<double>(config.aim_weight_tiebreak_ratio));
            double min_dist = std::numeric_limits<double>::max();
            for (auto* t : candidates)
                min_dist = std::min(min_dist, t->distance_to_center);
            if (tiebreak_ratio <= 0.0)
            {
                return *std::min_element(
                    candidates.begin(), candidates.end(),
                    [](const TargetCandidate* a, const TargetCandidate* b)
                    {
                        return a->distance_to_center < b->distance_to_center;
                    });
            }

            double scope = aim_scope > 0.0 ? aim_scope : std::max(1.0, min_dist);
            double threshold = scope * tiebreak_ratio;
            std::vector<TargetCandidate*> near_candidates;
            for (auto* t : candidates)
            {
                if (t->distance_to_center <= min_dist + threshold)
                    near_candidates.push_back(t);
            }
            if (near_candidates.size() == 1)
                return near_candidates[0];

            double w_dist = static_cast<double>(config.distance_scoring_weight);
            double w_center = static_cast<double>(config.center_scoring_weight);
            double w_size = static_cast<double>(config.size_scoring_weight);
            if (w_dist == 0.0 && w_center == 0.0 && w_size == 0.0)
            {
                return *std::min_element(
                    near_candidates.begin(), near_candidates.end(),
                    [](const TargetCandidate* a, const TargetCandidate* b)
                    {
                        return a->distance_to_center < b->distance_to_center;
                    });
            }
            double max_dist = 1.0;
            double max_center = 1.0;
            double max_size = 1e-6;
            for (auto* t : near_candidates)
            {
                max_dist = std::max(max_dist, t->distance_to_center);
                max_center = std::max(max_center, std::abs(t->dx) + std::abs(t->dy));
                max_size = std::max(max_size, t->size);
            }

            auto score = [&](const TargetCandidate* t)
                {
                    double dist_norm = t->distance_to_center / max_dist;
                    double center_norm = (std::abs(t->dx) + std::abs(t->dy)) / max_center;
                    double size_norm = t->size / max_size;
                    return (w_dist * dist_norm) +
                        (w_center * center_norm) +
                        (w_size * (1.0 - size_norm));
                };

            return *std::min_element(
                near_candidates.begin(), near_candidates.end(),
                [&](const TargetCandidate* a, const TargetCandidate* b)
                {
                    return score(a) < score(b);
                });
        };

    while (!shouldExit)
    {
        std::vector<cv::Rect> boxes;
        std::vector<int> classes;

        {
            std::unique_lock<std::mutex> lock(detectionBuffer.mutex);
            detectionBuffer.cv.wait(lock, [&] {
                return detectionBuffer.version > lastVersion || shouldExit;
                });
            if (shouldExit) break;
            boxes = detectionBuffer.boxes;
            classes = detectionBuffer.classes;
            lastVersion = detectionBuffer.version;
        }

        if (input_method_changed.load())
        {
            createInputDevices();
            assignInputDevices();
            input_method_changed.store(false);
        }

        if (detection_resolution_changed.load())
        {
            {
                std::lock_guard<std::mutex> cfgLock(configMutex);
                mouseThread.updateConfig(
                    config.detection_resolution,
                    config.fovX,
                    config.fovY,
                    config.minSpeedMultiplier,
                    config.maxSpeedMultiplier,
                    config.predictionInterval,
                    config.auto_shoot,
                    config.bScope_multiplier,
                    config.triggerbot_bScope_multiplier
                );
                mouseThread.setUseSmoothing(config.use_smoothing);
                mouseThread.setUseKalman(config.use_kalman);
                mouseThread.setSmoothnessValue(config.smoothness);
            }
            detection_resolution_changed.store(false);
        }

        // ????? ??????
        int screenCenterX = config.detection_resolution / 2;
        int screenCenterY = config.detection_resolution / 2;
        double max_distance = std::hypot(
            static_cast<double>(config.detection_resolution),
            static_cast<double>(config.detection_resolution)) / 2.0;
        double aim_scope = config.aim_bot_scope > 0.0 ? config.aim_bot_scope : max_distance;
        double base_scope = config.aim_bot_scope > 0.0 ? config.aim_bot_scope : aim_scope;

        auto allowed_list = parse_int_list(config.allowed_classes);
        std::unordered_set<int> allowed_set;
        if (!allowed_list.empty())
            allowed_set.insert(allowed_list.begin(), allowed_list.end());
        auto priority_order = parse_int_list(config.class_priority_order);

        int reference_class = config.target_reference_class;
        if (reference_class < 0)
            reference_class = config.class_player;
        int fallback_class = config.target_lock_fallback_class;
        if (fallback_class < 0)
            fallback_class = -1;

        auto is_valid_target_class = [&](int cls)
            {
                auto it_name = config.custom_class_names.find(cls);
                if (it_name != config.custom_class_names.end() && it_name->second == "__deleted__")
                    return false;
                if (config.disable_headshot && cls == config.class_head)
                    return false;
                if (cls == config.class_third_person && config.ignore_third_person)
                    return false;
                if ((cls == config.class_hideout_target_human || cls == config.class_hideout_target_balls) &&
                    !config.shooting_range_targets)
                    return false;
                if (allowed_set.empty())
                    return false;
                return allowed_set.find(cls) != allowed_set.end();
            };

        double lock_distance = std::max(1.0, static_cast<double>(config.target_lock_distance));
        if (!config.target_lock_enabled && config.focusTarget)
            lock_distance = max_distance;
        bool lock_enabled = (config.smart_target_lock || config.target_lock_enabled || config.focusTarget) && lock_distance > 0.0;
        if (!lock_enabled || (!aiming.load() && !config.auto_aim))
        {
            clear_lock_state();
        }
        double reacquire_time = std::max(0.0, static_cast<double>(config.target_lock_reacquire_time));

        std::vector<TargetCandidate> candidates;
        candidates.reserve(boxes.size());
        for (size_t i = 0; i < boxes.size(); ++i)
        {
            if (i >= classes.size())
                break;
            int cls = classes[i];
            if (!is_valid_target_class(cls))
                continue;
            const cv::Rect& box = boxes[i];
            TargetCandidate cand;
            cand.box = box;
            cand.class_id = cls;
            cand.lock_id = make_lock_id(box, 10);
            double aim_pos = get_aim_position_for_class(cls);
            cand.pivot_x = box.x + box.width * 0.5;
            cand.pivot_y = box.y + box.height * aim_pos;
            double area = static_cast<double>(box.width) * static_cast<double>(box.height);
            double frame_area = static_cast<double>(config.detection_resolution) *
                static_cast<double>(config.detection_resolution);
            cand.relative_size = frame_area > 0.0 ? area / frame_area : 0.0;
            double size_boost = 1.0;
            if (config.small_target_enhancement_enabled)
            {
                if (cand.relative_size < config.small_target_threshold)
                    size_boost = config.small_target_boost_factor;
                else if (cand.relative_size < config.small_target_medium_threshold)
                    size_boost = config.small_target_medium_boost;
            }
            cand.size = cand.relative_size * size_boost;
            candidates.push_back(cand);
        }

        if (config.small_target_enhancement_enabled && config.small_target_smooth_enabled && !candidates.empty())
        {
            auto now = std::chrono::steady_clock::now();
            int max_frames = std::max(1, config.small_target_smooth_frames);
            for (auto it = target_history.begin(); it != target_history.end();)
            {
                auto& frames = it->second;
                while (!frames.empty())
                {
                    double age = std::chrono::duration<double>(now - frames.front().time).count();
                    if (age > 1.0)
                        frames.pop_front();
                    else
                        break;
                }
                if (frames.empty())
                    it = target_history.erase(it);
                else
                    ++it;
            }

            for (auto& cand : candidates)
            {
                if (cand.relative_size >= config.small_target_threshold)
                    continue;
                uint64_t id = make_target_id(cand);
                auto& frames = target_history[id];
                frames.push_back({ cand.pivot_x, cand.pivot_y, cand.size, now });
                if (static_cast<int>(frames.size()) > max_frames)
                    frames.pop_front();
                if (frames.size() >= 2)
                {
                    double sum_x = 0.0;
                    double sum_y = 0.0;
                    double sum_size = 0.0;
                    for (const auto& f : frames)
                    {
                        sum_x += f.x;
                        sum_y += f.y;
                        sum_size += f.size;
                    }
                    cand.pivot_x = sum_x / frames.size();
                    cand.pivot_y = sum_y / frames.size();
                    cand.size = sum_size / frames.size();
                    cand.smoothed = true;
                }
            }
        }

        bool lock_blocking = false;
        int locked_idx = -1;
        if (lock_enabled)
        {
            locked_idx = apply_target_lock(candidates, lock_distance, reacquire_time, reference_class, fallback_class, lock_blocking);
            if (lock_blocking)
                candidates.clear();
            else if (locked_idx >= 0 && locked_idx < static_cast<int>(candidates.size()))
            {
                TargetCandidate locked = candidates[locked_idx];
                candidates.clear();
                candidates.push_back(locked);
            }
        }
        else
        {
            clear_lock_state();
        }

        TargetCandidate* selected = nullptr;
        if (!candidates.empty())
        {
            if (lock_enabled && smart_state.lock_active && candidates.size() == 1)
            {
                update_target_counts(candidates, reference_class);
                update_lock(candidates[0]);
                selected = &candidates[0];
            }
            else
            {
                std::vector<TargetCandidate*> valid_targets;
                valid_targets.reserve(candidates.size());
                for (auto& t : candidates)
                {
                    t.dx = t.pivot_x - screenCenterX;
                    t.dy = t.pivot_y - screenCenterY;
                    t.distance_to_center = std::hypot(t.dx, t.dy);
                    if (aim_scope <= 0.0 || t.distance_to_center <= aim_scope)
                        valid_targets.push_back(&t);
                }

                if (!lock_enabled)
                    clear_lock_state();

                if (!priority_order.empty())
                {
                    for (int class_id : priority_order)
                    {
                        std::vector<TargetCandidate*> class_candidates;
                        for (auto& t : candidates)
                        {
                            if (t.class_id != class_id)
                                continue;
                            if (base_scope > 0.0 && t.distance_to_center > base_scope)
                                continue;
                            class_candidates.push_back(&t);
                        }
                        if (!class_candidates.empty())
                        {
                            selected = choose_with_weights(class_candidates, aim_scope);
                            if (selected && lock_enabled && lock_distance > 0.0)
                                update_lock(*selected);
                            else if (!lock_enabled)
                                clear_lock_state();
                            break;
                        }
                    }
                }

                if (!selected)
                {
                    if (valid_targets.empty())
                    {
                        if (!lock_enabled || !smart_state.lock_active)
                        {
                            clear_lock_state();
                            if (smart_state.last_target_count > 0)
                            {
                                smart_state.last_target_count = 0;
                                smart_state.last_target_count_by_class.clear();
                            }
                        }
                    }
                    else
                    {
                        int target_switch_delay = std::max(0, config.target_switch_delay);
                        int current_total_count = static_cast<int>(valid_targets.size());
                        int prev_total_count = smart_state.last_target_count;
                        int current_target_count = 0;
                        for (auto* t : valid_targets)
                        {
                            if (t->class_id == reference_class)
                                ++current_target_count;
                        }

                        if (target_switch_delay > 0 &&
                            !smart_state.is_waiting_for_switch &&
                            prev_total_count > 1 &&
                            current_total_count < prev_total_count)
                        {
                            smart_state.is_waiting_for_switch = true;
                            smart_state.target_switch_time = std::chrono::steady_clock::now();
                        }

                        if (smart_state.is_waiting_for_switch && current_total_count > prev_total_count)
                            smart_state.is_waiting_for_switch = false;

                        if (smart_state.is_waiting_for_switch)
                        {
                            double elapsed_ms = std::chrono::duration<double, std::milli>(
                                std::chrono::steady_clock::now() - smart_state.target_switch_time).count();
                            if (elapsed_ms >= target_switch_delay)
                                smart_state.is_waiting_for_switch = false;
                            else
                            {
                                selected = nullptr;
                            }
                        }

                        if (!smart_state.is_waiting_for_switch)
                        {
                            smart_state.last_target_count_by_class[reference_class] = current_target_count;
                            smart_state.last_target_count = current_total_count;

                            if (!priority_order.empty())
                            {
                                std::unordered_map<int, int> priority_map;
                                for (size_t idx = 0; idx < priority_order.size(); ++idx)
                                    priority_map[priority_order[idx]] = static_cast<int>(idx);
                                std::sort(valid_targets.begin(), valid_targets.end(),
                                    [&](const TargetCandidate* a, const TargetCandidate* b)
                                    {
                                        int pa = priority_map.count(a->class_id) ? priority_map[a->class_id] : static_cast<int>(priority_map.size());
                                        int pb = priority_map.count(b->class_id) ? priority_map[b->class_id] : static_cast<int>(priority_map.size());
                                        if (pa != pb)
                                            return pa < pb;
                                        return a->distance_to_center < b->distance_to_center;
                                    });
                            }
                            else
                            {
                                std::sort(valid_targets.begin(), valid_targets.end(),
                                    [](const TargetCandidate* a, const TargetCandidate* b)
                                    {
                                        return a->distance_to_center < b->distance_to_center;
                                    });
                            }

                            selected = choose_with_weights(valid_targets, aim_scope);
                            if (selected && lock_enabled && lock_distance > 0.0)
                                update_lock(*selected);
                            else if (!lock_enabled)
                                clear_lock_state();
                        }
                    }
                }
            }
        }
        else
        {
            if (!lock_blocking && (!lock_enabled || !smart_state.lock_active))
            {
                clear_lock_state();
                if (smart_state.last_target_count > 0)
                {
                    smart_state.last_target_count = 0;
                    smart_state.last_target_count_by_class.clear();
                }
            }
        }

        AimbotTarget* target = nullptr;
        if (selected)
        {
            target = new AimbotTarget(
                selected->box.x,
                selected->box.y,
                selected->box.width,
                selected->box.height,
                selected->class_id,
                selected->pivot_x,
                selected->pivot_y);
        }

        if (target)
        {
            mouseThread.setLastTargetTime(std::chrono::steady_clock::now());
            mouseThread.setTargetDetected(true);

            auto futurePositions = mouseThread.predictFuturePositions(
                target->pivotX,
                target->pivotY,
                config.prediction_futurePositions
            );
            mouseThread.storeFuturePositions(futurePositions);
        }
        else
        {
            mouseThread.clearFuturePositions();
            mouseThread.setTargetDetected(false);
        }

        bool shouldPressAuto = false;
        bool shouldPressTrigger = false;
        bool triggerbotActive = config.triggerbot && triggerbot_button.load();
        static auto lastTriggerShot = std::chrono::steady_clock::now() - std::chrono::milliseconds(500);

        bool triggerbotInScope = false;
        if (target)
        {
            triggerbotInScope = mouseThread.check_target_in_scope(
                target->x,
                target->y,
                target->w,
                target->h,
                config.triggerbot_bScope_multiplier);
        }

        if (aiming && target)
        {
            mouseThread.moveMousePivot(target->pivotX, target->pivotY);
            if (config.auto_shoot)
                shouldPressAuto = true;
        }

        if (triggerbotActive && triggerbotInScope)
        {
            auto now = std::chrono::steady_clock::now();
            int reaction_ms = std::max(0, config.triggerbot_reaction_ms);
            if (reaction_ms <= 0 || now - lastTriggerShot >= std::chrono::milliseconds(reaction_ms))
            {
                shouldPressTrigger = true;
                lastTriggerShot = now;
            }
        }

        if (target && (shouldPressAuto || shouldPressTrigger))
        {
            if (shouldPressTrigger)
                mouseThread.pressMouse(*target, config.triggerbot_bScope_multiplier);
            else
                mouseThread.pressMouse(*target);
        }
        else
        {
            mouseThread.releaseMouse();
        }

        handleEasyNoRecoil(mouseThread);
        mouseThread.checkAndResetPredictions();

        delete target;
    }
}


int main()
{
    try
    {
#ifdef USE_CUDA
        int cuda_devices = 0;
        if (cudaGetDeviceCount(&cuda_devices) != cudaSuccess || cuda_devices == 0)
        {
            std::cerr << "[MAIN] CUDA required but no devices found." << std::endl;
            std::cin.get();
            return -1;
        }
#endif

        SetConsoleOutputCP(CP_UTF8);
        cv::utils::logging::setLogLevel(cv::utils::logging::LOG_LEVEL_FATAL);

        if (!CreateDirectory(L"screenshots", NULL) && GetLastError() != ERROR_ALREADY_EXISTS)
        {
            std::cout << "[MAIN] Error with screenshoot folder" << std::endl;
            std::cin.get();
            return -1;
        }

        if (!CreateDirectory(L"models", NULL) && GetLastError() != ERROR_ALREADY_EXISTS)
        {
            std::cout << "[MAIN] Error with models folder" << std::endl;
            std::cin.get();
            return -1;
        }

        if (!config.loadConfig())
        {
            std::cerr << "[Config] Error with loading config!" << std::endl;
            std::cin.get();
            return -1;
        }

        // Always start each run with a fresh console log file.
        {
            std::ofstream clear_log(k_console_log_path, std::ios::out | std::ios::trunc);
        }
        SetConsoleFileLoggingEnabled(config.verbose, false);

        if (config.capture_method == "virtual_camera")
        {
            auto cams = VirtualCameraCapture::GetAvailableVirtualCameras();
            if (!cams.empty())
            {
                if (config.virtual_camera_name == "None" ||
                    std::find(cams.begin(), cams.end(), config.virtual_camera_name) == cams.end())
                {
                    config.virtual_camera_name = cams[0];
                    config.saveConfig("config.ini");
                    std::cout << "[MAIN] Set virtual_camera_name = " << config.virtual_camera_name << std::endl;
                }
                std::cout << "[MAIN] Virtual cameras loaded: " << cams.size() << std::endl;
            }
            else
            {
                std::cerr << "[MAIN] No virtual cameras found" << std::endl;
            }
        }

        std::string modelPath = "models/" + config.ai_model;

        if (!std::filesystem::exists(modelPath))
        {
            std::cerr << "[MAIN] Specified model does not exist: " << modelPath << std::endl;

            std::vector<std::string> modelFiles = getModelFiles();

            if (!modelFiles.empty())
            {
                config.ai_model = modelFiles[0];
                config.saveConfig();
                std::cout << "[MAIN] Loaded first available model: " << config.ai_model << std::endl;
            }
            else
            {
                std::cerr << "[MAIN] No models found in 'models' directory." << std::endl;
                std::cin.get();
                return -1;
            }
        }

        createInputDevices();

        MouseThread mouseThread(
            config.detection_resolution,
            config.fovX,
            config.fovY,
            config.minSpeedMultiplier,
            config.maxSpeedMultiplier,
            config.predictionInterval,
            config.auto_shoot,
            config.bScope_multiplier,
            config.triggerbot_bScope_multiplier,
            arduinoSerial,
            kmboxSerial,
            kmboxNetSerial,
            makcu_conn
        );

        mouseThread.setUseSmoothing(config.use_smoothing);
        mouseThread.setSmoothnessValue(config.smoothness);
        mouseThread.setUseKalman(config.use_kalman);

        globalMouseThread = &mouseThread;
        assignInputDevices();

        std::vector<std::string> availableModels = getAvailableModels();

        if (!config.ai_model.empty())
        {
            std::string modelPath = "models/" + config.ai_model;
            if (!std::filesystem::exists(modelPath))
            {
                std::cerr << "[MAIN] Specified model does not exist: " << modelPath << std::endl;

                if (!availableModels.empty())
                {
                    config.ai_model = availableModels[0];
                    config.saveConfig("config.ini");
                    std::cout << "[MAIN] Loaded first available model: " << config.ai_model << std::endl;
                }
                else
                {
                    std::cerr << "[MAIN] No models found in 'models' directory." << std::endl;
                    std::cin.get();
                    return -1;
                }
            }
        }
        else
        {
            if (!availableModels.empty())
            {
                config.ai_model = availableModels[0];
                config.saveConfig();
                std::cout << "[MAIN] No AI model specified in config. Loaded first available model: " << config.ai_model << std::endl;
            }
            else
            {
                std::cerr << "[MAIN] No AI models found in 'models' directory." << std::endl;
                std::cin.get();
                return -1;
            }
        }

        std::thread dml_detThread;

        if (config.backend == "DML")
        {
            dml_detector = new DirectMLDetector("models/" + config.ai_model);
            std::cout << "[MAIN] DML detector initialized." << std::endl;
            dml_detThread = std::thread(&DirectMLDetector::dmlInferenceThread, dml_detector);
        }
        else if (config.backend == "COLOR")
        {
            color_detector = new ColorDetector();
            std::cout << "[Capture] backend=" << config.backend << std::endl;
            color_detector->initializeFromConfig(config);   
            std::cout << "[MAIN] Color detector initialized." << std::endl;
            color_detThread = std::thread(&ColorDetector::inferenceThread, color_detector);
        }
#ifdef USE_CUDA
        else
        {
            trt_detector.initialize("models/" + config.ai_model);
        }
#endif

        detection_resolution_changed.store(true);

        std::thread keyThread(keyboardListener);
        std::thread capThread(captureThread, config.detection_resolution, config.detection_resolution);

#ifdef USE_CUDA
        std::thread trt_detThread(&TrtDetector::inferenceThread, &trt_detector);
#endif
        std::thread mouseMovThread(mouseThreadFunction, std::ref(mouseThread));
        std::thread overlayThread(OverlayThread);
        std::thread gameOverlayThread(GameOverlayThreadFunction);

        welcome_message();

        keyThread.join();
        capThread.join();
        if (dml_detThread.joinable())
        {
            dml_detector->shouldExit = true;
            dml_detector->inferenceCV.notify_all();
            dml_detThread.join();
        }

        if (color_detThread.joinable())
        {
            color_detector->stop();
            color_detThread.join();
            delete color_detector;
            color_detector = nullptr;
        }


#ifdef USE_CUDA
        trt_detThread.join();
#endif
        mouseMovThread.join();
        overlayThread.join();
        gameOverlayThread.join();

        if (arduinoSerial)
        {
            delete arduinoSerial;
        }

        if (makcu_conn)
        {
            delete makcu_conn;
            makcu_conn = nullptr;
        }

        if (dml_detector)
        {
            delete dml_detector;
            dml_detector = nullptr;
        }

        SetConsoleFileLoggingEnabled(false);

        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << "[MAIN] An error has occurred in the main stream: " << e.what() << std::endl;
        std::cout << "Press Enter to exit...";
        std::cin.get();
        return -1;
    }
}
