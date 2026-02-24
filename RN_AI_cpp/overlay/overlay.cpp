#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <tchar.h>
#include <thread>
#include <mutex>
#include <atomic>
#include <d3d11.h>
#include <dxgi.h>
#include <filesystem>

#include <imgui.h>
#include <imgui_impl_dx11.h>
#include <imgui_impl_win32.h>
#include <imgui/imgui_internal.h>

#include "overlay.h"
#include "overlay/draw_settings.h"
#include "config.h"
#include "keycodes.h"
#include "rn_ai_cpp.h"
#include "capture.h"
#include "keyboard_listener.h"
#include "other_tools.h"
#include "virtual_camera.h"
#include "config_dirty.h"
#include "ui_theme.h"
#include "ui_runtime.h"
#ifdef USE_CUDA
#include "trt_detector.h"
#endif

ID3D11Device* g_pd3dDevice = NULL;
ID3D11DeviceContext* g_pd3dDeviceContext = NULL;
IDXGISwapChain* g_pSwapChain = NULL;
ID3D11RenderTargetView* g_mainRenderTargetView = NULL;
HWND g_hwnd = NULL;

extern Config config;
extern std::mutex configMutex;
extern std::atomic<bool> shouldExit;

bool CreateDeviceD3D(HWND hWnd);
void CleanupDeviceD3D();
void CreateRenderTarget();
void CleanupRenderTarget();

ID3D11BlendState* g_pBlendState = nullptr;
LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);
IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

const int BASE_OVERLAY_WIDTH = 680;
const int BASE_OVERLAY_HEIGHT = 480;
int overlayWidth = 0;
int overlayHeight = 0;

std::vector<std::string> availableModels;
std::vector<std::string> key_names;
std::vector<const char*> key_names_cstrs;

ID3D11ShaderResourceView* body_texture = nullptr;
ID3D11ShaderResourceView* g_menu_bg_texture = nullptr;
int g_menu_bg_w = 0;
int g_menu_bg_h = 0;
std::string g_menu_bg_loaded_path;
bool g_menu_bg_loaded_ok = false;

bool InitializeBlendState()
{
    D3D11_BLEND_DESC blendDesc;
    ZeroMemory(&blendDesc, sizeof(blendDesc));

    blendDesc.AlphaToCoverageEnable = FALSE;
    blendDesc.RenderTarget[0].BlendEnable = TRUE;
    blendDesc.RenderTarget[0].SrcBlend = D3D11_BLEND_SRC_ALPHA;
    blendDesc.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    blendDesc.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
    blendDesc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
    blendDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ZERO;
    blendDesc.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
    blendDesc.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;

    HRESULT hr = g_pd3dDevice->CreateBlendState(&blendDesc, &g_pBlendState);
    if (FAILED(hr))
    {
        return false;
    }

    float blendFactor[4] = { 0.f, 0.f, 0.f, 0.f };
    g_pd3dDeviceContext->OMSetBlendState(g_pBlendState, blendFactor, 0xffffffff);

    return true;
}

bool CreateDeviceD3D(HWND hWnd)
{
    DXGI_SWAP_CHAIN_DESC sd;
    ZeroMemory(&sd, sizeof(sd));
    sd.BufferCount = 2;
    sd.BufferDesc.Width = overlayWidth;
    sd.BufferDesc.Height = overlayHeight;
    sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.BufferDesc.RefreshRate.Numerator = 0;
    sd.BufferDesc.RefreshRate.Denominator = 0;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.OutputWindow = hWnd;
    sd.SampleDesc.Count = 1;
    sd.SampleDesc.Quality = 0;
    sd.Windowed = TRUE;
    sd.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;
    sd.Flags = DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH;

    UINT createDeviceFlags = 0;

    D3D_FEATURE_LEVEL featureLevel;
    const D3D_FEATURE_LEVEL featureLevelArray[2] =
    {
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_0,
    };

    HRESULT res = D3D11CreateDeviceAndSwapChain(NULL,
        D3D_DRIVER_TYPE_HARDWARE,
        NULL,
        createDeviceFlags,
        featureLevelArray,
        2,
        D3D11_SDK_VERSION,
        &sd,
        &g_pSwapChain,
        &g_pd3dDevice,
        &featureLevel,
        &g_pd3dDeviceContext);
    if (res != S_OK)
        return false;

    if (!InitializeBlendState())
        return false;

    CreateRenderTarget();
    return true;
}

