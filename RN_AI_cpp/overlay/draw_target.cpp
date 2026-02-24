#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>
#include <cstring>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <sstream>

#include "d3d11.h"
#include "imgui/imgui.h"

#include "overlay.h"
#include "draw_settings.h"
#include "ui_sections.h"
#include "ui_controls.h"
#include "ui_runtime.h"
#include "rn_ai_cpp.h"
#include "other_tools.h"
#include "memory_images.h"

ID3D11ShaderResourceView* bodyTexture = nullptr;
ImVec2 bodyImageSize;
static char class_priority_buf[128] = "";
static bool text_buffers_inited = false;
static const char* kDeletedClassMarker = "__deleted__";

static std::string trim_ascii(const std::string& s)
{
    size_t start = 0;
    while (start < s.size() && (s[start] == ' ' || s[start] == '\t' || s[start] == '\r' || s[start] == '\n'))
        ++start;

    size_t end = s.size();
    while (end > start && (s[end - 1] == ' ' || s[end - 1] == '\t' || s[end - 1] == '\r' || s[end - 1] == '\n'))
        --end;

    return s.substr(start, end - start);
}

static bool load_names_file(const std::string& path, std::vector<std::string>& out)
{
    std::ifstream file(path);
    if (!file.is_open())
        return false;

    out.clear();
    std::string line;
    while (std::getline(file, line))
    {
        std::string trimmed = trim_ascii(line);
        if (trimmed.empty())
            continue;
        if (!trimmed.empty() && trimmed[0] == '#')
            continue;
        out.push_back(trimmed);
    }

    return !out.empty();
}

static bool load_class_names_for_model(
    const std::string& model_name,
    std::vector<std::string>& out_names,
    std::string& out_source)
{
    out_names.clear();
    out_source.clear();

    std::vector<std::filesystem::path> candidates;
    if (!model_name.empty())
    {
        std::filesystem::path model_path = std::filesystem::path("models") / model_name;
        std::string stem = model_path.stem().string();
        candidates.push_back(model_path.parent_path() / (stem + ".names"));
        candidates.push_back(model_path.parent_path() / (stem + ".txt"));
        candidates.push_back(model_path.parent_path() / "classes.txt");
        candidates.push_back(model_path.parent_path() / "labels.txt");
    }

    candidates.push_back(std::filesystem::path("class_names.txt"));
    candidates.push_back(std::filesystem::path("classes.txt"));
    candidates.push_back(std::filesystem::path("config") / "class_names.txt");
    candidates.push_back(std::filesystem::path("config") / "classes.txt");
    candidates.push_back(std::filesystem::path("configs") / "class_names.txt");
    candidates.push_back(std::filesystem::path("configs") / "classes.txt");

    for (const auto& candidate : candidates)
    {
        if (!std::filesystem::exists(candidate))
            continue;

        std::vector<std::string> names;
        if (load_names_file(candidate.string(), names))
        {
            out_names = std::move(names);
            out_source = candidate.string();
            return true;
        }
    }

    return false;
}

static std::vector<int> parse_int_list(const std::string& text)
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
}

static std::string build_int_list(const std::vector<int>& values)
{
    if (values.empty())
        return "";

    std::ostringstream oss;
    for (size_t i = 0; i < values.size(); ++i)
    {
        if (i != 0)
            oss << "-";
        oss << values[i];
    }
    return oss.str();
}

static std::string fallback_legacy_name(int id)
{
    if (id == config.class_player) return "class_player";
    if (id == config.class_bot) return "class_bot";
    if (id == config.class_weapon) return "class_weapon";
    if (id == config.class_outline) return "class_outline";
    if (id == config.class_dead_body) return "class_dead_body";
    if (id == config.class_hideout_target_human) return "class_hideout_target_human";
    if (id == config.class_hideout_target_balls) return "class_hideout_target_balls";
    if (id == config.class_head) return "class_head";
    if (id == config.class_smoke) return "class_smoke";
    if (id == config.class_fire) return "class_fire";
    if (id == config.class_third_person) return "class_third_person";
    return "";
}

