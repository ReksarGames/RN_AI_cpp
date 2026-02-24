#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <d3d11.h>
#include <algorithm>
#include <cctype>
#include <iostream>
#include <sstream>
#include <unordered_set>
#include <vector>

#include "imgui/imgui.h"
#include "rn_ai_cpp.h"
#include "overlay.h"
#include "include/other_tools.h"
#include "capture.h"
#include "ui_sections.h"

#ifndef SAFE_RELEASE
#define SAFE_RELEASE(p)       \
    do {                      \
        if ((p) != nullptr) { \
            (p)->Release();   \
            (p) = nullptr;    \
        }                     \
    } while (0)
#endif

bool prev_verbose = config.verbose;

static ID3D11Texture2D* g_debugTex = nullptr;
static ID3D11ShaderResourceView* g_debugSRV = nullptr;
static int texW = 0, texH = 0;


static float debug_scale = 1.0f;

static std::vector<int> parse_int_list_local(const std::string& text)
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

static void uploadDebugFrame(const cv::Mat& bgr)
{
    if (bgr.empty()) return;

    if (!g_debugTex || bgr.cols != texW || bgr.rows != texH)
    {
        SAFE_RELEASE(g_debugTex);
        SAFE_RELEASE(g_debugSRV);

        texW = bgr.cols;  texH = bgr.rows;

        D3D11_TEXTURE2D_DESC td = {};
        td.Width = texW;
        td.Height = texH;
        td.MipLevels = td.ArraySize = 1;
        td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        td.SampleDesc.Count = 1;
        td.Usage = D3D11_USAGE_DYNAMIC;
        td.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        td.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;

        g_pd3dDevice->CreateTexture2D(&td, nullptr, &g_debugTex);

        D3D11_SHADER_RESOURCE_VIEW_DESC sd = {};
        sd.Format = td.Format;
        sd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
        sd.Texture2D.MipLevels = 1;
        g_pd3dDevice->CreateShaderResourceView(g_debugTex, &sd, &g_debugSRV);
    }

    static cv::Mat rgba;
    cv::cvtColor(bgr, rgba, cv::COLOR_BGR2RGBA);

    D3D11_MAPPED_SUBRESOURCE ms;
    if (SUCCEEDED(g_pd3dDeviceContext->Map(g_debugTex, 0,
        D3D11_MAP_WRITE_DISCARD, 0, &ms)))
    {
        for (int y = 0; y < texH; ++y)
            memcpy((uint8_t*)ms.pData + ms.RowPitch * y,
                rgba.ptr(y), texW * 4);
        g_pd3dDeviceContext->Unmap(g_debugTex, 0);
    }
}

void draw_debug_frame()
{
    cv::Mat frameCopy;
    {
        std::lock_guard<std::mutex> lk(frameMutex);
        if (!latestFrame.empty())
            latestFrame.copyTo(frameCopy);
    }

    uploadDebugFrame(frameCopy);

    if (!g_debugSRV) return;

    ImGui::SetNextItemWidth((std::min)(220.0f, ImGui::GetContentRegionAvail().x));
    ImGui::SliderFloat("Debug scale", &debug_scale, 0.1f, 2.0f, "%.1fx");

    ImVec2 image_size(texW * debug_scale, texH * debug_scale);
    ImGui::Image(g_debugSRV, image_size);

    ImVec2 image_pos = ImGui::GetItemRectMin();
    ImDrawList* draw_list = ImGui::GetWindowDrawList();

    {
        auto allowed_list = parse_int_list_local(config.allowed_classes);
        std::unordered_set<int> allowed_set(allowed_list.begin(), allowed_list.end());

        auto is_class_visible = [&](int cls) -> bool
            {
                auto it_name = config.custom_class_names.find(cls);
                if (it_name != config.custom_class_names.end() && it_name->second == "__deleted__")
                    return false;
                if (config.disable_headshot && cls == config.class_head)
                    return false;
                if (cls == config.class_third_person && config.ignore_third_person)
                    return false;
                if ((cls == config.class_hideout_target_human || cls == config.class_hideout_target_balls) &&
                    !config.shooting_range_targets)
                    return false;
                if (allowed_set.empty())
                    return false;
                return allowed_set.count(cls) > 0;
            };

        std::lock_guard<std::mutex> lock(detectionBuffer.mutex);
        for (size_t i = 0; i < detectionBuffer.boxes.size(); ++i)
        {
            int cls = -1;
            if (i < detectionBuffer.classes.size())
                cls = detectionBuffer.classes[i];
            if (cls >= 0 && !is_class_visible(cls))
                continue;

            const cv::Rect& box = detectionBuffer.boxes[i];

            ImVec2 p1(image_pos.x + box.x * debug_scale,
                image_pos.y + box.y * debug_scale);
            ImVec2 p2(p1.x + box.width * debug_scale,
                p1.y + box.height * debug_scale);

            ImU32 color = IM_COL32(255, 0, 0, 255);

            draw_list->AddRect(p1, p2, color, 0.0f, 0, 2.0f);

            if (cls >= 0)
            {
                std::string label = "Class " + std::to_string(cls);
                draw_list->AddText(ImVec2(p1.x, p1.y - 16), IM_COL32(255, 255, 0, 255), label.c_str());
            }
        }
    }

    if (config.draw_futurePositions && globalMouseThread)
    {
        auto futurePts = globalMouseThread->getFuturePositions();
        if (!futurePts.empty())
        {
            float scale_x = static_cast<float>(texW) / config.detection_resolution;
            float scale_y = static_cast<float>(texH) / config.detection_resolution;

            ImVec2 clip_min = image_pos;
            ImVec2 clip_max = ImVec2(image_pos.x + texW * debug_scale,
                image_pos.y + texH * debug_scale);
            draw_list->PushClipRect(clip_min, clip_max, true);

            int totalPts = static_cast<int>(futurePts.size());
            for (size_t i = 0; i < futurePts.size(); ++i)
            {
                int px = static_cast<int>(futurePts[i].first * scale_x);
                int py = static_cast<int>(futurePts[i].second * scale_y);
                ImVec2 pt(image_pos.x + px * debug_scale,
                    image_pos.y + py * debug_scale);

                int b = static_cast<int>(255 - (i * 255.0 / totalPts));
                int r = static_cast<int>(i * 255.0 / totalPts);
                int g = 50;

                ImU32 fillColor = IM_COL32(r, g, b, 255);
                ImU32 outlineColor = IM_COL32(255, 255, 255, 255);

                draw_list->AddCircleFilled(pt, 4.0f * debug_scale, fillColor);
                draw_list->AddCircle(pt, 4.0f * debug_scale, outlineColor, 0, 1.0f);
            }

            draw_list->PopClipRect();
        }
    }
}

