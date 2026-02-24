#ifndef OVERLAY_UI_SECTIONS_H
#define OVERLAY_UI_SECTIONS_H

namespace OverlayUI
{
bool BeginSection(const char* title, const char* id = nullptr);
void EndSection();
bool BeginCard(const char* title, const char* id = nullptr);
void EndCard();
void AdaptiveItemWidth(float ratio = 0.60f, float minWidth = 220.0f, float maxWidth = 520.0f);
}

#endif // OVERLAY_UI_SECTIONS_H