void CreateRenderTarget()
{
    ID3D11Texture2D* pBackBuffer = NULL;
    g_pSwapChain->GetBuffer(0, IID_PPV_ARGS(&pBackBuffer));
    g_pd3dDevice->CreateRenderTargetView(pBackBuffer, NULL, &g_mainRenderTargetView);
    pBackBuffer->Release();
}

void CleanupRenderTarget()
{
    if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = NULL; }
}

void CleanupDeviceD3D()
{
    CleanupRenderTarget();
    if (g_menu_bg_texture) { g_menu_bg_texture->Release(); g_menu_bg_texture = nullptr; }
    g_menu_bg_w = 0;
    g_menu_bg_h = 0;
    g_menu_bg_loaded_path.clear();
    g_menu_bg_loaded_ok = false;
    if (g_pSwapChain) { g_pSwapChain->Release(); g_pSwapChain = NULL; }
    if (g_pd3dDeviceContext) { g_pd3dDeviceContext->Release(); g_pd3dDeviceContext = NULL; }
    if (g_pd3dDevice) { g_pd3dDevice->Release(); g_pd3dDevice = NULL; }
    if (g_pBlendState) { g_pBlendState->Release(); g_pBlendState = nullptr; }
}

LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    if (ImGui_ImplWin32_WndProcHandler(hWnd, msg, wParam, lParam))
        return true;

    switch (msg)
    {
    case WM_SIZE:
        if (g_pd3dDevice != NULL && wParam != SIZE_MINIMIZED)
        {
            RECT rect;
            GetWindowRect(hWnd, &rect);
            UINT width = rect.right - rect.left;
            UINT height = rect.bottom - rect.top;

            CleanupRenderTarget();
            g_pSwapChain->ResizeBuffers(0, width, height, DXGI_FORMAT_UNKNOWN, 0);
            CreateRenderTarget();
        }
        return 0;
    case WM_DESTROY:
        shouldExit = true;
        ::PostQuitMessage(0);
        return 0;
    default:
        return ::DefWindowProc(hWnd, msg, wParam, lParam);
    }
}

void SetupImGui()
{
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();

    ImGuiIO& io = ImGui::GetIO();
    io.FontGlobalScale = config.overlay_ui_scale;

    // Merge Windows icon font into the default ImGui font for sidebar icons.
    io.Fonts->Clear();
    io.Fonts->AddFontDefault();
    ImFontConfig icon_cfg{};
    icon_cfg.MergeMode = true;
    icon_cfg.PixelSnapH = true;
    static const ImWchar icon_ranges[] = { 0xE700, 0xF8FF, 0 };
    ImFont* icon_font = io.Fonts->AddFontFromFileTTF("C:\\Windows\\Fonts\\segmdl2.ttf", 17.0f, &icon_cfg, icon_ranges);
    if (!icon_font)
    {
        io.Fonts->AddFontFromFileTTF("C:\\Windows\\Fonts\\Segoe Fluent Icons.ttf", 17.0f, &icon_cfg, icon_ranges);
    }

    ImGui_ImplWin32_Init(g_hwnd);
    ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);

    ImGui::StyleColorsDark();
    OverlayTheme_LoadAndApply("ui_theme.ini");

    load_body_texture();
}

