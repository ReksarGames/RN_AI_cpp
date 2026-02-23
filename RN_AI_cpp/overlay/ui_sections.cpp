#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>

#include "imgui/imgui.h"
#include "ui_sections.h"

namespace OverlayUI
{
bool BeginSection(const char* title, const char* id)
{
    ImGui::SeparatorText(title);
    const char* sectionId = id ? id : title;
    ImGui::PushID(sectionId);
    ImGui::BeginGroup();
    return true;
}

void EndSection()
{
    ImGui::EndGroup();
    ImGui::PopID();
    ImGui::Spacing();
}

void AdaptiveItemWidth(float ratio, float minWidth, float maxWidth)
{
    const float avail = ImGui::GetContentRegionAvail().x;
    const float width = std::clamp(avail * ratio, minWidth, maxWidth);
    ImGui::SetNextItemWidth(width);
}
}