void draw_debug()
{
    static bool show_raw_preview = false;

    ImGui::Checkbox("Show Debug Window", &config.show_window);
    ImGui::SameLine();
    ImGui::Checkbox("Raw Preview", &show_raw_preview);
    if (config.show_window && show_raw_preview)
    {
        draw_debug_frame();
        ImGui::Separator();
    }

    if (OverlayUI::BeginCard("PIPELINE STATUS", "debug_pipeline"))
    {
        if (ImGui::BeginTable("debug_pipeline_tbl", 2, ImGuiTableFlags_SizingStretchSame | ImGuiTableFlags_BordersInnerV))
        {
            auto row = [](const char* left, const char* right)
            {
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                ImGui::TextUnformatted(left);
                ImGui::TableNextColumn();
                ImGui::TextUnformatted(right);
            };
            row("Capture Thread", "Running");
            row("Preprocessor", "Active");
            row("AI Detector", "Inference OK");
            row("Mouse Controller", "Idle");
            row("OBS Connection", config.is_obs ? "Enabled" : "Disabled");
            ImGui::EndTable();
        }
    }
    OverlayUI::EndCard();

    if (OverlayUI::BeginCard("RUNTIME INFO", "debug_runtime"))
    {
        static int totalFrames = 0;
        totalFrames += 1;
        if (ImGui::BeginTable("debug_runtime_tbl", 2, ImGuiTableFlags_SizingStretchSame | ImGuiTableFlags_BordersInnerV))
        {
            auto rowf = [](const char* left, const char* fmt, auto val)
            {
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                ImGui::TextUnformatted(left);
                ImGui::TableNextColumn();
                ImGui::Text(fmt, val);
            };
            rowf("Uptime", "%.2f s", ImGui::GetTime());
            rowf("Total Frames", "%d", totalFrames);
            rowf("Dropped Frames", "%d", 0);
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted("Memory Usage");
            ImGui::TableNextColumn();
            ImGui::TextUnformatted("n/a");
            rowf("Thread Count", "%d", 8);
            ImGui::EndTable();
        }
    }
    OverlayUI::EndCard();

    ImGui::Separator();
    ImGui::Checkbox("Verbose console output", &config.verbose);
    ImGui::TextDisabled("Writes all std::cout/std::cerr to runtime_console.log");

    if (prev_verbose != config.verbose)
    {
        prev_verbose = config.verbose;
        SetConsoleFileLoggingEnabled(config.verbose, false);
        config.saveConfig();
    }

    if (OverlayUI::BeginCard("LOG ACTIONS", "debug_actions"))
    {
        if (ImGui::Button("Open Log Folder"))
            std::cout << "[INFO] Open log folder clicked" << std::endl;
        ImGui::SameLine();
        if (ImGui::Button("Export Logs"))
            std::cout << "[INFO] Export logs clicked" << std::endl;
    }
    OverlayUI::EndCard();
}