bool CreateOverlayWindow()
{
    overlayWidth = static_cast<int>(BASE_OVERLAY_WIDTH * config.overlay_ui_scale);
    overlayHeight = static_cast<int>(BASE_OVERLAY_HEIGHT * config.overlay_ui_scale);

    WNDCLASSEX wc = { sizeof(WNDCLASSEX), CS_CLASSDC, WndProc, 0L, 0L,
                      GetModuleHandle(NULL), NULL, NULL, NULL, NULL,
                      _T("Edge"), NULL };
    ::RegisterClassEx(&wc);

    g_hwnd = ::CreateWindowEx(
        WS_EX_TOPMOST | WS_EX_LAYERED,
        wc.lpszClassName, _T("Chrome"),
        WS_POPUP, 0, 0, overlayWidth, overlayHeight,
        NULL, NULL, wc.hInstance, NULL);

    if (g_hwnd == NULL)
        return false;

#ifndef WDA_EXCLUDEFROMCAPTURE
#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#endif
    // Prevent recursive self-capture in debug view.
    SetWindowDisplayAffinity(g_hwnd, WDA_EXCLUDEFROMCAPTURE);
    
    if (config.overlay_opacity <= 20)
    {
        config.overlay_opacity = 20;
        config.saveConfig("config.ini");
    }

    if (config.overlay_opacity >= 256)
    {
        config.overlay_opacity = 255;
        config.saveConfig("config.ini");
    }

    BYTE opacity = config.overlay_opacity;

    SetLayeredWindowAttributes(g_hwnd, 0, opacity, LWA_ALPHA);

    if (!CreateDeviceD3D(g_hwnd))
    {
        CleanupDeviceD3D();
        ::UnregisterClass(wc.lpszClassName, wc.hInstance);
        return false;
    }

    return true;
}

