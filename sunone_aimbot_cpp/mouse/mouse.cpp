#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#define _USE_MATH_DEFINES
#include <cmath>
#include <algorithm>
#include <chrono>
#include <mutex>
#include <atomic>
#include <vector>

#include "mouse.h"
#include "capture.h"
#include "SerialConnection.h"
#include "sunone_aimbot_cpp.h"

MouseThread::MouseThread(
    int resolution,
    int fovX,
    int fovY,
    double minSpeedMultiplier,
    double maxSpeedMultiplier,
    double predictionInterval,
    bool auto_shoot,
    float bScope_multiplier,
    float triggerbot_bScope_multiplier,
    SerialConnection* serialConnection,
    KmboxConnection* kmboxConnection,
    KmboxNetConnection* Kmbox_Net_Connection,
    MakcuConnection* makcu)
    : screen_width(resolution),
    screen_height(resolution),
    prediction_interval(predictionInterval),
    fov_x(fovX),
    fov_y(fovY),
    max_distance(std::hypot(resolution, resolution) / 2.0),
    min_speed_multiplier(minSpeedMultiplier),
    max_speed_multiplier(maxSpeedMultiplier),
    center_x(resolution / 2.0),
    center_y(resolution / 2.0),
    auto_shoot(auto_shoot),
    bScope_multiplier(bScope_multiplier),
    triggerbot_bScope_multiplier(triggerbot_bScope_multiplier),
    serial(serialConnection),
    kmbox(kmboxConnection),
    kmbox_net(Kmbox_Net_Connection),
    makcu(makcu),

    prev_velocity_x(0.0),
    prev_velocity_y(0.0),
    prev_x(0.0),
    prev_y(0.0)
{
    prev_time = std::chrono::steady_clock::time_point();
    last_target_time = std::chrono::steady_clock::now();

    wind_mouse_enabled = config.wind_mouse_enabled;
    wind_G = config.wind_G;
    wind_W = config.wind_W;
    wind_M = config.wind_M;
    wind_D = config.wind_D;

    use_smoothing = config.use_smoothing;
    use_kalman = config.use_kalman;

    kfX = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    kfY = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    last_kalman_q = config.kalman_process_noise;
    last_kalman_r = config.kalman_measurement_noise;

    last_prediction_q = config.prediction_kalman_process_noise;
    last_prediction_r = config.prediction_kalman_measurement_noise;
    resetAimState();

    moveWorker = std::thread(&MouseThread::moveWorkerLoop, this);
}

void MouseThread::updateConfig(
    int resolution,
    int fovX,
    int fovY,
    double minSpeedMultiplier,
    double maxSpeedMultiplier,
    double predictionInterval,
    bool auto_shoot,
    float bScope_multiplier,
    float triggerbot_bScope_multiplier
)
{
    screen_width = screen_height = resolution;
    fov_x = fovX;  fov_y = fovY;
    min_speed_multiplier = minSpeedMultiplier;
    max_speed_multiplier = maxSpeedMultiplier;
    prediction_interval = predictionInterval;
    this->auto_shoot = auto_shoot;
    this->bScope_multiplier = bScope_multiplier;
    this->triggerbot_bScope_multiplier = triggerbot_bScope_multiplier;

    center_x = center_y = resolution / 2.0;
    max_distance = std::hypot(resolution, resolution) / 2.0;

    wind_mouse_enabled = config.wind_mouse_enabled;
    wind_G = config.wind_G; wind_W = config.wind_W;
    wind_M = config.wind_M; wind_D = config.wind_D;

    use_smoothing = config.use_smoothing;
    use_kalman = config.use_kalman;

    kfX = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    kfY = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    last_kalman_q = config.kalman_process_noise;
    last_kalman_r = config.kalman_measurement_noise;

}

MouseThread::~MouseThread()
{
    workerStop = true;
    queueCv.notify_all();
    if (moveWorker.joinable()) moveWorker.join();
}

void MouseThread::queueMove(int dx, int dy)
{
    std::lock_guard lg(queueMtx);
    if (moveQueue.size() >= queueLimit) moveQueue.pop();
    moveQueue.push({ dx,dy });
    queueCv.notify_one();
}

void MouseThread::moveWorkerLoop()
{
    while (!workerStop)
    {
        std::unique_lock ul(queueMtx);
        queueCv.wait(ul, [&] { return workerStop || !moveQueue.empty(); });

        while (!moveQueue.empty())
        {
            Move m = moveQueue.front();
            moveQueue.pop();
            ul.unlock();
            sendMovementToDriver(m.dx, m.dy);
            ul.lock();
        }
    }
}

