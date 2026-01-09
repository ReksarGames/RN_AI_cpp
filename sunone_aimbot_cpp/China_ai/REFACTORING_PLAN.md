# Plan: Split core.py into Multiple Files

# !!! IMPORTANT !!!
# ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
# REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
# DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS

# !!! IMPORTANT !!!
# ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
# REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
# DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS

# !!! IMPORTANT !!!
# ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
# REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
# DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS

## Overview
Split the large `ZTXAI/core.py` (5720 lines, 331KB) into 9 smaller files in a `core/` subfolder using the **Mixin class pattern**.

## CRITICAL RULES - READ BEFORE STARTING

```
!!! IMPORTANT !!!
ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS
```

**WHAT TO DO:**
- Copy code EXACTLY as-is to new files
- Translate Chinese comments to English
- Create Mixin classes to hold methods
- Update imports

**WHAT NOT TO DO:**
- DO NOT change any logic
- DO NOT rename variables
- DO NOT refactor code structure
- DO NOT "improve" or "clean up" code
- DO NOT add type hints
- DO NOT add docstrings
- DO NOT change function signatures
- DO NOT change indentation style
- DO NOT reorganize code within methods

## Architecture: Mixin Pattern

Each module will contain a Mixin class with related methods. The main `Valorant` class will inherit from all mixins.

```python
# core.py (after refactoring)
from core.utils import check_tensorrt_availability, create_gradient_image, key2str, ...
from core.input import InputMixin
from core.auth import AuthMixin
from core.config import ConfigMixin
from core.aiming import AimingMixin
from core.gui import GuiMixin
from core.recoil import RecoilMixin
from core.flashbang import FlashbangMixin
from core.model import ModelMixin

class Valorant(InputMixin, AuthMixin, ConfigMixin, AimingMixin,
               GuiMixin, RecoilMixin, FlashbangMixin, ModelMixin):
    def __init__(self):
        # Only __init__ stays here
        ...
```

## Step 0: Backup
```bash
cp /Users/dsokolyuk/assist/ZTXAI/core.py /Users/dsokolyuk/assist/ZTXAI/core.py.backup
mkdir -p /Users/dsokolyuk/assist/ZTXAI/core
```

## File Structure (9 files + __init__.py)

```
ZTXAI/
├── core.py                    # Main: imports + Valorant class shell + __init__
├── core.py.backup             # Original backup
├── core/
│   ├── __init__.py           # Package exports
│   ├── utils.py              # ~100 lines  - Module-level functions (5 functions)
│   ├── input.py              # ~650 lines  - Input handlers + device listeners (19 methods)
│   ├── auth.py               # ~160 lines  - Authentication only (7 methods)
│   ├── config.py             # ~220 lines  - Configuration management (8 methods)
│   ├── aiming.py             # ~760 lines  - Targeting + mouse + trigger + inference (18 methods)
│   ├── gui.py                # ~1350 lines - GUI main + all callbacks (~102 methods)
│   ├── recoil.py             # ~290 lines  - Mouse recoil trajectory (16 methods)
│   ├── flashbang.py          # ~560 lines  - Auto-flashbang feature (21 methods)
│   └── model.py              # ~650 lines  - Model management (30 methods)
```

## File Sizes Summary

| File | Methods | Lines | Content |
|------|---------|-------|---------|
| utils.py | 5 funcs | ~100 | Module-level functions |
| input.py | 19 | ~650 | Input handlers + listeners |
| auth.py | 7 | ~160 | Authentication only |
| config.py | 8 | ~220 | Configuration management |
| aiming.py | 18 | ~760 | Targeting + mouse + trigger + inference |
| gui.py | ~102 | ~1350 | GUI main (incl. 378-line gui()) + callbacks |
| recoil.py | 16 | ~290 | Mouse recoil trajectory (mouse_re) |
| flashbang.py | 21 | ~560 | Auto-flashbang detection + evasion |
| model.py | 30 | ~650 | Model management + class detection |
| **Total** | **~226** | **~4740** | |

---

# !!! REMINDER !!!
# DO NOT CHANGE LOGIC - ONLY TRANSLATE COMMENTS
# DO NOT REFACTOR CODE - JUST MOVE IT TO NEW FILES

---

## Detailed File Contents