void OverlayThread()
{
    if (!CreateOverlayWindow())
    {
        std::cout << "[Overlay] Can't create overlay window!" << std::endl;
        return;
    }

    SetupImGui();

    bool show_overlay = false;
    int prev_opacity = config.overlay_opacity;

    for (const auto& pair : KeyCodes::key_code_map)
    {
        key_names.push_back(pair.first);
    }
    std::sort(key_names.begin(), key_names.end());

    key_names_cstrs.reserve(key_names.size());
    for (const auto& name : key_names)
    {
        key_names_cstrs.push_back(name.c_str());
    }

    std::vector<std::string> availableModels = getAvailableModels();

    MSG msg;
    ZeroMemory(&msg, sizeof(msg));
    while (!shouldExit)
    {
        while (::PeekMessage(&msg, NULL, 0U, 0U, PM_REMOVE))
        {
            ::TranslateMessage(&msg);
            ::DispatchMessage(&msg);
            if (msg.message == WM_QUIT)
            {
                shouldExit = true;
                return;
            }
        }

        if (isAnyKeyPressed(config.button_open_overlay) & 0x1)
        {
            show_overlay = !show_overlay;

            if (show_overlay)
            {
                ShowWindow(g_hwnd, SW_SHOW);
                SetForegroundWindow(g_hwnd);
            }
            else
            {
                ShowWindow(g_hwnd, SW_HIDE);
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(200));
        }

        if (show_overlay)
        {
            ImGui_ImplDX11_NewFrame();
            ImGui_ImplWin32_NewFrame();
            ImGui::NewFrame();

            ImGui::SetNextWindowPos(ImVec2(0, 0));
            ImGui::SetNextWindowSize(ImVec2((float)overlayWidth, (float)overlayHeight));

            ImGui::Begin(
                "Options",
                &show_overlay,
                ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoTitleBar |
                ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse);
            {
                std::lock_guard<std::mutex> lock(configMutex);
                const bool want_bg = OverlayUI::g_menu_bg_enabled && !OverlayUI::g_menu_bg_path.empty();
                if (!want_bg)
                {
                    if (g_menu_bg_texture)
                    {
                        g_menu_bg_texture->Release();
                        g_menu_bg_texture = nullptr;
                    }
                    g_menu_bg_loaded_path.clear();
                    g_menu_bg_loaded_ok = false;
                    g_menu_bg_w = 0;
                    g_menu_bg_h = 0;
                }
                else if (g_menu_bg_loaded_path != OverlayUI::g_menu_bg_path || !g_menu_bg_loaded_ok)
                {
                    if (g_menu_bg_texture)
                    {
                        g_menu_bg_texture->Release();
                        g_menu_bg_texture = nullptr;
                    }
                    g_menu_bg_w = 0;
                    g_menu_bg_h = 0;
                    g_menu_bg_loaded_ok = LoadTextureFromFile(
                        OverlayUI::g_menu_bg_path.c_str(),
                        g_pd3dDevice,
                        &g_menu_bg_texture,
                        &g_menu_bg_w,
                        &g_menu_bg_h);
                    g_menu_bg_loaded_path = OverlayUI::g_menu_bg_path;
                }

                if (g_menu_bg_texture && g_menu_bg_loaded_ok)
                {
                    ImDrawList* bg = ImGui::GetWindowDrawList();
                    ImVec2 wp = ImGui::GetWindowPos();
                    ImVec2 ws = ImGui::GetWindowSize();
                    const float a = (std::clamp)(OverlayUI::g_menu_bg_opacity, 0.02f, 1.0f);
                    bg->AddImage(
                        (ImTextureID)g_menu_bg_texture,
                        wp,
                        ImVec2(wp.x + ws.x, wp.y + ws.y),
                        ImVec2(0, 0),
                        ImVec2(1, 1),
                        IM_COL32(255, 255, 255, (int)(a * 255.0f)));
                }

                static int selected_tab = 0;
                if (OverlayUI::g_nav_width < 120.0f)
                    OverlayUI::g_nav_width = 172.0f;
                const float nav_width = OverlayUI::g_nav_width * config.overlay_ui_scale;

                ImGui::BeginChild("left_nav", ImVec2(nav_width, 0), true, ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse);
                ImGui::Text("NAVIGATION");
                ImGui::Separator();

                enum class NavIcon
                {
                    Camera, Target, Layers, Mouse, Brain, Gamepad, Eye, Chart, Bug, Cube
                };
                struct NavItem { NavIcon icon; const char* label; };
                static const NavItem kItems[] = {
                    { NavIcon::Camera, "Capture" },
                    { NavIcon::Target, "Target" },
                    { NavIcon::Layers, "Classes" },
                    { NavIcon::Mouse, "Mouse" },
                    { NavIcon::Brain, "AI" },
                    { NavIcon::Gamepad, "Buttons" },
                    { NavIcon::Eye, "Overlay" },
                    { NavIcon::Eye, "Game Overlay" },
                    { NavIcon::Chart, "Stats" },
                    { NavIcon::Bug, "Debug" },
                    { NavIcon::Cube, "Components" },
                };

                auto draw_nav_icon = [](ImDrawList* dl, NavIcon icon, const ImVec2& p, float s, ImU32 col)
                {
                    const float t = 1.7f;
                    const float r = s * 0.5f;
                    const float cx = p.x + r;
                    const float cy = p.y + r;
                    switch (icon)
                    {
                    case NavIcon::Camera:
                        dl->AddRect(ImVec2(p.x + s * 0.12f, p.y + s * 0.28f), ImVec2(p.x + s * 0.88f, p.y + s * 0.80f), col, 3.0f, 0, t);
                        dl->AddCircle(ImVec2(cx, p.y + s * 0.54f), s * 0.14f, col, 0, t);
                        dl->AddRect(ImVec2(p.x + s * 0.26f, p.y + s * 0.16f), ImVec2(p.x + s * 0.44f, p.y + s * 0.30f), col, 2.0f, 0, t);
                        break;
                    case NavIcon::Target:
                        dl->AddCircle(ImVec2(cx, cy), s * 0.36f, col, 0, t);
                        dl->AddCircle(ImVec2(cx, cy), s * 0.16f, col, 0, t);
                        dl->AddCircleFilled(ImVec2(cx, cy), s * 0.04f, col);
                        break;
                    case NavIcon::Layers:
                        for (int i = 0; i < 3; ++i)
                        {
                            float y = p.y + s * (0.22f + i * 0.22f);
                            ImVec2 pts[4] = {
                                ImVec2(cx, y),
                                ImVec2(p.x + s * 0.86f, y + s * 0.10f),
                                ImVec2(cx, y + s * 0.20f),
                                ImVec2(p.x + s * 0.14f, y + s * 0.10f)
                            };
                            dl->AddPolyline(pts, 4, col, true, t);
                        }
                        break;
                    case NavIcon::Mouse:
                        dl->AddRect(ImVec2(p.x + s * 0.30f, p.y + s * 0.14f), ImVec2(p.x + s * 0.70f, p.y + s * 0.86f), col, 6.0f, 0, t);
                        dl->AddLine(ImVec2(cx, p.y + s * 0.20f), ImVec2(cx, p.y + s * 0.44f), col, t);
                        dl->AddCircleFilled(ImVec2(cx, p.y + s * 0.30f), s * 0.03f, col);
                        break;
                    case NavIcon::Brain:
                        dl->AddCircle(ImVec2(p.x + s * 0.38f, p.y + s * 0.40f), s * 0.16f, col, 0, t);
                        dl->AddCircle(ImVec2(p.x + s * 0.62f, p.y + s * 0.40f), s * 0.16f, col, 0, t);
                        dl->AddCircle(ImVec2(p.x + s * 0.38f, p.y + s * 0.64f), s * 0.16f, col, 0, t);
                        dl->AddCircle(ImVec2(p.x + s * 0.62f, p.y + s * 0.64f), s * 0.16f, col, 0, t);
                        dl->AddLine(ImVec2(cx, p.y + s * 0.22f), ImVec2(cx, p.y + s * 0.82f), col, t);
                        break;
                    case NavIcon::Gamepad:
                        dl->AddRect(ImVec2(p.x + s * 0.16f, p.y + s * 0.36f), ImVec2(p.x + s * 0.84f, p.y + s * 0.78f), col, 5.0f, 0, t);
                        dl->AddLine(ImVec2(p.x + s * 0.30f, p.y + s * 0.56f), ImVec2(p.x + s * 0.42f, p.y + s * 0.56f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.36f, p.y + s * 0.50f), ImVec2(p.x + s * 0.36f, p.y + s * 0.62f), col, t);
                        dl->AddCircle(ImVec2(p.x + s * 0.64f, p.y + s * 0.56f), s * 0.04f, col, 0, t);
                        dl->AddCircle(ImVec2(p.x + s * 0.74f, p.y + s * 0.56f), s * 0.04f, col, 0, t);
                        break;
                    case NavIcon::Eye:
                        dl->AddBezierCubic(ImVec2(p.x + s * 0.14f, cy), ImVec2(p.x + s * 0.30f, p.y + s * 0.20f), ImVec2(p.x + s * 0.70f, p.y + s * 0.20f), ImVec2(p.x + s * 0.86f, cy), col, t);
                        dl->AddBezierCubic(ImVec2(p.x + s * 0.14f, cy), ImVec2(p.x + s * 0.30f, p.y + s * 0.80f), ImVec2(p.x + s * 0.70f, p.y + s * 0.80f), ImVec2(p.x + s * 0.86f, cy), col, t);
                        dl->AddCircle(ImVec2(cx, cy), s * 0.10f, col, 0, t);
                        break;
                    case NavIcon::Chart:
                        dl->AddLine(ImVec2(p.x + s * 0.16f, p.y + s * 0.80f), ImVec2(p.x + s * 0.86f, p.y + s * 0.80f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.16f, p.y + s * 0.24f), ImVec2(p.x + s * 0.16f, p.y + s * 0.80f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.32f, p.y + s * 0.80f), ImVec2(p.x + s * 0.32f, p.y + s * 0.52f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.50f, p.y + s * 0.80f), ImVec2(p.x + s * 0.50f, p.y + s * 0.36f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.68f, p.y + s * 0.80f), ImVec2(p.x + s * 0.68f, p.y + s * 0.60f), col, t);
                        break;
                    case NavIcon::Bug:
                        dl->AddCircle(ImVec2(cx, p.y + s * 0.54f), s * 0.20f, col, 0, t);
                        dl->AddCircle(ImVec2(cx, p.y + s * 0.30f), s * 0.10f, col, 0, t);
                        dl->AddLine(ImVec2(p.x + s * 0.26f, p.y + s * 0.50f), ImVec2(p.x + s * 0.12f, p.y + s * 0.44f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.26f, p.y + s * 0.62f), ImVec2(p.x + s * 0.12f, p.y + s * 0.68f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.74f, p.y + s * 0.50f), ImVec2(p.x + s * 0.88f, p.y + s * 0.44f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.74f, p.y + s * 0.62f), ImVec2(p.x + s * 0.88f, p.y + s * 0.68f), col, t);
                        break;
                    case NavIcon::Cube:
                    {
                        ImVec2 pts[6] = {
                            ImVec2(cx, p.y + s * 0.16f),
                            ImVec2(p.x + s * 0.80f, p.y + s * 0.30f),
                            ImVec2(p.x + s * 0.80f, p.y + s * 0.68f),
                            ImVec2(cx, p.y + s * 0.84f),
                            ImVec2(p.x + s * 0.20f, p.y + s * 0.68f),
                            ImVec2(p.x + s * 0.20f, p.y + s * 0.30f)
                        };
                        dl->AddPolyline(pts, 6, col, true, t);
                        dl->AddLine(ImVec2(cx, p.y + s * 0.16f), ImVec2(cx, p.y + s * 0.52f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.20f, p.y + s * 0.30f), ImVec2(cx, p.y + s * 0.52f), col, t);
                        dl->AddLine(ImVec2(p.x + s * 0.80f, p.y + s * 0.30f), ImVec2(cx, p.y + s * 0.52f), col, t);
                        break;
                    }
                    }
                };

                for (int i = 0; i < IM_ARRAYSIZE(kItems); ++i)
                {
                    const bool active = (selected_tab == i);
                    if (active)
                    {
                        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.22f, 0.29f, 0.38f, 0.55f));
                        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.25f, 0.33f, 0.43f, 0.70f));
                        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.28f, 0.36f, 0.47f, 0.80f));
                    }
                    else
                    {
                        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.00f, 0.00f, 0.00f, 0.00f));
                        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.20f, 0.24f, 0.30f, 0.35f));
                        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.22f, 0.28f, 0.36f, 0.50f));
                    }

                    std::string title = std::string("      ") + kItems[i].label;
                    if (ImGui::Button(title.c_str(), ImVec2(-1.0f, 34.0f * config.overlay_ui_scale)))
                        selected_tab = i;
                    ImVec2 rmin = ImGui::GetItemRectMin();
                    float ih = ImGui::GetItemRectSize().y;
                    ImU32 icol = active ? IM_COL32(248, 248, 248, 255) : IM_COL32(220, 220, 220, 245);
                    ImVec2 ipos(rmin.x + 8.0f * config.overlay_ui_scale, rmin.y + (ih - 16.0f * config.overlay_ui_scale) * 0.5f);
                    draw_nav_icon(ImGui::GetWindowDrawList(), kItems[i].icon, ipos, 16.0f * config.overlay_ui_scale, icol);
                    ImGui::PopStyleColor(3);
                }
                ImGui::EndChild();

                ImGui::SameLine();
                ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.16f, 0.19f, 0.24f, 0.90f));
                ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.25f, 0.31f, 0.40f, 1.00f));
                ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.25f, 0.31f, 0.40f, 1.00f));
                ImGui::Button("##nav_splitter", ImVec2(6.0f, -1.0f));
                ImGui::PopStyleColor(3);
                if (ImGui::IsItemActive())
                {
                    OverlayUI::g_nav_width += ImGui::GetIO().MouseDelta.x / (std::max)(0.25f, config.overlay_ui_scale);
                    OverlayUI::g_nav_width = (std::clamp)(OverlayUI::g_nav_width, 120.0f, 360.0f);
                    OverlayTheme_Save("ui_theme.ini");
                }

                ImGui::SameLine();
                ImGui::BeginChild(
                    "right_panel",
                    ImVec2(0, 0),
                    false,
                    ImGuiWindowFlags_None);
                switch (selected_tab)
                {
                case 0: draw_capture_settings(); break;
                case 1: draw_target(); break;
                case 2: draw_classes(); break;
                case 3: draw_mouse(); break;
                case 4: draw_ai(); break;
                case 5: draw_buttons(); break;
                case 6: draw_overlay(); break;
                case 7: draw_game_overlay_settings(); break;
                case 8: draw_stats(); break;
                case 9: draw_debug(); break;
                case 10: draw_components(); break;
                default: draw_capture_settings(); break;
                }
                ImGui::EndChild();

                if (prev_opacity != config.overlay_opacity)
                {
                    BYTE opacity = config.overlay_opacity;
                    SetLayeredWindowAttributes(g_hwnd, 0, opacity, LWA_ALPHA);
                    OverlayConfig_MarkDirty();
                    prev_opacity = config.overlay_opacity;
                }

                // Visible resize handles (right edge, bottom edge, and corner).
                const float edge_thickness = 8.0f;
                const float grip_size = 24.0f;
                const ImVec2 wpos = ImGui::GetWindowPos();
                const ImVec2 wsize = ImGui::GetWindowSize();
                ImDrawList* wnd_dl = ImGui::GetWindowDrawList();

                // Right edge handle.
                ImGui::SetCursorScreenPos(ImVec2(wpos.x + wsize.x - edge_thickness, wpos.y));
                ImGui::InvisibleButton("##overlay_resize_right", ImVec2(edge_thickness, wsize.y - grip_size));
                if (ImGui::IsItemHovered() || ImGui::IsItemActive())
                    ImGui::SetMouseCursor(ImGuiMouseCursor_ResizeEW);
                if (ImGui::IsItemActive())
                {
                    overlayWidth = (std::max)(520, overlayWidth + static_cast<int>(ImGui::GetIO().MouseDelta.x));
                    SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
                }

                // Bottom edge handle.
                ImGui::SetCursorScreenPos(ImVec2(wpos.x, wpos.y + wsize.y - edge_thickness));
                ImGui::InvisibleButton("##overlay_resize_bottom", ImVec2(wsize.x - grip_size, edge_thickness));
                if (ImGui::IsItemHovered() || ImGui::IsItemActive())
                    ImGui::SetMouseCursor(ImGuiMouseCursor_ResizeNS);
                if (ImGui::IsItemActive())
                {
                    overlayHeight = (std::max)(360, overlayHeight + static_cast<int>(ImGui::GetIO().MouseDelta.y));
                    SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
                }

                // Bottom-right corner grip.
                ImVec2 grip_pos(wpos.x + wsize.x - grip_size, wpos.y + wsize.y - grip_size);
                ImGui::SetCursorScreenPos(grip_pos);
                ImGui::InvisibleButton("##overlay_resize_grip", ImVec2(grip_size, grip_size));
                const bool grip_hot = ImGui::IsItemHovered() || ImGui::IsItemActive();
                if (grip_hot)
                    ImGui::SetMouseCursor(ImGuiMouseCursor_ResizeNWSE);
                const ImU32 grip_col = grip_hot ? IM_COL32(190, 220, 255, 240) : IM_COL32(145, 170, 205, 190);
                wnd_dl->AddLine(
                    ImVec2(grip_pos.x + 6.0f, grip_pos.y + grip_size - 4.0f),
                    ImVec2(grip_pos.x + grip_size - 4.0f, grip_pos.y + 6.0f),
                    grip_col, 1.8f);
                wnd_dl->AddLine(
                    ImVec2(grip_pos.x + 11.0f, grip_pos.y + grip_size - 4.0f),
                    ImVec2(grip_pos.x + grip_size - 4.0f, grip_pos.y + 11.0f),
                    grip_col, 1.8f);
                if (ImGui::IsItemActive())
                {
                    overlayWidth = (std::max)(520, overlayWidth + static_cast<int>(ImGui::GetIO().MouseDelta.x));
                    overlayHeight = (std::max)(360, overlayHeight + static_cast<int>(ImGui::GetIO().MouseDelta.y));
                    SetWindowPos(g_hwnd, NULL, 0, 0, overlayWidth, overlayHeight, SWP_NOMOVE | SWP_NOZORDER);
                }
            }

            ImGui::End();
            ImGui::Render();

            const float clear_color_with_alpha[4] = { 0.0f, 0.0f, 0.0f, 0.0f };
            g_pd3dDeviceContext->OMSetRenderTargets(1, &g_mainRenderTargetView, NULL);
            g_pd3dDeviceContext->ClearRenderTargetView(g_mainRenderTargetView, clear_color_with_alpha);
            ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());

            HRESULT result = g_pSwapChain->Present(0, 0);

            if (result == DXGI_STATUS_OCCLUDED || result == DXGI_ERROR_ACCESS_LOST)
            {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            OverlayConfig_FlushIfDue(220);
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        else
        {
            OverlayConfig_FlushIfDue(220);
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }

    OverlayConfig_FlushNow();

    release_body_texture();

    ImGui_ImplDX11_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();

    CleanupDeviceD3D();
    ::DestroyWindow(g_hwnd);
    ::UnregisterClass(_T("Edge"), GetModuleHandle(NULL));
}

int APIENTRY _tWinMain(_In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPTSTR    lpCmdLine,
    _In_ int       nCmdShow)
{
    std::thread overlay(OverlayThread);
    overlay.join();
    return 0;
}

