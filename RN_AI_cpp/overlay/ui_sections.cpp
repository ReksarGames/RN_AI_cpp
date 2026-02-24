#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>
#include <vector>

#include "imgui/imgui.h"
#include "ui_sections.h"

namespace OverlayUI
{
namespace
{
struct CardState
{
    ImVec2 topLeft;
    float width;
    float headerHeight;
};

std::vector<CardState> g_card_stack;
}

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

bool BeginCard(const char* title, const char* id)
{
    const char* cardId = id ? id : title;
    ImGui::PushID(cardId);

    const float width = ImGui::GetContentRegionAvail().x;
    const ImVec2 topLeft = ImGui::GetCursorScreenPos();
    const float headerHeight = ImGui::GetFrameHeight() + 6.0f;

    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec4 borderCol = ImGui::GetStyleColorVec4(ImGuiCol_Border);
    const ImVec4 headerCol = ImGui::GetStyleColorVec4(ImGuiCol_TitleBgActive);
    const ImVec4 bgCol = ImGui::GetStyleColorVec4(ImGuiCol_FrameBg);

    dl->AddRectFilled(topLeft, ImVec2(topLeft.x + width, topLeft.y + headerHeight), ImGui::ColorConvertFloat4ToU32(headerCol), 0.0f);
    dl->AddRectFilled(ImVec2(topLeft.x + 1.0f, topLeft.y + headerHeight + 1.0f), ImVec2(topLeft.x + width - 1.0f, topLeft.y + headerHeight + 2.0f), ImGui::ColorConvertFloat4ToU32(borderCol), 0.0f);
    dl->AddRectFilled(ImVec2(topLeft.x + 1.0f, topLeft.y + headerHeight + 2.0f), ImVec2(topLeft.x + width - 1.0f, topLeft.y + headerHeight + 3.0f), ImGui::ColorConvertFloat4ToU32(bgCol), 0.0f);
    dl->AddText(ImVec2(topLeft.x + 10.0f, topLeft.y + 4.0f), ImGui::GetColorU32(ImGuiCol_Text), title);

    ImGui::Dummy(ImVec2(width, headerHeight + 6.0f));
    ImGui::SetCursorPosX(ImGui::GetCursorPosX() + 10.0f);
    ImGui::BeginGroup();

    g_card_stack.push_back({ topLeft, width, headerHeight });
    return true;
}

void EndCard()
{
    if (g_card_stack.empty())
    {
        ImGui::PopID();
        return;
    }

    ImGui::EndGroup();
    ImVec2 contentMax = ImGui::GetItemRectMax();
    CardState st = g_card_stack.back();
    g_card_stack.pop_back();

    const float bottom = contentMax.y + 10.0f;
    ImDrawList* dl = ImGui::GetWindowDrawList();
    dl->AddRect(st.topLeft, ImVec2(st.topLeft.x + st.width, bottom), ImGui::GetColorU32(ImGuiCol_Border), 0.0f, 0, 1.0f);

    const float localBottom = bottom - ImGui::GetWindowPos().y;
    ImGui::SetCursorPosY(localBottom + 8.0f);
    ImGui::PopID();
}

void AdaptiveItemWidth(float ratio, float minWidth, float maxWidth)
{
    const float avail = ImGui::GetContentRegionAvail().x;
    const float width = std::clamp(avail * ratio, minWidth, maxWidth);
    ImGui::SetNextItemWidth(width);
}
}
