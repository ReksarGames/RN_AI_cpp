#ifndef OVERLAY_UI_THEME_H
#define OVERLAY_UI_THEME_H

bool OverlayTheme_LoadAndApply(const char* filename = "ui_theme.ini");
bool OverlayTheme_Reload(const char* filename = "ui_theme.ini");
bool OverlayTheme_Save(const char* filename = "ui_theme.ini");

#endif // OVERLAY_UI_THEME_H
