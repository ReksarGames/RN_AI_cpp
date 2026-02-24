#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "imgui/imgui.h"
#include "ui_theme.h"
#include "ui_runtime.h"

namespace
{
std::string trim_ascii(const std::string& s)
{
    size_t b = 0;
    while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b])) != 0)
        ++b;
    size_t e = s.size();
    while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1])) != 0)
        --e;
    return s.substr(b, e - b);
}

std::vector<float> parse_floats_csv(const std::string& csv)
{
    std::vector<float> out;
    std::stringstream ss(csv);
    std::string token;
    while (std::getline(ss, token, ','))
    {
        token = trim_ascii(token);
        if (token.empty())
            continue;
        try
        {
            out.push_back(std::stof(token));
        }
        catch (...)
        {
            return {};
        }
    }
    return out;
}

bool parse_color(const std::string& value, ImVec4& out)
{
    auto vals = parse_floats_csv(value);
    if (vals.size() < 3 || vals.size() > 4)
        return false;

    float r = vals[0];
    float g = vals[1];
    float b = vals[2];
    float a = vals.size() == 4 ? vals[3] : 1.0f;

    const bool byteRange = (r > 1.0f || g > 1.0f || b > 1.0f || a > 1.0f);
    if (byteRange)
    {
        r /= 255.0f;
        g /= 255.0f;
        b /= 255.0f;
        a /= 255.0f;
    }

    out = ImVec4(
        std::clamp(r, 0.0f, 1.0f),
        std::clamp(g, 0.0f, 1.0f),
        std::clamp(b, 0.0f, 1.0f),
        std::clamp(a, 0.0f, 1.0f));
    return true;
}

void write_default_theme_file(const char* filename)
{
    std::ofstream out(filename, std::ios::trunc);
    if (!out.is_open())
        return;

    out << "# UI theme values. Colors: r,g,b,a (0..255 or 0..1)\n";
    out << "alpha = 1.0\n";
    out << "window_rounding = 6\n";
    out << "frame_rounding = 4\n";
    out << "grab_rounding = 4\n";
    out << "scrollbar_rounding = 6\n";
    out << "item_spacing_x = 8\n";
    out << "item_spacing_y = 6\n";
    out << "frame_padding_x = 6\n";
    out << "frame_padding_y = 4\n";
    out << "color_text = 230,230,230,255\n";
    out << "color_window_bg = 22,22,24,240\n";
    out << "color_title_bg = 28,30,34,255\n";
    out << "color_title_bg_active = 42,46,52,255\n";
    out << "color_frame_bg = 36,39,44,255\n";
    out << "color_frame_bg_hovered = 48,53,60,255\n";
    out << "color_frame_bg_active = 56,62,72,255\n";
    out << "color_button = 42,74,124,255\n";
    out << "color_button_hovered = 60,96,152,255\n";
    out << "color_button_active = 78,118,176,255\n";
    out << "color_header = 42,74,124,190\n";
    out << "color_header_hovered = 60,96,152,220\n";
    out << "color_header_active = 78,118,176,255\n";
    out << "color_border = 69,86,120,255\n";
    out << "color_tab = 45,47,52,255\n";
    out << "color_tab_hovered = 58,64,74,255\n";
    out << "color_tab_active = 67,74,86,255\n";
    out << "show_descriptions = 1\n";
    out << "row_button_width = 22\n";
    out << "row_input_width = 54\n";
}

bool load_and_apply_internal(const char* filename)
{
    ImGuiStyle& style = ImGui::GetStyle();
    if (!std::ifstream(filename).good())
        write_default_theme_file(filename);

    std::ifstream in(filename);
    if (!in.is_open())
        return false;

    std::string line;
    while (std::getline(in, line))
    {
        line = trim_ascii(line);
        if (line.empty() || line[0] == '#')
            continue;

        const size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;
        std::string key = trim_ascii(line.substr(0, eq));
        std::string val = trim_ascii(line.substr(eq + 1));
        if (key.empty() || val.empty())
            continue;

        try
        {
            if (key == "alpha") style.Alpha = std::stof(val);
            else if (key == "window_rounding") style.WindowRounding = std::stof(val);
            else if (key == "frame_rounding") style.FrameRounding = std::stof(val);
            else if (key == "grab_rounding") style.GrabRounding = std::stof(val);
            else if (key == "scrollbar_rounding") style.ScrollbarRounding = std::stof(val);
            else if (key == "item_spacing_x") style.ItemSpacing.x = std::stof(val);
            else if (key == "item_spacing_y") style.ItemSpacing.y = std::stof(val);
            else if (key == "frame_padding_x") style.FramePadding.x = std::stof(val);
            else if (key == "frame_padding_y") style.FramePadding.y = std::stof(val);
            else if (key == "color_text") parse_color(val, style.Colors[ImGuiCol_Text]);
            else if (key == "color_window_bg") parse_color(val, style.Colors[ImGuiCol_WindowBg]);
            else if (key == "color_title_bg") parse_color(val, style.Colors[ImGuiCol_TitleBg]);
            else if (key == "color_title_bg_active") parse_color(val, style.Colors[ImGuiCol_TitleBgActive]);
            else if (key == "color_frame_bg") parse_color(val, style.Colors[ImGuiCol_FrameBg]);
            else if (key == "color_frame_bg_hovered") parse_color(val, style.Colors[ImGuiCol_FrameBgHovered]);
            else if (key == "color_frame_bg_active") parse_color(val, style.Colors[ImGuiCol_FrameBgActive]);
            else if (key == "color_button") parse_color(val, style.Colors[ImGuiCol_Button]);
            else if (key == "color_button_hovered") parse_color(val, style.Colors[ImGuiCol_ButtonHovered]);
            else if (key == "color_button_active") parse_color(val, style.Colors[ImGuiCol_ButtonActive]);
            else if (key == "color_header") parse_color(val, style.Colors[ImGuiCol_Header]);
            else if (key == "color_header_hovered") parse_color(val, style.Colors[ImGuiCol_HeaderHovered]);
            else if (key == "color_header_active") parse_color(val, style.Colors[ImGuiCol_HeaderActive]);
            else if (key == "color_border") parse_color(val, style.Colors[ImGuiCol_Border]);
            else if (key == "color_tab") parse_color(val, style.Colors[ImGuiCol_Tab]);
            else if (key == "color_tab_hovered") parse_color(val, style.Colors[ImGuiCol_TabHovered]);
            else if (key == "color_tab_active") parse_color(val, style.Colors[ImGuiCol_TabActive]);
            else if (key == "show_descriptions") OverlayUI::g_show_descriptions = (std::stoi(val) != 0);
            else if (key == "row_button_width") OverlayUI::g_row_button_width = std::stof(val);
            else if (key == "row_input_width") OverlayUI::g_row_input_width = std::stof(val);
        }
        catch (...)
        {
        }
    }

    style.Alpha = std::clamp(style.Alpha, 0.20f, 1.00f);
    OverlayUI::g_row_button_width = std::clamp(OverlayUI::g_row_button_width, 18.0f, 40.0f);
    OverlayUI::g_row_input_width = std::clamp(OverlayUI::g_row_input_width, 46.0f, 120.0f);
    return true;
}

