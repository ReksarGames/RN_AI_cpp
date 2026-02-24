#ifndef OVERLAY_CONFIG_DIRTY_H
#define OVERLAY_CONFIG_DIRTY_H

void OverlayConfig_MarkDirty();
bool OverlayConfig_IsDirty();
bool OverlayConfig_FlushIfDue(int debounceMs = 200);
void OverlayConfig_FlushNow();

#endif // OVERLAY_CONFIG_DIRTY_H
