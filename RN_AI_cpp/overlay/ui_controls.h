#ifndef OVERLAY_UI_CONTROLS_H
#define OVERLAY_UI_CONTROLS_H

namespace OverlayUI
{
bool SliderIntWithButtons(const char* label, int* value, int minValue, int maxValue, int step = 1, const char* sliderFormat = "%d");
bool SliderFloatWithButtons(const char* label, float* value, float minValue, float maxValue, float step = 0.01f, const char* sliderFormat = "%.2f", const char* inputFormat = "%.3f");
bool IntControlRow(const char* label, int* value, int minValue, int maxValue, int step, const char* unit = nullptr, const char* hint = nullptr);
bool FloatControlRow(const char* label, float* value, float minValue, float maxValue, float step, const char* sliderFormat = "%.2f", const char* inputFormat = "%.3f", const char* unit = nullptr, const char* hint = nullptr);
}

#endif // OVERLAY_UI_CONTROLS_H
