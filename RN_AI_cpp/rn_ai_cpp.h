#ifndef RN_AI_CPP_H
#define RN_AI_CPP_H

#include <atomic>

#include "config.h"
#ifdef USE_CUDA
#include "trt_detector.h"
#endif
#include "dml_detector.h"
#include "mouse.h"
#include "SerialConnection.h"
#include "detection_buffer.h"
#include "Kmbox_b.h"
#include "KmboxNetConnection.h"
#include "MakcuConnection.h"
#include "color_detector.h"

extern Config config;
#ifdef USE_CUDA
extern TrtDetector trt_detector;
#endif
extern DirectMLDetector* dml_detector;
extern DetectionBuffer detectionBuffer;
extern MouseThread* globalMouseThread;
extern SerialConnection* arduinoSerial;
extern KmboxConnection* kmboxSerial;
extern KmboxNetConnection* kmboxNetSerial;
extern MakcuConnection* makcu_conn;
extern ColorDetector* color_detector;

// Backward-compatible alias for legacy code paths that still reference `makcu`.
#ifndef makcu
#define makcu makcu_conn
#endif

extern std::atomic<bool> input_method_changed;
extern std::atomic<bool> aiming;
extern std::atomic<bool> shooting;
extern std::atomic<bool> zooming;
extern std::atomic<bool> triggerbot_button;

#endif // RN_AI_CPP_H
