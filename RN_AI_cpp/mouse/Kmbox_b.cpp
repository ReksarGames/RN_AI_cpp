/*  KmboxConnection.cpp  */
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <windows.h>
#include <iostream>
#include <thread>
#include <mutex>

#include "Kmbox_b.h"
#include "config.h"
#include "rn_ai_cpp.h"

/* ---------------- Makcu-????????? ---------------- */
static const uint32_t BOOT_BAUD = 115200;   // ??? ???????????
static const uint32_t WORK_BAUD = 4000000;  // ??????? 4 ????/?

/* ????????? ????? ????? ???????? */
static const uint8_t  BAUD_CHANGE_CMD[9] =
{ 0xDE,0xAD,0x05,0x00,0xA5,0x00,0x09,0x3D,0x00 };

/* ------------------------------------------------- */

KmboxConnection::KmboxConnection(const std::string& port, unsigned int /*baud_rate*/)
    : is_open_(false),
    listening_(false),
    aiming_active(false),
    shooting_active(false),
    zooming_active(false),
    side1_active(false),
    side2_active(false),
    left_active(false),
    right_active(false),
    middle_active(false)
{
    try {
        /* 1. ????????? ???? @115 200 */
        serial_.setPort(port);
        serial_.setBaudrate(BOOT_BAUD);
        serial_.open();
        if (!serial_.isOpen())
            throw std::runtime_error("open failed");

        /* 2. ???????? ????? — MCU ??????????????? @4 ???? */
        serial_.write(BAUD_CHANGE_CMD, sizeof(BAUD_CHANGE_CMD));
        serial_.close();
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        /* 3. ????????? ?????? @4 ???? */
        serial_.setBaudrate(WORK_BAUD);
        serial_.open();
        if (!serial_.isOpen())
            throw std::runtime_error("re-open @4M failed");

        is_open_ = true;
        std::cout << "[Makcu] Connected @4 Mbps on " << port << '\n';

        /* 4. ??????? echo ? ???????? ????? ?????? */
        sendCommand("km.echo(0)");
        sendCommand("km.buttons(1)");

        startListening();
    }
    catch (const std::exception& e) {
        std::cerr << "[Makcu] Error: " << e.what() << '\n';
    }
}

KmboxConnection::~KmboxConnection()
{
    listening_ = false;
    if (serial_.isOpen()) {
        try { serial_.close(); }
        catch (...) {}
    }
    if (listening_thread_.joinable())
        listening_thread_.join();
    is_open_ = false;
}

/* ------------------------------------------------ */

bool KmboxConnection::isOpen() const { return is_open_; }

void KmboxConnection::write(const std::string& data)
{
    std::lock_guard<std::mutex> lock(write_mutex_);
    if (!is_open_) return;
    try { serial_.write(data); }
    catch (...) { is_open_ = false; }
}

std::string KmboxConnection::read()
{
    if (!is_open_) return {};

    try {
        std::string res = serial_.readline(65536, "\n");
        std::cout << res;
        return res;
    }
    catch (...) { is_open_ = false; }
    return {};
}

/* --- ??????? km.* ---------------------------------------------------- */

void KmboxConnection::move(int x, int y)
{
    if (!is_open_) return;
    write("km.move(" + std::to_string(x) + "," + std::to_string(y) + ")\r\n");
}

void KmboxConnection::click(int button /*=0*/)
{
    sendCommand("km.click(" + std::to_string(button) + ')');
}

void KmboxConnection::press(int /*button*/) { sendCommand("km.left(1)"); }
void KmboxConnection::release(int /*button*/) { sendCommand("km.left(0)"); }

void KmboxConnection::start_boot()
{
    write("\x03\x03");
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    write("exec(open('boot.py').read(),globals())\r\n");
}

void KmboxConnection::reboot()
{
    write("\x03\x03");
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    write("km.reboot()");
}

void KmboxConnection::send_stop() { write("\x03\x03"); }

void KmboxConnection::sendCommand(const std::string& cmd) { write(cmd + "\r\n"); }

std::vector<int> KmboxConnection::splitValue(int value) { return {}; }

/* --------------------------- ????????? -------------------------- */

void KmboxConnection::startListening()
{
    listening_ = true;
    if (listening_thread_.joinable())
        listening_thread_.join();
    listening_thread_ = std::thread(&KmboxConnection::listeningThreadFunc, this);
}

void KmboxConnection::listeningThreadFunc()
{
    // allowed bits: 0x01 (LMB), 0x02 (RMB), 0x10 (side2)
    constexpr uint8_t allowed_mask = 0x01 | 0x02 | 0x10;

    while (listening_ && is_open_) {
        try {
            if (!serial_.available()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                continue;
            }
            uint8_t b = 0;
            serial_.read(&b, 1);

            // drop byte if it contains unexpected bits
            if (b & ~allowed_mask)
                continue;

            // update state flags
            shooting_active = (b & 0x01) != 0; // LMB
            zooming_active = (b & 0x02) != 0;  // RMB
            aiming_active = (b & 0x10) != 0;   // side2

            left_active = shooting_active;
            right_active = zooming_active;
            middle_active = false;
            side1_active = false;
            side2_active = aiming_active;

            shooting.store(shooting_active);
            aiming.store(aiming_active);

            // debug output
            std::cout << "LMB: " << (shooting_active ? "PRESS" : "release")
                << " | SIDE: " << (aiming_active ? "PRESS" : "release")
                << '\n';
        }
        catch (...) { is_open_ = false; break; }
    }
}

/* ---------- ?????? ?????? ????? (???????? ??? ?????????) ------------- */
void KmboxConnection::processIncomingLine(const std::string& line)
{
    try {
        if (line.rfind("BD:", 0) == 0) {
            int btnId = std::stoi(line.substr(3));
            switch (btnId) {
            case 1: shooting_active = true;  shooting.store(true);  break;
            case 2: aiming_active = true;  aiming.store(true);    break;
            }
        }
        else if (line.rfind("BU:", 0) == 0) {
            int btnId = std::stoi(line.substr(3));
            switch (btnId) {
            case 1: shooting_active = false; shooting.store(false); break;
            case 2: aiming_active = false; aiming.store(false);   break;
            }
        }
    }
    catch (const std::exception& e) {
        std::cerr << "[Kmbox_b] Error processing line '" << line
            << "': " << e.what() << '\n';
    }
}
