#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>
#include <algorithm>

#include "imgui/imgui.h"
#include "rn_ai_cpp.h"
#include "overlay.h"
#include "ui_controls.h"
#include "config_dirty.h"

void draw_overlay()
{
    ImGui::PushID("Overlay Opacity");
    ImGui::TextUnformatted("Overlay Opacity");
    bool opacity_changed = false;
    if (ImGui::Button("-", ImVec2(24.0f, 0.0f)))
    {
        config.overlay_opacity = std::clamp(config.overlay_opacity - 1, 40, 255);
        opacity_changed = true;
    }
    ImGui::SameLine();
    ImGui::SetNextItemWidth(220.0f);
    if (ImGui::SliderInt("##slider", &config.overlay_opacity, 40, 255, "%d"))
    {
        config.overlay_opacity = std::clamp(config.overlay_opacity, 40, 255);
        opacity_changed = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(24.0f, 0.0f)))
    {
        config.overlay_opacity = std::clamp(config.overlay_opacity + 1, 40, 255);
        opacity_changed = true;
    }
    ImGui::PopID();

    if (opacity_changed)
        OverlayConfig_MarkDirty();

    static float ui_scale = config.overlay_ui_scale;
    static int window_w = overlayWidth;
    static int window_h = overlayHeight;
    bool ui_scale_changed = false;

    ImGui::SameLine();
    ImGui::PushID("UI Scale Inline");
    ImGui::TextUnformatted("UI Scale");
    ImGui::SameLine();
    if (ImGui::Button("-", ImVec2(24.0f, 0.0f)))
    {
        ui_scale = std::clamp(ui_scale - 0.05f, 0.5f, 3.0f);
        ui_scale_changed = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("+", ImVec2(24.0f, 0.0f)))
    {
        ui_scale = std::clamp(ui_scale + 0.05f, 0.5f, 3.0f);
        ui_scale_changed = true;
    }
    ImGui::SameLine();
    ImGui::SetNextItemWidth(90.0f);
    if (ImGui::InputFloat("##input", &ui_scale, 0.0f, 0.0f, "%.2f"))
    {
        ui_scale = std::clamp(ui_scale, 0.5f, 3.0f);
        ui_scale_changed = true;
    }
    ImGui::PopID();

    if (ui_scale_changed)
    {
        ImGui::GetIO().FontGlobalScale = ui_scale;
        config.overlay_ui_scale = ui_scale;
        OverlayConfig_MarkDirty();
        extern const int BASE_OVERLAY_WIDTH;
        extern const int BASE_OVERLAY_HEIGHT;
        overlayWidth = static_cast<int>(BASE_OVERLAY_WIDTH * ui_scale);
        overlayHeight = static_cast<int>(BASE_OVERLAY_HEIGHT * ui_scale);
        SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
        window_w = overlayWidth;
        window_h = overlayHeight;
    }

    if (window_w != overlayWidth || window_h != overlayHeight)
    {
        window_w = overlayWidth;
        window_h = overlayHeight;
    }

    if (OverlayUI::SliderIntWithButtons("Window Width", &window_w, 520, 2200, 10, "%d"))
    {
        overlayWidth = window_w;
        SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
    }

    if (OverlayUI::SliderIntWithButtons("Window Height", &window_h, 360, 1400, 10, "%d"))
    {
        overlayHeight = window_h;
        SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
    }
}
