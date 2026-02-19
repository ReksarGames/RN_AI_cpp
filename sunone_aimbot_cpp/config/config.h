#ifndef CONFIG_H
#define CONFIG_H

#include <string>
#include <vector>
#include <unordered_map>
#include <utility>
#include <cstdint> 

class Config
{
public:
    // Capture
    std::string capture_method; // "duplication_api", "winrt", "virtual_camera", "obs"
    int detection_resolution;
    int capture_fps;
    int monitor_idx;
    bool circle_mask;
    bool capture_borders;
    bool capture_cursor;
    std::string virtual_camera_name;
    int virtual_camera_width;
    int virtual_camera_heigth;

    // Target
    bool disable_headshot;
    float body_y_offset;
    float head_y_offset;
    bool ignore_third_person;
    bool shooting_range_targets;
    bool focusTarget;
    bool auto_aim;
    bool target_lock_enabled;
    float target_lock_distance;
    float target_lock_reacquire_time;
    bool smart_target_lock;
    int target_reference_class;
    int target_lock_fallback_class;
    int target_switch_delay;
    float aim_bot_scope;
    float aim_bot_position;
    float aim_bot_position2;
    std::string allowed_classes;
    std::string class_priority_order;
    std::unordered_map<int, std::string> custom_class_names;
    float distance_scoring_weight;
    float center_scoring_weight;
    float size_scoring_weight;
    float aim_weight_tiebreak_ratio;
    bool small_target_enhancement_enabled;
    float small_target_boost_factor;
    float small_target_threshold;
    float small_target_medium_threshold;
    float small_target_medium_boost;
    bool small_target_smooth_enabled;
    int small_target_smooth_frames;
    std::unordered_map<int, std::pair<float, float>> class_aim_positions;

    // Mouse
    int fovX;
    int fovY;
    float minSpeedMultiplier;
    float maxSpeedMultiplier;

    int smoothness;
    bool use_smoothing;
    bool tracking_smoothing;

    bool use_kalman;
    float kalman_process_noise;
    float kalman_measurement_noise;
    float kalman_speed_multiplier_x;
    float kalman_speed_multiplier_y;
    float resetThreshold;

    float predictionInterval;
    int prediction_mode;
    float prediction_kalman_lead_ms;
    float prediction_kalman_max_lead_ms;
    float prediction_velocity_smoothing;
    float prediction_velocity_scale;
    float prediction_kalman_process_noise;
    float prediction_kalman_measurement_noise;
    bool prediction_use_future_for_aim;
    int prediction_futurePositions;
    bool draw_futurePositions;

    bool camera_compensation_enabled;
    float camera_compensation_max_shift;
    float camera_compensation_strength;

    float snapRadius;
    float nearRadius;
    float speedCurveExponent;
    float snapBoostFactor;

    bool easynorecoil;
    float easynorecoilstrength;
    std::string input_method; // "WIN32", "ARDUINO", "MAKCU", "KMBOX_B", "KMBOX_NET"

    // Wind mouse
    bool wind_mouse_enabled;
    float wind_G;
    float wind_W;
    float wind_M;
    float wind_D;

    // Arduino
    int arduino_baudrate;
    std::string arduino_port;
    bool arduino_16_bit_mouse;
    bool arduino_enable_keys;

    // Makcu 
    std::string makcu_port;  
    int makcu_baudrate;     

    // kmbox_b
    int kmbox_b_baudrate;
    std::string kmbox_b_port;

    // kmbox_net
    std::string kmbox_net_ip;
    std::string kmbox_net_port;
    std::string kmbox_net_uuid;

    // Mouse shooting
    bool auto_shoot;
    bool triggerbot;
    double triggerbot_interval;      // seconds between triggerbot shots (0 = continuous hold)
    double triggerbot_predict_ms;    // prediction lead for triggerbot (ms, 0 = off)
    double triggerbot_predict_alpha; // smoothing factor for predicted velocity (0..1)
    float bScope_multiplier;
    float triggerbot_bScope_multiplier;

    // AI
    std::string backend;
    int dml_device_id;
    std::string ai_model;
    float confidence_threshold;
    float nms_threshold;
    bool adaptive_nms;
    int max_detections;
    std::string postprocess;
    int batch_size;
#ifdef USE_CUDA
    bool export_enable_fp8;
    bool export_enable_fp16;
#endif
    bool fixed_input_size;

    // CUDA
#ifdef USE_CUDA
    bool use_cuda_graph;
    bool use_pinned_memory;
#endif
    // Buttons
    std::vector<std::string> button_targeting;
    std::vector<std::string> button_shoot;
    std::vector<std::string> button_triggerbot;
    std::vector<std::string> button_zoom;
    std::vector<std::string> button_disable_headshot;
    std::vector<std::string> button_exit;
    std::vector<std::string> button_pause;
    std::vector<std::string> button_reload_config;
    std::vector<std::string> button_open_overlay;
    bool enable_arrows_settings;

    // Overlay
    int overlay_opacity;
    bool overlay_snow_theme;
    float overlay_ui_scale;

    // OBS
    bool is_obs;
    std::string obs_ip;
    int obs_port;
    int obs_fps;

    // Custom Classes
    int class_player;                  // 0
    int class_bot;                     // 1
    int class_weapon;                  // 2
    int class_outline;                 // 3
    int class_dead_body;               // 4
    int class_hideout_target_human;    // 5
    int class_hideout_target_balls;    // 6
    int class_head;                    // 7
    int class_smoke;                   // 8
    int class_fire;                    // 9
    int class_third_person;            // 10

    // Debug
    bool show_window;
    bool show_fps;
    std::vector<std::string> screenshot_button;
    int screenshot_delay;
    bool verbose;

    // Color
    int color_erode_iter;
    int color_dilate_iter;
    int color_min_area;
    int tinyArea;
    bool isOnlyTop;
    float scanError;
    std::string color_target;  

    struct ColorRange {
        std::string name;
        int h_low, s_low, v_low;
        int h_high, s_high, v_high;
    };
    std::vector<ColorRange> color_ranges;

    struct GameProfile
    {
        std::string name;
        double sens;
        double yaw;
        double pitch;
        bool fovScaled;
        double baseFOV;
    };

    std::unordered_map<std::string, GameProfile> game_profiles;
    std::string                                  active_game;

    const GameProfile & currentProfile() const;
    std::pair<double, double> degToCounts(double degX, double degY, double fovNow) const;

    bool loadConfig(const std::string& filename = "config.ini");
    bool saveConfig(const std::string& filename = "config.ini");

    std::string joinStrings(const std::vector<std::string>& vec, const std::string& delimiter = ",");
private:
    std::vector<std::string> splitString(const std::string& str, char delimiter = ',');
};

#endif // CONFIG_H