static std::string class_label(
    int id,
    const std::unordered_map<int, std::string>& names)
{
    auto it = names.find(id);
    if (it != names.end() && !it->second.empty())
        return std::to_string(id) + ": " + it->second;
    return "Class " + std::to_string(id);
}

static bool is_deleted_class_name(const std::string& value)
{
    return value == kDeletedClassMarker;
}

void draw_target()
{
    bool changed = false;
    if (config.target_lock_enabled != config.smart_target_lock)
    {
        config.target_lock_enabled = config.smart_target_lock;
        changed = true;
    }
    if (config.focusTarget)
    {
        config.focusTarget = false;
        changed = true;
    }

    if (OverlayUI::BeginCard("GENERAL TARGETING", "target_general_card"))
    {
        if (ImGui::Checkbox("Disable Headshot Mode", &config.disable_headshot))
            changed = true;
        if (OverlayUI::g_show_descriptions)
            ImGui::TextDisabled("Aim for body center instead of head");

        if (ImGui::Checkbox("Ignore Third Person", &config.ignore_third_person))
            changed = true;
        if (OverlayUI::g_show_descriptions)
            ImGui::TextDisabled("Don't aim at your own character in 3rd person view");

        if (ImGui::Checkbox("Auto Aim Active", &config.auto_aim))
            changed = true;

        int head_id = config.class_head;
        ImGui::TextUnformatted("Head Class Id");
        ImGui::SetNextItemWidth((std::min)(220.0f, ImGui::GetContentRegionAvail().x));
        if (ImGui::InputInt("##head_class_id", &head_id, 0, 0))
        {
            config.class_head = std::max(0, head_id);
            changed = true;
        }

        float max_scope_px = static_cast<float>(std::hypot(
            static_cast<double>(config.detection_resolution),
            static_cast<double>(config.detection_resolution))) / 2.0f;
        float scope_percent = 0.0f;
        if (config.aim_bot_scope > 0.0f && max_scope_px > 0.0f)
            scope_percent = (config.aim_bot_scope / max_scope_px) * 100.0f;
        scope_percent = std::clamp(scope_percent, 0.0f, 100.0f);
        float scope_percent_edit = scope_percent;
        if (OverlayUI::FloatControlRow(
            "Aim Scope Radius",
            &scope_percent_edit,
            0.0f,
            100.0f,
            1.0f,
            "%.0f",
            "%.1f",
            "%",
            "% of screen radius to search for targets"))
        {
            if (scope_percent_edit <= 0.0f || max_scope_px <= 0.0f)
                config.aim_bot_scope = 0.0f;
            else
                config.aim_bot_scope = (scope_percent_edit / 100.0f) * max_scope_px;
            changed = true;
        }
    }
    OverlayUI::EndCard();

    if (OverlayUI::BeginCard("SMART TARGET LOCK", "target_lock_card"))
    {
        if (ImGui::Checkbox("Enable Smart Target Lock", &config.smart_target_lock))
        {
            config.target_lock_enabled = config.smart_target_lock;
            changed = true;
        }
        if (config.smart_target_lock)
        {
            if (OverlayUI::FloatControlRow(
                "Lock Distance",
                &config.target_lock_distance,
                20.0f,
                400.0f,
                1.0f,
                "%.0f",
                "%.1f",
                "px",
                "Max pixel distance to maintain lock on current target"))
                changed = true;

            float reacquire_ms = config.target_lock_reacquire_time * 1000.0f;
            if (OverlayUI::FloatControlRow(
                "Reacquire Time",
                &reacquire_ms,
                50.0f,
                2000.0f,
                10.0f,
                "%.0f",
                "%.0f",
                "ms",
                "Time before searching for new target after losing current"))
            {
                config.target_lock_reacquire_time = reacquire_ms / 1000.0f;
                changed = true;
            }

            float switch_delay_ms = static_cast<float>(std::max(0, config.target_switch_delay));
            if (OverlayUI::FloatControlRow(
                "Target Switch Delay",
                &switch_delay_ms,
                0.0f,
                2000.0f,
                10.0f,
                "%.0f",
                "%.0f",
                "ms",
                "Debounce time before switching to different target"))
            {
                config.target_switch_delay = static_cast<int>(switch_delay_ms + 0.5f);
                changed = true;
            }
        }
    }
    OverlayUI::EndCard();

    if (ImGui::CollapsingHeader("ADVANCED CLASS CONTROLS"))
    {
        ImGui::SetNextItemWidth((std::min)(120.0f, ImGui::GetContentRegionAvail().x));
        if (ImGui::InputInt("Target Reference Class", &config.target_reference_class, 0, 0))
            changed = true;
        ImGui::SetNextItemWidth((std::min)(120.0f, ImGui::GetContentRegionAvail().x));
        if (ImGui::InputInt("Target Lock Fallback Class (-1 = off)", &config.target_lock_fallback_class, 0, 0))
            changed = true;
    }

    if (ImGui::CollapsingHeader("SMART TARGET WEIGHTS"))
    {
        if (OverlayUI::FloatControlRow("Distance Weight", &config.distance_scoring_weight, 0.0f, 2.0f, 0.01f, "%.2f", "%.3f"))
            changed = true;
        if (OverlayUI::FloatControlRow("Center Weight", &config.center_scoring_weight, 0.0f, 2.0f, 0.01f, "%.2f", "%.3f"))
            changed = true;
        if (OverlayUI::FloatControlRow("Size Weight", &config.size_scoring_weight, 0.0f, 2.0f, 0.01f, "%.2f", "%.3f"))
            changed = true;
        if (OverlayUI::FloatControlRow("Tiebreak Ratio", &config.aim_weight_tiebreak_ratio, 0.0f, 1.0f, 0.01f, "%.2f", "%.3f"))
            changed = true;
    }

    if (changed)
        config.saveConfig();
}

