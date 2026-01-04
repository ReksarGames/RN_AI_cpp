#include "udp_capture.h"
#include <iostream>
#include <vector>
#include <chrono>
#include <thread>

UDPCapture::UDPCapture(int width, int height, const std::string& ip, int port)
    : width_(width), height_(height), ip_(ip), port_(port), socket_(INVALID_SOCKET),
      is_connected_(false), should_stop_(false), received_frames_(0), dropped_frames_(0)
{
    // 初始化 Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
    {
        std::cerr << "[UDPCapture] WSAStartup failed" << std::endl;
        return;
    }
}

UDPCapture::~UDPCapture()
{
    Cleanup();
    WSACleanup();
}

bool UDPCapture::Initialize()
{
    // 創建 UDP socket
    socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (socket_ == INVALID_SOCKET)
    {
        std::cerr << "[UDPCapture] Failed to create socket: " << WSAGetLastError() << std::endl;
        return false;
    }

    // 設定 socket 選項
    int buffer_size = 1024 * 1024; // 1MB buffer
    if (setsockopt(socket_, SOL_SOCKET, SO_RCVBUF, (char*)&buffer_size, sizeof(buffer_size)) == SOCKET_ERROR)
    {
        std::cerr << "[UDPCapture] Failed to set receive buffer size: " << WSAGetLastError() << std::endl;
    }

    // 設定非阻塞模式
    u_long mode = 1;
    if (ioctlsocket(socket_, FIONBIO, &mode) == SOCKET_ERROR)
    {
        std::cerr << "[UDPCapture] Failed to set non-blocking mode: " << WSAGetLastError() << std::endl;
    }

    // 設定 server address
    memset(&server_addr_, 0, sizeof(server_addr_));
    server_addr_.sin_family = AF_INET;
    server_addr_.sin_port = htons(port_);
    
    if (inet_pton(AF_INET, ip_.c_str(), &server_addr_.sin_addr) <= 0)
    {
        std::cerr << "[UDPCapture] Invalid IP address: " << ip_ << std::endl;
        return false;
    }

    // 綁定到本地地址
    sockaddr_in local_addr;
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = INADDR_ANY;
    local_addr.sin_port = htons(port_);

    if (bind(socket_, (sockaddr*)&local_addr, sizeof(local_addr)) == SOCKET_ERROR)
    {
        std::cerr << "[UDPCapture] Failed to bind socket: " << WSAGetLastError() << std::endl;
        return false;
    }

    is_connected_ = true;
    should_stop_ = false;

    // 啟動接收線程
    receive_thread_ = std::thread(&UDPCapture::ReceiveThread, this);

    std::cout << "[UDPCapture] Initialized successfully on " << ip_ << ":" << port_ << std::endl;
    return true;
}

void UDPCapture::Cleanup()
{
    should_stop_ = true;
    is_connected_ = false;

    if (receive_thread_.joinable())
    {
        receive_thread_.join();
    }

    if (socket_ != INVALID_SOCKET)
    {
        closesocket(socket_);
        socket_ = INVALID_SOCKET;
    }
}

void UDPCapture::SetUDPParams(const std::string& ip, int port)
{
    if (ip_ != ip || port_ != port)
    {
        ip_ = ip;
        port_ = port;
        
        if (is_connected_)
        {
            Cleanup();
            Initialize();
        }
    }
}

cv::Mat UDPCapture::GetNextFrameCpu()
{
    std::lock_guard<std::mutex> lock(frame_mutex_);
    
    if (frame_queue_.empty())
    {
        return cv::Mat();
    }

    cv::Mat frame = frame_queue_.front();
    frame_queue_.pop();
    return frame;
}

void UDPCapture::ReceiveThread()
{
    std::vector<uint8_t> buffer(MAX_FRAME_SIZE);
    std::vector<uint8_t> frame_data;
    
    while (!should_stop_)
    {
        sockaddr_in from_addr;
        int from_len = sizeof(from_addr);
        
        int bytes_received = recvfrom(socket_, (char*)buffer.data(), buffer.size(), 0, 
                                    (sockaddr*)&from_addr, &from_len);
        
        if (bytes_received == SOCKET_ERROR)
        {
            int error = WSAGetLastError();
            if (error == WSAEWOULDBLOCK)
            {
                // 非阻塞模式，沒有數據可讀
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                continue;
            }
            else
            {
                std::cerr << "[UDPCapture] Receive error: " << error << std::endl;
                break;
            }
        }
        else if (bytes_received > 0)
        {
            // 將接收到的數據添加到 frame_data
            frame_data.insert(frame_data.end(), buffer.begin(), buffer.begin() + bytes_received);
            
            // 嘗試解析 MJPEG frame
            cv::Mat frame;
            if (ParseMJPEGFrame(frame_data, frame))
            {
                if (!frame.empty())
                {
                    // 調整 frame 大小
                    if (frame.cols != width_ || frame.rows != height_)
                    {
                        cv::resize(frame, frame, cv::Size(width_, height_));
                    }
                    
                    std::lock_guard<std::mutex> lock(frame_mutex_);
                    
                    // 限制隊列大小
                    while (frame_queue_.size() >= MAX_QUEUE_SIZE)
                    {
                        frame_queue_.pop();
                        dropped_frames_++;
                    }
                    
                    frame_queue_.push(frame.clone());
                    received_frames_++;
                }
                
                // 清空已處理的數據
                frame_data.clear();
            }
        }
    }
}

bool UDPCapture::ParseMJPEGFrame(const std::vector<uint8_t>& data, cv::Mat& frame)
{
    if (data.size() < 4)
        return false;

    // 查找 JPEG 標記
    size_t start_pos = 0;
    bool found_start = false;
    
    for (size_t i = 0; i < data.size() - 1; ++i)
    {
        if (data[i] == 0xFF && data[i + 1] == 0xD8) // JPEG start marker
        {
            start_pos = i;
            found_start = true;
            break;
        }
    }
    
    if (!found_start)
        return false;
    
    // 查找 JPEG 結束標記
    size_t end_pos = data.size();
    bool found_end = false;
    
    for (size_t i = start_pos + 2; i < data.size() - 1; ++i)
    {
        if (data[i] == 0xFF && data[i + 1] == 0xD9) // JPEG end marker
        {
            end_pos = i + 2;
            found_end = true;
            break;
        }
    }
    
    if (!found_end)
        return false;
    
    // 提取 JPEG 數據
    std::vector<uint8_t> jpeg_data(data.begin() + start_pos, data.begin() + end_pos);
    
    // 解碼 JPEG
    try
    {
        frame = cv::imdecode(jpeg_data, cv::IMREAD_COLOR);
        return !frame.empty();
    }
    catch (const cv::Exception& e)
    {
        std::cerr << "[UDPCapture] JPEG decode error: " << e.what() << std::endl;
        return false;
    }
}