void MouseThread::windMouseMoveRelative(int dx, int dy)
{
    if (dx == 0 && dy == 0) return;

    constexpr double SQRT3 = 1.7320508075688772;
    constexpr double SQRT5 = 2.23606797749979;

    double sx = 0, sy = 0;
    double dxF = static_cast<double>(dx);
    double dyF = static_cast<double>(dy);
    double vx = 0, vy = 0, wX = 0, wY = 0;
    int    cx = 0, cy = 0;

    while (std::hypot(dxF - sx, dyF - sy) >= 1.0)
    {
        double dist = std::hypot(dxF - sx, dyF - sy);
        double wMag = std::min(wind_W, dist);

        if (dist >= wind_D)
        {
            wX = wX / SQRT3 + ((double)rand() / RAND_MAX * 2.0 - 1.0) * wMag / SQRT5;
            wY = wY / SQRT3 + ((double)rand() / RAND_MAX * 2.0 - 1.0) * wMag / SQRT5;
        }
        else
        {
            wX /= SQRT3;  wY /= SQRT3;
            wind_M = wind_M < 3.0 ? ((double)rand() / RAND_MAX) * 3.0 + 3.0 : wind_M / SQRT5;
        }

        vx += wX + wind_G * (dxF - sx) / dist;
        vy += wY + wind_G * (dyF - sy) / dist;

        double vMag = std::hypot(vx, vy);
        if (vMag > wind_M)
        {
            double vClip = wind_M / 2.0 + ((double)rand() / RAND_MAX) * wind_M / 2.0;
            vx = (vx / vMag) * vClip;
            vy = (vy / vMag) * vClip;
        }

        sx += vx;  sy += vy;
        int rx = static_cast<int>(std::round(sx));
        int ry = static_cast<int>(std::round(sy));
        int step_x = rx - cx;
        int step_y = ry - cy;
        if (step_x || step_y)
        {
            queueMove(step_x, step_y);
            cx = rx; cy = ry;
        }
    }
}

double MouseThread::clampValue(double v, double lo, double hi)
{
    return std::max(lo, std::min(hi, v));
}

void MouseThread::resetPredictionState()
{
    prediction_prev_time = std::chrono::steady_clock::time_point{};
    prediction_prev_x = 0.0;
    prediction_prev_y = 0.0;
    prediction_smoothed_velocity_x = 0.0;
    prediction_smoothed_velocity_y = 0.0;
    prediction_velocity_x = 0.0;
    prediction_velocity_y = 0.0;
    prediction_initialized = false;
    prediction_kalman_time = std::chrono::steady_clock::time_point{};
    prediction_kalman_initialized = false;
    last_prediction_mode = -1;
    last_raw_velocity_x = 0.0;
    last_raw_velocity_y = 0.0;

    double q = (last_prediction_q > 0.0) ? last_prediction_q : 0.01;
    double r = (last_prediction_r > 0.0) ? last_prediction_r : 0.1;
    prediction_kf_x = Kalman1D(q, r);
    prediction_kf_y = Kalman1D(q, r);
}

void MouseThread::resetKalmanState()
{
    kfX = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    kfY = Kalman1D(config.kalman_process_noise, config.kalman_measurement_noise);
    prevKalmanTime = std::chrono::steady_clock::time_point{};
    kalman_smoothing_initialized = false;
    last_raw_kalman_x = 0.0;
    last_raw_kalman_y = 0.0;
    last_kx = 0.0;
    last_ky = 0.0;
}

void MouseThread::resetSmoothingState()
{
    move_overflow_x = 0.0;
    move_overflow_y = 0.0;
    smooth_frame = 0;
    smooth_start_x = 0.0;
    smooth_start_y = 0.0;
    smooth_prev_x = 0.0;
    smooth_prev_y = 0.0;
    smooth_last_tx = 0.0;
    smooth_last_ty = 0.0;

    tracking_initialized = false;
    track_x = 0.0;
    track_y = 0.0;
    track_prev_x = 0.0;
    track_prev_y = 0.0;
    track_time = std::chrono::steady_clock::time_point{};
    last_tracking_mode = -1;
}

void MouseThread::resetAimState()
{
    prev_time = std::chrono::steady_clock::time_point{};
    prev_x = 0.0;
    prev_y = 0.0;
    prev_velocity_x = 0.0;
    prev_velocity_y = 0.0;
    last_target_time = std::chrono::steady_clock::time_point{};
    target_detected.store(false);
    resetPredictionState();
    resetKalmanState();
    resetSmoothingState();
}

void MouseThread::markTargetSeen()
{
    last_target_time = std::chrono::steady_clock::now();
    target_detected.store(true);
}

void MouseThread::resetIfStale(double timeout_s)
{
    if (!target_detected.load())
        return;
    auto now = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(now - last_target_time).count();
    if (elapsed > timeout_s)
    {
        resetAimState();
    }
}

void MouseThread::ensurePredictionKalman(double q, double r)
{
    q = std::max(q, 1e-6);
    r = std::max(r, 1e-6);
    if (q != last_prediction_q || r != last_prediction_r)
    {
        last_prediction_q = q;
        last_prediction_r = r;
        resetPredictionState();
    }
}

