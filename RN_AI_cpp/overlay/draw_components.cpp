#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include "imgui/imgui.h"

#include "ui_sections.h"
#include "ui_theme.h"
#include "ui_runtime.h"

void draw_components()
{
    ImGuiStyle& style = ImGui::GetStyle();
    bool changed = false;

    if (OverlayUI::BeginCard("DESIGN TOKENS", "components_tokens"))
    {
        changed |= ImGui::Checkbox("Show descriptions", &OverlayUI::g_show_descriptions);

        if (ImGui::BeginTable("components_layout", 2, ImGuiTableFlags_SizingStretchSame))
        {
            ImGui::TableNextColumn();
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Button width", &OverlayUI::g_row_button_width, 18.0f, 40.0f, "%.0f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Input width", &OverlayUI::g_row_input_width, 46.0f, 120.0f, "%.0f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Item Spacing X", &style.ItemSpacing.x, 2.0f, 24.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Item Spacing Y", &style.ItemSpacing.y, 2.0f, 24.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Frame Padding X", &style.FramePadding.x, 2.0f, 24.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Frame Padding Y", &style.FramePadding.y, 1.0f, 20.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Frame Rounding", &style.FrameRounding, 0.0f, 8.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Window Rounding", &style.WindowRounding, 0.0f, 8.0f, "%.1f");
            ImGui::SetNextItemWidth(160.0f);
            changed |= ImGui::SliderFloat("Alpha", &style.Alpha, 0.2f, 1.0f, "%.2f");

            ImGui::TableNextColumn();
            changed |= ImGui::ColorEdit4("Text", (float*)&style.Colors[ImGuiCol_Text], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Window Bg", (float*)&style.Colors[ImGuiCol_WindowBg], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Frame Bg", (float*)&style.Colors[ImGuiCol_FrameBg], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Button", (float*)&style.Colors[ImGuiCol_Button], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Border", (float*)&style.Colors[ImGuiCol_Border], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Tab", (float*)&style.Colors[ImGuiCol_Tab], ImGuiColorEditFlags_NoInputs);
            changed |= ImGui::ColorEdit4("Tab Active", (float*)&style.Colors[ImGuiCol_TabActive], ImGuiColorEditFlags_NoInputs);
            ImGui::EndTable();
        }

        if (ImGui::Button("Reload ui_theme.ini"))
            changed |= OverlayTheme_Reload("ui_theme.ini");
    }
    OverlayUI::EndCard();

    if (changed)
        OverlayTheme_Save("ui_theme.ini");
}