### 1. `core/utils.py` - Module Functions (~100 lines)
```
Functions (Lines 38-199, 5705-5719):
- check_tensorrt_availability()        # Lines 38-71
- create_gradient_image(width, height) # Lines 111-122
- key2str(key)                         # Lines 172-199
- auto_convert_engine(onnx_path)       # Lines 5705-5711
- global_exception_hook(exctype, value, tb) # Lines 5713-5718

Also: TENSORRT_AVAILABLE global variable
```

### 2. `core/input.py` - InputMixin (~650 lines)
```
Input handlers (Lines 492-661):
- down_func()           # Lines 492-523 (recoil timer callback)
- screenshot()          # Lines 525-527 (deprecated wrapper)
- on_click()            # Lines 529-576
- on_scroll()           # Lines 578-582
- on_press()            # Lines 586-594
- on_release()          # Lines 598-619
- reset_target_lock()   # Lines 621-661

Device listeners (Lines 876-1357):
- start_listen()          # Lines 876-880
- start_listen_km_net()   # Lines 882-951
- check_long_press()      # Lines 953-956
- left_press()            # Lines 958-968
- left_release()          # Lines 970-978
- start_listen_pnmh()     # Lines 980-1014
- start_listen_makcu()    # Lines 1016-1152
- start_listen_catbox()   # Lines 1154-1169
- start_listen_dhz()      # Lines 1171-1238
- stop_listen()           # Lines 1240-1252
- disconnect_device()     # Lines 1254-1324
- unmask_all()            # Lines 1326-1357
```

### 3. `core/auth.py` - AuthMixin (~160 lines)
```
Authentication methods (Lines 663-816):
- start_verify_init()        # Lines 663-675
- error_exit()               # Lines 677-710
- verify()                   # Lines 712-741
- _decrypt_encrypted_model() # Lines 743-765
- _validate_onnx_data()      # Lines 767-776
- _update_class_checkboxes() # Lines 778-787
- _secure_cleanup()          # Lines 789-816
```

### 4. `core/config.py` - ConfigMixin (~220 lines)
```
Configuration management (Lines 1852-2066):
- save_config_callback()              # Lines 1852-1868
- build_config()                      # Lines 1870-1960
- init_all_keys_class_aim_positions() # Lines 1962-2002
- migrate_config_to_class_based()     # Lines 2004-2031
- calculate_max_pixel_distance()      # Lines 2033-2036
- refresh_controller_params()         # Lines 2038-2047
- refresh_pressed_key_config()        # Lines 2049-2056
- get_aim_position_for_class()        # Lines 2058-2066
```

### 5. `core/aiming.py` - AimingMixin (~760 lines)
```
Target selection (Lines 1358-1565):
- smooth_small_targets()       # Lines 1358-1393
- select_target_by_priority()  # Lines 1395-1450
- aim_bot_func()               # Lines 1452-1526
- execute_move()               # Lines 1528-1534
- _execute_move_async()        # Lines 1536-1565

Inference engine (Lines 1567-1850):
- infer()                      # Lines 1567-1752
- _update_dynamic_aim_scope()  # Lines 1754-1822
- get_dynamic_aim_scope()      # Lines 1824-1832
- reset_dynamic_aim_scope()    # Lines 1834-1850

Mouse control (Lines 2068-2146):
- mouse_left_down()  # Lines 2068-2106
- mouse_left_up()    # Lines 2108-2146

Trigger system (Lines 2148-2294):
- trigger_process()             # Lines 2148-2168
- continuous_trigger_process()  # Lines 2170-2191
- stop_continuous_trigger()     # Lines 2193-2196
- start_trigger_recoil()        # Lines 2198-2219
- stop_trigger_recoil()         # Lines 2221-2233
- trigger()                     # Lines 2235-2285
- reset_pid()                   # Lines 2287-2294
```

