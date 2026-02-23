#ifndef MAKCU_CONNECTION_H
#define MAKCU_CONNECTION_H

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>

#if __has_include("Makcu.h")
#include "Makcu.h"
#define RN_MAKCU_SDK_AVAILABLE 1
#elif __has_include("../modules/makcu/include/makcu.h")
#include "../modules/makcu/include/makcu.h"
#define RN_MAKCU_SDK_AVAILABLE 1
#else
#define RN_MAKCU_SDK_AVAILABLE 0
#include <thread>
#include <vector>
#include "serial/serial.h"
#endif

class MakcuConnection
{
public:
    MakcuConnection(const std::string& port, unsigned int baud_rate);
    ~MakcuConnection();

    bool isOpen() const;

    void write(const std::string& data);
    std::string read();

    void click(int button);
    void press(int button);
    void release(int button);
    void move(int x, int y);

    void start_boot();
    void reboot();
    void send_stop();

    bool aiming_active;
    bool shooting_active;
    bool zooming_active;
    bool triggerbot_active;
    bool side1_active;
    bool side2_active;
    bool left_active;
    bool right_active;
    bool middle_active;

private:
#if RN_MAKCU_SDK_AVAILABLE
    void onButtonCallback(makcu::MouseButton button, bool pressed);
    makcu::MouseButton toMouseButton(int button) const;
    makcu::Device device_;
#else
    bool queryButtonStateBinary(uint8_t cmd, bool& pressed);
    bool readBinaryFrame(uint8_t expected_cmd, std::vector<uint8_t>& payload, int timeout_ms);
    void writeBinaryCommand(uint8_t cmd, const std::vector<uint8_t>& payload);

    void sendCommand(const std::string& command);
    std::vector<int> splitValue(int value);
    void startListening();
    void listeningThreadFunc();
    void processIncomingLine(const std::string& line);

    serial::Serial serial_;
    std::atomic<bool> listening_;
    std::thread listening_thread_;
#endif

    std::atomic<bool> is_open_;
    std::mutex write_mutex_;
};

#endif // MAKCU_CONNECTION_H
