#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <Windows.h>

#include <atomic>
#include <chrono>

#include "config_dirty.h"
#include "config.h"

extern Config config;

namespace
{
std::atomic<bool> g_config_dirty{ false };
std::chrono::steady_clock::time_point g_last_dirty_at = std::chrono::steady_clock::now();
}

void OverlayConfig_MarkDirty()
{
    g_last_dirty_at = std::chrono::steady_clock::now();
    g_config_dirty.store(true, std::memory_order_relaxed);
}

bool OverlayConfig_IsDirty()
{
    return g_config_dirty.load(std::memory_order_relaxed);
}

bool OverlayConfig_FlushIfDue(int debounceMs)
{
    if (!g_config_dirty.load(std::memory_order_relaxed))
        return false;

    const auto elapsed =
        std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - g_last_dirty_at).count();
    if (elapsed < debounceMs)
        return false;

    config.saveConfig();
    g_config_dirty.store(false, std::memory_order_relaxed);
    return true;
}

void OverlayConfig_FlushNow()
{
    if (!g_config_dirty.load(std::memory_order_relaxed))
        return;

    config.saveConfig();
    g_config_dirty.store(false, std::memory_order_relaxed);
}
