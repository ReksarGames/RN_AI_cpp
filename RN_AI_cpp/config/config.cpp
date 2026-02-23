#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <windows.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <string>
#include <filesystem>
#include <unordered_map>
#include <algorithm>
#include <cctype>

#include "config.h"
#include "modules/SimpleIni.h"

std::vector<std::string> Config::splitString(const std::string& str, char delimiter)
{
    std::vector<std::string> tokens;
    std::stringstream ss(str);
    std::string item;
    while (std::getline(ss, item, delimiter))
    {
        while (!item.empty() && (item.front() == ' ' || item.front() == '\t'))
            item.erase(item.begin());
        while (!item.empty() && (item.back() == ' ' || item.back() == '\t'))
            item.pop_back();

        tokens.push_back(item);
    }
    return tokens;
}

std::string Config::joinStrings(const std::vector<std::string>& vec, const std::string& delimiter)
{
    std::ostringstream oss;
    for (size_t i = 0; i < vec.size(); ++i)
    {
        if (i != 0) oss << delimiter;
        oss << vec[i];
    }
    return oss.str();
}

bool Config::loadConfig(const std::string& filename)
{
    if (!std::filesystem::exists(filename))
    {
        std::cerr << "[Config] Config file does not exist, creating default config: " << filename << std::endl;

        // Capture
        capture_method = "duplication_api";
        detection_resolution = 320;
        capture_fps = 60;
        monitor_idx = 0;
        circle_mask = true;
        capture_borders = true;
        capture_cursor = true;
        virtual_camera_name = "None";
        virtual_camera_width = 1920;
        virtual_camera_heigth = 1080;

        // Target
        disable_headshot = false;
        body_y_offset = 0.15f;
        head_y_offset = 0.05f;
        ignore_third_person = false;
        shooting_range_targets = false;
        focusTarget = false;
        auto_aim = false;
        target_lock_enabled = false;
        target_lock_distance = 100.0f;
        target_lock_reacquire_time = 0.30f;
        smart_target_lock = true;
        target_reference_class = 0;
        target_lock_fallback_class = -1;
        target_switch_delay = 0;
        aim_bot_scope = 160.0f;
        aim_bot_position = 0.5f;
        aim_bot_position2 = 0.5f;
        allowed_classes = "";
        class_priority_order = "";
        distance_scoring_weight = 1.0f;
        center_scoring_weight = 1.0f;
        size_scoring_weight = 1.0f;
        aim_weight_tiebreak_ratio = 0.1f;
        small_target_enhancement_enabled = true;
        small_target_boost_factor = 0.1f;
        small_target_threshold = 0.02f;
        small_target_medium_threshold = 0.05f;
        small_target_medium_boost = 1.5f;
        small_target_smooth_enabled = true;
        small_target_smooth_frames = 2;
        class_aim_positions.clear();
        custom_class_names.clear();

        // Mouse
        fovX = 106;
        fovY = 74;
        minSpeedMultiplier = 0.1f;
        maxSpeedMultiplier = 0.1f;

        smoothness = 100;
        use_smoothing = true;
        tracking_smoothing = false;

        use_kalman = false;
        kalman_process_noise = 0.01f;
        kalman_measurement_noise = 0.10f;
        kalman_speed_multiplier_x = 1.0;
        kalman_speed_multiplier_y = 1.0;
        resetThreshold = 5;
    
        predictionInterval = 0.01f;
        prediction_mode = 0;
        prediction_kalman_lead_ms = 0.0f;
        prediction_kalman_max_lead_ms = 0.0f;
        prediction_velocity_smoothing = 0.4f;
        prediction_velocity_scale = 1.0f;
        prediction_kalman_process_noise = 0.01f;
        prediction_kalman_measurement_noise = 0.10f;
        prediction_use_future_for_aim = false;
        prediction_futurePositions = 20;
        draw_futurePositions = true;

        camera_compensation_enabled = false;
        camera_compensation_max_shift = 50.0f;
        camera_compensation_strength = 1.0f;

        snapRadius = 1.5f;
        nearRadius = 25.0f;
        speedCurveExponent = 3.0f;
        snapBoostFactor = 1.15f; 

        easynorecoil = false;
        easynorecoilstrength = 0.0f;
        input_method = "WIN32";

        // Wind mouse
        wind_mouse_enabled = false;
        wind_G = 18.0f;
        wind_W = 15.0f;
        wind_M = 10.0f;
        wind_D = 8.0f;
        // Makcu
        makcu_baudrate = 4000000;
        makcu_port = "COM1";

        // kmbox_B
        kmbox_b_baudrate = 115200;
        kmbox_b_port = "COM0";

        // Mouse shooting
        auto_shoot = false;
        triggerbot = false;
        triggerbot_reaction_ms = 0;
        bScope_multiplier = 1.0f;
        triggerbot_bScope_multiplier = 1.0f;

        // AI
#ifdef USE_CUDA
        backend = "TRT";
#else
        backend = "DML";
#endif
        dml_device_id = 0;

#ifdef USE_CUDA
        ai_model = "sunxds_0.5.6.engine";
#else
        ai_model = "sunxds_0.5.6.onnx";
#endif

        confidence_threshold = 0.10f;
        nms_threshold = 0.50f;
        adaptive_nms = true;
        max_detections = 100;

        postprocess = "yolo10";
        batch_size = 1;
#ifdef USE_CUDA
        export_enable_fp8 = false;
        export_enable_fp16 = true;
#endif
        fixed_input_size = false;

        // CUDA
#ifdef USE_CUDA
        use_cuda_graph = false;
        use_pinned_memory = false;
        capture_use_cuda = true;
#endif

        // Buttons
        button_targeting = splitString("RightMouseButton");
        button_shoot = splitString("LeftMouseButton");
        button_triggerbot = splitString("X2MouseButton");
        button_disable_headshot = splitString("M");
        button_exit = splitString("F2");
        button_pause = splitString("F3");
        button_reload_config = splitString("F4");
        button_open_overlay = splitString("Home");
        enable_arrows_settings = false;

        // Overlay
        overlay_opacity = 225;
        overlay_snow_theme = true;
        overlay_ui_scale = 1.0f;

        // OBS
        is_obs = false;
        obs_ip = "0.0.0.0";
        obs_port = 4455;
        obs_fps = 240;

        // Custom classes
        class_player = 0;
        class_bot = 1;
        class_weapon = 2;
        class_outline = 3;
        class_dead_body = 4;
        class_hideout_target_human = 5;
        class_hideout_target_balls = 6;
        class_head = 7;
        class_smoke = 8;
        class_fire = 9;
        class_third_person = 10;

        // Color defaults
        color_erode_iter = 1;
        color_dilate_iter = 2;
        color_min_area = 50;
        tinyArea = 2;
        isOnlyTop = true;
        scanError = 0.1f;

        // ????????? ????????? ????????? HSV
        color_ranges.clear();

        // Yellow
        ColorRange yellow;
        yellow.name = "Yellow";
        yellow.h_low = 30; yellow.s_low = 125; yellow.v_low = 150;
        yellow.h_high = 30; yellow.s_high = 255; yellow.v_high = 255;
        color_ranges.push_back(yellow);

        ColorRange yellow2;
        yellow2.name = "Yellow2";
        yellow2.h_low = 20; yellow2.s_low = 100; yellow2.v_low = 120;
        yellow2.h_high = 35; yellow2.s_high = 255; yellow2.v_high = 255;
        color_ranges.push_back(yellow2);

        ColorRange purple;
        purple.name = "Purple";
        purple.h_low = 220; purple.s_low = 100; purple.v_low = 195;
        purple.h_high = 255; purple.s_high = 195; purple.v_high = 255;
        color_ranges.push_back(purple);

        color_target = "Yellow";

        // Debug
        show_window = true;
        screenshot_button = splitString("None");
        screenshot_delay = 500;
        verbose = false;

        saveConfig(filename);
        return true;
    }

    CSimpleIniA ini;
    ini.SetUnicode();
    SI_Error rc = ini.LoadFile(filename.c_str());
    if (rc < 0)
    {
        std::cerr << "[Config] Error parsing INI file: " << filename << std::endl;
        return false;
    }

    auto get_raw_value_compat = [&](const char* key) -> const char*
    {
        const char* val = ini.GetValue("", key, nullptr);
        if (val == nullptr)
            val = ini.GetValue("ClassNames", key, nullptr);
        if (val == nullptr)
            val = ini.GetValue("Colors", key, nullptr);
        return val;
    };

    auto get_string = [&](const char* key, const std::string& defval)
    {
        const char* val = get_raw_value_compat(key);
        return val ? std::string(val) : defval;
    };

    auto get_bool = [&](const char* key, bool defval)
        {
            std::string value = get_string(key, defval ? "true" : "false");
            std::transform(value.begin(), value.end(), value.begin(),
                [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
            if (value == "1" || value == "true" || value == "yes" || value == "on")
                return true;
            if (value == "0" || value == "false" || value == "no" || value == "off")
                return false;
            return defval;
        };

    auto get_long = [&](const char* key, long defval)
        {
            try
            {
                return static_cast<int>(std::stol(get_string(key, std::to_string(defval))));
            }
            catch (...)
            {
                return static_cast<int>(defval);
            }
        };

    auto get_double = [&](const char* key, double defval)
        {
            try
            {
                return std::stod(get_string(key, std::to_string(defval)));
            }
            catch (...)
            {
                return defval;
            }
        };

    game_profiles.clear();

    CSimpleIniA::TNamesDepend keys;
    ini.GetAllKeys("Games", keys);

    for (const auto& k : keys)
    {
        std::string name = k.pItem;
        std::string val = ini.GetValue("Games", k.pItem, "");
        auto parts = splitString(val, ',');

        try
        {
            if (parts.size() < 2)
                throw std::runtime_error("not enough values");

            GameProfile gp;
            gp.name = name;
            gp.sens = std::stod(parts[0]);
            gp.yaw = std::stod(parts[1]);
            gp.pitch = parts.size() > 2 ? std::stod(parts[2]) : gp.yaw;
            gp.fovScaled = parts.size() > 3 && (parts[3] == "true" || parts[3] == "1");
            gp.baseFOV = parts.size() > 4 ? std::stod(parts[4]) : 0.0;

            game_profiles[name] = gp;
        }
        catch (const std::exception& e)
        {
            std::cerr << "[Config] Failed to parse profile: " << name
                << " = " << val << " (" << e.what() << ")" << std::endl;
        }
    }

    if (!game_profiles.count("UNIFIED"))
    {
        GameProfile uni;
        uni.name = "UNIFIED";
        uni.sens = 1.0;
        uni.yaw = 0.022;
        uni.pitch = uni.yaw;
        uni.fovScaled = false;
        uni.baseFOV = 0.0;
        game_profiles[uni.name] = uni;
    }

    active_game = get_string("active_game", active_game);
    if (!game_profiles.count(active_game) && !game_profiles.empty())
        active_game = game_profiles.begin()->first;

    // Capture
    capture_method = get_string("capture_method", "duplication_api");
    detection_resolution = get_long("detection_resolution", 320);
    if (detection_resolution != 240 && detection_resolution != 320 && detection_resolution != 640)
        detection_resolution = 320;

    capture_fps = get_long("capture_fps", 60);
    monitor_idx = get_long("monitor_idx", 0);
    circle_mask = get_bool("circle_mask", true);
    capture_borders = get_bool("capture_borders", true);
    capture_cursor = get_bool("capture_cursor", true);
    virtual_camera_name = get_string("virtual_camera_name", "None");
    virtual_camera_width = get_long("virtual_camera_width", 1920);
    virtual_camera_heigth = get_long("virtual_camera_heigth", 1080);

    // Target
    disable_headshot = get_bool("disable_headshot", false);
    body_y_offset = (float)get_double("body_y_offset", 0.15);
    head_y_offset = (float)get_double("head_y_offset", 0.05);
    ignore_third_person = get_bool("ignore_third_person", false);
    shooting_range_targets = get_bool("shooting_range_targets", false);
    focusTarget = get_bool("focusTarget", false);
    auto_aim = get_bool("auto_aim", false);
    target_lock_enabled = get_bool("target_lock_enabled", false);
    target_lock_distance = static_cast<float>(get_double("target_lock_distance", 100.0));
    target_lock_reacquire_time = static_cast<float>(get_double("target_lock_reacquire_time", 0.30));
    smart_target_lock = get_bool("smart_target_lock", true);
    target_reference_class = get_long("target_reference_class", 0);
    target_lock_fallback_class = get_long("target_lock_fallback_class", -1);
    target_switch_delay = get_long("target_switch_delay", 0);
    aim_bot_scope = static_cast<float>(get_double("aim_bot_scope", 160.0));
    if (aim_bot_scope < 0.0f)
        aim_bot_scope = 0.0f;
    aim_bot_position = static_cast<float>(get_double("aim_bot_position", 0.5));
    aim_bot_position2 = static_cast<float>(get_double("aim_bot_position2", 0.5));
    allowed_classes = get_string("allowed_classes", "");
    class_priority_order = get_string("class_priority_order", "");
    distance_scoring_weight = static_cast<float>(get_double("distance_scoring_weight", 1.0));
    center_scoring_weight = static_cast<float>(get_double("center_scoring_weight", 1.0));
    size_scoring_weight = static_cast<float>(get_double("size_scoring_weight", 1.0));
    aim_weight_tiebreak_ratio = static_cast<float>(get_double("aim_weight_tiebreak_ratio", 0.1));
    small_target_enhancement_enabled = get_bool("small_target_enhancement_enabled", true);
    small_target_boost_factor = static_cast<float>(get_double("small_target_boost_factor", 0.1));
    small_target_threshold = static_cast<float>(get_double("small_target_threshold", 0.02));
    small_target_medium_threshold = static_cast<float>(get_double("small_target_medium_threshold", 0.05));
    small_target_medium_boost = static_cast<float>(get_double("small_target_medium_boost", 1.5));
    small_target_smooth_enabled = get_bool("small_target_smooth_enabled", true);
    small_target_smooth_frames = get_long("small_target_smooth_frames", 2);
    if (small_target_smooth_frames < 1)
        small_target_smooth_frames = 1;

    class_aim_positions.clear();
    CSimpleIniA::TNamesDepend classAimKeys;
    ini.GetAllKeys("ClassAim", classAimKeys);
    for (const auto& k : classAimKeys)
    {
        std::string key = k.pItem;
        if (key.empty() || !std::all_of(key.begin(), key.end(),
            [](unsigned char c) { return std::isdigit(c) != 0; }))
            continue;
        std::string val = ini.GetValue("ClassAim", key.c_str(), "");
        auto parts = splitString(val, ',');
        if (parts.size() < 2)
            continue;
        try
        {
            int class_id = std::stoi(key);
            float pos1 = std::stof(parts[0]);
            float pos2 = std::stof(parts[1]);
            class_aim_positions[class_id] = { pos1, pos2 };
        }
        catch (...)
        {
            std::cerr << "[Config] Invalid ClassAim entry: " << key << " = " << val << std::endl;
        }
    }

    custom_class_names.clear();
    CSimpleIniA::TNamesDepend classNameKeys;
    ini.GetAllKeys("ClassNames", classNameKeys);
    for (const auto& k : classNameKeys)
    {
        std::string key = k.pItem;
        if (key.empty() || !std::all_of(key.begin(), key.end(),
            [](unsigned char c) { return std::isdigit(c) != 0; }))
            continue;
        std::string val = ini.GetValue("ClassNames", key.c_str(), "");
        try
        {
            int class_id = std::stoi(key);
            if (!val.empty())
                custom_class_names[class_id] = val;
        }
        catch (...) {}
    }

    // Mouse
    fovX = get_long("fovX", 106);
    fovY = get_long("fovY", 74);
    minSpeedMultiplier = (float)get_double("minSpeedMultiplier", 0.1);
    maxSpeedMultiplier = (float)get_double("maxSpeedMultiplier", 0.1);

    smoothness = get_long("smoothness", 100);
    use_smoothing = get_bool("use_smoothing", true);
    tracking_smoothing = get_bool("tracking_smoothing", false);

    use_kalman = get_bool("use_kalman", false);
    kalman_process_noise = (float)get_double("kalman_process_noise", 0.01);
    kalman_measurement_noise = (float)get_double("kalman_measurement_noise", 0.10);
    kalman_speed_multiplier_x = (float)get_double("kalman_speed_multiplier_x", 1.0);
    kalman_speed_multiplier_y = (float)get_double("kalman_speed_multiplier_y", 1.0);
    resetThreshold = (float)get_double("resetThreshold", 5);

    predictionInterval = (float)get_double("predictionInterval", 0.01);
    prediction_mode = get_long("prediction_mode", 0);
    if (prediction_mode < 0) prediction_mode = 0;
    if (prediction_mode > 2) prediction_mode = 2;
    prediction_kalman_lead_ms = (float)get_double("prediction_kalman_lead_ms", 0.0);
    prediction_kalman_max_lead_ms = (float)get_double("prediction_kalman_max_lead_ms", 0.0);
    prediction_velocity_smoothing = (float)get_double("prediction_velocity_smoothing", 0.4);
    prediction_velocity_scale = (float)get_double("prediction_velocity_scale", 1.0);
    prediction_kalman_process_noise = (float)get_double("prediction_kalman_process_noise", 0.01);
    prediction_kalman_measurement_noise = (float)get_double("prediction_kalman_measurement_noise", 0.10);
    prediction_use_future_for_aim = get_bool("prediction_use_future_for_aim", false);
    prediction_futurePositions = get_long("prediction_futurePositions", 20);
    draw_futurePositions = get_bool("draw_futurePositions", true);

    camera_compensation_enabled = get_bool("camera_compensation_enabled", false);
    camera_compensation_max_shift = (float)get_double("camera_compensation_max_shift", 50.0);
    camera_compensation_strength = (float)get_double("camera_compensation_strength", 1.0);
    
    snapRadius = (float)get_double("snapRadius", 1.5);
    nearRadius = (float)get_double("nearRadius", 25.0);
    speedCurveExponent = (float)get_double("speedCurveExponent", 3.0);
    snapBoostFactor = (float)get_double("snapBoostFactor", 1.15);

    // Easynorecoil
    easynorecoil = get_bool("easynorecoil", false);
    easynorecoilstrength = (float)get_double("easynorecoilstrength", 0.0);
    input_method = get_string("input_method", "WIN32");

    // Wind mouse
    wind_mouse_enabled = get_bool("wind_mouse_enabled", false);
    wind_G = (float)get_double("wind_G", 18.0f);
    wind_W = (float)get_double("wind_W", 15.0f);
    wind_M = (float)get_double("wind_M", 10.0f);
    wind_D = (float)get_double("wind_D", 8.0f);
    // Makcu
    makcu_baudrate = get_long("makcu_baudrate", 4000000);
    makcu_port = get_string("makcu_port", "COM1");
    if (makcu_port.empty() || makcu_port == "COM0")
        makcu_port = "COM1";

    // kmbox_B
    kmbox_b_baudrate = get_long("kmbox_baudrate", 115200);
    kmbox_b_port = get_string("kmbox_port", "COM0");

    // Mouse shooting
    auto_shoot = get_bool("auto_shoot", false);
    triggerbot = get_bool("triggerbot", false);
    long reaction_ms_raw = get_long("triggerbot_reaction_ms", -1);
    if (reaction_ms_raw >= 0)
    {
        triggerbot_reaction_ms = static_cast<int>(reaction_ms_raw);
    }
    else
    {
        double legacy_interval_s = get_double("triggerbot_interval", 0.0);
        triggerbot_reaction_ms = static_cast<int>(legacy_interval_s * 1000.0 + 0.5);
    }
    if (triggerbot_reaction_ms < 0)
        triggerbot_reaction_ms = 0;
    bScope_multiplier = (float)get_double("bScope_multiplier", 1.2);
    triggerbot_bScope_multiplier = (float)get_double("triggerbot_bScope_multiplier", 1.2);

    // Color detection
    color_erode_iter = get_long("color_erode_iter", 1);
    color_dilate_iter = get_long("color_dilate_iter", 2);
    color_min_area = get_long("color_min_area", 50);
    color_target = get_string("color_target", "yellow");
    tinyArea = get_long("tinyArea", 2);
    isOnlyTop = get_bool("isOnlyTop", true);
    scanError = static_cast<float>(get_double("scanError", 0.1));

    // HSV ranges
    color_ranges.clear();
    CSimpleIniA::TNamesDepend colorKeys;
    ini.GetAllKeys("Colors", colorKeys);

    for (const auto& k : colorKeys) {
        std::string key = k.pItem; // ???????? "Yellow"
        std::string val = ini.GetValue("Colors", key.c_str(), "");
        auto parts = splitString(val, ',');
        if (parts.size() == 6) {
            try {
                ColorRange cr;
                cr.name = key;
                cr.h_low = std::stoi(parts[0]);
                cr.s_low = std::stoi(parts[1]);
                cr.v_low = std::stoi(parts[2]);
                cr.h_high = std::stoi(parts[3]);
                cr.s_high = std::stoi(parts[4]);
                cr.v_high = std::stoi(parts[5]);
                color_ranges.push_back(cr);
            }
            catch (...) {
                std::cerr << "[Config] Invalid HSV values for color: " << key << std::endl;
            }
        }
    }

    // AI
    backend = get_string("backend",
#ifdef USE_CUDA
        "TRT"
#else
        "DML"
#endif
    );

    // ???????? ?????????? ???????? (TRT / DML / COLOR)
    if (backend != "TRT" && backend != "DML" && backend != "COLOR") {
#ifdef USE_CUDA
        backend = "TRT";
#else
        backend = "DML";
#endif
    }

    dml_device_id = get_long("dml_device_id", 0);

#ifdef USE_CUDA
    ai_model = get_string("ai_model", "sunxds_0.5.6.engine");
#else
    ai_model = get_string("ai_model", "sunxds_0.5.6.onnx");
#endif
    confidence_threshold = (float)get_double("confidence_threshold", 0.15);
    nms_threshold = (float)get_double("nms_threshold", 0.50);
    adaptive_nms = get_bool("adaptive_nms", true);
    max_detections = get_long("max_detections", 20);

    postprocess = get_string("postprocess", "yolo10");

    batch_size = get_long("batch_size", 1);
    if (batch_size < 1) batch_size = 1;
    if (batch_size > 8) batch_size = 8;

#ifdef USE_CUDA
    export_enable_fp8 = get_bool("export_enable_fp8", true);
    export_enable_fp16 = get_bool("export_enable_fp16", true);
#endif
    fixed_input_size = get_bool("fixed_input_size", false);

    // CUDA
#ifdef USE_CUDA
    use_cuda_graph = get_bool("use_cuda_graph", false);
    use_pinned_memory = get_bool("use_pinned_memory", true);
    capture_use_cuda = get_bool("capture_use_cuda", true);
#endif

    // Buttons
    button_targeting = splitString(get_string("button_targeting", "RightMouseButton"));
    button_shoot = splitString(get_string("button_shoot", "LeftMouseButton"));
    button_triggerbot = splitString(get_string("button_triggerbot", "X2MouseButton"));
    button_disable_headshot = splitString(get_string("button_disable_headshot", "M"));
    button_exit = splitString(get_string("button_exit", "F2"));
    button_pause = splitString(get_string("button_pause", "F3"));
    button_reload_config = splitString(get_string("button_reload_config", "F4"));
    button_open_overlay = splitString(get_string("button_open_overlay", "Home"));
    enable_arrows_settings = get_bool("enable_arrows_settings", false);

    // Overlay
    overlay_opacity = get_long("overlay_opacity", 225);
    overlay_snow_theme = get_bool("overlay_snow_theme", true);
    overlay_ui_scale = (float)get_double("overlay_ui_scale", 1.0);

    // OBS
    is_obs = get_bool("is_obs", false);
    obs_ip = get_string("obs_ip", "0.0.0.0");
    obs_port = get_long("obs_port", 4455);
    obs_fps = get_long("obs_fps", 240);

    // Custom Classes
    class_player = get_long("class_player", 0);
    class_bot = get_long("class_bot", 1);
    class_weapon = get_long("class_weapon", 2);
    class_outline = get_long("class_outline", 3);
    class_dead_body = get_long("class_dead_body", 4);
    class_hideout_target_human = get_long("class_hideout_target_human", 5);
    class_hideout_target_balls = get_long("class_hideout_target_balls", 6);
    class_head = get_long("class_head", 7);
    class_smoke = get_long("class_smoke", 8);
    class_fire = get_long("class_fire", 9);
    class_third_person = get_long("class_third_person", 10);

    // Debug window
    show_window = get_bool("show_window", true);
    screenshot_button = splitString(get_string("screenshot_button", "None"));
    screenshot_delay = get_long("screenshot_delay", 500);
    verbose = get_bool("verbose", false);

    return true;
}

bool Config::saveConfig(const std::string& filename)
{
    std::ofstream file(filename);
    if (!file.is_open())
    {
        std::cerr << "Error opening config for writing: " << filename << std::endl;
        return false;
    }

    file << "# An explanation of the options can be found at:\n";
    file << "# https://github.com/RN-AI/RN_AI_cpp\n\n";

    // Capture
    file << "# Capture\n"
        << "capture_method = " << capture_method << "\n"
        << "detection_resolution = " << detection_resolution << "\n"
        << "capture_fps = " << capture_fps << "\n"
        << "monitor_idx = " << monitor_idx << "\n"
        << "circle_mask = " << (circle_mask ? "true" : "false") << "\n"
        << "capture_borders = " << (capture_borders ? "true" : "false") << "\n"
        << "capture_cursor = " << (capture_cursor ? "true" : "false") << "\n"
        << "virtual_camera_name = " << virtual_camera_name << "\n"
        << "virtual_camera_width = " << virtual_camera_width << "\n"
        << "virtual_camera_heigth = " << virtual_camera_heigth << "\n\n";

    // Target
    file << "# Target\n"
        << "disable_headshot = " << (disable_headshot ? "true" : "false") << "\n"
        << std::fixed << std::setprecision(2)
        << "body_y_offset = " << body_y_offset << "\n"
        << "head_y_offset = " << head_y_offset << "\n"
        << "ignore_third_person = " << (ignore_third_person ? "true" : "false") << "\n"
        << "shooting_range_targets = " << (shooting_range_targets ? "true" : "false") << "\n"
        << "focusTarget = " << (focusTarget ? "true" : "false") << "\n"
        << "auto_aim = " << (auto_aim ? "true" : "false") << "\n"
        << "target_lock_enabled = " << (target_lock_enabled ? "true" : "false") << "\n"
        << std::fixed << std::setprecision(1)
        << "target_lock_distance = " << target_lock_distance << "\n"
        << std::fixed << std::setprecision(2)
        << "target_lock_reacquire_time = " << target_lock_reacquire_time << "\n"
        << "smart_target_lock = " << (smart_target_lock ? "true" : "false") << "\n"
        << "target_reference_class = " << target_reference_class << "\n"
        << "target_lock_fallback_class = " << target_lock_fallback_class << "\n"
        << "target_switch_delay = " << target_switch_delay << "\n"
        << std::fixed << std::setprecision(1)
        << "aim_bot_scope = " << aim_bot_scope << "\n"
        << std::fixed << std::setprecision(2)
        << "aim_bot_position = " << aim_bot_position << "\n"
        << "aim_bot_position2 = " << aim_bot_position2 << "\n"
        << "allowed_classes = " << allowed_classes << "\n"
        << "class_priority_order = " << class_priority_order << "\n"
        << "distance_scoring_weight = " << distance_scoring_weight << "\n"
        << "center_scoring_weight = " << center_scoring_weight << "\n"
        << "size_scoring_weight = " << size_scoring_weight << "\n"
        << "aim_weight_tiebreak_ratio = " << aim_weight_tiebreak_ratio << "\n"
        << "small_target_enhancement_enabled = " << (small_target_enhancement_enabled ? "true" : "false") << "\n"
        << "small_target_boost_factor = " << small_target_boost_factor << "\n"
        << "small_target_threshold = " << small_target_threshold << "\n"
        << "small_target_medium_threshold = " << small_target_medium_threshold << "\n"
        << "small_target_medium_boost = " << small_target_medium_boost << "\n"
        << "small_target_smooth_enabled = " << (small_target_smooth_enabled ? "true" : "false") << "\n"
        << "small_target_smooth_frames = " << small_target_smooth_frames << "\n\n";

    // Mouse
    file << "# Mouse move\n"
        << "fovX = " << fovX << "\n"
        << "fovY = " << fovY << "\n"
        << "minSpeedMultiplier = " << minSpeedMultiplier << "\n"
        << "maxSpeedMultiplier = " << maxSpeedMultiplier << "\n"
        << "smoothness = " << smoothness << "\n"
        << "use_smoothing = " << (use_smoothing ? "true" : "false") << "\n"
        << "tracking_smoothing = " << (tracking_smoothing ? "true" : "false") << "\n"
        << "use_kalman = " << (use_kalman ? "true" : "false") << "\n\n"
        << "kalman_process_noise = " << kalman_process_noise << "\n"
        << "kalman_measurement_noise = " << kalman_measurement_noise << "\n"
        << "kalman_speed_multiplier_x = " << kalman_speed_multiplier_x << "\n"
        << "kalman_speed_multiplier_y = " << kalman_speed_multiplier_y << "\n"
        << "resetThreshold = " << resetThreshold << "\n\n"

        << std::fixed << std::setprecision(2)
        << "predictionInterval = " << predictionInterval << "\n"
        << "prediction_mode = " << prediction_mode << "\n"
        << "prediction_kalman_lead_ms = " << prediction_kalman_lead_ms << "\n"
        << "prediction_kalman_max_lead_ms = " << prediction_kalman_max_lead_ms << "\n"
        << "prediction_velocity_smoothing = " << prediction_velocity_smoothing << "\n"
        << "prediction_velocity_scale = " << prediction_velocity_scale << "\n"
        << "prediction_kalman_process_noise = " << prediction_kalman_process_noise << "\n"
        << "prediction_kalman_measurement_noise = " << prediction_kalman_measurement_noise << "\n"
        << "prediction_use_future_for_aim = " << (prediction_use_future_for_aim ? "true" : "false") << "\n"
        << "prediction_futurePositions = " << prediction_futurePositions << "\n"
        << "draw_futurePositions = " << (draw_futurePositions ? "true" : "false") << "\n"

        << "camera_compensation_enabled = " << (camera_compensation_enabled ? "true" : "false") << "\n"
        << "camera_compensation_max_shift = " << camera_compensation_max_shift << "\n"
        << "camera_compensation_strength = " << camera_compensation_strength << "\n"

        << "snapRadius = " << snapRadius << "\n"
        << "nearRadius = " << nearRadius << "\n"
        << "speedCurveExponent = " << speedCurveExponent << "\n"
        << std::fixed << std::setprecision(2)
        << "snapBoostFactor = " << snapBoostFactor << "\n"

        << "easynorecoil = " << (easynorecoil ? "true" : "false") << "\n"
        << std::fixed << std::setprecision(1)
        << "easynorecoilstrength = " << easynorecoilstrength << "\n"

        << "# WIN32, ARDUINO, MAKCU, KMBOX_B, KMBOX_NET\n"
        << "input_method = " << input_method << "\n\n";

    // Wind mouse
    file << "# Wind mouse\n"
        << "wind_mouse_enabled = " << (wind_mouse_enabled ? "true" : "false") << "\n"
        << "wind_G = " << wind_G << "\n"
        << "wind_W = " << wind_W << "\n"
        << "wind_M = " << wind_M << "\n"
        << "wind_D = " << wind_D << "\n\n";
    // Makcu
    file << "# Makcu\n"
        << "makcu_baudrate = " << makcu_baudrate << "\n"
        << "makcu_port = " << makcu_port << "\n\n";

    // kmbox_B
    file << "# Kmbox_B\n"
        << "kmbox_baudrate = " << kmbox_b_baudrate << "\n"
        << "kmbox_port = " << kmbox_b_port << "\n\n";

    // Mouse shooting
    file << "# Mouse shooting\n"
        << "auto_shoot = " << (auto_shoot ? "true" : "false") << "\n"
        << "triggerbot = " << (triggerbot ? "true" : "false") << "\n"
        << "triggerbot_reaction_ms = " << triggerbot_reaction_ms << "\n"
        << std::fixed << std::setprecision(2)
        << "triggerbot_interval = " << (static_cast<double>(triggerbot_reaction_ms) / 1000.0) << "\n"
        << std::fixed << std::setprecision(1)
        << "bScope_multiplier = " << bScope_multiplier << "\n"
        << "triggerbot_bScope_multiplier = " << triggerbot_bScope_multiplier << "\n\n";

    // AI
    file << "# AI\n"
        << "backend = " << backend << "\n"
        << "dml_device_id = " << dml_device_id << "\n"
        << "ai_model = " << ai_model << "\n"
        << std::fixed << std::setprecision(2)
        << "confidence_threshold = " << confidence_threshold << "\n"
        << "nms_threshold = " << nms_threshold << "\n"
        << "adaptive_nms = " << (adaptive_nms ? "true" : "false") << "\n"
        << std::setprecision(0)
        << "max_detections = " << max_detections << "\n"
        << "postprocess = " << postprocess << "\n"
        << "batch_size = " << batch_size << "\n"
#ifdef USE_CUDA
        << "export_enable_fp8 = " << (export_enable_fp8 ? "true" : "false") << "\n"
        << "export_enable_fp16 = " << (export_enable_fp16 ? "true" : "false") << "\n"
#endif
        << "fixed_input_size = " << (fixed_input_size ? "true" : "false") << "\n";
    
    // CUDA
#ifdef USE_CUDA
    file << "\n# CUDA\n"
        << "use_cuda_graph = " << (use_cuda_graph ? "true" : "false") << "\n"
        << "use_pinned_memory = " << (use_pinned_memory ? "true" : "false") << "\n"
        << "capture_use_cuda = " << (capture_use_cuda ? "true" : "false") << "\n\n";
#endif

    // Buttons
    file << "# Buttons\n"
        << "button_targeting = " << joinStrings(button_targeting) << "\n"
        << "button_shoot = " << joinStrings(button_shoot) << "\n"
        << "button_triggerbot = " << joinStrings(button_triggerbot) << "\n"
        << "button_disable_headshot = " << joinStrings(button_disable_headshot) << "\n"
        << "button_exit = " << joinStrings(button_exit) << "\n"
        << "button_pause = " << joinStrings(button_pause) << "\n"
        << "button_reload_config = " << joinStrings(button_reload_config) << "\n"
        << "button_open_overlay = " << joinStrings(button_open_overlay) << "\n"
        << "enable_arrows_settings = " << (enable_arrows_settings ? "true" : "false") << "\n\n";

    // Overlay
    file << "# Overlay\n"
        << "overlay_opacity = " << overlay_opacity << "\n"
        << "overlay_snow_theme = " << (overlay_snow_theme ? "true" : "false") << "\n"
        << std::fixed << std::setprecision(2)
        << "overlay_ui_scale = " << overlay_ui_scale << "\n\n";

    file << "# OBS\n"
        << "is_obs = " << (is_obs ? "true" : "false") << "\n"
        << "obs_ip = " << obs_ip << "\n"
        << "obs_port = " << obs_port << "\n"
        << "obs_fps = " << obs_fps << "\n\n";

    // Color detection
    file << "# Color detection\n";
    file << "color_erode_iter = " << color_erode_iter << "\n";
    file << "color_dilate_iter = " << color_dilate_iter << "\n";
    file << "color_min_area = " << color_min_area << "\n";
    file << "color_target = " << color_target << "\n";
    file << "tinyArea = " << tinyArea << "\n";
    file << "isOnlyTop = " << isOnlyTop << "\n";
    file << "scanError = " << scanError << "\n\n";

    // Debug
    file << "# Debug\n"
        << "show_window = " << (show_window ? "true" : "false") << "\n"
        << "show_fps = " << (show_fps ? "true" : "false") << "\n"
        << "screenshot_button = " << joinStrings(screenshot_button) << "\n"
        << "screenshot_delay = " << screenshot_delay << "\n"
        << "verbose = " << (verbose ? "true" : "false") << "\n\n";

    // Active game
    file << "# Active game profile\n";
    file << "active_game = " << active_game << "\n\n";

    file << "[Colors]\n";
    for (const auto& cr : color_ranges) {
        file << cr.name << " = "
            << cr.h_low << "," << cr.s_low << "," << cr.v_low << ","
            << cr.h_high << "," << cr.s_high << "," << cr.v_high << "\n";
    }
    file << "\n";

    file << "[Games]\n";
    for (auto& kv : game_profiles)
    {
        auto & gp = kv.second;
        file << gp.name << " = "
             << gp.sens << "," << gp.yaw;
        file << "," << gp.pitch;
        if (gp.fovScaled)
            file << ",true," << gp.baseFOV;
        file << "\n";
    }
    file << "\n";

    if (!class_aim_positions.empty())
    {
        std::vector<int> class_ids;
        class_ids.reserve(class_aim_positions.size());
        for (const auto& kv : class_aim_positions)
            class_ids.push_back(kv.first);
        std::sort(class_ids.begin(), class_ids.end());
        file << "[ClassAim]\n";
        file << std::fixed << std::setprecision(2);
        for (int class_id : class_ids)
        {
            auto it = class_aim_positions.find(class_id);
            if (it == class_aim_positions.end())
                continue;
            file << class_id << " = " << it->second.first << "," << it->second.second << "\n";
        }
        file << "\n";
    }

    if (!custom_class_names.empty())
    {
        std::vector<int> class_ids;
        class_ids.reserve(custom_class_names.size());
        for (const auto& kv : custom_class_names)
            class_ids.push_back(kv.first);
        std::sort(class_ids.begin(), class_ids.end());
        file << "[ClassNames]\n";
        for (int class_id : class_ids)
        {
            auto it = custom_class_names.find(class_id);
            if (it == custom_class_names.end())
                continue;
            file << class_id << " = " << it->second << "\n";
        }
        file << "\n";
    }

    file.close();
    return true;
}

const Config::GameProfile& Config::currentProfile() const
{
    auto it = game_profiles.find(active_game);
    if (it != game_profiles.end()) return it->second;
    throw std::runtime_error("Active game profile not found: " + active_game);
}

std::pair<double, double> Config::degToCounts(double degX, double degY, double fovNow) const
{
    const auto& gp = currentProfile();
    double scale = (gp.fovScaled && gp.baseFOV > 1.0) ? (fovNow / gp.baseFOV) : 1.0;

    if (gp.sens == 0.0 || gp.yaw == 0.0 || gp.pitch == 0.0)
        return { 0.0, 0.0 };

    double cx = degX / (gp.sens * gp.yaw * scale);
    double cy = degY / (gp.sens * gp.pitch * scale);
    return { cx, cy };
}



