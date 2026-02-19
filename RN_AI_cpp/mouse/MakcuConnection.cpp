#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <windows.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "MakcuConnection.h"
#include "config.h"
#include "rn_ai_cpp.h"

namespace {
std::mutex g_makcu_state_log_mutex;

void logMakcuButtons(const char* source, const MakcuConnection& connection, int raw_value = -1)
{
    std::lock_guard<std::mutex> lock(g_makcu_state_log_mutex);
    std::cout << "[Makcu][" << source << "]";
    if (raw_value >= 0) {
        std::cout << " raw=" << raw_value;
    }
    std::cout
        << " L=" << (connection.left_active ? 1 : 0)
        << " R=" << (connection.right_active ? 1 : 0)
        << " M=" << (connection.middle_active ? 1 : 0)
        << " S1=" << (connection.side1_active ? 1 : 0)
        << " S2=" << (connection.side2_active ? 1 : 0)
        << " shoot=" << (connection.shooting_active ? 1 : 0)
        << " aim=" << (connection.aiming_active ? 1 : 0)
        << " zoom=" << (connection.zooming_active ? 1 : 0)
        << " trig=" << (connection.triggerbot_active ? 1 : 0)
        << std::endl;
}
} // namespace

#if RN_MAKCU_SDK_AVAILABLE

MakcuConnection::MakcuConnection(const std::string& port, unsigned int baud_rate)
    : is_open_(false)
    , aiming_active(false)
    , shooting_active(false)
    , zooming_active(false)
    , triggerbot_active(false)
    , side1_active(false)
    , side2_active(false)
    , left_active(false)
    , right_active(false)
    , middle_active(false)
{
    try
    {
        device_.setMouseButtonCallback([this](makcu::MouseButton button, bool pressed) {
            onButtonCallback(button, pressed);
        });

        device_.enableButtonMonitoring(true);

        if (device_.connect(port))
        {
            if (baud_rate > 0)
            {
                if (!device_.setBaudRate(baud_rate, true))
                {
                    std::cerr << "[Makcu] Failed to set baud rate to " << baud_rate
                              << ", continuing with current baud rate." << std::endl;
                }
            }

            is_open_ = true;
            std::cout << "[Makcu] Connected! PORT: " << port << std::endl;
        }
        else
        {
            std::cerr << "[Makcu] Unable to connect to the port: " << port << std::endl;
        }
    }
    catch (const makcu::MakcuException& e)
    {
        std::cerr << "[Makcu] Error: " << e.what() << std::endl;
    }
    catch (const std::exception& e)
    {
        std::cerr << "[Makcu] Error: " << e.what() << std::endl;
    }
}

MakcuConnection::~MakcuConnection()
{
    try
    {
        device_.enableButtonMonitoring(false);
        device_.disconnect();
    }
    catch (...)
    {
    }
    is_open_ = false;
}

bool MakcuConnection::isOpen() const
{
    return is_open_ && device_.isConnected();
}

void MakcuConnection::write(const std::string&)
{
}

std::string MakcuConnection::read()
{
    return std::string();
}

void MakcuConnection::move(int x, int y)
{
    if (!isOpen())
        return;

    std::lock_guard<std::mutex> lock(write_mutex_);
    try
    {
        device_.mouseMove(x, y);
    }
    catch (...)
    {
        is_open_ = false;
    }
}

makcu::MouseButton MakcuConnection::toMouseButton(int button) const
{
    switch (button)
    {
    case 1: return makcu::MouseButton::RIGHT;
    case 2: return makcu::MouseButton::MIDDLE;
    case 3: return makcu::MouseButton::SIDE1;
    case 4: return makcu::MouseButton::SIDE2;
    case 0:
    default:
        return makcu::MouseButton::LEFT;
    }
}

void MakcuConnection::click(int button)
{
    if (!isOpen())
        return;

    std::lock_guard<std::mutex> lock(write_mutex_);
    try
    {
        device_.click(toMouseButton(button));
    }
    catch (...)
    {
        is_open_ = false;
    }
}

void MakcuConnection::press(int button)
{
    if (!isOpen())
        return;

    std::lock_guard<std::mutex> lock(write_mutex_);
    try
    {
        device_.mouseDown(toMouseButton(button));
    }
    catch (...)
    {
        is_open_ = false;
    }
}

void MakcuConnection::release(int button)
{
    if (!isOpen())
        return;

    std::lock_guard<std::mutex> lock(write_mutex_);
    try
    {
        device_.mouseUp(toMouseButton(button));
    }
    catch (...)
    {
        is_open_ = false;
    }
}

void MakcuConnection::start_boot()
{
}

void MakcuConnection::reboot()
{
}

void MakcuConnection::send_stop()
{
}

void MakcuConnection::onButtonCallback(makcu::MouseButton button, bool pressed)
{
    switch (button)
    {
    case makcu::MouseButton::LEFT:
        left_active = pressed;
        shooting_active = pressed;
        shooting.store(pressed);
        break;

    case makcu::MouseButton::RIGHT:
        right_active = pressed;
        zooming_active = pressed;
        zooming.store(pressed);
        break;

    case makcu::MouseButton::MIDDLE:
        middle_active = pressed;
        break;

    case makcu::MouseButton::SIDE1:
        side1_active = pressed;
        triggerbot_active = pressed;
        triggerbot_button.store(pressed);
        break;

    case makcu::MouseButton::SIDE2:
        side2_active = pressed;
        aiming_active = pressed;
        aiming.store(pressed);
        break;

    default:
        break;
    }

    logMakcuButtons("callback", *this, static_cast<int>(button));
}

#else

/* ---------- Serial fallback constants ---------------------------- */
static const uint32_t BOOT_BAUD = 115200;
static const uint32_t WORK_BAUD = 4000000;