bool save_internal(const char* filename)
{
    if (!std::ifstream(filename).good())
        write_default_theme_file(filename);

    std::ofstream out(filename, std::ios::trunc);
    if (!out.is_open())
        return false;

    const ImGuiStyle& style = ImGui::GetStyle();
    auto c = [&](ImGuiCol idx)
    {
        const ImVec4& v = style.Colors[idx];
        int r = static_cast<int>(v.x * 255.0f + 0.5f);
        int g = static_cast<int>(v.y * 255.0f + 0.5f);
        int b = static_cast<int>(v.z * 255.0f + 0.5f);
        int a = static_cast<int>(v.w * 255.0f + 0.5f);
        return std::to_string(r) + "," + std::to_string(g) + "," + std::to_string(b) + "," + std::to_string(a);
    };

    out << "# UI theme values. Colors: r,g,b,a (0..255 or 0..1)\n";
    out << "alpha = " << style.Alpha << "\n";
    out << "window_rounding = " << style.WindowRounding << "\n";
    out << "frame_rounding = " << style.FrameRounding << "\n";
    out << "grab_rounding = " << style.GrabRounding << "\n";
    out << "scrollbar_rounding = " << style.ScrollbarRounding << "\n";
    out << "item_spacing_x = " << style.ItemSpacing.x << "\n";
    out << "item_spacing_y = " << style.ItemSpacing.y << "\n";
    out << "frame_padding_x = " << style.FramePadding.x << "\n";
    out << "frame_padding_y = " << style.FramePadding.y << "\n\n";

    out << "color_text = " << c(ImGuiCol_Text) << "\n";
    out << "color_window_bg = " << c(ImGuiCol_WindowBg) << "\n";
    out << "color_title_bg = " << c(ImGuiCol_TitleBg) << "\n";
    out << "color_title_bg_active = " << c(ImGuiCol_TitleBgActive) << "\n";
    out << "color_frame_bg = " << c(ImGuiCol_FrameBg) << "\n";
    out << "color_frame_bg_hovered = " << c(ImGuiCol_FrameBgHovered) << "\n";
    out << "color_frame_bg_active = " << c(ImGuiCol_FrameBgActive) << "\n";
    out << "color_button = " << c(ImGuiCol_Button) << "\n";
    out << "color_button_hovered = " << c(ImGuiCol_ButtonHovered) << "\n";
    out << "color_button_active = " << c(ImGuiCol_ButtonActive) << "\n";
    out << "color_header = " << c(ImGuiCol_Header) << "\n";
    out << "color_header_hovered = " << c(ImGuiCol_HeaderHovered) << "\n";
    out << "color_header_active = " << c(ImGuiCol_HeaderActive) << "\n";
    out << "color_border = " << c(ImGuiCol_Border) << "\n";
    out << "color_tab = " << c(ImGuiCol_Tab) << "\n";
    out << "color_tab_hovered = " << c(ImGuiCol_TabHovered) << "\n";
    out << "color_tab_active = " << c(ImGuiCol_TabActive) << "\n";
    out << "show_descriptions = " << (OverlayUI::g_show_descriptions ? 1 : 0) << "\n";
    out << "row_button_width = " << OverlayUI::g_row_button_width << "\n";
    out << "row_input_width = " << OverlayUI::g_row_input_width << "\n";
    return true;
}
}

bool OverlayTheme_LoadAndApply(const char* filename)
{
    return load_and_apply_internal(filename);
}

bool OverlayTheme_Reload(const char* filename)
{
    return load_and_apply_internal(filename);
}

bool OverlayTheme_Save(const char* filename)
{
    return save_internal(filename);
}