void MouseThread::ensureKalman(double q, double r)
{
    q = std::max(q, 1e-6);
    r = std::max(r, 1e-6);
    if (q != last_kalman_q || r != last_kalman_r)
    {
        kfX = Kalman1D(q, r);
        kfY = Kalman1D(q, r);
        last_kalman_q = q;
        last_kalman_r = r;
        kalman_smoothing_initialized = false;
        prevKalmanTime = std::chrono::steady_clock::time_point{};
    }
}

std::pair<double, double> MouseThread::cameraVelocity(double camera_dx, double camera_dy, double dt)
{
    if (!config.camera_compensation_enabled || dt <= 0.0)
        return { 0.0, 0.0 };
    double max_shift = std::max(0.0, static_cast<double>(config.camera_compensation_max_shift));
    double strength = std::max(0.0, static_cast<double>(config.camera_compensation_strength));
    double dx = clampValue(camera_dx, -max_shift, max_shift) * strength;
    double dy = clampValue(camera_dy, -max_shift, max_shift) * strength;
    return { dx / dt, dy / dt };
}

std::pair<double, double> MouseThread::updateStandardVelocity(
    double targetX, double targetY, double camera_dx, double camera_dy)
{
    auto now = std::chrono::steady_clock::now();
    if (prev_time.time_since_epoch().count() == 0 || !target_detected.load())
    {
        prev_time = now;
        prev_x = targetX;
        prev_y = targetY;
        prev_velocity_x = 0.0;
        prev_velocity_y = 0.0;
        return { 0.0, 0.0 };
    }
    double dt = std::max(std::chrono::duration<double>(now - prev_time).count(), 1e-8);
    auto cam = cameraVelocity(camera_dx, camera_dy, dt);
    double vx = (targetX - prev_x) / dt - cam.first;
    double vy = (targetY - prev_y) / dt - cam.second;
    prev_time = now;
    prev_x = targetX;
    prev_y = targetY;
    prev_velocity_x = clampValue(vx, -20000.0, 20000.0);
    prev_velocity_y = clampValue(vy, -20000.0, 20000.0);
    return { prev_velocity_x, prev_velocity_y };
}

std::pair<double, double> MouseThread::updatePredictionState(
    double pivotX, double pivotY, double camera_dx, double camera_dy)
{
    int mode = config.prediction_mode;
    if (mode != last_prediction_mode)
    {
        resetPredictionState();
        last_prediction_mode = mode;
    }

    auto now = std::chrono::steady_clock::now();
    const double max_gap = 0.25;
    if (prediction_prev_time.time_since_epoch().count() == 0)
    {
        prediction_prev_time = now;
        prediction_prev_x = pivotX;
        prediction_prev_y = pivotY;
        if (mode != 0)
        {
            prediction_kf_x.reset(pivotX, 0.0);
            prediction_kf_y.reset(pivotY, 0.0);
            prediction_kalman_time = now;
            prediction_kalman_initialized = true;
        }
        return { pivotX, pivotY };
    }

    double dt = std::chrono::duration<double>(now - prediction_prev_time).count();
    if (dt > max_gap)
    {
        resetPredictionState();
        prediction_prev_time = now;
        prediction_prev_x = pivotX;
        prediction_prev_y = pivotY;
        if (mode != 0)
        {
            prediction_kf_x.reset(pivotX, 0.0);
            prediction_kf_y.reset(pivotY, 0.0);
            prediction_kalman_time = now;
            prediction_kalman_initialized = true;
        }
        return { pivotX, pivotY };
    }

    dt = std::max(dt, 1e-8);
    auto cam = cameraVelocity(camera_dx, camera_dy, dt);
    double raw_vx = (pivotX - prediction_prev_x) / dt - cam.first;
    double raw_vy = (pivotY - prediction_prev_y) / dt - cam.second;
    raw_vx = clampValue(raw_vx, -20000.0, 20000.0);
    raw_vy = clampValue(raw_vy, -20000.0, 20000.0);
    prediction_prev_x = pivotX;
    prediction_prev_y = pivotY;
    prediction_prev_time = now;
    last_raw_velocity_x = raw_vx;
    last_raw_velocity_y = raw_vy;

    double base_vx = raw_vx;
    double base_vy = raw_vy;
    double filt_x = pivotX;
    double filt_y = pivotY;

    if (mode != 0)
    {
        double reset_threshold = std::max(1.0, static_cast<double>(config.resetThreshold));
        if (!prediction_kalman_initialized ||
            std::hypot(pivotX - prediction_kf_x.x, pivotY - prediction_kf_y.x) > reset_threshold)
        {
            prediction_kf_x.reset(pivotX, 0.0);
            prediction_kf_y.reset(pivotY, 0.0);
            prediction_kalman_time = now;
            prediction_kalman_initialized = true;
        }

        double kdt = dt;
        if (prediction_kalman_time.time_since_epoch().count() != 0)
            kdt = std::max(std::chrono::duration<double>(now - prediction_kalman_time).count(), 1e-8);
        prediction_kalman_time = now;

        filt_x = prediction_kf_x.update(pivotX, kdt);
        filt_y = prediction_kf_y.update(pivotY, kdt);
        base_vx = prediction_kf_x.v - cam.first;
        base_vy = prediction_kf_y.v - cam.second;
    }

    double alpha = clampValue(config.prediction_velocity_smoothing, 0.0, 1.0);
    if (!prediction_initialized)
    {
        prediction_smoothed_velocity_x = base_vx;
        prediction_smoothed_velocity_y = base_vy;
        prediction_initialized = true;
    }
    else
    {
        prediction_smoothed_velocity_x += (base_vx - prediction_smoothed_velocity_x) * alpha;
        prediction_smoothed_velocity_y += (base_vy - prediction_smoothed_velocity_y) * alpha;
    }

    double scale = std::max(0.0, static_cast<double>(config.prediction_velocity_scale));
    prediction_velocity_x = prediction_smoothed_velocity_x * scale;
    prediction_velocity_y = prediction_smoothed_velocity_y * scale;

    if (mode == 0)
        return { pivotX, pivotY };

    double lead_ms = std::max(0.0, static_cast<double>(config.prediction_kalman_lead_ms));
    double max_lead_ms = std::max(0.0, static_cast<double>(config.prediction_kalman_max_lead_ms));
    if (max_lead_ms > 0.0 && lead_ms > max_lead_ms)
        lead_ms = max_lead_ms;
    double lead_s = lead_ms / 1000.0;

    return { filt_x + prediction_velocity_x * lead_s,
             filt_y + prediction_velocity_y * lead_s };
}

