// mouse.h
#ifndef MOUSE_H
#define MOUSE_H

#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <mutex>
#include <atomic>
#include <chrono>
#include <vector>
#include <utility>
#include <queue>
#include <thread>
#include <condition_variable>
#include <cmath> // std::modf, std::cos, M_PI

#include "AimbotTarget.h"
#include "SerialConnection.h"
#include "Kmbox_b.h"
#include "KmboxNetConnection.h"
#include "MakcuConnection.h"

class MouseThread
{
private:
    // ???????? ?????????
    double screen_width, screen_height;
    double prediction_interval;
    double fov_x, fov_y;
    double max_distance;
    double min_speed_multiplier, max_speed_multiplier;
    double center_x, center_y;
    bool   auto_shoot;
    float  bScope_multiplier;
    float  triggerbot_bScope_multiplier;

    // ??? ????????????
    double prev_x, prev_y;
    double prev_velocity_x, prev_velocity_y;
    std::chrono::time_point<std::chrono::steady_clock> prev_time;
    std::chrono::steady_clock::time_point last_target_time;
    std::atomic<bool> target_detected{ false };
    std::atomic<bool> mouse_pressed{ false };

    // ?????????? ?????
    SerialConnection* serial;
    KmboxConnection* kmbox;
    KmboxNetConnection* kmbox_net;
    MakcuConnection* makcu;

    // ???????? ????????
    void sendMovementToDriver(int dx, int dy);
    struct Move { int dx, dy; };
    std::queue<Move>            moveQueue;
    std::mutex                  queueMtx;
    std::condition_variable     queueCv;
    const size_t                queueLimit = 5;
    std::thread                 moveWorker;
    std::atomic<bool>           workerStop{ false };

    // ???? ?????? ??????
    bool use_smoothing = { false };
    bool use_kalman = { true };

    // ??? «?????»
    bool   wind_mouse_enabled = true;
    double wind_G, wind_W, wind_M, wind_D;
    void   windMouseMoveRelative(int dx, int dy);

    // ?????? ???????? ???????? ? ????????
    std::pair<double, double> calc_movement(double tx, double ty);
    double calculate_speed_multiplier(double distance);

    // ???????? ?????????
    std::vector<std::pair<double, double>> futurePositions;
    std::mutex                            futurePositionsMutex;

    void moveWorkerLoop();
    void queueMove(int dx, int dy);

    // ????????? ??? ???????????
    int    smoothness{ 100 };
    double move_overflow_x{ 0.0 }, move_overflow_y{ 0.0 };

    double easeInOut(double t);
    std::pair<double, double> addOverflow(double dx, double dy,
        double& overflow_x, double& overflow_y);

    struct Kalman1D {
        double x{ 0 }, v{ 0 }, P{ 1 }, Q{ 0.01 }, R{ 0.1 };
        Kalman1D() = default;
        Kalman1D(double processNoise, double measurementNoise)
            : Q(processNoise), R(measurementNoise) {
        }
        void reset(double x0 = 0.0, double v0 = 0.0) {
            x = x0;
            v = v0;
            P = 1.0;
        }
        double update(double z, double dt) {
            x += v * dt;
            P += Q * dt;
            double K = P / (P + R);
            x += K * (z - x);
            P *= (1 - K);
            v = (1 - K) * v + K * ((z - x) / std::max(dt, 1e-8));
            return x;
        }
    };

    Kalman1D    kfX{ 0.01, 0.1 }, kfY{ 0.01, 0.1 };
    std::chrono::steady_clock::time_point prevKalmanTime{};
    double last_kx{ 0.0 };
    double last_ky{ 0.0 };
    double last_raw_kalman_x{ 0.0 };
    double last_raw_kalman_y{ 0.0 };
    bool   kalman_smoothing_initialized{ false };
    double last_kalman_q{ -1.0 };
    double last_kalman_r{ -1.0 };

    // RN_AI prediction state
    std::chrono::steady_clock::time_point prediction_prev_time{};
    double prediction_prev_x{ 0.0 };
    double prediction_prev_y{ 0.0 };
    double prediction_smoothed_velocity_x{ 0.0 };
    double prediction_smoothed_velocity_y{ 0.0 };
    double prediction_velocity_x{ 0.0 };
    double prediction_velocity_y{ 0.0 };
    bool   prediction_initialized{ false };
    std::chrono::steady_clock::time_point prediction_kalman_time{};
    bool   prediction_kalman_initialized{ false };
    int    last_prediction_mode{ -1 };
    double last_prediction_q{ -1.0 };
    double last_prediction_r{ -1.0 };
    Kalman1D prediction_kf_x{ 0.01, 0.1 };
    Kalman1D prediction_kf_y{ 0.01, 0.1 };
    double last_raw_velocity_x{ 0.0 };
    double last_raw_velocity_y{ 0.0 };

    // Smoothing state
    int    smooth_frame{ 0 };
    double smooth_start_x{ 0.0 };
    double smooth_start_y{ 0.0 };
    double smooth_prev_x{ 0.0 };
    double smooth_prev_y{ 0.0 };
    double smooth_last_tx{ 0.0 };
    double smooth_last_ty{ 0.0 };

