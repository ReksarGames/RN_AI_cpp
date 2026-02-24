#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <algorithm>
#include <cstdio>
#include <string>

#include "imgui/imgui.h"
#include "rn_ai_cpp.h"
#include "overlay.h"
#include "capture.h"
#include "ui_sections.h"

void draw_stats()
{
    static float preprocess_times[120] = {};
    static float inference_times[120] = {};
    static float copy_times[120] = {};
    static float postprocess_times[120] = {};
    static float nms_times[120] = {};
    static int index_inf = 0;

    float current_preprocess = 0.0f;
    float current_inference = 0.0f;
    float current_copy = 0.0f;
    float current_post = 0.0f;
    float current_nms = 0.0f;

    if (config.backend == "DML" && dml_detector) {}
#ifdef USE_CUDA
    else
    {
        current_preprocess = static_cast<float>(trt_detector.lastPreprocessTime.count());
        current_inference = static_cast<float>(trt_detector.lastInferenceTime.count());
        current_copy = static_cast<float>(trt_detector.lastCopyTime.count());
        current_post = static_cast<float>(trt_detector.lastPostprocessTime.count());
        current_nms = static_cast<float>(trt_detector.lastNmsTime.count());
    }
#endif
    preprocess_times[index_inf] = current_preprocess;
    inference_times[index_inf] = current_inference;
    copy_times[index_inf] = current_copy;
    postprocess_times[index_inf] = current_post;
    nms_times[index_inf] = current_nms;
    index_inf = (index_inf + 1) % IM_ARRAYSIZE(inference_times);

    auto avg = [](const float* arr, int n) -> float {
        float sum = 0.0f; int cnt = 0;
        for (int i = 0; i < n; ++i) if (arr[i] > 0.0f) { sum += arr[i]; ++cnt; }
        return cnt ? sum / cnt : 0.0f;
    };

    float avg_preprocess = avg(preprocess_times, IM_ARRAYSIZE(preprocess_times));
    float avg_inference = avg(inference_times, IM_ARRAYSIZE(inference_times));
    float avg_copy = avg(copy_times, IM_ARRAYSIZE(copy_times));
    float avg_post = avg(postprocess_times, IM_ARRAYSIZE(postprocess_times));
    float avg_nms = avg(nms_times, IM_ARRAYSIZE(nms_times));
    (void)avg_preprocess;
    (void)avg_inference;
    (void)avg_copy;
    (void)avg_post;
    (void)avg_nms;

    static float capture_fps_vals[120] = {};
    static int index_fps = 0;

    float current_fps = static_cast<float>(captureFps.load());
    capture_fps_vals[index_fps] = current_fps;
    index_fps = (index_fps + 1) % IM_ARRAYSIZE(capture_fps_vals);

    int latestWidth = 0;
    int latestHeight = 0;
    size_t queueDepth = 0;
    {
        std::lock_guard<std::mutex> lk(frameMutex);
        if (!latestFrame.empty())
        {
            latestWidth = latestFrame.cols;
            latestHeight = latestFrame.rows;
        }
        queueDepth = frameQueue.size();
    }

    if (OverlayUI::BeginCard("PERFORMANCE METRICS", "stats_metrics"))
    {
        auto metricBox = [](const char* id, const char* title, float nowVal, const char* unit, const float* vals, int count, int idx, float maxY, ImU32 valueColor, ImVec4 lineColor)
        {
            ImGui::BeginChild(id, ImVec2(0, 146), true, ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse);

            ImGui::TextUnformatted(title);

            char value_buf[64] = {};
            if (unit && unit[0] != '\0')
                snprintf(value_buf, sizeof(value_buf), "%.1f %s", nowVal, unit);
            else
                snprintf(value_buf, sizeof(value_buf), "%.0f", nowVal);

            const float value_w = ImGui::CalcTextSize(value_buf).x;
            ImGui::SameLine();
            ImGui::SetCursorPosX(ImGui::GetWindowContentRegionMax().x - value_w);
            ImGui::SetWindowFontScale(1.12f);
            ImGui::TextColored(ImGui::ColorConvertU32ToFloat4(valueColor), "%s", value_buf);
            ImGui::SetWindowFontScale(1.00f);

            ImGui::Dummy(ImVec2(0.0f, 6.0f));
            ImGui::PushStyleColor(ImGuiCol_PlotLines, lineColor);
            ImGui::PushStyleColor(ImGuiCol_PlotLinesHovered, lineColor);
            ImGui::PlotLines("##plot", vals, count, idx, nullptr, 0.0f, maxY, ImVec2(-1, 80));
            ImGui::PopStyleColor(2);
            ImGui::EndChild();
        };

        if (ImGui::BeginTable("metrics_tbl", 2, ImGuiTableFlags_SizingStretchSame))
        {
            ImGui::TableNextColumn();
            metricBox("m_fps", "CAPTURE FPS", current_fps, "", capture_fps_vals, IM_ARRAYSIZE(capture_fps_vals), index_fps, 240.0f, IM_COL32(88, 220, 95, 255), ImVec4(0.28f, 0.82f, 0.36f, 1.0f));
            ImGui::TableNextColumn();
            metricBox("m_pre", "PREPROCESS", current_preprocess, "ms", preprocess_times, IM_ARRAYSIZE(preprocess_times), index_inf, 20.0f, IM_COL32(120, 212, 255, 255), ImVec4(0.36f, 0.78f, 0.98f, 1.0f));
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            metricBox("m_inf", "INFERENCE", current_inference, "ms", inference_times, IM_ARRAYSIZE(inference_times), index_inf, 20.0f, IM_COL32(232, 200, 64, 255), ImVec4(0.88f, 0.73f, 0.18f, 1.0f));
            ImGui::TableNextColumn();
            static float queue_vals[120] = {};
            static int queue_idx = 0;
            queue_vals[queue_idx] = static_cast<float>(queueDepth);
            queue_idx = (queue_idx + 1) % IM_ARRAYSIZE(queue_vals);
            metricBox("m_qd", "QUEUE DEPTH", static_cast<float>(queueDepth), "", queue_vals, IM_ARRAYSIZE(queue_vals), queue_idx, 16.0f, IM_COL32(224, 224, 224, 255), ImVec4(0.85f, 0.85f, 0.85f, 1.0f));
            ImGui::EndTable();
        }
    }
    OverlayUI::EndCard();

    std::string captureSource = "Unknown";
    if (config.capture_method == "duplication_api" || config.capture_method == "obs")
    {
        captureSource = "Monitor " + std::to_string(std::max(0, config.monitor_idx) + 1);
    }
    else if (config.capture_method == "winrt")
    {
        captureSource = "WinRT";
    }
    else if (config.capture_method == "virtual_camera")
    {
        captureSource = "Camera: " + config.virtual_camera_name;
    }

    if (OverlayUI::BeginCard("CAPTURE DETAILS", "stats_capture"))
    {
        if (ImGui::BeginTable("stats_capture_tbl", 2, ImGuiTableFlags_SizingStretchProp))
        {
            auto row_text = [](const char* key, const char* val)
            {
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                ImGui::TextUnformatted(key);
                ImGui::TableNextColumn();
                ImGui::TextWrapped("%s", val);
            };

            row_text("Capture Method:", config.capture_method.c_str());
            row_text("Backend:", config.backend.c_str());
            row_text("Source:", captureSource.c_str());

            char frame_size_buf[32] = {};
            if (latestWidth > 0 && latestHeight > 0)
                snprintf(frame_size_buf, sizeof(frame_size_buf), "%dx%d", latestWidth, latestHeight);
            else
                snprintf(frame_size_buf, sizeof(frame_size_buf), "n/a");
            row_text("Frame Size:", frame_size_buf);

            char det_res_buf[32] = {};
            snprintf(det_res_buf, sizeof(det_res_buf), "%d", config.detection_resolution);
            row_text("Detection Resolution:", det_res_buf);

            char qd_buf[32] = {};
            snprintf(qd_buf, sizeof(qd_buf), "%d", static_cast<int>(queueDepth));
            row_text("Frame Queue Depth:", qd_buf);

            row_text("Circle Mask:", config.circle_mask ? "on" : "off");
            ImGui::EndTable();
        }

#ifdef USE_CUDA
        if (config.backend == "TRT")
        {
            const bool canUseCudaCapture = (config.capture_method == "duplication_api");
            const bool directCaptureActive = canUseCudaCapture && config.capture_use_cuda && !config.circle_mask;

            std::string directCaptureStatus;
            if (!canUseCudaCapture)
                directCaptureStatus = "N/A (requires duplication_api)";
            else if (!config.capture_use_cuda)
                directCaptureStatus = "Disabled by user";
            else if (config.circle_mask)
                directCaptureStatus = "CPU fallback (circle mask is enabled)";
            else
                directCaptureStatus = "Active";

            ImGui::Separator();
            ImGui::Text("CUDA Direct Capture: %s", config.capture_use_cuda ? "enabled" : "disabled");
            ImGui::Text("Capture pipeline: %s", directCaptureActive ? "GPU direct path" : "CPU readback");
            ImGui::TextWrapped("Direct capture status: %s", directCaptureStatus.c_str());
        }
#endif
    }
    OverlayUI::EndCard();

    if (OverlayUI::BeginCard("SYSTEM INFO", "stats_system"))
    {
        if (ImGui::BeginTable("stats_system_tbl", 2, ImGuiTableFlags_SizingStretchProp))
        {
            auto row_text = [](const char* key, const char* val)
            {
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                ImGui::TextUnformatted(key);
                ImGui::TableNextColumn();
                ImGui::TextWrapped("%s", val);
            };
            row_text("GPU:", "NVIDIA GPU");
            row_text("CUDA Version:", "12.x");
            row_text("Driver:", "n/a");
            ImGui::EndTable();
        }
    }
    OverlayUI::EndCard();

    if (ImGui::CollapsingHeader("DETECTION STATISTICS", ImGuiTreeNodeFlags_DefaultOpen))
    {
        size_t detCount = 0;
        {
            std::lock_guard<std::mutex> lock(detectionBuffer.mutex);
            detCount = detectionBuffer.boxes.size();
        }
        if (ImGui::BeginTable("stats_det_tbl", 2, ImGuiTableFlags_SizingStretchProp))
        {
            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted("Total Detections:");
            ImGui::TableNextColumn();
            ImGui::Text("%d", static_cast<int>(detCount));

            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted("Avg Confidence:");
            ImGui::TableNextColumn();
            ImGui::Text("%.2f", config.confidence_threshold);

            ImGui::TableNextRow();
            ImGui::TableNextColumn();
            ImGui::TextUnformatted("Target Locks:");
            ImGui::TableNextColumn();
            ImGui::TextUnformatted(config.smart_target_lock ? "enabled" : "disabled");
            ImGui::EndTable();
        }
    }
}