std::vector<std::pair<double, double>> MouseThread::predictFuturePositionsInternal(
    double pivotX, double pivotY, int frames, double fps)
{
    std::vector<std::pair<double, double>> result;
    if (frames <= 0)
        return result;
    if (prediction_prev_time.time_since_epoch().count() == 0)
        return result;

    double dt = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - prediction_prev_time).count();
    if (dt > 0.5)
        return result;

    double frame_time = 1.0 / std::max(fps, 1.0);
    double vx = prediction_initialized ? prediction_velocity_x : 0.0;
    double vy = prediction_initialized ? prediction_velocity_y : 0.0;

    result.reserve(frames);
    for (int i = 1; i <= frames; ++i)
    {
        double t = frame_time * i;
        result.push_back({ pivotX + vx * t, pivotY + vy * t });
    }
    return result;
}

std::pair<double, double> MouseThread::predict_target_position(double target_x, double target_y)
{
    ensurePredictionKalman(config.prediction_kalman_process_noise,
        config.prediction_kalman_measurement_noise);
    ensureKalman(config.kalman_process_noise, config.kalman_measurement_noise);

    double infer_ms = 0.0;
    if (config.backend == "DML" && dml_detector)
    {
        infer_ms = dml_detector->lastInferenceTimeDML.count();
    }
#ifdef USE_CUDA
    else if (config.backend != "COLOR")
    {
        infer_ms = trt_detector.lastInferenceTime.count();
    }
#endif

    auto pred = updatePredictionState(target_x, target_y, 0.0, 0.0);
    double predX = pred.first;
    double predY = pred.second;

    int mode = config.prediction_mode;
    double interval = std::max(0.0, static_cast<double>(config.predictionInterval));
    if (mode == 0)
    {
        auto vel = updateStandardVelocity(target_x, target_y, 0.0, 0.0);
        double latency_s = std::max(0.0, infer_ms) / 1000.0;
        predX = target_x + vel.first * (interval + latency_s);
        predY = target_y + vel.second * (interval + latency_s);
    }
    else if (mode == 2)
    {
        predX += last_raw_velocity_x * interval;
        predY += last_raw_velocity_y * interval;
    }

    double latency_s = std::max(0.0, infer_ms) / 1000.0;
    double extra_lead_s = latency_s;
    if (mode == 1)
        extra_lead_s += interval;
    if ((mode == 1 || mode == 2) && extra_lead_s > 0.0)
    {
        predX += prediction_velocity_x * extra_lead_s;
        predY += prediction_velocity_y * extra_lead_s;
    }

    return { predX, predY };
}

void MouseThread::sendMovementToDriver(int dx, int dy)
{
    std::lock_guard<std::mutex> lock(input_method_mutex);
    if (makcu)
    {
        makcu->move(dx, dy);
    }
    else if (kmbox)
    {
        kmbox->move(dx, dy);
    }
    else if (kmbox_net)
    {
        kmbox_net->move(dx, dy);
    }
    else if (serial)
    {
        serial->move(dx, dy);
    }
    else
    {
        INPUT in{ 0 };
        in.type = INPUT_MOUSE;
        in.mi.dx = dx;  in.mi.dy = dy;
        in.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK;
        SendInput(1, &in, sizeof(INPUT));
    }
}