    bool   tracking_initialized{ false };
    double track_x{ 0.0 };
    double track_y{ 0.0 };
    double track_prev_x{ 0.0 };
    double track_prev_y{ 0.0 };
    std::chrono::steady_clock::time_point track_time{};
    int    last_tracking_mode{ -1 };

    double kalman_speed_multiplier_x{ 1.0 };
    double kalman_speed_multiplier_y{ 1.0 };

    static double clampValue(double v, double lo, double hi);
    void resetAimState();
    void resetPredictionState();
    void resetKalmanState();
    void resetSmoothingState();
    void markTargetSeen();
    void resetIfStale(double timeout_s);
    void ensurePredictionKalman(double q, double r);
    void ensureKalman(double q, double r);
    std::pair<double, double> cameraVelocity(double camera_dx, double camera_dy, double dt);
    std::pair<double, double> updateStandardVelocity(double targetX, double targetY, double camera_dx, double camera_dy);
    std::pair<double, double> updatePredictionState(double pivotX, double pivotY, double camera_dx, double camera_dy);
    std::vector<std::pair<double, double>> predictFuturePositionsInternal(double pivotX, double pivotY, int frames, double fps);
    std::pair<int, int> moveWithSmoothing(double targetX, double targetY, double fps);
    std::pair<int, int> moveWithKalman(double targetX, double targetY, double fps);
    std::pair<int, int> moveWithKalmanAndSmoothing(double targetX, double targetY, double fps);
    std::pair<int, int> computeMove(double targetX, double targetY, double fps, double infer_latency_ms, double camera_dx, double camera_dy);
public:
    std::mutex input_method_mutex;

    MouseThread(
        int resolution,
        int fovX,
        int fovY,
        double minSpeedMultiplier,
        double maxSpeedMultiplier,
        double predictionInterval,
        bool auto_shoot,
        float bScope_multiplier,
        float triggerbot_bScope_multiplier,
        SerialConnection* serialConnection = nullptr,
        KmboxConnection* kmboxConnection = nullptr,
        KmboxNetConnection* kmboxNetConnection = nullptr,
        MakcuConnection* makcu = nullptr
    );
    ~MouseThread();

    void updateConfig(
        int resolution,
        int fovX,
        int fovY,
        double minSpeedMultiplier,
        double maxSpeedMultiplier,
        double predictionInterval,
        bool auto_shoot,
        float bScope_multiplier,
        float triggerbot_bScope_multiplier
    );

    // ????????????? ??????
    void setUseSmoothing(bool v) { use_smoothing = v; }
    bool isUsingSmoothing() const { return use_smoothing; }

    void setUseKalman(bool v) { use_kalman = v; }
    bool isUsingKalman() const { return use_kalman; }

    // ????????? «?????????»
    void setSmoothness(int s) { smoothness = (s > 0 ? s : 1); }
    int  getSmoothness() const { return smoothness; }

    // API ???????? ? ??????
    void moveMousePivot(double pivotX, double pivotY);
    std::pair<double, double> predict_target_position(double x, double y);
    void moveMouse(const AimbotTarget& target);
    void pressMouse(const AimbotTarget& target, float scope_multiplier = -1.0f);
    void releaseMouse();
    void resetPrediction();
    void checkAndResetPredictions();
    bool check_target_in_scope(double x, double y,
        double w, double h, double reduction_factor);

    // ??????? ???????
    std::vector<std::pair<double, double>> predictFuturePositions(
        double pivotX, double pivotY, int frames);
    void storeFuturePositions(
        const std::vector<std::pair<double, double>>& pos);
    void clearFuturePositions();
    std::vector<std::pair<double, double>> getFuturePositions();

    // ??????? ???????????
    void setSerialConnection(SerialConnection* s);
    void setKmboxConnection(KmboxConnection* k);
    void setKmboxNetConnection(KmboxNetConnection* k);
    void setMakcuConnection(MakcuConnection* m);

    // Smooth
    void setSmoothnessValue(int value) { smoothness = value; }
    int getSmoothnessValue() const { return smoothness; }

    // Kalma + smooth
    void moveMouseWithKalmanAndSmoothing(double targetX, double targetY);

    // Kalma
    void moveMouseWithKalman(double targetX, double targetY);
    void setKalmanParams(double processNoise, double measurementNoise);
    void setKalmanSpeedMultiplierX(double m) {
        std::lock_guard<std::mutex> lg(input_method_mutex);
        kalman_speed_multiplier_x = std::max(0.0, m);
    }
    double getKalmanSpeedMultiplierX() const {
        return kalman_speed_multiplier_x;
    }

    void setKalmanSpeedMultiplierY(double m) {
        std::lock_guard<std::mutex> lg(input_method_mutex);
        kalman_speed_multiplier_y = std::max(0.0, m);
    }
    double getKalmanSpeedMultiplierY() const {
        return kalman_speed_multiplier_y;
    }

    // Target
    void setTargetDetected(bool d) {
        target_detected.store(d);
    }
    void setLastTargetTime(
        const std::chrono::steady_clock::time_point& t)
    {
        last_target_time = t;
    }
};

#endif // MOUSE_H