### 6. `core/gui.py` - GuiMixin (~1350 lines)
```
GUI main setup (Lines 2296-2827):
- get_system_dpi_scale()         # Lines 2296-2308
- get_dpi_aware_screen_size()    # Lines 2310-2324
- update_combo_methods()         # Lines 2326-2328
- update_target_reference_class_combo() # Lines 2330-2345
- get_gradient_color()           # Lines 2347-2354 (staticmethod)
- gui()                          # Lines 2356-2734  [378 lines - main GUI init]
- on_start_button_click()        # Lines 2736-2812
- on_save_button_click()         # Lines 2814-2815
- on_game_sensitivity_change()   # Lines 2817-2818
- on_mouse_dpi_change()          # Lines 2820-2821
- update_sensitivity_display()   # Lines 2823-2824
- calculate_sensitivity_multiplier() # Lines 2826-2827

GUI callbacks (Lines 3118-3883, ~90 methods):
- on_infer_debug_change()                  # Lines 3118-3120
- on_is_curve_change()                     # Lines 3122-3124
- on_is_curve_uniform_change()             # Lines 3126-3128
- on_distance_scoring_weight_change()      # Lines 3130-3133
- on_center_scoring_weight_change()        # Lines 3135-3138
- on_size_scoring_weight_change()          # Lines 3140-3143
- on_print_fps_change()                    # Lines 3277-3279
- on_show_motion_speed_change()            # Lines 3281-3284
- on_is_show_curve_change()                # Lines 3286-3288
- on_enable_parallel_processing_change()   # Lines 3290-3294
- on_turbo_mode_change()                   # Lines 3296-3300
- on_skip_frame_processing_change()        # Lines 3302-3306
- on_is_show_down_change()                 # Lines 3308-3310
- on_is_obs_change()                       # Lines 3312-3316
- on_is_cjk_change()                       # Lines 3318-3322
- on_obs_ip_change(), on_cjk_*_change()    # Lines 3324-3370
- on_offset_boundary_*_change()            # Lines 3372-3398
- on_km_box_*_change(), on_km_net_*_change()  # Lines 3400-3450
- on_group_change()                        # Lines 3452-3473
- on_confidence_threshold_change()         # Lines 3475-3481
- on_iou_t_change()                        # Lines 3483-3489
- on_infer_model_change()                  # Lines 3491-3522
- on_select_model_click()                  # Lines 3524-3548
- on_aim_bot_position*_change()            # Lines 3550-3564
- on_class_priority_change()               # Lines 3566-3575
- parse_class_priority(), format_class_priority()  # Lines 3577-3610
- on_class_aim_combo_change()              # Lines 3612-3617
- update_class_aim_inputs(), update_class_aim_combo()  # Lines 3619-3670
- on_aim_bot_scope_change()                # Lines 3672-3674
- on_dynamic_scope_*_change()              # Lines 3676-3721
- on_min_position_offset_change()          # Lines 3723-3725
- on_smoothing_*_change()                  # Lines 3727-3760
- on_velocity_*_change()                   # Lines 3762-3800
- on_*_trigger_*_change()                  # Lines 3822-3872
- update_rect()                            # Lines 3874-3883
- Game/Gun/Stage methods                   # Lines 4469-4589
- Mask methods                             # Lines 4591-4795
- Debug/Display methods                    # Lines 4797-4912
- Config handler methods                   # Lines 5131-5219
```

### 7. `core/recoil.py` - RecoilMixin (~290 lines)
```
Mouse recoil trajectory (Lines 2829-3116):
- update_mouse_re_ui_status()              # Lines 2829-2855
- on_use_mouse_re_trajectory_change()      # Lines 2857-2865
- on_mouse_re_replay_speed_change()        # Lines 2867-2876
- on_mouse_re_pixel_enhancement_change()   # Lines 2878-2887
- on_import_mouse_re_trajectory_click()    # Lines 2889-2909
- on_clear_mouse_re_mapping_click()        # Lines 2911-2924
- _load_mouse_re_trajectory_for_current()  # Lines 2926-2946
- _parse_mouse_re_json()                   # Lines 2948-2992
- _start_mouse_re_recoil()                 # Lines 2994-3007
- _stop_mouse_re_recoil()                  # Lines 3009-3011
- _recoil_replay_worker()                  # Lines 3013-3055
- render_mouse_re_games_combo()            # Lines 3057-3074
- render_mouse_re_guns_combo()             # Lines 3076-3099
- on_mouse_re_games_change()               # Lines 3101-3107
- on_mouse_re_guns_change()                # Lines 3109-3113
- on_card_change()                         # Lines 3115-3116
```