static const uint8_t BAUD_CHANGE_CMD[9] =
{ 0xDE, 0xAD, 0x05, 0x00, 0xA5, 0x00, 0x09, 0x3D, 0x00 };

MakcuConnection::MakcuConnection(const std::string& port, unsigned int /*baud_rate*/)
    : is_open_(false)
    , listening_(false)
    , aiming_active(false)
    , shooting_active(false)
    , zooming_active(false)
    , triggerbot_active(false)
    , side1_active(false)
    , side2_active(false)
    , left_active(false)
    , right_active(false)
    , middle_active(false)
{
    std::cerr << "[Makcu] SDK header not found. Using serial fallback parser." << std::endl;

    try {
        serial_.setPort(port);
        serial_.setBaudrate(BOOT_BAUD);
        serial_.open();
        if (!serial_.isOpen())
            throw std::runtime_error("open failed");

        serial_.write(BAUD_CHANGE_CMD, sizeof(BAUD_CHANGE_CMD));
        serial_.close();
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        serial_.setBaudrate(WORK_BAUD);
        serial_.open();
        if (!serial_.isOpen())
            throw std::runtime_error("re-open @4M failed");

        is_open_ = true;
        std::cout << "[Makcu] Connected @4 Mbps on " << port << '\n';

        sendCommand("km.echo(0)");
        sendCommand("km.buttons(1)");

        startListening();
    }
    catch (const std::exception& e) {
        std::cerr << "[Makcu] Error: " << e.what() << '\n';
    }
}

MakcuConnection::~MakcuConnection()
{
    listening_ = false;
    if (serial_.isOpen()) {
        try { serial_.close(); } catch (...) {}
    }
    if (listening_thread_.joinable())
        listening_thread_.join();
    is_open_ = false;
}

bool MakcuConnection::isOpen() const { return is_open_; }

void MakcuConnection::write(const std::string& data)
{
    std::lock_guard<std::mutex> lock(write_mutex_);
    if (!is_open_) return;
    try { serial_.write(data); }
    catch (...) { is_open_ = false; }
}

std::string MakcuConnection::read()
{
    if (!is_open_)
        return std::string();

    std::string result;
    try
    {
        result = serial_.readline(65536, "\n");
    }
    catch (...)
    {
        is_open_ = false;
    }
    return result;
}

void MakcuConnection::move(int x, int y)
{
    if (!is_open_)
        return;

    std::string cmd = "km.move(" + std::to_string(x) + "," + std::to_string(y) + ")\r\n";
    write(cmd);
}

void MakcuConnection::click(int button)
{
    (void)button;
    sendCommand("km.click(0)");
}

void MakcuConnection::press(int button)
{
    (void)button;
    sendCommand("km.left(1)");
}

void MakcuConnection::release(int button)
{
    (void)button;
    sendCommand("km.left(0)");
}

void MakcuConnection::start_boot()
{
    write("\x03\x03");
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    write("exec(open('boot.py').read(),globals())\r\n");
}

void MakcuConnection::reboot()
{
    write("\x03\x03");
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    write("km.reboot()");
}

void MakcuConnection::send_stop()
{
    write("\x03\x03");
}

void MakcuConnection::sendCommand(const std::string& cmd) { write(cmd + "\r\n"); }
std::vector<int> MakcuConnection::splitValue(int) { return {}; }

void MakcuConnection::startListening()
{
    listening_ = true;
    if (listening_thread_.joinable())
        listening_thread_.join();

    listening_thread_ = std::thread(&MakcuConnection::listeningThreadFunc, this);
}

void MakcuConnection::listeningThreadFunc()
{
    constexpr uint8_t button_mask = 0x3F;
    auto popcount8 = [](uint8_t v) {
        v = (v & 0x55) + ((v >> 1) & 0x55);
        v = (v & 0x33) + ((v >> 2) & 0x33);
        return static_cast<int>((v + (v >> 4)) & 0x0F);
    };

    uint8_t last_buttons = 0;

    while (listening_ && is_open_) {
        try {
            if (!serial_.available()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                continue;
            }

            uint8_t b = 0;
            serial_.read(&b, 1);

            const uint8_t filtered = static_cast<uint8_t>(b & button_mask);
            const int bit_cnt = popcount8(filtered);
            const bool valid_empty = filtered == 0x00;
            const bool valid_single = (filtered <= 0x1F) && (bit_cnt == 1);

            if (valid_empty) {
                last_buttons = 0;
            }
            else if (valid_single) {
                last_buttons = filtered;
            }
            else {
                continue;
            }

            const uint8_t previous_buttons = static_cast<uint8_t>((left_active ? 0x01 : 0x00) |
                                                                   (right_active ? 0x02 : 0x00) |
                                                                   (middle_active ? 0x04 : 0x00) |
                                                                   (side1_active ? 0x08 : 0x00) |
                                                                   (side2_active ? 0x10 : 0x00));

            left_active = (last_buttons & 0x01) != 0;
            right_active = (last_buttons & 0x02) != 0;
            middle_active = (last_buttons & 0x04) != 0;
            side1_active = (last_buttons & 0x08) != 0;
            side2_active = (last_buttons & 0x10) != 0;

            shooting_active = left_active;
            aiming_active = side2_active;
            zooming_active = middle_active;
            triggerbot_active = side1_active;

            triggerbot_button.store(triggerbot_active);
            shooting.store(shooting_active);
            aiming.store(aiming_active);
            zooming.store(zooming_active);

            if (last_buttons != previous_buttons) {
                logMakcuButtons("serial", *this, static_cast<int>(b));
            }
        }
        catch (...) {
            is_open_ = false;
            break;
        }
    }
}

void MakcuConnection::processIncomingLine(const std::string&)
{
}

#endif