std::pair<double, double> MouseThread::calc_movement(double tx, double ty)
{
    double offx = tx - center_x;
    double offy = ty - center_y;
    double dist = std::hypot(offx, offy);
    double speed = calculate_speed_multiplier(dist);

    double degPerPxX = fov_x / screen_width;
    double degPerPxY = fov_y / screen_height;

    double mmx = offx * degPerPxX;
    double mmy = offy * degPerPxY;

    double corr = 1.0;
    double fps = static_cast<double>(captureFps.load());
    if (fps > 30.0) corr = 30.0 / fps;

    auto counts_pair = config.degToCounts(mmx, mmy, fov_x);
    double move_x = counts_pair.first * speed * corr;
    double move_y = counts_pair.second * speed * corr;

    return { move_x, move_y };
}

double MouseThread::calculate_speed_multiplier(double distance)
{
    if (distance < config.snapRadius)
        return min_speed_multiplier * config.snapBoostFactor;

    if (distance < config.nearRadius)
    {
        double t = distance / config.nearRadius;
        double curve = 1.0 - std::pow(1.0 - t, config.speedCurveExponent);
        return min_speed_multiplier +
            (max_speed_multiplier - min_speed_multiplier) * curve;
    }

    double norm = std::clamp(distance / max_distance, 0.0, 1.0);
    return min_speed_multiplier +
        (max_speed_multiplier - min_speed_multiplier) * norm;
}

bool MouseThread::check_target_in_scope(double target_x, double target_y, double target_w, double target_h, double reduction_factor)
{
    double center_target_x = target_x + target_w / 2.0;
    double center_target_y = target_y + target_h / 2.0;

    double reduced_w = target_w * (reduction_factor / 2.0);
    double reduced_h = target_h * (reduction_factor / 2.0);

    double x1 = center_target_x - reduced_w;
    double x2 = center_target_x + reduced_w;
    double y1 = center_target_y - reduced_h;
    double y2 = center_target_y + reduced_h;

    return (center_x > x1 && center_x < x2 && center_y > y1 && center_y < y2);
}