### 8. `core/flashbang.py` - FlashbangMixin (~560 lines)
```
Auto-flashbang callbacks (Lines 3145-3275):
- on_auto_flashbang_enabled_change()       # Lines 3145-3157
- on_auto_flashbang_delay_change()         # Lines 3159-3164
- on_auto_flashbang_angle_change()         # Lines 3166-3171
- on_auto_flashbang_sensitivity_change()   # Lines 3173-3178
- on_auto_flashbang_return_delay_change()  # Lines 3180-3185
- on_test_flashbang_left()                 # Lines 3187-3193
- on_test_flashbang_right()                # Lines 3195-3201
- on_auto_flashbang_curve_change()         # Lines 3203-3208
- on_auto_flashbang_curve_speed_change()   # Lines 3210-3215
- on_auto_flashbang_curve_knots_change()   # Lines 3217-3222
- on_auto_flashbang_min_confidence_change()# Lines 3224-3229
- on_auto_flashbang_min_size_change()      # Lines 3231-3236
- on_flashbang_debug_info()                # Lines 3238-3258
- update_auto_flashbang_ui_state()         # Lines 3260-3275

Flashbang detection & evasion (Lines 5221-5651):
- detect_and_handle_flashbang()            # Lines 5221-5294
- execute_flashbang_turn()                 # Lines 5296-5322
- execute_flashbang_return()               # Lines 5323-5351
- execute_flashbang_curve_move()           # Lines 5352-5437
- execute_flashbang_curve_move_fast()      # Lines 5439-5516
- execute_flashbang_curve_move_with_tracking() # Lines 5518-5610
- execute_flashbang_ultra_fast_move()      # Lines 5612-5651
```

### 9. `core/model.py` - ModelMixin (~650 lines)
```
Group/Key management (Lines 3885-4069):
- render_group_combo()                  # Lines 3885-3889
- render_key_combo()                    # Lines 3891-3901
- on_key_change()                       # Lines 3903-3907
- update_key_inputs()                   # Lines 3909-3965
- update_group_inputs()                 # Lines 3967-3972
- create_checkboxes()                   # Lines 3974-3980
- remove_checkboxes()                   # Lines 3982-3985
- on_checkbox_change()                  # Lines 3987-3996
- update_checkboxes_state()             # Lines 3998-4003
- on_delete_group_click()               # Lines 4005-4020
- on_group_name_change()                # Lines 4022-4023
- on_add_group_click()                  # Lines 4025-4030
- on_delete_key_click()                 # Lines 4032-4039
- on_key_name_change()                  # Lines 4041-4042
- on_add_key_click()                    # Lines 4044-4053
- init_class_aim_positions_for_key()    # Lines 4055-4069

Mouse/Engine init (Lines 4071-4467):
- init_mouse()                          # Lines 4071-4268
- _clear_queues()                       # Lines 4270-4284
- _reset_aim_states()                   # Lines 4286-4296
- refresh_engine()                      # Lines 4298-4376
- _create_engine_from_bytes()           # Lines 4378-4451
- on_is_v8_change()                     # Lines 4453-4455
- on_auto_y_change()                    # Lines 4457-4460
- on_right_down_change()                # Lines 4462-4464
- init_target_priority()                # Lines 4466-4467

Class detection (Lines 4914-5002, 5653-5702):
- get_trt_class_num()                   # Lines 4914-4940
- get_onnx_class_num()                  # Lines 4942-4977
- get_current_class_num()               # Lines 4979-5002
- is_using_dopa_model()                 # Lines 5653-5676
- is_using_encrypted_model()            # Lines 5678-5702
```

### 10. Remaining in main `core.py` (~350 lines):
```
- All imports (consolidated at top)
- __init__() method                     # Lines 203-414
- _change_callback()                    # Lines 416-490
- start()                               # Lines 818-825
- go()                                  # Lines 827-853
- save_config()                         # Lines 855-874
- _init_config_handlers()               # Lines 5004-5129
```

---

# !!! REMINDER !!!
# DO NOT CHANGE LOGIC - ONLY TRANSLATE COMMENTS
# DO NOT REFACTOR CODE - JUST MOVE IT TO NEW FILES

---

## Implementation Steps

### Step 1: Create backup and folder structure
```bash
cp core.py core.py.backup
mkdir -p core
```

