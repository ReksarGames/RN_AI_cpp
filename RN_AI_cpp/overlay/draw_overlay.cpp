#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include "imgui/imgui.h"
#include "rn_ai_cpp.h"
#include "overlay.h"
#include "ui_controls.h"
#include "ui_theme.h"
#include "config_dirty.h"

void draw_overlay()
{
    if (OverlayUI::SliderIntWithButtons("Overlay Opacity", &config.overlay_opacity, 40, 255, 1, "%d"))
        OverlayConfig_MarkDirty();

    static float ui_scale = config.overlay_ui_scale;

    if (OverlayUI::SliderFloatWithButtons("UI Scale", &ui_scale, 0.5f, 3.0f, 0.05f, "%.2f", "%.2f"))
    {
        ImGui::GetIO().FontGlobalScale = ui_scale;

        config.overlay_ui_scale = ui_scale;
        OverlayConfig_MarkDirty();

        extern const int BASE_OVERLAY_WIDTH;
        extern const int BASE_OVERLAY_HEIGHT;
        overlayWidth = static_cast<int>(BASE_OVERLAY_WIDTH * ui_scale);
        overlayHeight = static_cast<int>(BASE_OVERLAY_HEIGHT * ui_scale);

        SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
    }

    if (ImGui::Button("Reload ui_theme.ini"))
    {
        OverlayTheme_Reload("ui_theme.ini");
    }
    ImGui::SameLine();
    ImGui::TextDisabled("Theme file: ui_theme.ini");
}
