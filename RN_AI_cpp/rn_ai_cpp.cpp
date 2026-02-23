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

#include "capture.h"
#include "mouse.h"
#include "rn_ai_cpp.h"
#include "keyboard_listener.h"
#include "overlay.h"
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