### Step 2: Create `core/__init__.py`
```python
"""Core module containing Valorant class mixins."""
from .utils import (
    check_tensorrt_availability,
    create_gradient_image,
    key2str,
    auto_convert_engine,
    global_exception_hook,
    TENSORRT_AVAILABLE
)
from .input import InputMixin
from .auth import AuthMixin
from .config import ConfigMixin
from .aiming import AimingMixin
from .gui import GuiMixin
from .recoil import RecoilMixin
from .flashbang import FlashbangMixin
from .model import ModelMixin

__all__ = [
    'InputMixin', 'AuthMixin', 'ConfigMixin', 'AimingMixin',
    'GuiMixin', 'RecoilMixin', 'FlashbangMixin', 'ModelMixin',
    'check_tensorrt_availability', 'create_gradient_image',
    'key2str', 'auto_convert_engine', 'global_exception_hook',
    'TENSORRT_AVAILABLE'
]
```

### Step 3: Extract each mixin file (in order)
1. `core/utils.py` - Module-level functions (5 functions)
2. `core/input.py` - InputMixin (19 methods)
3. `core/auth.py` - AuthMixin (7 methods)
4. `core/config.py` - ConfigMixin (8 methods)
5. `core/aiming.py` - AimingMixin (18 methods)
6. `core/gui.py` - GuiMixin (~102 methods)
7. `core/recoil.py` - RecoilMixin (16 methods)
8. `core/flashbang.py` - FlashbangMixin (21 methods)
9. `core/model.py` - ModelMixin (30 methods)

### Step 4: Update main `core.py`
```python
# Imports from standard library and third-party
import copy
import ctypes
# ... all other imports ...

# Import from core submodules
from core import (
    InputMixin, AuthMixin, ConfigMixin, AimingMixin,
    GuiMixin, RecoilMixin, FlashbangMixin, ModelMixin,
    check_tensorrt_availability, TENSORRT_AVAILABLE
)

class Valorant(InputMixin, AuthMixin, ConfigMixin, AimingMixin,
               GuiMixin, RecoilMixin, FlashbangMixin, ModelMixin):
    def __init__(self):
        # Original __init__ code here (Lines 203-414)
        ...

    def _change_callback(self, path, value):
        # Original code (Lines 416-490)
        ...

    def start(self):
        # Original code (Lines 818-825)
        ...

    def go(self):
        # Original code (Lines 827-853)
        ...

    def save_config(self):
        # Original code (Lines 855-874)
        ...

    def _init_config_handlers(self):
        # Original code (Lines 5004-5129)
        ...
```

---

# !!! REMINDER !!!
# DO NOT CHANGE LOGIC - ONLY TRANSLATE COMMENTS
# DO NOT REFACTOR CODE - JUST MOVE IT TO NEW FILES

---

## Verification

After refactoring:
1. Run `python -c "from ZTXAI.core import Valorant"` - should import without errors
2. Run `python ZTXAI/main.py` - should start normally
3. Compare method count: should still have 296 methods
4. Test basic functionality

## Risk Mitigation

1. **Backup first** - Always keep `core.py.backup`
2. **One file at a time** - Extract and test incrementally
3. **No logic changes** - Only move code, translate comments
4. **Self references** - All `self.method()` calls will work because of mixin inheritance
5. **Import order** - Ensure mixins don't have circular imports

## Estimated File Sizes (Final 9-file structure)

| File | Methods | ~Lines | Content |
|------|---------|--------|---------|
| core/utils.py | 5 funcs | ~100 | Module-level functions |
| core/input.py | 19 | ~650 | Input handlers + device listeners |
| core/auth.py | 7 | ~160 | Authentication only |
| core/config.py | 8 | ~220 | Configuration management |
| core/aiming.py | 18 | ~760 | Targeting + mouse + trigger + inference |
| core/gui.py | ~102 | ~1350 | GUI main (378-line gui()) + all callbacks |
| core/recoil.py | 16 | ~290 | Mouse recoil trajectory (mouse_re) |
| core/flashbang.py | 21 | ~560 | Auto-flashbang detection + evasion |
| core/model.py | 30 | ~650 | Model management + class detection |
| core.py (main) | 6 | ~350 | Imports + __init__ + start + go |
| **Total** | **~232** | **~5090** | |

---

# !!! FINAL REMINDER !!!
# ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
# REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
# DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS
# COPY CODE EXACTLY AS-IS TO NEW FILES
# ONLY TRANSLATE CHINESE COMMENTS TO ENGLISH
