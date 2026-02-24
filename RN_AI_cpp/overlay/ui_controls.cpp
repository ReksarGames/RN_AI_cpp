#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>

#include "imgui/imgui.h"
#include "ui_controls.h"
#include "ui_runtime.h"

namespace OverlayUI
{
bool SliderIntWithButtons(const char* label, int* value, int minValue, int maxValue, int step, const char* sliderFormat)
{
    bool changed = false;
    ImGui::PushID(label);
    ImGui::TextUnformatted(label);

    if (ImGui::Button("-", ImVec2(24.0f, 0.0f)))
    {
        *value = std::clamp(*value - step, minValue, maxValue);
        changed = true;
    }

    ImGui::SameLine();
    ImGui::SetNextItemWidth(220.0f);
    changed |= ImGui::SliderInt("##slider", value, minValue, maxValue, sliderFormat);

    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(24.0f, 0.0f)))
    {
        *value = std::clamp(*value + step, minValue, maxValue);
        changed = true;
    }

    ImGui::SameLine();
    ImGui::SetNextItemWidth(90.0f);
    if (ImGui::InputInt("##input", value, 0, 0))
    {
        *value = std::clamp(*value, minValue, maxValue);
        changed = true;
    }

    ImGui::PopID();
    return changed;
}

bool SliderFloatWithButtons(const char* label, float* value, float minValue, float maxValue, float step, const char* sliderFormat, const char* inputFormat)
{
    bool changed = false;
    ImGui::PushID(label);
    ImGui::TextUnformatted(label);

    if (ImGui::Button("-", ImVec2(24.0f, 0.0f)))
    {
        *value = std::clamp(*value - step, minValue, maxValue);
        changed = true;
    }

    ImGui::SameLine();
    ImGui::SetNextItemWidth(220.0f);
    changed |= ImGui::SliderFloat("##slider", value, minValue, maxValue, sliderFormat);

    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(24.0f, 0.0f)))
    {
        *value = std::clamp(*value + step, minValue, maxValue);
        changed = true;
    }

    ImGui::SameLine();
    ImGui::SetNextItemWidth(90.0f);
    if (ImGui::InputFloat("##input", value, 0.0f, 0.0f, inputFormat))
    {
        *value = std::clamp(*value, minValue, maxValue);
        changed = true;
    }

    ImGui::PopID();
    return changed;
}

bool IntControlRow(const char* label, int* value, int minValue, int maxValue, int step, const char* unit, const char* hint)
{
    bool changed = false;
    ImGui::PushID(label);

    const float rowAvail = ImGui::GetContentRegionAvail().x;
    const float btnW = g_row_button_width;
    const float inputW = g_row_input_width;
    const float unitW = (unit && unit[0] != '\0') ? (ImGui::CalcTextSize(unit).x + 8.0f) : 0.0f;
    float sliderW = rowAvail - btnW - btnW - inputW - unitW - 16.0f;
    sliderW = (std::max)(80.0f, sliderW);

    ImGui::TextUnformatted(label);
    ImGui::SetNextItemWidth(sliderW);

    if (ImGui::Button("-", ImVec2(btnW, 0.0f)))
    {
        *value = std::clamp(*value - step, minValue, maxValue);
        changed = true;
    }
    ImGui::SameLine();
    changed |= ImGui::SliderInt("##slider", value, minValue, maxValue, "");
    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(btnW, 0.0f)))
    {
        *value = std::clamp(*value + step, minValue, maxValue);
        changed = true;
    }
    ImGui::SameLine();
    ImGui::SetNextItemWidth(inputW);
    if (ImGui::InputInt("##input", value, 0, 0))
    {
        *value = std::clamp(*value, minValue, maxValue);
        changed = true;
    }
    if (unit && unit[0] != '\0')
    {
        ImGui::SameLine();
        ImGui::TextUnformatted(unit);
    }

    if (g_show_descriptions && hint && hint[0] != '\0')
    {
        ImGui::TextDisabled("%s", hint);
    }

    ImGui::PopID();
    return changed;
}

bool FloatControlRow(const char* label, float* value, float minValue, float maxValue, float step, const char* sliderFormat, const char* inputFormat, const char* unit, const char* hint)
{
    bool changed = false;
    ImGui::PushID(label);

    const float rowAvail = ImGui::GetContentRegionAvail().x;
    const float btnW = g_row_button_width;
    const float inputW = g_row_input_width;
    const float unitW = (unit && unit[0] != '\0') ? (ImGui::CalcTextSize(unit).x + 8.0f) : 0.0f;
    float sliderW = rowAvail - btnW - btnW - inputW - unitW - 16.0f;
    sliderW = (std::max)(80.0f, sliderW);

    ImGui::TextUnformatted(label);

    if (ImGui::Button("-", ImVec2(btnW, 0.0f)))
    {
        *value = std::clamp(*value - step, minValue, maxValue);
        changed = true;
    }
    ImGui::SameLine();
    ImGui::SetNextItemWidth(sliderW);
    changed |= ImGui::SliderFloat("##slider", value, minValue, maxValue, sliderFormat);
    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(btnW, 0.0f)))
    {
        *value = std::clamp(*value + step, minValue, maxValue);
        changed = true;
    }
    ImGui::SameLine();
    ImGui::SetNextItemWidth(inputW);
    if (ImGui::InputFloat("##input", value, 0.0f, 0.0f, inputFormat))
    {
        *value = std::clamp(*value, minValue, maxValue);
        changed = true;
    }
    if (unit && unit[0] != '\0')
    {
        ImGui::SameLine();
        ImGui::TextUnformatted(unit);
    }

    if (g_show_descriptions && hint && hint[0] != '\0')
    {
        ImGui::TextDisabled("%s", hint);
    }

    ImGui::PopID();
    return changed;
}
}