void MouseThread::pressMouse(const AimbotTarget& target, float scope_multiplier)
{
    std::lock_guard<std::mutex> lock(input_method_mutex);

    double multiplier = scope_multiplier > 0.0f ? scope_multiplier : bScope_multiplier;
    bool bScope = check_target_in_scope(target.x, target.y, target.w, target.h, multiplier);
    if (bScope && !mouse_pressed)
    {
        if (makcu)
        {
            makcu->press(0);
        }
        else if (kmbox)
        {
            kmbox->press(0);
        }
        else if (kmbox_net)
        {
            kmbox_net->keyDown(0);
        }
        else if (serial)
        {
            serial->press();
        }
        else
        {
            INPUT input = { 0 };
            input.type = INPUT_MOUSE;
            input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
            SendInput(1, &input, sizeof(INPUT));
        }
        mouse_pressed = true;
    }
    else if (!bScope && mouse_pressed)
    {
        if (makcu)
        {
            makcu->release(0);
        }
        else if (kmbox)
        {
            kmbox->release(0);
        }
        else if (kmbox_net)
        {
            kmbox_net->keyUp(0);
        }
        else if (serial)
        {
            serial->release();
        }
        else
        {
            INPUT input = { 0 };
            input.type = INPUT_MOUSE;
            input.mi.dwFlags = MOUSEEVENTF_LEFTUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        mouse_pressed = false;
    }
}

void MouseThread::releaseMouse()
{
    std::lock_guard<std::mutex> lock(input_method_mutex);

    if (mouse_pressed)
    {
        if (makcu)
        {
            makcu->release(0);
        }
        else if (kmbox)
        {
            kmbox->release(0);
        }
        else if (kmbox_net)
        {
            kmbox_net->keyUp(0);
        }
        else if (serial)
        {
            serial->release();
        }
        else
        {
            INPUT input = { 0 };
            input.type = INPUT_MOUSE;
            input.mi.dwFlags = MOUSEEVENTF_LEFTUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        mouse_pressed = false;
    }
}

void MouseThread::resetPrediction()
{
    resetAimState();
}

void MouseThread::checkAndResetPredictions()
{
    resetIfStale(0.5);
}

std::vector<std::pair<double, double>> MouseThread::predictFuturePositions(double pivotX, double pivotY, int frames)
{
    double fps = static_cast<double>(captureFps.load());
    return predictFuturePositionsInternal(pivotX, pivotY, frames, fps);
}

void MouseThread::storeFuturePositions(const std::vector<std::pair<double, double>>& positions)
{
    std::lock_guard<std::mutex> lock(futurePositionsMutex);
    futurePositions = positions;
}

void MouseThread::clearFuturePositions()
{
    std::lock_guard<std::mutex> lock(futurePositionsMutex);
    futurePositions.clear();
}

std::vector<std::pair<double, double>> MouseThread::getFuturePositions()
{
    std::lock_guard<std::mutex> lock(futurePositionsMutex);
    return futurePositions;
}

void MouseThread::setSerialConnection(SerialConnection* newSerial)
{
    std::lock_guard<std::mutex> lock(input_method_mutex);
    serial = newSerial;
}

void MouseThread::setKmboxConnection(KmboxConnection* newKmbox)
{
    std::lock_guard<std::mutex> lock(input_method_mutex);
    kmbox = newKmbox;
}

void MouseThread::setKmboxNetConnection(KmboxNetConnection* newKmbox_net)
{
    std::lock_guard<std::mutex> lock(input_method_mutex);
    kmbox_net = newKmbox_net;
}

void MouseThread::setMakcuConnection(MakcuConnection* newMakcu)
{
    std::lock_guard<std::mutex> lock(   input_method_mutex);
    makcu = newMakcu;
}
std::pair<int, int> MouseThread::moveWithSmoothing(double targetX, double targetY, double fps)
{
    int N = smoothness > 0 ? smoothness : 1;
    bool tracking = config.tracking_smoothing;

    int tracking_flag = tracking ? 1 : 0;
    if (last_tracking_mode == -1 || last_tracking_mode != tracking_flag)
    {
        resetSmoothingState();
        last_tracking_mode = tracking_flag;
    }

    if (tracking)
    {
        auto now = std::chrono::steady_clock::now();
        double dt;
        if (track_time.time_since_epoch().count() == 0)
            dt = 1.0 / std::max(fps, 1.0);
        else
            dt = std::max(std::chrono::duration<double>(now - track_time).count(), 1e-8);
        dt = std::min(dt, 0.25);
        track_time = now;

        if (!tracking_initialized)
        {
            track_x = center_x;
            track_y = center_y;
            track_prev_x = track_x;
            track_prev_y = track_y;
            tracking_initialized = true;
        }

        double delta = std::hypot(targetX - track_x, targetY - track_y);
        double reset_threshold = std::max(1.0, static_cast<double>(config.resetThreshold));
        double base_alpha = 1.0 - std::exp(-dt * std::max(fps, 1.0) / N);
        double catchup = clampValue(delta / std::max(reset_threshold, 1e-3), 0.0, 1.0);
        double alpha = clampValue(base_alpha + (0.65 - base_alpha) * catchup, base_alpha, 0.65);

        track_x += (targetX - track_x) * alpha;
        track_y += (targetY - track_y) * alpha;

        double dx = track_x - track_prev_x;
        double dy = track_y - track_prev_y;

        auto mv = addOverflow(dx, dy, move_overflow_x, move_overflow_y);
        int ix = static_cast<int>(mv.first);
        int iy = static_cast<int>(mv.second);

        track_prev_x = track_x;
        track_prev_y = track_y;
        smooth_last_tx = targetX;
        smooth_last_ty = targetY;
        return { ix, iy };
    }

    if (smooth_frame == 0 ||
        std::hypot(targetX - smooth_last_tx, targetY - smooth_last_ty) > 1.0)
    {
        smooth_start_x = center_x;
        smooth_start_y = center_y;
        smooth_prev_x = smooth_start_x;
        smooth_prev_y = smooth_start_y;
        smooth_frame = 0;
    }

    smooth_last_tx = targetX;
    smooth_last_ty = targetY;
    smooth_frame = std::min(smooth_frame + 1, N);
    double t = static_cast<double>(smooth_frame) / N;
    double p = easeInOut(t);

    double curX = smooth_start_x + (targetX - smooth_start_x) * p;
    double curY = smooth_start_y + (targetY - smooth_start_y) * p;

    double dx = curX - smooth_prev_x;
    double dy = curY - smooth_prev_y;

    auto mv = addOverflow(dx, dy, move_overflow_x, move_overflow_y);
    int ix = static_cast<int>(mv.first);
    int iy = static_cast<int>(mv.second);

    smooth_prev_x = curX;
    smooth_prev_y = curY;
    return { ix, iy };
}

std::pair<int, int> MouseThread::moveWithKalman(double targetX, double targetY, double fps)
{
    double reset_threshold = std::max(1.0, static_cast<double>(config.resetThreshold));
    auto now = std::chrono::steady_clock::now();

    if (prevKalmanTime.time_since_epoch().count() == 0 ||
        std::hypot(targetX - last_raw_kalman_x, targetY - last_raw_kalman_y) > reset_threshold)
    {
        kfX.reset(targetX, 0.0);
        kfY.reset(targetY, 0.0);
        prevKalmanTime = now;
    }

    last_raw_kalman_x = targetX;
    last_raw_kalman_y = targetY;

    auto now2 = std::chrono::steady_clock::now();
    double dt;
    if (prevKalmanTime.time_since_epoch().count() == 0)
        dt = 1.0 / std::max(fps, 1.0);
    else
        dt = std::max(std::chrono::duration<double>(now2 - prevKalmanTime).count(), 1e-8);
    prevKalmanTime = now2;

    double filtX = kfX.update(targetX, dt);
    double filtY = kfY.update(targetY, dt);

    auto mv = calc_movement(filtX, filtY);
    double mvX = mv.first * kalman_speed_multiplier_x;
    double mvY = mv.second * kalman_speed_multiplier_y;

    return { static_cast<int>(std::round(mvX)), static_cast<int>(std::round(mvY)) };
}

std::pair<int, int> MouseThread::moveWithKalmanAndSmoothing(double targetX, double targetY, double fps)
{
    double reset_threshold = std::max(1.0, static_cast<double>(config.resetThreshold));
    auto now = std::chrono::steady_clock::now();
    const double max_dt = 0.25;

    bool need_reset = !kalman_smoothing_initialized;
    if (!need_reset)
    {
        double jump = std::hypot(targetX - last_raw_kalman_x, targetY - last_raw_kalman_y);
        if (jump > reset_threshold)
            need_reset = true;
        if (prevKalmanTime.time_since_epoch().count() != 0)
        {
            double since_last = std::chrono::duration<double>(now - prevKalmanTime).count();
            if (since_last > max_dt)
                need_reset = true;
        }
    }

    if (need_reset || prevKalmanTime.time_since_epoch().count() == 0)
    {
        kfX.reset(targetX, 0.0);
        kfY.reset(targetY, 0.0);
        prevKalmanTime = now;
        last_kx = targetX;
        last_ky = targetY;
        move_overflow_x = 0.0;
        move_overflow_y = 0.0;
        kalman_smoothing_initialized = true;
    }

    last_raw_kalman_x = targetX;
    last_raw_kalman_y = targetY;

    double dt;
    if (prevKalmanTime.time_since_epoch().count() == 0 || need_reset)
        dt = 1.0 / std::max(fps, 1.0);
    else
        dt = std::chrono::duration<double>(now - prevKalmanTime).count();
    prevKalmanTime = now;
    dt = clampValue(dt, 1e-8, max_dt);

    double filtX = kfX.update(targetX, dt);
    double filtY = kfY.update(targetY, dt);

    int N = smoothness > 0 ? smoothness : 1;
    double base_alpha = 1.0 - std::exp(-dt * std::max(fps, 1.0) / N);
    double delta = std::hypot(filtX - last_kx, filtY - last_ky);
    double catchup = clampValue(delta / std::max(reset_threshold, 1e-3), 0.0, 1.0);
    double max_alpha = config.tracking_smoothing ? 0.65 : 0.45;
    double alpha = clampValue(base_alpha + (max_alpha - base_alpha) * catchup, base_alpha, max_alpha);

    if (delta > reset_threshold)
    {
        last_kx = filtX;
        last_ky = filtY;
    }
    else
    {
        last_kx += (filtX - last_kx) * alpha;
        last_ky += (filtY - last_ky) * alpha;
    }

    auto mv = calc_movement(last_kx, last_ky);
    double mvX = mv.first * kalman_speed_multiplier_x;
    double mvY = mv.second * kalman_speed_multiplier_y;

    auto step = addOverflow(mvX, mvY, move_overflow_x, move_overflow_y);
    return { static_cast<int>(step.first), static_cast<int>(step.second) };
}

std::pair<int, int> MouseThread::computeMove(
    double targetX, double targetY, double fps, double infer_latency_ms,
    double camera_dx, double camera_dy)
{
    markTargetSeen();
    ensurePredictionKalman(config.prediction_kalman_process_noise,
        config.prediction_kalman_measurement_noise);
    ensureKalman(config.kalman_process_noise, config.kalman_measurement_noise);

    auto pred = updatePredictionState(targetX, targetY, camera_dx, camera_dy);
    double predX = pred.first;
    double predY = pred.second;

    int mode = config.prediction_mode;
    double interval = std::max(0.0, static_cast<double>(config.predictionInterval));

    if (mode == 0)
    {
        auto vel = updateStandardVelocity(targetX, targetY, camera_dx, camera_dy);
        double latency_s = std::max(0.0, infer_latency_ms) / 1000.0;
        predX = targetX + vel.first * (interval + latency_s);
        predY = targetY + vel.second * (interval + latency_s);
    }
    else if (mode == 2)
    {
        predX += last_raw_velocity_x * interval;
        predY += last_raw_velocity_y * interval;
    }

    double latency_s = std::max(0.0, infer_latency_ms) / 1000.0;
    double extra_lead_s = latency_s;
    if (mode == 1)
        extra_lead_s += interval;
    if ((mode == 1 || mode == 2) && extra_lead_s > 0.0)
    {
        predX += prediction_velocity_x * extra_lead_s;
        predY += prediction_velocity_y * extra_lead_s;
    }

    bool use_future_for_aim = config.prediction_use_future_for_aim;
    bool need_future = use_future_for_aim || config.draw_futurePositions;
    if (need_future)
    {
        auto future = predictFuturePositionsInternal(
            predX, predY, config.prediction_futurePositions, fps);
        if (use_future_for_aim && !future.empty())
        {
            predX = future.back().first;
            predY = future.back().second;
        }
        storeFuturePositions(future);
    }
    else
    {
        clearFuturePositions();
    }

    if (use_kalman && use_smoothing)
        return moveWithKalmanAndSmoothing(predX, predY, fps);
    if (use_kalman)
        return moveWithKalman(predX, predY, fps);
    if (use_smoothing)
        return moveWithSmoothing(predX, predY, fps);

    auto mv = calc_movement(predX, predY);
    return { static_cast<int>(std::round(mv.first)), static_cast<int>(std::round(mv.second)) };
}

// Kalman (public wrappers)
void MouseThread::moveMouseWithKalman(double targetX, double targetY)
{
    double fps = std::max(1.0, static_cast<double>(captureFps.load()));
    auto delta = moveWithKalman(targetX, targetY, fps);
    if (delta.first || delta.second)
    {
        if (wind_mouse_enabled)
            windMouseMoveRelative(delta.first, delta.second);
        else
            queueMove(delta.first, delta.second);
    }
}

// Kalman + smoothing (public wrappers)
void MouseThread::moveMouseWithKalmanAndSmoothing(double targetX, double targetY)
{
    double fps = std::max(1.0, static_cast<double>(captureFps.load()));
    auto delta = moveWithKalmanAndSmoothing(targetX, targetY, fps);
    if (delta.first || delta.second)
    {
        if (wind_mouse_enabled)
            windMouseMoveRelative(delta.first, delta.second);
        else
            queueMove(delta.first, delta.second);
    }
}


// easing-функция для плавности
double MouseThread::easeInOut(double t) {
    return -0.5 * (std::cos(M_PI * t) - 1.0);
}

// Управление дробной частью, чтобы не терять пиксели
std::pair<double, double> MouseThread::addOverflow(
    double dx, double dy,
    double& overflow_x, double& overflow_y)
{
    double int_x = 0.0, int_y = 0.0;
    double frac_x = std::modf(dx + overflow_x, &int_x);
    double frac_y = std::modf(dy + overflow_y, &int_y);

    if (std::abs(frac_x) > 1.0) {
        double extra = 0.0;
        frac_x = std::modf(frac_x, &extra);
        int_x += extra;
    }
    if (std::abs(frac_y) > 1.0) {
        double extra = 0.0;
        frac_y = std::modf(frac_y, &extra);
        int_y += extra;
    }

    overflow_x = frac_x;
    overflow_y = frac_y;
    return { int_x, int_y };
}

void MouseThread::setKalmanParams(double processNoise, double measurementNoise) {
    std::lock_guard<std::mutex> lg(input_method_mutex);
    // просто перезапускаем фильтры с новыми Q/R
    kfX = Kalman1D(processNoise, measurementNoise);
    kfY = Kalman1D(processNoise, measurementNoise);
    last_kalman_q = processNoise;
    last_kalman_r = measurementNoise;
    kalman_smoothing_initialized = false;
    prevKalmanTime = std::chrono::steady_clock::time_point{};
}

void MouseThread::moveMouse(const AimbotTarget& target)
{
    double fps = std::max(1.0, static_cast<double>(captureFps.load()));
    double infer_ms = 0.0;
    if (config.backend == "DML" && dml_detector)
        infer_ms = dml_detector->lastInferenceTimeDML.count();
#ifdef USE_CUDA
    else if (config.backend != "COLOR")
        infer_ms = trt_detector.lastInferenceTime.count();
#endif

    auto delta = computeMove(target.pivotX, target.pivotY, fps, infer_ms, 0.0, 0.0);
    if (delta.first || delta.second)
    {
        if (wind_mouse_enabled)
            windMouseMoveRelative(delta.first, delta.second);
        else
            queueMove(delta.first, delta.second);
    }
}

// Аналогично для moveMousePivot
void MouseThread::moveMousePivot(double pivotX, double pivotY)
{
    double fps = std::max(1.0, static_cast<double>(captureFps.load()));
    double infer_ms = 0.0;
    if (config.backend == "DML" && dml_detector)
        infer_ms = dml_detector->lastInferenceTimeDML.count();
#ifdef USE_CUDA
    else if (config.backend != "COLOR")
        infer_ms = trt_detector.lastInferenceTime.count();
#endif

    auto delta = computeMove(pivotX, pivotY, fps, infer_ms, 0.0, 0.0);
    if (delta.first || delta.second)
    {
        if (wind_mouse_enabled)
            windMouseMoveRelative(delta.first, delta.second);
        else
            queueMove(delta.first, delta.second);
    }
}
