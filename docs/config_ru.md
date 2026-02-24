# Config Logic Guide (RN_AI)

Этот документ описывает логику параметров без привязки к файлам.

## 1) Как выбирается цель

Пайплайн:
1. Берутся детекции текущего кадра.
2. Применяются фильтры по классам и ограничениям.
3. Для кандидатов считается pivot (точка прицеливания).
4. Если включен lock, сначала удерживается текущая цель.
5. Иначе выбирается новая цель по приоритетам и весам.
6. Для выбранной цели считается движение мыши.

---

## 2) Target: базовые флаги

`disable_headshot`
- Исключает `class_head` из выбора.

`ignore_third_person`
- Игнорирует `class_third_person`.

`auto_aim`
- Разрешает автоматическую наводку при активном условии прицеливания.

`aim_bot_scope`
- Радиус зоны поиска цели в пикселях от центра.

---

## 3) Smart Target Lock

`smart_target_lock`
- Удерживает текущую цель между кадрами, уменьшает перескоки.

`target_lock_distance`
- Максимальная дистанция удержания/переискания lock.

`target_lock_reacquire_time`
- Сколько ждать после потери lock-цели до полного сброса.

`target_switch_delay`
- Debounce переключения на другую цель (мс), убирает дрожание выбора.

---

## 4) Advanced Class Controls

`target_reference_class`
- Базовый класс для lock-логики.

`target_lock_fallback_class`
- Запасной класс при потере reference-класса (`-1` = выключено).

`allowed_classes`
- Белый список классов. Вне списка цель не участвует.

`class_priority_order`
- Жесткий порядок классов. Если задан, сначала выбирается первый доступный класс.

`class_aim_positions`
- Для каждого класса задает вертикальный диапазон точки прицеливания (`pos1..pos2`).

Пример `head -> body`:
1. `class_head` = ID головы.
2. Head и body есть в `allowed_classes`.
3. `target_reference_class` = head (или head первый в `class_priority_order`).
4. `target_lock_fallback_class` = body.

Результат:
- head есть: lock держит head;
- head пропал: lock удерживается через body;
- head вернулся: возможен возврат на head с учетом `target_switch_delay`.

Важно:
- при `disable_headshot=true` возврат на head не произойдет.

---

## 5) Target Weights

`distance_scoring_weight`
- Вес дистанции до центра.

`center_scoring_weight`
- Дополнительный вес центральности.

`size_scoring_weight`
- Вес размера бокса.

`aim_weight_tiebreak_ratio`
- Развязка почти равных кандидатов.

---

## 6) Mouse: коррекция и ведение

`snapRadius`
- Внутренняя зона быстрого захвата.

`nearRadius`
- Переходная зона для более мягкого движения.

`minSpeed`, `maxSpeed`, `speedCurveExponent`, `snapBoostFactor`
- Формируют кривую скорости движения к цели.

`use_smoothing`
- Включает сглаживание движения мыши.
- Рекомендуется держать включенным.

`use_kalman`
- Включает Kalman в контуре движения мыши.
- Обычно хорошо работает в паре с `use_smoothing=true`.

`tracking_smoothing`
- Режим сопровождения движущейся цели.
- Делает трекинг более "липким": быстрее догоняет цель без резких рывков.

`kalman_process_noise`
- Шум процесса movement-Kalman.
- Больше значение: быстрее реакция, больше чувствительность к шуму.

`kalman_measurement_noise`
- Шум измерения movement-Kalman.
- Больше значение: сильнее фильтрация, больше инерция.

`kalman_speed_multiplier_x`, `kalman_speed_multiplier_y`
- Осевые множители движения после Kalman.

`camera_compensation_enabled`
- Включает компенсацию движения камеры в оценке скорости цели.

`camera_compensation_max_shift`
- Ограничение входного смещения камеры (clamp).

`camera_compensation_strength`
- Сила компенсации камеры.
- `0` почти выключает эффект, `1` базовая компенсация, `>1` усиленная.

Примечание для 4K:
- `aim_bot_scope`, `snapRadius`, `nearRadius` заданы в пикселях, на 4K их обычно увеличивают относительно FHD.

---

## 7) Prediction + Kalman

Важно: здесь два разных контура.
- Prediction-Kalman: прогноз будущей позиции цели.
- Movement-Kalman: сглаживание движения мыши (раздел 6).

`prediction_mode`
- `0`: classic velocity.
- `1`: Kalman lead.
- `2`: Kalman + raw velocity (hybrid).

`predictionInterval`
- Базовый горизонт упреждения (сек).

`prediction_kalman_lead_ms`
- Дополнительный lead в миллисекундах.

`prediction_kalman_max_lead_ms`
- Верхний лимит для lead.

`prediction_velocity_smoothing`
- EMA-сглаживание предсказанной скорости.

`prediction_velocity_scale`
- Множитель предсказанной скорости.

`prediction_kalman_process_noise` (`Pred Kalman Q`)
- Шум процесса prediction-Kalman.

`prediction_kalman_measurement_noise` (`Pred Kalman R`)
- Шум измерения prediction-Kalman.

`prediction_use_future_for_aim`
- Если включено, аим использует последнюю точку future-траектории.

`prediction_futurePositions`
- Количество точек future path.

`draw_futurePositions`
- Рисовать future path в debug.

`game_overlay_draw_future`
- Рисовать future path в game overlay.

Итого по шумам:
- prediction: `prediction_kalman_process_noise`, `prediction_kalman_measurement_noise`.
- movement: `kalman_process_noise`, `kalman_measurement_noise`.

---

## 8) AI: NMS и малые цели

`nms_threshold`
- Базовый IoU-порог NMS.

`adaptive_nms`
- Включает адаптивный NMS для маленьких боксов.
- Логика: считается медианная площадь детекций; для маленьких боксов порог повышается до `min(nms_threshold * 1.5, 0.8)`.

`small_target_enhancement_enabled`
- Включает буст маленьких целей в scoring.

`small_target_threshold`
- Порог относительного размера для "малой" цели.

`small_target_boost_factor`
- Буст для очень маленьких целей.

`small_target_medium_threshold`
- Порог для "средне-малых" целей.

`small_target_medium_boost`
- Буст для средне-малых целей.

`small_target_smooth_enabled`
- Включает сглаживание pivot/size маленьких целей по истории.

`small_target_smooth_frames`
- Количество кадров истории для сглаживания.

---

## 9) Game Overlay

`show fps counter`
- Показывает FPS поверх игры.

`show latency`
- Показывает latency поверх игры.

`overlay_fps_text_size`, `overlay_latency_text_size`
- Размер текста метрик.

Цвета боксов:
- класс `0` всегда зеленый;
- остальные классы получают цвет автоматически из палитры.

---

## 10) Debug и логи

При включенном логировании в файл:
- лог очищается при старте новой сессии;
- события из консоли пишутся в runtime лог.
