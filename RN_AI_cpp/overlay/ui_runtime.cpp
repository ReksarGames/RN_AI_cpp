#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include "ui_runtime.h"

namespace OverlayUI
{
bool g_show_descriptions = true;
float g_row_button_width = 22.0f;
float g_row_input_width = 54.0f;
float g_nav_width = 172.0f;
bool g_menu_bg_enabled = false;
float g_menu_bg_opacity = 0.22f;
std::string g_menu_bg_path = "ui_bg.png";
float g_overlay_fps_text_size = 19.0f;
float g_overlay_latency_text_size = 18.0f;
}
