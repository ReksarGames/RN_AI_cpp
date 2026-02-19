#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <string>
#include <vector>

#include "imgui/imgui.h"

#include "sunone_aimbot_cpp.h"

static const char* get_class_name(int cls)
{
    if (cls == config.class_player) return "Player";
    if (cls == config.class_bot) return "Bot";
    if (cls == config.class_weapon) return "Weapon";
    if (cls == config.class_outline) return "Outline";
    if (cls == config.class_dead_body) return "Dead Body";
    if (cls == config.class_hideout_target_human) return "Hideout Human";
    if (cls == config.class_hideout_target_balls) return "Hideout Balls";
    if (cls == config.class_head) return "Head";
    if (cls == config.class_smoke) return "Smoke";
    if (cls == config.class_fire) return "Fire";
    if (cls == config.class_third_person) return "Third Person";
    return nullptr;
}

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

static bool load_model_class_names(
    const std::string& model_name,
    std::vector<std::string>& out,
    std::string& source_path)
{
    out.clear();
    source_path.clear();
    if (model_name.empty())
        return false;

    std::filesystem::path model_path = std::filesystem::path("models") / model_name;
    std::string stem = model_path.stem().string();

    const std::vector<std::filesystem::path> candidates = {
        model_path.parent_path() / (stem + ".names"),
        model_path.parent_path() / (stem + ".txt"),
        model_path.parent_path() / "classes.txt",
        model_path.parent_path() / "labels.txt"
    };

    for (const auto& candidate : candidates)
    {
        if (!std::filesystem::exists(candidate))
            continue;
        std::vector<std::string> names;
        if (load_names_file(candidate.string(), names))
        {
            out = std::move(names);
            source_path = candidate.string();
            return true;
        }
    }

    return false;
}

static void draw_detected_classes()
{
    static std::map<int, int> seen_classes;
    std::map<int, int> current_counts;

    {
        std::lock_guard<std::mutex> lock(detectionBuffer.mutex);
        for (int cls : detectionBuffer.classes)
        {
            current_counts[cls] += 1;
            seen_classes[cls] = 1;
        }
    }

    ImGui::SeparatorText("Detected Classes");
    if (ImGui::Button("Clear Seen Classes"))
    {
        seen_classes.clear();
    }

    if (current_counts.empty())
    {
        ImGui::TextDisabled("Current frame: no detections");
    }
    else
    {
        ImGui::Text("Current frame:");
        for (const auto& kv : current_counts)
        {
            int cls = kv.first;
            int count = kv.second;
            const char* name = get_class_name(cls);
            if (name)
                ImGui::Text(" - %s [%d] x%d", name, cls, count);
            else
                ImGui::Text(" - Class %d x%d", cls, count);
        }
    }

    if (seen_classes.empty())
    {
        ImGui::TextDisabled("Seen this session: none");
    }
    else
    {
        ImGui::Text("Seen this session:");
        for (const auto& kv : seen_classes)
        {
            int cls = kv.first;
            const char* name = get_class_name(cls);
            if (name)
                ImGui::Text(" - %s [%d]", name, cls);
            else
                ImGui::Text(" - Class %d", cls);
        }
    }
}

static void draw_class_mapping()
{
    ImGui::SeparatorText("Class Mapping");

    auto edit_class = [](const char* label, int& value) -> bool {
        int prev = value;
        if (ImGui::InputInt(label, &value))
        {
            if (value < 0) value = 0;
            return value != prev;
        }
        return false;
    };

    bool class_changed = false;
    class_changed |= edit_class("Player Class Id", config.class_player);
    class_changed |= edit_class("Bot Class Id", config.class_bot);
    class_changed |= edit_class("Head Class Id", config.class_head);
    class_changed |= edit_class("Third Person Class Id", config.class_third_person);
    class_changed |= edit_class("Hideout Human Class Id", config.class_hideout_target_human);
    class_changed |= edit_class("Hideout Balls Class Id", config.class_hideout_target_balls);
    class_changed |= edit_class("Weapon Class Id", config.class_weapon);
    class_changed |= edit_class("Outline Class Id", config.class_outline);
    class_changed |= edit_class("Dead Body Class Id", config.class_dead_body);
    class_changed |= edit_class("Smoke Class Id", config.class_smoke);
    class_changed |= edit_class("Fire Class Id", config.class_fire);

    if (class_changed)
    {
        config.saveConfig();
    }
}

static void draw_model_classes()
{
    static std::string cached_model;
    static std::vector<std::string> cached_names;
    static std::string cached_source;
    static bool cached_loaded = false;

    bool reload = false;
    if (ImGui::Button("Reload Class Names"))
        reload = true;

    if (cached_model != config.ai_model || reload)
    {
        cached_model = config.ai_model;
        cached_loaded = load_model_class_names(cached_model, cached_names, cached_source);
    }

    ImGui::SeparatorText("Model Classes");
    if (cached_loaded)
    {
        ImGui::Text("Source: %s", cached_source.c_str());
        ImGui::Text("Total: %d", static_cast<int>(cached_names.size()));

        ImGui::BeginChild("##model_class_list", ImVec2(0, 90), true);
        for (size_t i = 0; i < cached_names.size(); ++i)
        {
            ImGui::Text(" - %zu: %s", i, cached_names[i].c_str());
        }
        ImGui::EndChild();
    }
    else
    {
        ImGui::TextDisabled("No labels file found for current model.");
        ImGui::TextDisabled("Expected: models/<model>.names or models/<model>.txt");
    }
}

void draw_classes()
{
    draw_class_mapping();
    ImGui::Separator();
    draw_model_classes();
    ImGui::Separator();
    draw_detected_classes();
}
