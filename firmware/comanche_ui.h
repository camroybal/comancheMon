#pragma once
// Small, allocation-free helpers shared by the UI lambdas.  Keeping the
// formatting and change detection here avoids building a std::string for every
// label on every timer tick, and it makes the YAML much easier to audit.

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <lvgl.h>

namespace cm {

inline uint64_t us() { return static_cast<uint64_t>(esp_timer_get_time()); }
inline uint32_t seconds() { return static_cast<uint32_t>(us() / 1000000ULL); }

// Set a label only when the rendered text actually changes.  LVGL invalidates
// the whole object when lv_label_set_text is called, even for an identical
// string, so the comparison saves a lot of redundant redraws at 10 Hz.
inline void text(lv_obj_t *obj, const char *fmt, ...) {
  char buf[64];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  const char *current = lv_label_get_text(obj);
  if (current == nullptr || strcmp(current, buf) != 0)
    lv_label_set_text(obj, buf);
}

inline void text_raw(lv_obj_t *obj, const char *value) {
  const char *current = lv_label_get_text(obj);
  if (current == nullptr || strcmp(current, value) != 0)
    lv_label_set_text(obj, value);
}

inline void y(lv_obj_t *obj, int value) {
  if (lv_obj_get_y(obj) != value)
    lv_obj_set_y(obj, value);
}

// Angles are quantised to 0.5 degrees; rotating a bitmap is not free, and a
// half-degree step is already smoother than the eye can resolve at 5 Hz.
inline void rot(lv_obj_t *obj, float degrees) {
  int32_t angle = static_cast<int32_t>(lroundf(degrees * 2.0f)) * 5;
  if (lv_image_get_rotation(obj) != angle)
    lv_image_set_rotation(obj, angle);
}

inline void bar(lv_obj_t *obj, float percent) {
  int value = static_cast<int>(lroundf(percent));
  if (value < 0) value = 0;
  if (value > 100) value = 100;
  if (lv_bar_get_value(obj) != value)
    lv_bar_set_value(obj, value, LV_ANIM_OFF);
}

inline void check(lv_obj_t *obj, bool on) {
  bool is_on = lv_obj_has_state(obj, LV_STATE_CHECKED);
  if (on && !is_on)
    lv_obj_add_state(obj, LV_STATE_CHECKED);
  else if (!on && is_on)
    lv_obj_clear_state(obj, LV_STATE_CHECKED);
}

inline int internal_kb() {
  return static_cast<int>(
      heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT) / 1024);
}

inline int psram_kb() {
  return static_cast<int>(
      heap_caps_get_free_size(MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT) / 1024);
}

}  // namespace cm
