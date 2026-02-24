#ifndef UDP_CAPTURE_H
#define UDP_CAPTURE_H

#include "capture.h"
#include <opencv2/opencv.hpp>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <thread>
#include <atomic>
#include <mutex>
#include <queue>
#include <string>

#pragma comment(lib, "ws2_32.lib")

class UDPCapture : public IScreenCapture
{
public:
    UDPCapture(int width, int height, const std::string& ip = "127.0.0.1", int port = 1234);
    ~UDPCapture();

    cv::Mat GetNextFrameCpu() override;
    
    bool Initialize();
    void Cleanup();
    
    // 設定 UDP 接收參數
    void SetUDPParams(const std::string& ip, int port);
    
    // 獲取連接狀態
    bool IsConnected() const { return is_connected_.load(); }
    
    // 獲取統計信息
    int GetReceivedFrames() const { return received_frames_.load(); }
    int GetDroppedFrames() const { return dropped_frames_.load(); }

private:
    void ReceiveThread();
    bool ParseMJPEGFrame(const std::vector<uint8_t>& data, cv::Mat& frame);
    
    int width_;
    int height_;
    std::string ip_;
    int port_;
    
    SOCKET socket_;
    sockaddr_in server_addr_;
    
    std::atomic<bool> is_connected_;
    std::atomic<bool> should_stop_;
    std::atomic<int> received_frames_;
    std::atomic<int> dropped_frames_;
    
    std::thread receive_thread_;
    std::mutex frame_mutex_;
    std::queue<cv::Mat> frame_queue_;
    
    static const int MAX_FRAME_SIZE = 1024 * 1024; // 1MB
    static const int MAX_QUEUE_SIZE = 5;
};

#endif // UDP_CAPTURE_H