void draw_classes()
{
    bool changed = false;

    static std::string cached_model;
    static std::vector<std::string> cached_model_names;
    static std::string cached_name_source;
    static bool cached_names_loaded = false;

    bool reload_names = ImGui::Button("Reload Class Names");
    if (reload_names || cached_model != config.ai_model)
    {
        cached_model = config.ai_model;
        cached_names_loaded = load_class_names_for_model(
            cached_model,
            cached_model_names,
            cached_name_source);

        if (cached_names_loaded)
        {
            for (int i = 0; i < static_cast<int>(cached_model_names.size()); ++i)
            {
                auto it_existing = config.custom_class_names.find(i);
                if (it_existing != config.custom_class_names.end() &&
                    is_deleted_class_name(it_existing->second))
                    continue;

                if (!config.custom_class_names.count(i))
                {
                    config.custom_class_names[i] = cached_model_names[i];
                    changed = true;
                }
            }
        }
    }

    std::unordered_map<int, std::string> names_by_id;
    for (const auto& kv : config.custom_class_names)
    {
        if (is_deleted_class_name(kv.second))
            continue;
        if (!kv.second.empty())
            names_by_id[kv.first] = kv.second;
    }

    std::vector<int> allowed_list = parse_int_list(config.allowed_classes);
    std::vector<int> priority_list = parse_int_list(config.class_priority_order);
    std::unordered_set<int> allowed_set(allowed_list.begin(), allowed_list.end());
    std::unordered_set<int> id_set;
    std::vector<int> class_ids;
    class_ids.reserve(64);

    auto add_class_id = [&](int id)
        {
            if (id < 0)
                return;
            if (id_set.insert(id).second)
                class_ids.push_back(id);
        };
    auto is_class_deleted = [&](int id) -> bool
        {
            auto it = config.custom_class_names.find(id);
            return it != config.custom_class_names.end() &&
                is_deleted_class_name(it->second);
        };

    for (const auto& kv : config.custom_class_names)
    {
        if (is_deleted_class_name(kv.second))
            continue;
        add_class_id(kv.first);
    }

    for (const auto& kv : config.class_aim_positions)
    {
        if (is_class_deleted(kv.first))
            continue;
        add_class_id(kv.first);
    }

    for (int id : allowed_list)
    {
        if (is_class_deleted(id))
            continue;
        add_class_id(id);
    }

    for (int id : priority_list)
    {
        if (is_class_deleted(id))
            continue;
        add_class_id(id);
    }

    {
        std::lock_guard<std::mutex> lock(detectionBuffer.mutex);
        for (int id : detectionBuffer.classes)
        {
            auto it_existing = config.custom_class_names.find(id);
            if (it_existing != config.custom_class_names.end() &&
                is_deleted_class_name(it_existing->second))
                continue;

            add_class_id(id);
            if (!config.custom_class_names.count(id))
            {
                std::string fallback = fallback_legacy_name(id);
                if (fallback.empty())
                    fallback = "class_" + std::to_string(id);
                config.custom_class_names[id] = fallback;
                names_by_id[id] = fallback;
                changed = true;
            }
        }
    }

    std::sort(class_ids.begin(), class_ids.end());
    for (int id : class_ids)
    {
        if (!names_by_id.count(id) || names_by_id[id].empty())
        {
            std::string fallback = fallback_legacy_name(id);
            if (fallback.empty())
                fallback = "class_" + std::to_string(id);
            names_by_id[id] = fallback;
        }

        auto it_custom = config.custom_class_names.find(id);
        if (it_custom == config.custom_class_names.end())
        {
            config.custom_class_names[id] = names_by_id[id];
            changed = true;
        }
        else if (it_custom->second.empty())
        {
            it_custom->second = names_by_id[id];
            changed = true;
        }
    }

    ImGui::SeparatorText("Class Names");
    if (cached_names_loaded)
    {
        ImGui::Text("Source: %s", cached_name_source.c_str());
        ImGui::Text("Classes detected from file: %d", static_cast<int>(cached_model_names.size()));
    }
    else
    {
        ImGui::TextDisabled("No class names file found. Using config/detection based IDs.");
    }

    ImGui::SeparatorText("Class Priority");
    if (!text_buffers_inited)
    {
        strncpy_s(class_priority_buf, sizeof(class_priority_buf), config.class_priority_order.c_str(), _TRUNCATE);
        text_buffers_inited = true;
    }
    if (ImGui::InputText("Class Priority Order", class_priority_buf, IM_ARRAYSIZE(class_priority_buf)))
    {
        config.class_priority_order = class_priority_buf;
        changed = true;
    }
    ImGui::TextDisabled("Format: 7-0-4");

    ImGui::SeparatorText("Inference Classes");
    ImGui::Text("Enabled classes: %d", static_cast<int>(allowed_set.size()));
    if (allowed_set.empty())
        ImGui::TextColored(ImVec4(1.0f, 0.6f, 0.2f, 1.0f), "No classes enabled.");

    if (ImGui::Button("Select All"))
    {
        std::unordered_set<int> working(class_ids.begin(), class_ids.end());
        std::vector<int> new_list(working.begin(), working.end());
        std::sort(new_list.begin(), new_list.end());
        config.allowed_classes = build_int_list(new_list);
        allowed_set = std::move(working);
        changed = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("Clear All"))
    {
        allowed_set.clear();
        config.allowed_classes.clear();
        changed = true;
    }

    static int add_class_input_id = 0;
    static char add_class_name[64] = "";
    ImGui::PushItemWidth(120.0f);
    ImGui::InputInt("Class ID##add_class", &add_class_input_id);
    ImGui::PopItemWidth();
    ImGui::SameLine();
    ImGui::PushItemWidth(180.0f);
    ImGui::InputText("Class Name##add_class", add_class_name, IM_ARRAYSIZE(add_class_name));
    ImGui::PopItemWidth();
    ImGui::SameLine();
    if (ImGui::Button("Add Class"))
    {
        if (add_class_input_id >= 0)
        {
            std::string new_name = trim_ascii(add_class_name);
            if (new_name.empty())
                new_name = "class_" + std::to_string(add_class_input_id);

            config.custom_class_names[add_class_input_id] = new_name;
            names_by_id[add_class_input_id] = new_name;
            add_class_id(add_class_input_id);
            std::sort(class_ids.begin(), class_ids.end());
            allowed_set.insert(add_class_input_id);

            std::vector<int> new_allowed(allowed_set.begin(), allowed_set.end());
            std::sort(new_allowed.begin(), new_allowed.end());
            config.allowed_classes = build_int_list(new_allowed);

            add_class_name[0] = '\0';
            changed = true;
        }
    }

    if (ImGui::BeginTable(
        "class_filter_table",
        4,
        ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg | ImGuiTableFlags_Resizable))
    {
        ImGui::TableSetupColumn("Enabled", ImGuiTableColumnFlags_WidthFixed, 90.0f);
        ImGui::TableSetupColumn("Class");
        ImGui::TableSetupColumn("Class ID", ImGuiTableColumnFlags_WidthFixed, 90.0f);
        ImGui::TableSetupColumn("Actions", ImGuiTableColumnFlags_WidthFixed, 90.0f);
        ImGui::TableHeadersRow();

        auto apply_toggle = [&](int class_id, bool enabled)
            {
                std::unordered_set<int> working = allowed_set;
                if (enabled)
                    working.insert(class_id);
                else
                    working.erase(class_id);

                std::vector<int> new_list(working.begin(), working.end());
                std::sort(new_list.begin(), new_list.end());
                config.allowed_classes = build_int_list(new_list);
                allowed_set = std::move(working);
                changed = true;
            };

        for (int id : class_ids)
        {
            ImGui::TableNextRow();

            ImGui::TableSetColumnIndex(0);
            bool enabled = (allowed_set.count(id) > 0);
            ImGui::PushID(id);
            if (ImGui::Checkbox("##class_enabled", &enabled))
                apply_toggle(id, enabled);
            ImGui::PopID();

            ImGui::TableSetColumnIndex(1);
            std::string label = class_label(id, names_by_id);
            ImGui::TextUnformatted(label.c_str());

            ImGui::TableSetColumnIndex(2);
            ImGui::Text("%d", id);

            ImGui::TableSetColumnIndex(3);
            ImGui::PushID(id + 100000);
            if (ImGui::SmallButton("Delete"))
            {
                config.custom_class_names[id] = kDeletedClassMarker;
                config.class_aim_positions.erase(id);
                allowed_set.erase(id);
                priority_list.erase(
                    std::remove(priority_list.begin(), priority_list.end(), id),
                    priority_list.end());
                std::vector<int> new_allowed(allowed_set.begin(), allowed_set.end());
                std::sort(new_allowed.begin(), new_allowed.end());
                config.allowed_classes = build_int_list(new_allowed);
                config.class_priority_order = build_int_list(priority_list);
                strncpy_s(class_priority_buf, sizeof(class_priority_buf), config.class_priority_order.c_str(), _TRUNCATE);
                changed = true;
            }
            ImGui::PopID();
        }

        ImGui::EndTable();
    }

    ImGui::SeparatorText("Class Aim Positions");
    static int selected_class_id = -1;
    if (!class_ids.empty())
    {
        if (!id_set.count(selected_class_id))
            selected_class_id = class_ids.front();

        std::string preview = class_label(selected_class_id, names_by_id);
        if (ImGui::BeginCombo("Select Class", preview.c_str()))
        {
            for (int id : class_ids)
            {
                std::string label = class_label(id, names_by_id);
                bool is_selected = (id == selected_class_id);
                if (ImGui::Selectable(label.c_str(), is_selected))
                    selected_class_id = id;
                if (is_selected)
                    ImGui::SetItemDefaultFocus();
            }
            ImGui::EndCombo();
        }

        float pos1 = config.aim_bot_position;
        float pos2 = config.aim_bot_position2;
        auto it = config.class_aim_positions.find(selected_class_id);
        if (it != config.class_aim_positions.end())
        {
            pos1 = it->second.first;
            pos2 = it->second.second;
        }

        bool aim_changed = false;
        if (ImGui::InputFloat("Aim Position", &pos1, 0.01f, 0.05f, "%.3f"))
        {
            pos1 = std::clamp(pos1, 0.0f, 1.0f);
            aim_changed = true;
        }
        if (ImGui::InputFloat("Aim Position2", &pos2, 0.01f, 0.05f, "%.3f"))
        {
            pos2 = std::clamp(pos2, 0.0f, 1.0f);
            aim_changed = true;
        }
        if (aim_changed)
        {
            config.class_aim_positions[selected_class_id] = { pos1, pos2 };
            changed = true;
        }

        if (ImGui::Button("Reset Current Class Aim"))
        {
            config.class_aim_positions.erase(selected_class_id);
            changed = true;
        }
        ImGui::TextDisabled("If class has no override, global Aim Position values are used.");

        if (bodyTexture)
        {
            ImGui::Image((void*)bodyTexture, bodyImageSize);
            ImVec2 image_pos = ImGui::GetItemRectMin();
            ImVec2 image_size = ImGui::GetItemRectSize();
            ImDrawList* draw_list = ImGui::GetWindowDrawList();
            float line1_y = image_pos.y + pos1 * image_size.y;
            float line2_y = image_pos.y + pos2 * image_size.y;
            ImVec2 line1_start = ImVec2(image_pos.x, line1_y);
            ImVec2 line1_end = ImVec2(image_pos.x + image_size.x, line1_y);
            ImVec2 line2_start = ImVec2(image_pos.x, line2_y);
            ImVec2 line2_end = ImVec2(image_pos.x + image_size.x, line2_y);
            draw_list->AddLine(line1_start, line1_end, IM_COL32(255, 0, 0, 255), 2.0f);
            draw_list->AddLine(line2_start, line2_end, IM_COL32(0, 255, 0, 255), 2.0f);
            draw_list->AddText(ImVec2(line1_end.x + 5, line1_y - 7), IM_COL32(255, 0, 0, 255), "Aim1");
            draw_list->AddText(ImVec2(line2_end.x + 5, line2_y - 7), IM_COL32(0, 255, 0, 255), "Aim2");
        }
        else
        {
            ImGui::TextDisabled("Image not found.");
        }
    }
    else
    {
        ImGui::TextDisabled("No class ids available.");
    }

    if (changed)
        config.saveConfig();
}

void load_body_texture()
{
    int image_width = 0;
    int image_height = 0;

    std::string body_image = std::string(bodyImageBase64_1) + std::string(bodyImageBase64_2) + std::string(bodyImageBase64_3);

    bool ret = LoadTextureFromMemory(body_image, g_pd3dDevice, &bodyTexture, &image_width, &image_height);
    if (!ret)
    {
        std::cerr << "[Overlay] Can't load image!" << std::endl;
    }
    else
    {
        bodyImageSize = ImVec2((float)image_width, (float)image_height);
    }
}

void release_body_texture()
{
    if (bodyTexture)
    {
        bodyTexture->Release();
        bodyTexture = nullptr;
    }
}
