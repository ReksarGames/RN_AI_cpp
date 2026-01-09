"""GUI mixin for main interface and callbacks.

!!! IMPORTANT !!!
ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS
"""
import copy
import ctypes
import os
import random
import string
import tkinter as tk
from threading import Timer
from tkinter import filedialog

import dearpygui.dearpygui as dpg
import kmNet
from catbox_wrapper import catbox, init_catbox, catbox_move, catbox_left_down, catbox_left_up, catbox_disconnect

from .utils import create_gradient_image, TENSORRT_AVAILABLE, VERSION, UPDATE_TIME
from gui_handlers import ConfigItemGroup

try:
    if TENSORRT_AVAILABLE:
        from inference_engine import ensure_engine_from_memory
    else:
        ensure_engine_from_memory = None
except ImportError:
    ensure_engine_from_memory = None


class GuiMixin:
    """Mixin class for GUI interface and callback methods."""

    def get_system_dpi_scale(self):
        """Get system DPI scale ratio"""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            scale = dpi / 96.0
            scale = max(1.0, min(scale, 3.0))
            return scale
        except Exception as e:
            print(f'Failed to get DPI scale, using default: {e}')
            return 1.0

    def get_dpi_aware_screen_size(self):
        """Get DPI-aware actual available screen size"""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            root.destroy()
            return (width, height)
        except Exception as e:
            width = win32api.GetSystemMetrics(0)
            height = win32api.GetSystemMetrics(1)
            return (width, height)

    def update_combo_methods(self):
        self.render_group_combo()
        self.update_target_reference_class_combo()

    def update_target_reference_class_combo(self):
        """Update target reference class combo box options"""
        if not hasattr(self, 'target_reference_class_combo') or self.target_reference_class_combo is None:
            return None
        try:
            class_num = self.get_current_class_num()
            items = [f'Class{i}' for i in range(class_num)]
            import dearpygui.dearpygui as dpg
            dpg.configure_item(self.target_reference_class_combo, items=items)
            current_reference_class = self.pressed_key_config.get('target_reference_class', 0)
            if current_reference_class < 0 or current_reference_class >= class_num:
                current_reference_class = 0
                self.config['groups'][self.group]['aim_keys'][self.select_key]['target_reference_class'] = 0
            dpg.set_value(self.target_reference_class_combo, f'Class{current_reference_class}')
        except Exception as e:
            print(f'Failed to update target reference class combo: {e}')

    def get_gradient_color(base_color, step):
        """Generate color gradient based on base color"""
        r, g, b, a = base_color
        factor = 1 + step
        r = min(int(r * factor), 255)
        g = min(int(g * factor), 255)
        b = min(int(b * factor), 255)
        return (r, g, b, a)

    def gui(self):
        title = ''.join(random.sample(string.ascii_letters + string.digits, 8)).join(VERSION)
        dpg.create_context()
        gradient_path = create_gradient_image(self.gui_window_width, self.scaled_bar_height)
        with dpg.texture_registry(show=False):
            dpg.add_dynamic_texture(8, 12, [0] * 384, tag='checkbox_texture')
        with dpg.texture_registry():
            width, height, channels, data = dpg.load_image(gradient_path)
            texture_id = dpg.add_static_texture(width, height, data)
        with dpg.font_registry():
            with dpg.font('ChillBitmap_16px.ttf', self.scaled_font_size_main) as msyh:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
                dpg.bind_font(msyh)
            custom_font = dpg.add_font('undefeated.ttf', self.scaled_font_size_custom)
        with dpg.theme() as tab_bar_theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (45, 45, 45, 255))
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 0)
        with dpg.theme() as skeet_theme:
            with dpg.theme_component(dpg.mvCheckbox):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (75, 75, 75, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (95, 95, 95, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (154, 197, 39, 255))
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255, 255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (203, 203, 203, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 1, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (35, 35, 35, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (65, 65, 65, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (25, 25, 25, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 50, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (203, 203, 203, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (150, 150, 150, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 3)
            with dpg.theme_component(dpg.mvInputInt):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (65, 65, 65, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (85, 85, 85, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (203, 203, 203, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 4, 4)
            with dpg.theme_component(dpg.mvCombo):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 45, 45, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (65, 65, 65, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (85, 85, 85, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (203, 203, 203, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (35, 35, 35, 255))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 4, 4)
        dpg.create_viewport(title=title, width=self.gui_window_width, height=self.gui_window_height)
        dpg.setup_dearpygui()

        def switch_tab(sender, app_data, user_data):
            """Switch to corresponding tab"""
            dpg.set_value('tab_bar', user_data)
        with dpg.window(label=title, no_title_bar=True, no_resize=True, no_move=True, width=self.gui_window_width, height=self.gui_window_height) as self.window_tag:
            dpg.draw_image(texture_id, (0, 0), (self.gui_window_width, self.scaled_bar_height))
            with dpg.group(horizontal=True):
                with dpg.child_window(width=self.scaled_sidebar_width, height=self.gui_window_height - 120):
                    button_size = int(50 * self.dpi_scale)
                    system = dpg.add_button(label='s', width=button_size, height=button_size, callback=switch_tab, user_data='system_settings')
                    driver = dpg.add_button(label='v', width=button_size, height=button_size, callback=switch_tab, user_data='driver_settings')
                    bypass = dpg.add_button(label='o', width=button_size, height=button_size, callback=switch_tab, user_data='bypass_settings')
                    strafe = dpg.add_button(label='W', width=button_size, height=button_size, callback=switch_tab, user_data='strafe_settings')
                    config = dpg.add_button(label='u', width=button_size, height=button_size, callback=switch_tab, user_data='config_settings')
                    dpg.bind_item_font(system, custom_font)
                    dpg.bind_item_font(driver, custom_font)
                    dpg.bind_item_font(bypass, custom_font)
                    dpg.bind_item_font(strafe, custom_font)
                    dpg.bind_item_font(config, custom_font)
                with dpg.child_window(width=self.gui_window_width - self.scaled_sidebar_width, height=self.gui_window_height - 120) as tab_bar_container:
                    dpg.bind_item_theme(tab_bar_container, tab_bar_theme)
                    dpg.bind_theme(skeet_theme)
                    with dpg.tab_bar(tag='tab_bar'):
                        with dpg.tab(tag='system_settings'):
                            with dpg.group(horizontal=True):
                                self.dpi_scale_slider = dpg.add_slider_float(label='GUI DPI Scale', default_value=self.dpi_scale, min_value=0.5, max_value=3.0, format='%.2f', callback=self.on_gui_dpi_scale_change, width=self.scaled_width_xlarge)
                                dpg.add_button(label='Auto Detect', callback=self.on_reset_dpi_scale_click)
                            dpg.add_text(f'Adjust GUI interface scale (Current system detection: {self.get_system_dpi_scale():.2f}, effective after restart)')
                            dpg.add_separator()
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Inference Window', default_value=self.config['infer_debug'], callback=self.on_infer_debug_change)
                                dpg.add_checkbox(label='Print FPS', default_value=self.config['print_fps'], callback=self.on_print_fps_change)
                                dpg.add_checkbox(label='Show Motion Speed', default_value=self.config['show_motion_speed'], callback=self.on_show_motion_speed_change)
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Show Curve', default_value=self.config['is_show_curve'], callback=self.on_is_show_curve_change)
                                dpg.add_checkbox(label='Show Infer Time', default_value=self.config.get('show_infer_time', True), callback=self.on_show_infer_time_change)
                                dpg.add_checkbox(label='Screenshot Separation (Multi-thread)', default_value=self.config.get('enable_parallel_processing', True), callback=self.on_enable_parallel_processing_change)
                            dpg.add_separator()
                            dpg.add_text('Small Target Enhancement Settings', color=(100, 200, 255))
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Enable Small Target Enhancement', tag='small_target_enabled_checkbox', default_value=self.config['small_target_enhancement']['enabled'], callback=self.on_small_target_enabled_change)
                                dpg.add_checkbox(label='Enable Small Target Smoothing', tag='small_target_smooth_checkbox', default_value=self.config['small_target_enhancement']['smooth_enabled'], callback=self.on_small_target_smooth_change)
                                dpg.add_checkbox(label='Adaptive NMS', tag='small_target_nms_checkbox', default_value=self.config['small_target_enhancement']['adaptive_nms'], callback=self.on_small_target_nms_change)
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Small Target Boost', tag='small_target_boost_input', default_value=self.config['small_target_enhancement']['boost_factor'], min_value=1.0, max_value=5.0, step=0.1, callback=self.on_small_target_boost_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Smooth History Frames', tag='small_target_frames_input', default_value=self.config['small_target_enhancement']['smooth_frames'], min_value=2, max_value=10, callback=self.on_small_target_frames_change, width=self.scaled_width_medium)
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Small Target Threshold', tag='small_target_threshold_input', default_value=self.config['small_target_enhancement']['threshold'], min_value=0.001, max_value=0.1, step=0.001, format='%.3f', callback=self.on_small_target_threshold_change, width=self.scaled_width_normal)
                                dpg.add_input_float(label='Medium Target Threshold', tag='medium_target_threshold_input', default_value=self.config['small_target_enhancement']['medium_threshold'], min_value=0.01, max_value=0.2, step=0.01, format='%.3f', callback=self.on_medium_target_threshold_change, width=self.scaled_width_normal)
                            dpg.add_text('Note: Small target enhancement can improve detection stability for distant or small-sized targets', color=(150, 150, 150), wrap=self.scaled_width_xlarge)
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Turbo Mode', default_value=self.config.get('turbo_mode', True), callback=self.on_turbo_mode_change)
                                dpg.add_checkbox(label='Skip Frame Processing', default_value=self.config.get('skip_frame_processing', True), callback=self.on_skip_frame_processing_change)
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Recoil Debug', default_value=self.config['is_show_down'], callback=self.on_is_show_down_change)
                                dpg.add_checkbox(label='Class Priority Debug', default_value=self.config.get('is_show_priority_debug', False), callback=self.on_is_show_priority_debug_change)
                                dpg.add_checkbox(label='Show Aim Scope', default_value=self.config.get('show_fov', True), callback=self.on_show_fov_change)
                            dpg.add_checkbox(label='OBS', default_value=self.config['is_obs'], callback=self.on_is_obs_change)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='OBS IP', default_value=self.config['obs_ip'], callback=self.on_obs_ip_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='OBS Port', default_value=self.config['obs_port'], callback=self.on_obs_port_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='OBS FPS', default_value=self.config['obs_fps'], callback=self.on_obs_fps_change, width=self.scaled_width_normal)
                            dpg.add_checkbox(label='Capture Card', default_value=self.config['is_cjk'], callback=self.on_is_cjk_change)
                            with dpg.group(horizontal=True):
                                dpg.add_input_int(label='Capture Device', default_value=self.config['cjk_device_id'], callback=self.on_cjk_device_id_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Capture FPS', default_value=self.config['cjk_fps'], callback=self.on_cjk_fps_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='Capture Resolution', default_value=self.config['cjk_resolution'], callback=self.on_cjk_resolution_change, width=self.scaled_width_medium)
                                dpg.add_input_text(label='Capture Crop Size', default_value=self.config['cjk_crop_size'], callback=self.on_cjk_crop_size_change, width=self.scaled_width_medium)
                            dpg.add_input_text(label='Video Codec Format', default_value=self.config.get('cjk_fourcc_format', 'NV12'), callback=self.on_cjk_fourcc_format_change, width=self.scaled_width_medium, hint='e.g.: NV12, MJPG, YUYV')
                            dpg.add_text('Aim Weights')
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Distance Weight', default_value=self.config['distance_scoring_weight'], min_value=0.0, step=0.05, callback=self.on_distance_scoring_weight_change, width=self.scaled_width_normal)
                                dpg.add_input_float(label='Center Weight', default_value=self.config['center_scoring_weight'], min_value=0.0, step=0.05, callback=self.on_center_scoring_weight_change, width=self.scaled_width_normal)
                                dpg.add_input_float(label='Size Weight', default_value=self.config['size_scoring_weight'], min_value=0.0, step=0.05, callback=self.on_size_scoring_weight_change, width=self.scaled_width_normal)
                            dpg.add_separator()
                            dpg.add_text('Auto Flashbang Settings')
                            is_dopa = self.is_using_dopa_model()
                            dopa_status_text = 'Currently using ZTX model, feature available' if is_dopa else 'Currently not using ZTX model, feature unavailable'
                            dopa_color = (0, 255, 0) if is_dopa else (255, 100, 100)
                            dpg.add_text(f'Note: This feature only supports ZTX models - {dopa_status_text}', color=dopa_color, wrap=self.scaled_width_xlarge)
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Enable Auto Flashbang', tag='auto_flashbang_enabled_checkbox', default_value=self.config['auto_flashbang']['enabled'] and is_dopa, enabled=is_dopa, callback=self.on_auto_flashbang_enabled_change)
                                dpg.add_input_int(label='Flashbang Delay(ms)', tag='auto_flashbang_delay_input', default_value=self.config['auto_flashbang']['delay_ms'], min_value=50, max_value=2000, enabled=is_dopa, callback=self.on_auto_flashbang_delay_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Turn Angle', tag='auto_flashbang_angle_input', default_value=self.config['auto_flashbang']['turn_angle'], min_value=45, max_value=180, enabled=is_dopa, callback=self.on_auto_flashbang_angle_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Sensitivity Multiplier', tag='auto_flashbang_sensitivity_input', default_value=self.config['auto_flashbang']['sensitivity_multiplier'], min_value=0.5, max_value=9999, step=0.1, enabled=is_dopa, callback=self.on_auto_flashbang_sensitivity_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Return Delay(ms)', tag='auto_flashbang_return_delay_input', default_value=self.config['auto_flashbang']['return_delay'], min_value=100, max_value=2000, enabled=is_dopa, callback=self.on_auto_flashbang_return_delay_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Use Curve Movement', tag='auto_flashbang_curve_checkbox', default_value=self.config['auto_flashbang']['use_curve'], enabled=is_dopa, callback=self.on_auto_flashbang_curve_change)
                                dpg.add_input_float(label='Curve Speed', tag='auto_flashbang_curve_speed_input', default_value=self.config['auto_flashbang']['curve_speed'], min_value=0.1, max_value=2.0, step=0.1, enabled=is_dopa, callback=self.on_auto_flashbang_curve_speed_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Control Points', tag='auto_flashbang_curve_knots_input', default_value=self.config['auto_flashbang']['curve_knots'], min_value=5, max_value=50, enabled=is_dopa, callback=self.on_auto_flashbang_curve_knots_change, width=self.scaled_width_normal)
                            dpg.add_text('Filter Conditions (Adjust these parameters to change trigger sensitivity)')
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Min Confidence', tag='auto_flashbang_min_confidence_input', default_value=self.config['auto_flashbang']['min_confidence'], min_value=0.1, max_value=0.9, step=0.05, format='%.2f', enabled=is_dopa, callback=self.on_auto_flashbang_min_confidence_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Min Size(pixels)', tag='auto_flashbang_min_size_input', default_value=self.config['auto_flashbang']['min_size'], min_value=1, max_value=50, enabled=is_dopa, callback=self.on_auto_flashbang_min_size_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_button(label='Test Left Turn', tag='auto_flashbang_test_left_button', enabled=is_dopa, callback=self.on_test_flashbang_left)
                                dpg.add_button(label='Test Right Turn', tag='auto_flashbang_test_right_button', enabled=is_dopa, callback=self.on_test_flashbang_right)
                                dpg.add_button(label='Debug Info', tag='auto_flashbang_debug_button', enabled=is_dopa, callback=self.on_flashbang_debug_info)
                        with dpg.tab(tag='driver_settings'):
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(label='Move Curve', default_value=self.config['is_curve'], callback=self.on_is_curve_change)
                                dpg.add_checkbox(label='Compensation Curve', default_value=self.config['is_curve_uniform'], callback=self.on_is_curve_uniform_change)
                                dpg.add_input_int(label='Horizontal Boundary', default_value=self.config['offset_boundary_x'], callback=self.on_offset_boundary_x_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Vertical Boundary', default_value=self.config['offset_boundary_y'], callback=self.on_offset_boundary_y_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_int(label='Control Points', default_value=self.config['knots_count'], callback=self.on_knots_count_change, width=self.scaled_width_normal)
                                dpg.add_input_float(label='Distortion Mean', default_value=self.config['distortion_mean'], callback=self.on_distortion_mean_change, width=self.scaled_width_normal)
                                dpg.add_input_float(label='Distortion StdDev', default_value=self.config['distortion_st_dev'], callback=self.on_distortion_st_dev_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(label='Distortion Frequency', default_value=self.config['distortion_frequency'], callback=self.on_distortion_frequency_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='Path Points Total', default_value=self.config['target_points'], callback=self.on_target_points_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='KM Box VID', default_value=self.config['km_box_vid'], callback=self.on_km_box_vid_change, width=self.scaled_width_small)
                                dpg.add_input_text(label='KM Box PID', default_value=self.config['km_box_pid'], callback=self.on_km_box_pid_change, width=self.scaled_width_small)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='KM Net IP', default_value=self.config['km_net_ip'], callback=self.on_km_net_ip_change, width=self.scaled_width_large)
                                dpg.add_input_text(label='KM Net Port', default_value=self.config['km_net_port'], callback=self.on_km_net_port_change, width=self.scaled_width_small)
                                dpg.add_input_text(label='KM Net UUID', default_value=self.config['km_net_uuid'], callback=self.on_km_net_uuid_change, width=self.scaled_width_medium)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='DHZ IP', default_value=self.config['dhz_ip'], callback=self.on_dhz_ip_change, width=self.scaled_width_large)
                                dpg.add_input_int(label='DHZ Port', default_value=self.config['dhz_port'], callback=self.on_dhz_port_change, width=self.scaled_width_normal)
                                dpg.add_input_int(label='DHZ RANDOM', default_value=self.config['dhz_random'], callback=self.on_dhz_random_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='CatBox IP', default_value=self.config['catbox_ip'], callback=self.on_catbox_ip_change, width=self.scaled_width_large)
                                dpg.add_input_int(label='CatBox Port', default_value=self.config['catbox_port'], callback=self.on_catbox_port_change, width=self.scaled_width_normal)
                                dpg.add_input_text(label='CatBox UUID', default_value=self.config['catbox_uuid'], callback=self.on_catbox_uuid_change, width=self.scaled_width_medium)
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label='COM', default_value=self.config['km_com'], callback=self.on_km_com_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                dpg.add_combo(label='Move Method', items=['send_input', 'dhz', 'km_net', 'pnmh', 'km_box_a', 'logitech', 'makcu', 'catbox'], default_value=self.config['move_method'], callback=self.on_move_method_change, width=self.scaled_width_large)
                        with dpg.tab(tag='bypass_settings'):
                            with dpg.group(horizontal=True):
                                self.mask_left_checkbox = dpg.add_checkbox(label='Mask Left', default_value=self.config['mask_left'], callback=self.on_mask_left_change)
                                self.mask_right_checkbox = dpg.add_checkbox(label='Mask Right', default_value=self.config['mask_right'], callback=self.on_mask_right_change)
                                self.mask_middle_checkbox = dpg.add_checkbox(label='Mask Middle', default_value=self.config['mask_middle'], callback=self.on_mask_middle_change)
                                self.mask_side1_checkbox = dpg.add_checkbox(label='Mask Side1', default_value=self.config['mask_side1'], callback=self.on_mask_side1_change)
                                self.mask_side2_checkbox = dpg.add_checkbox(label='Mask Side2', default_value=self.config['mask_side2'], callback=self.on_mask_side2_change)
                            with dpg.group(horizontal=True):
                                self.mask_x_checkbox = dpg.add_checkbox(label='Mask X Axis', default_value=self.config['mask_x'], callback=self.on_mask_x_change)
                                self.mask_y_checkbox = dpg.add_checkbox(label='Mask Y Axis', default_value=self.config['mask_y'], callback=self.on_mask_y_change)
                                self.aim_mask_x_checkbox = dpg.add_checkbox(label='Aim Mask X', default_value=self.config['aim_mask_x'], callback=self.on_aim_mask_x_change)
                                self.aim_mask_y_checkbox = dpg.add_checkbox(label='Aim Mask Y', default_value=self.config['aim_mask_y'], callback=self.on_aim_mask_y_change)
                                self.mask_wheel_checkbox = dpg.add_checkbox(label='Mask Wheel', default_value=self.config['mask_wheel'], callback=self.on_mask_wheel_change)
                        with dpg.tab(tag='strafe_settings'):
                            self.right_down_checkbox = dpg.add_checkbox(label='Check Right Button', callback=self.on_right_down_change)
                            with dpg.group(horizontal=True):
                                with dpg.group() as self.dpg_games_tag:
                                    self.render_games_combo()
                                dpg.add_button(label='Delete Game', callback=self.on_delete_game_click, width=self.scaled_width_60)
                                dpg.add_input_text(label='Game Name', callback=self.on_game_name_change, width=self.scaled_width_60)
                                dpg.add_button(label='Add Game', callback=self.on_add_game_click, width=self.scaled_width_60)
                            with dpg.group(horizontal=True):
                                with dpg.group() as self.dpg_guns_tag:
                                    self.render_guns_combo()
                                dpg.add_button(label='Delete Gun', callback=self.on_delete_gun_click, width=self.scaled_width_60)
                                dpg.add_input_text(label='Gun Name', callback=self.on_gun_name_change, width=self.scaled_width_60)
                                dpg.add_button(label='Add Gun', callback=self.on_add_gun_click, width=self.scaled_width_60)
                            with dpg.group(horizontal=True):
                                with dpg.group() as self.dpg_stages_tag:
                                    self.render_stages_combo()
                                number = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['number']
                                x = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][0]
                                y = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][1]
                            with dpg.group(horizontal=True):
                                self.number_input = dpg.add_input_int(label='Count', callback=self.on_number_change, default_value=number, width=self.scaled_width_normal)
                                self.x_input = dpg.add_input_float(label='X', step=0.01, callback=self.on_x_change, default_value=x, width=self.scaled_width_normal)
                                self.y_input = dpg.add_input_float(label='Y', step=0.01, callback=self.on_y_change, default_value=y, width=self.scaled_width_normal)
                                dpg.add_button(label='Delete Index', callback=self.on_delete_stage_click, width=self.scaled_width_60)
                                dpg.add_button(label='Add Index', callback=self.on_add_stage_click, width=self.scaled_width_60)
                            dpg.add_separator()
                            with dpg.collapsing_header(label='mouse_re Trajectory Recoil', default_open=True):
                                with dpg.group(horizontal=True):
                                    dpg.add_checkbox(label='Enable mouse_re Trajectory Recoil', default_value=self.config['recoil']['use_mouse_re_trajectory'], callback=self.on_use_mouse_re_trajectory_change)
                                    dpg.add_input_float(label='Replay Speed', default_value=self.config['recoil']['replay_speed'], step=0.1, min_value=0.1, max_value=5.0, format='%.2f', width=self.scaled_width_normal, callback=self.on_mouse_re_replay_speed_change)
                                    dpg.add_input_float(label='Pixel Enhancement Ratio', default_value=self.config['recoil']['pixel_enhancement_ratio'], step=0.1, min_value=0.1, max_value=3.0, format='%.2f', width=self.scaled_width_normal, callback=self.on_mouse_re_pixel_enhancement_change)
                                dpg.add_text('mouse_re Recoil Config:', color=(150, 150, 150))
                                with dpg.group(horizontal=True, tag='mouse_re_combos_group'):
                                    pass
                                with dpg.group(horizontal=True):
                                    dpg.add_button(label='Import Trajectory File', callback=self.on_import_mouse_re_trajectory_click, width=self.scaled_width_normal)
                                    dpg.add_button(label='Clear Mapping', callback=self.on_clear_mouse_re_mapping_click, width=self.scaled_width_normal)
                                dpg.add_text('Note: Supports loading JSON files generated by mouse_re.py, hold left button to replay trajectory for recoil')
                                dpg.add_separator()
                                dpg.add_text('Current Status:', color=(150, 150, 150))
                                dpg.add_text('Switch: OFF', tag='mouse_re_switch_text')
                                dpg.add_text('Mapping File: None', wrap=self.scaled_width_xlarge, tag='mouse_re_file_text')
                                dpg.add_text('Trajectory Points: 0', tag='mouse_re_points_text')
                        with dpg.tab(tag='config_settings'):
                            model_params_group = dpg.add_collapsing_header(label='Model Controller Parameters', default_open=True)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                with dpg.group() as self.dpg_group_tag:
                                    self.render_group_combo()
                                dpg.add_button(label='Delete Group', callback=self.on_delete_group_click, width=self.scaled_width_60)
                                dpg.add_input_text(label='Group Name', callback=self.on_group_name_change, width=self.scaled_width_60)
                                dpg.add_button(label='Add Group', callback=self.on_add_group_click, width=self.scaled_width_60)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.is_trt_checkbox = dpg.add_checkbox(label='TRT', callback=self.on_is_trt_change)
                                self.is_v8_checkbox = dpg.add_checkbox(label='V8', callback=self.on_is_v8_change)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.infer_model_input = dpg.add_input_text(label='Inference Model', default_value=self.config['groups'][self.group]['infer_model'], callback=self.on_infer_model_change, width=self.scaled_width_xlarge + 50)
                                dpg.add_button(label='Select Model', callback=self.on_select_model_click, width=100)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.auto_y_checkbox = dpg.add_checkbox(label='Long Press No Lock Y', callback=self.on_auto_y_change)
                                self.long_press_duration_input = dpg.add_input_int(label='Long Press Threshold', default_value=self.config['groups'][self.group]['long_press_duration'], callback=self.on_long_press_duration_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.target_switch_delay_input = dpg.add_input_int(label='Target Switch Delay(ms)', default_value=0, min_value=0, max_value=2000, callback=self.on_target_switch_delay_change, width=self.scaled_width_normal)
                                self.target_reference_class_combo = dpg.add_combo(label='Target Reference Class', items=['Class0'], default_value='Class0', callback=self.on_target_reference_class_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                with dpg.group() as self.aim_key_combo_group:
                                    self.render_key_combo()
                                dpg.add_button(label='Delete Key', callback=self.on_delete_key_click, width=self.scaled_width_60)
                                dpg.add_input_text(label='Key Name', callback=self.on_key_name_change, width=self.scaled_width_60)
                                dpg.add_button(label='Add Key', callback=self.on_add_key_click, width=self.scaled_width_60)
                            dpg.add_separator()
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.class_priority_input = dpg.add_input_text(label='Class Priority', hint='Format: 0-1-2-3-4', default_value='', callback=self.on_class_priority_change, width=self.scaled_width_large)
                                dpg.add_text('Inference Classes:')
                                self.checkbox_group_tag = dpg.add_group(horizontal=True)
                                class_num = self.get_current_class_num()
                                class_ary = list(range(class_num))
                                self.create_checkboxes(class_ary)
                                self.update_class_aim_combo()
                                self.update_target_reference_class_combo()
                            with dpg.group(horizontal=True, parent=model_params_group):
                                dpg.add_text('Class Aim Config:')
                                self.class_aim_combo = dpg.add_combo(items=[], label='Select Class', callback=self.on_class_aim_combo_change, width=self.scaled_width_normal, default_value='')
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.confidence_threshold_input = dpg.add_input_float(label='Confidence Threshold', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_confidence_threshold_change, width=self.scaled_width_normal)
                                self.iou_t_input = dpg.add_input_float(label='IOU', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_iou_t_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.aim_bot_position_input = dpg.add_input_float(label='Aim Position', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_aim_bot_position_change, width=self.scaled_width_normal)
                                self.aim_bot_position2_input = dpg.add_input_float(label='Aim Position2', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_aim_bot_position2_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.min_position_offset_input = dpg.add_input_int(label='Min Offset', callback=self.on_min_position_offset_change, width=self.scaled_width_normal)
                                self.aim_bot_scope_input = dpg.add_input_int(label='Aim Scope', callback=self.on_aim_bot_scope_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=model_params_group):
                                self.dynamic_scope_enabled_input = dpg.add_checkbox(label='Dynamic Scope', callback=self.on_dynamic_scope_enabled_change)
                                self.dynamic_scope_min_scope_input = dpg.add_input_int(label='Min Scope', min_value=0, max_value=2000, callback=self.on_dynamic_scope_min_scope_change, width=self.scaled_width_normal)
                                self.dynamic_scope_shrink_ms_input = dpg.add_input_int(label='Shrink Duration', min_value=0, max_value=5000, callback=self.on_dynamic_scope_shrink_ms_change, width=self.scaled_width_normal)
                                self.dynamic_scope_recover_ms_input = dpg.add_input_int(label='Recover Duration', min_value=0, max_value=5000, callback=self.on_dynamic_scope_recover_ms_change, width=self.scaled_width_normal)
                            self.pid_params_group = dpg.add_collapsing_header(label='PID Controller Parameters', default_open=True)
                            dpg.add_text('PID Parameters', parent=self.pid_params_group)
                            with dpg.group(horizontal=True, parent=self.pid_params_group):
                                self.pid_kp_x_input = dpg.add_input_float(label='X Proportional', default_value=0.4, step=0.0001, format='%.4f', callback=self.on_pid_kp_x_change, width=self.scaled_width_normal)
                                self.pid_ki_x_input = dpg.add_input_float(label='X Integral', default_value=0.0, step=0.0001, format='%.4f', callback=self.on_pid_ki_x_change, width=self.scaled_width_normal)
                                self.pid_kd_x_input = dpg.add_input_float(label='X Derivative', default_value=0.002, step=0.0001, format='%.4f', callback=self.on_pid_kd_x_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=self.pid_params_group):
                                self.pid_kp_y_input = dpg.add_input_float(label='Y Proportional', default_value=0.4, step=0.0001, format='%.4f', callback=self.on_pid_kp_y_change, width=self.scaled_width_normal)
                                self.pid_ki_y_input = dpg.add_input_float(label='Y Integral', default_value=0, step=0.0001, format='%.4f', callback=self.on_pid_ki_y_change, width=self.scaled_width_normal)
                                self.pid_kd_y_input = dpg.add_input_float(label='Y Derivative', default_value=0.002, step=0.0001, format='%.4f', callback=self.on_pid_kd_y_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=self.pid_params_group):
                                self.pid_integral_limit_x_input = dpg.add_input_float(label='X Limit', default_value=0.0, min_value=0.0, max_value=100.0, step=0.0001, format='%.4f', callback=self.on_pid_integral_limit_x_change, width=self.scaled_width_normal)
                                self.smooth_x_input = dpg.add_input_float(label='X Smooth', default_value=0, min_value=0.0, max_value=1000.0, step=0.0001, format='%.4f', callback=self.on_smooth_x_change, width=self.scaled_width_normal)
                                self.smooth_algorithm_input = dpg.add_input_float(label='Smooth Algorithm', default_value=1.0, min_value=0.1, max_value=10.0, step=0.0001, format='%.4f', callback=self.on_smooth_algorithm_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=self.pid_params_group):
                                self.pid_integral_limit_y_input = dpg.add_input_float(label='Y Limit', default_value=0.0, min_value=0.0, max_value=100.0, step=0.0001, format='%.4f', callback=self.on_pid_integral_limit_y_change, width=self.scaled_width_normal)
                                self.smooth_y_input = dpg.add_input_float(label='Y Smooth', default_value=0, min_value=0.0, max_value=1000.0, step=0.0001, format='%.4f', callback=self.on_smooth_y_change, width=self.scaled_width_normal)
                                self.smooth_deadzone_input = dpg.add_input_float(label='Smooth Deadzone', default_value=0.0, min_value=0.0, max_value=50.0, step=0.0001, format='%.4f', callback=self.on_smooth_deadzone_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True, parent=self.pid_params_group):
                                self.move_deadzone_input = dpg.add_input_float(label='Move Deadzone', default_value=1.0, min_value=0.0, max_value=10.0, step=0.0001, format='%.4f', callback=self.on_move_deadzone_change, width=self.scaled_width_normal)
                            trigger_setting_tag = dpg.add_collapsing_header(label='Trigger Config', default_open=True)
                            with dpg.group(parent=trigger_setting_tag):
                                with dpg.group(horizontal=True):
                                    self.status_input = dpg.add_checkbox(label='Auto Trigger', callback=self.on_status_change)
                                    self.continuous_trigger_input = dpg.add_checkbox(label='Continuous Trigger', callback=self.on_continuous_trigger_change)
                                    self.trigger_recoil_input = dpg.add_checkbox(label='Trigger Recoil', callback=self.on_trigger_recoil_change)
                            with dpg.group(horizontal=True):
                                self.start_delay_input = dpg.add_input_int(label='Trigger Delay', min_value=0, max_value=1000, callback=self.on_start_delay_change, width=self.scaled_width_normal)
                                self.press_delay_input = dpg.add_input_int(label='Press Duration', min_value=0, max_value=1000, callback=self.on_press_delay_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                self.end_delay_input = dpg.add_input_int(label='Trigger Cooldown', min_value=0, max_value=1000, callback=self.on_end_delay_change, width=self.scaled_width_normal)
                                self.random_delay_input = dpg.add_input_int(label='Random Delay', min_value=0, max_value=1000, callback=self.on_random_delay_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                self.x_trigger_scope_input = dpg.add_input_float(label='X Trigger Scope', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_x_trigger_scope_change, width=self.scaled_width_normal)
                                self.y_trigger_scope_input = dpg.add_input_float(label='Y Trigger Scope', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_y_trigger_scope_change, width=self.scaled_width_normal)
                            with dpg.group(horizontal=True):
                                self.x_trigger_offset_input = dpg.add_input_float(label='X Trigger Offset', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_x_trigger_offset_change, width=self.scaled_width_normal)
                                self.y_trigger_offset_input = dpg.add_input_float(label='Y Trigger Offset', min_value=0.0, max_value=1.0, step=0.01, callback=self.on_y_trigger_offset_change, width=self.scaled_width_normal)
                            with dpg.drawlist(width=self.scaled_width_small, height=self.scaled_height_normal):
                                dpg.draw_rectangle((0, 0), (50, 100), color=(255, 255, 255))
                                x_trigger_offset = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_offset']
                                y_trigger_offset = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_offset']
                                x_trigger_scope = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_scope']
                                y_trigger_scope = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_scope']
                                x_trigger_offset = x_trigger_offset * 50
                                y_trigger_offset = y_trigger_offset * 100
                                dpg.draw_rectangle((x_trigger_offset, y_trigger_offset), (x_trigger_offset + 50 * x_trigger_scope, y_trigger_offset + 100 * y_trigger_scope), fill=(255, 0, 0), tag='small_rect')
                            self.update_group_inputs()
                    with dpg.group(horizontal=True):
                        self.start_button_tag = dpg.add_button(label='Start', callback=self.on_start_button_click, width=self.scaled_width_normal)
                        dpg.add_button(label='Save Config', callback=self.on_save_button_click, width=self.scaled_width_normal)
                        dpg.add_text('', tag='output_text')
            with dpg.group():
                dpg.add_spacer(height=5)
                with dpg.group(horizontal=True):
                    version_text = dpg.add_text(f'Version: {VERSION} {UPDATE_TIME}')
                    with dpg.theme() as version_theme, dpg.theme_component(dpg.mvText):
                        dpg.add_theme_color(dpg.mvThemeCol_Text, (150, 150, 150, 255))
                    dpg.bind_item_theme(version_text, version_theme)
            dpg.show_viewport()
            dpg.set_primary_window(self.window_tag, True)
            self.update_sensitivity_display()
            self.render_mouse_re_games_combo()
            self.render_mouse_re_guns_combo()
            self.update_mouse_re_ui_status()
            dpg.start_dearpygui()
        self.running = False
        self.disconnect_device()
        self.close_screenshot()
        print('Exit')
        dpg.destroy_context()

    def on_start_button_click(self, sender, app_data):
        current_label = dpg.get_item_label(sender)
        if current_label == 'Start':
            dpg.configure_item(sender, label='Do Not Click!!!')
            self.running = True
            if self.config['groups'][self.group].get('is_trt', False) and TENSORRT_AVAILABLE:
                print('TRT mode detected, checking engine file...')
                current_model = self.config['groups'][self.group]['infer_model']
                engine_path = os.path.splitext(current_model)[0] + '.engine'
                if not os.path.exists(engine_path):
                    print(f'Engine file does not exist: {engine_path}')
                    print('Starting TRT engine conversion...')
                    dpg.set_value('output_text', 'Converting TRT engine, please wait...')
                    if current_model.endswith('.onnx'):
                        print('Converting TRT engine from ONNX file...')
                        from inference_engine import auto_convert_engine
                        if auto_convert_engine(current_model):
                            print(f'TRT engine conversion successful: {engine_path}')
                            self.config['groups'][self.group]['infer_model'] = engine_path
                            dpg.set_value(self.infer_model_input, engine_path)
                        else:
                            print('TRT engine conversion failed, will use original model')
                            self.config['groups'][self.group]['is_trt'] = False
                            dpg.set_value(self.is_trt_checkbox, False)
                else:
                    print(f'Found existing engine file: {engine_path}')
                    self.config['groups'][self.group]['infer_model'] = engine_path
                    dpg.set_value(self.infer_model_input, engine_path)
            if self.go():
                dpg.configure_item(sender, label='Stop')
            else:
                dpg.configure_item(sender, label='Start')
        else:
            dpg.configure_item(sender, label='Do Not Click!!!')
            self.running = False
            if self.timer_id != 0:
                self.time_kill_event(self.timer_id)
                self.timer_id = 0
            if self.timer_id2 != 0:
                self.time_kill_event(self.timer_id2)
                self.timer_id2 = 0
            self.close_screenshot()
            self.unmask_all()
            self.stop_listen()
            dpg.configure_item(sender, label='Start')

    def on_save_button_click(self, sender, app_data):
        self.save_config_callback()

    def on_game_sensitivity_change(self, sender, app_data):
        return

    def on_mouse_dpi_change(self, sender, app_data):
        return

    def update_sensitivity_display(self):
        return

    def calculate_sensitivity_multiplier(self):
        return 1.0

    def on_infer_debug_change(self, sender, app_data):
        self.config['infer_debug'] = app_data
        print(f"changed to: {self.config['infer_debug']}")

    def on_is_curve_change(self, sender, app_data):
        self.config['is_curve'] = app_data
        print(f"changed to: {self.config['is_curve']}")

    def on_is_curve_uniform_change(self, sender, app_data):
        self.config['is_curve_uniform'] = app_data
        print(f"changed to: {self.config['is_curve_uniform']}")

    def on_distance_scoring_weight_change(self, sender, app_data):
        self.config['distance_scoring_weight'] = app_data
        self.init_target_priority()
        print(f"changed to: {self.config['distance_scoring_weight']}")

    def on_center_scoring_weight_change(self, sender, app_data):
        self.config['center_scoring_weight'] = app_data
        self.init_target_priority()
        print(f"changed to: {self.config['center_scoring_weight']}")

    def on_size_scoring_weight_change(self, sender, app_data):
        self.config['size_scoring_weight'] = app_data
        self.init_target_priority()
        print(f"changed to: {self.config['size_scoring_weight']}")

    def on_print_fps_change(self, sender, app_data):
        self.config['print_fps'] = app_data
        print(f"changed to: {self.config['print_fps']}")

    def on_show_motion_speed_change(self, sender, app_data):
        self.config['show_motion_speed'] = app_data
        self.refresh_controller_params()
        print(f"changed to: {self.config['show_motion_speed']}")

    def on_is_show_curve_change(self, sender, app_data):
        self.config['is_show_curve'] = app_data
        print(f"changed to: {self.config['is_show_curve']}")

    def on_enable_parallel_processing_change(self, sender, app_data):
        self.config['enable_parallel_processing'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('enable_parallel_processing', app_data)
        print(f"changed to: {self.config['enable_parallel_processing']}")

    def on_turbo_mode_change(self, sender, app_data):
        self.config['turbo_mode'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('turbo_mode', app_data)
        print(f"Turbo mode: {('enabled' if app_data else 'disabled')}")

    def on_skip_frame_processing_change(self, sender, app_data):
        self.config['skip_frame_processing'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('skip_frame_processing', app_data)
        print(f"Skip frame processing: {('enabled' if app_data else 'disabled')}")

    def on_is_show_down_change(self, sender, app_data):
        self.config['is_show_down'] = app_data
        print(f"changed to: {self.config['is_show_down']}")

    def on_is_obs_change(self, sender, app_data):
        self.config['is_obs'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('is_obs', app_data)
        print(f"changed to: {self.config['is_obs']}")

    def on_is_cjk_change(self, sender, app_data):
        self.config['is_cjk'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('is_cjk', app_data)
        print(f"changed to: {self.config['is_cjk']}")

    def on_obs_ip_change(self, sender, app_data):
        self.config['obs_ip'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('obs_ip', app_data)
        print(f"changed to: {self.config['obs_ip']}")

    def on_cjk_device_id_change(self, sender, app_data):
        self.config['cjk_device_id'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('cjk_device_id', app_data)
        print(f"changed to: {self.config['cjk_device_id']}")

    def on_cjk_fps_change(self, sender, app_data):
        self.config['cjk_fps'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('cjk_fps', app_data)
        print(f"changed to: {self.config['cjk_fps']}")

    def on_cjk_resolution_change(self, sender, app_data):
        self.config['cjk_resolution'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('cjk_resolution', app_data)
        print(f"changed to: {self.config['cjk_resolution']}")

    def on_cjk_crop_size_change(self, sender, app_data):
        self.config['cjk_crop_size'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('cjk_crop_size', app_data)
        print(f"changed to: {self.config['cjk_crop_size']}")

    def on_cjk_fourcc_format_change(self, sender, app_data):
        self.config['cjk_fourcc_format'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('cjk_fourcc_format', app_data)
        print(f'Capture card video codec format set to: {app_data}')

    def on_obs_fps_change(self, sender, app_data):
        self.config['obs_fps'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('obs_fps', app_data)
        print(f"changed to: {self.config['obs_fps']}")

    def on_obs_port_change(self, sender, app_data):
        self.config['obs_port'] = app_data
        if self.screenshot_manager:
            self.screenshot_manager.update_config('obs_port', app_data)
        print(f"changed to: {self.config['obs_port']}")

    def on_offset_boundary_x_change(self, sender, app_data):
        self.config['offset_boundary_x'] = app_data
        print(f"changed to: {self.config['offset_boundary_x']}")

    def on_offset_boundary_y_change(self, sender, app_data):
        self.config['offset_boundary_y'] = app_data
        print(f"changed to: {self.config['offset_boundary_y']}")

    def on_knots_count_change(self, sender, app_data):
        self.config['knots_count'] = app_data
        print(f"changed to: {self.config['knots_count']}")

    def on_distortion_mean_change(self, sender, app_data):
        self.config['distortion_mean'] = app_data
        print(f"changed to: {self.config['distortion_mean']}")

    def on_distortion_st_dev_change(self, sender, app_data):
        self.config['distortion_st_dev'] = app_data
        print(f"changed to: {self.config['distortion_st_dev']}")

    def on_distortion_frequency_change(self, sender, app_data):
        self.config['distortion_frequency'] = app_data
        print(f"changed to: {self.config['distortion_frequency']}")

    def on_target_points_change(self, sender, app_data):
        self.config['target_points'] = app_data
        print(f"changed to: {self.config['target_points']}")

    def on_km_box_vid_change(self, sender, app_data):
        self.config['km_box_vid'] = app_data
        print(f"changed to: {self.config['km_box_vid']}")

    def on_km_box_pid_change(self, sender, app_data):
        self.config['km_box_pid'] = app_data
        print(f"changed to: {self.config['km_box_pid']}")

    def on_km_net_ip_change(self, sender, app_data):
        self.config['km_net_ip'] = app_data
        print(f"changed to: {self.config['km_net_ip']}")

    def on_km_net_port_change(self, sender, app_data):
        self.config['km_net_port'] = app_data
        print(f"changed to: {self.config['km_net_port']}")

    def on_km_net_uuid_change(self, sender, app_data):
        self.config['km_net_uuid'] = app_data
        print(f"changed to: {self.config['km_net_uuid']}")

    def on_dhz_ip_change(self, sender, app_data):
        self.config['dhz_ip'] = app_data
        print(f"changed to: {self.config['dhz_ip']}")

    def on_dhz_port_change(self, sender, app_data):
        self.config['dhz_port'] = app_data
        print(f"changed to: {self.config['dhz_port']}")

    def on_dhz_random_change(self, sender, app_data):
        self.config['dhz_random'] = app_data
        print(f"changed to: {self.config['dhz_random']}")

    def on_catbox_ip_change(self, sender, app_data):
        self.config['catbox_ip'] = app_data
        print(f"changed to: {self.config['catbox_ip']}")

    def on_catbox_port_change(self, sender, app_data):
        self.config['catbox_port'] = app_data
        print(f"changed to: {self.config['catbox_port']}")

    def on_catbox_uuid_change(self, sender, app_data):
        self.config['catbox_uuid'] = app_data
        print(f"changed to: {self.config['catbox_uuid']}")

    def on_km_com_change(self, sender, app_data):
        self.config['km_com'] = app_data
        print(f"changed to: {self.config['km_com']}")

    def on_move_method_change(self, sender, app_data):
        self.config['move_method'] = app_data
        print(f"changed to: {self.config['move_method']}")

    def on_group_change(self, sender, app_data):
        self.select_key = ''
        self.config['group'] = app_data
        self.group = app_data
        self.refresh_engine()
        class_num = self.get_current_class_num()
        class_ary = list(range(class_num))
        self.create_checkboxes(class_ary)
        self.update_class_aim_combo()
        self.update_target_reference_class_combo()
        self.aim_keys_dist = self.config['groups'][app_data]['aim_keys']
        self.aim_key = list(self.aim_keys_dist.keys())
        self.render_key_combo()
        self.update_group_inputs()
        self.update_auto_flashbang_ui_state()
        print(f"changed to: {self.config['group']}")

    def on_confidence_threshold_change(self, sender, app_data):
        if 'class_aim_positions' not in self.config['groups'][self.group]['aim_keys'][self.select_key]:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'] = {}
        if self.current_selected_class not in self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions']:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0, 'confidence_threshold': 0.5, 'iou_t': 1.0}
        self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class]['confidence_threshold'] = round(app_data, 4)
        print(f'Class {self.current_selected_class} confidence threshold changed to: {round(app_data, 4)}')

    def on_iou_t_change(self, sender, app_data):
        if 'class_aim_positions' not in self.config['groups'][self.group]['aim_keys'][self.select_key]:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'] = {}
        if self.current_selected_class not in self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions']:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0, 'confidence_threshold': 0.5, 'iou_t': 1.0}
        self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class]['iou_t'] = round(app_data, 4)
        print(f'Class {self.current_selected_class} IOU threshold changed to: {round(app_data, 4)}')

    def on_infer_model_change(self, sender, app_data):
        if app_data != '' and os.path.exists(app_data):
            if app_data.endswith('.onnx'):
                self.config['groups'][self.group]['original_infer_model'] = app_data
            elif app_data.endswith('.engine'):
                onnx_path = os.path.splitext(app_data)[0] + '.onnx'
                if os.path.exists(onnx_path):
                    self.config['groups'][self.group]['original_infer_model'] = onnx_path
                else:
                    print(f'Warning: Cannot find corresponding ONNX model: {onnx_path}, TRT mode switching may not work properly')
            self.config['groups'][self.group]['infer_model'] = app_data
            self.refresh_engine()
            class_num = self.get_current_class_num()
            class_ary = list(range(class_num))
            self.create_checkboxes(class_ary)
            self.update_class_aim_combo()
            self.update_target_reference_class_combo()
            self.update_auto_flashbang_ui_state()
            print(app_data + ' model file exists, updated')
        else:
            print(app_data + ' model file does not exist, please check the path')

    def on_select_model_click(self, sender, app_data):
        """Select model file callback function"""
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            filetypes = [('ONNX Model', '*.onnx'), ('TensorRT Engine', '*.engine'), ('All Files', '*.*')]
            file_path = filedialog.askopenfilename(title='Select Model File', filetypes=filetypes, parent=root)
            root.destroy()
            if file_path:
                valid_extensions = ['.onnx', '.engine']
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in valid_extensions:
                    if hasattr(self, 'is_trt_checkbox') and self.is_trt_checkbox is not None:
                        current_trt_value = dpg.get_value(self.is_trt_checkbox)
                        if current_trt_value:
                            dpg.set_value(self.is_trt_checkbox, False)
                            self.config['groups'][self.group]['is_trt'] = False
                    dpg.set_value(self.infer_model_input, file_path)
                    self.on_infer_model_change(self.infer_model_input, file_path)
                else:
                    print(f'Unsupported file format: {file_ext}')
                    print('Supported formats: .onnx, .engine')
        except Exception as e:
            print(f'Error selecting model file: {e}')

    def on_aim_bot_position_change(self, sender, app_data):
        if 'class_aim_positions' not in self.config['groups'][self.group]['aim_keys'][self.select_key]:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'] = {}
        if self.current_selected_class not in self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions']:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0}
        self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class]['aim_bot_position'] = round(app_data, 4)
        print(f'Class {self.current_selected_class} aim position 1 changed to: {round(app_data, 4)}')

    def on_aim_bot_position2_change(self, sender, app_data):
        if 'class_aim_positions' not in self.config['groups'][self.group]['aim_keys'][self.select_key]:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'] = {}
        if self.current_selected_class not in self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions']:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0}
        self.config['groups'][self.group]['aim_keys'][self.select_key]['class_aim_positions'][self.current_selected_class]['aim_bot_position2'] = round(app_data, 4)
        print(f'Class {self.current_selected_class} aim position 2 changed to: {round(app_data, 4)}')

    def on_class_priority_change(self, sender, app_data):
        """Class priority input callback function"""
        priority_text = app_data.strip()
        print(f'Class priority input: {priority_text}')
        priority_order = self.parse_class_priority(priority_text)
        if priority_order is not None:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['class_priority_order'] = priority_order
            print(f'Class priority updated: {priority_order}')
        else:
            print(f'Class priority format error: {priority_text}')

    def parse_class_priority(self, priority_text):
        """Parse class priority string"""
        if not priority_text:
            return []
        try:
            import re
            parts = re.split('[-,\\s]+', priority_text.strip())
            priority_order = []
            seen = set()
            for part in parts:
                if part.strip():
                    try:
                        class_id = int(part.strip())
                        if class_id not in seen:
                            priority_order.append(class_id)
                            seen.add(class_id)
                    except ValueError:
                        return
            else:
                return priority_order
        except Exception:
            return None

    def format_class_priority(self, priority_order):
        """Format priority list to string"""
        return '-'.join(map(str, priority_order)) if priority_order else ''

    def get_class_priority_order(self):
        """Get current key's class priority order"""
        try:
            key_config = self.config['groups'][self.group]['aim_keys'][self.select_key]
            return key_config.get('class_priority_order', [])
        except:
            return []

    def on_class_aim_combo_change(self, sender, app_data):
        """Class selection combo callback function"""
        if app_data:
            self.current_selected_class = app_data.replace('Class', '')
            print(f'Current selected class: {self.current_selected_class}')
            self.update_class_aim_inputs()

    def update_class_aim_inputs(self):
        """Update aim position input values based on currently selected class"""
        if not hasattr(self, 'aim_bot_position_input') or self.aim_bot_position_input is None:
            return None
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        cap = key_cfg.get('class_aim_positions', {})
        if isinstance(cap, list):
            converted = {}
            for i, item in enumerate(cap):
                if isinstance(item, dict):
                    converted[str(i)] = {'aim_bot_position': float(item.get('aim_bot_position', 0.0)), 'aim_bot_position2': float(item.get('aim_bot_position2', 0.0)), 'confidence_threshold': float(item.get('confidence_threshold', 0.5)), 'iou_t': float(item.get('iou_t', 1.0))}
                else:
                    converted[str(i)] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0, 'confidence_threshold': 0.5, 'iou_t': 1.0}
            key_cfg['class_aim_positions'] = converted
        else:
            if not isinstance(cap, dict):
                key_cfg['class_aim_positions'] = {}
        if not self.current_selected_class or not str(self.current_selected_class).isdigit():
            self.current_selected_class = '0'
        if self.current_selected_class not in key_cfg['class_aim_positions']:
            key_cfg['class_aim_positions'][self.current_selected_class] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0, 'confidence_threshold': 0.5, 'iou_t': 1.0}
        class_config = key_cfg['class_aim_positions'][self.current_selected_class]
        import dearpygui.dearpygui as dpg
        dpg.set_value(self.aim_bot_position_input, float(class_config.get('aim_bot_position', 0.0)))
        dpg.set_value(self.aim_bot_position2_input, float(class_config.get('aim_bot_position2', 0.0)))
        if hasattr(self, 'confidence_threshold_input') and self.confidence_threshold_input is not None:
            dpg.set_value(self.confidence_threshold_input, float(class_config.get('confidence_threshold', 0.5)))
        if hasattr(self, 'iou_t_input') and self.iou_t_input is not None:
            dpg.set_value(self.iou_t_input, float(class_config.get('iou_t', 1.0)))

    def update_class_aim_combo(self):
        """Update class combo options"""
        if not hasattr(self, 'class_aim_combo') or self.class_aim_combo is None:
            return None
        try:
            class_num = self.get_current_class_num()
            class_num = int(class_num)
            class_items = [f'Class{i}' for i in range(class_num)]
            import dearpygui.dearpygui as dpg
            dpg.configure_item(self.class_aim_combo, items=class_items)
            if class_items:
                try:
                    current_class_int = int(self.current_selected_class) if self.current_selected_class and self.current_selected_class.isdigit() else (-1)
                    if not self.current_selected_class or current_class_int < 0 or current_class_int >= class_num:
                        self.current_selected_class = '0'
                except (ValueError, TypeError):
                    self.current_selected_class = '0'
                dpg.set_value(self.class_aim_combo, f'Class{self.current_selected_class}')
                self.update_class_aim_inputs()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def on_aim_bot_scope_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['aim_bot_scope'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['aim_bot_scope']}")

    def on_dynamic_scope_enabled_change(self, sender, app_data):
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        if 'dynamic_scope' not in key_cfg:
            key_cfg['dynamic_scope'] = {}
        key_cfg['dynamic_scope']['enabled'] = bool(app_data)

    def on_dynamic_scope_min_ratio_change(self, sender, app_data):
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        if 'dynamic_scope' not in key_cfg:
            key_cfg['dynamic_scope'] = {}
        try:
            v = float(app_data)
        except Exception:
            v = 0.5
        v = max(0.0, min(1.0, v))
        key_cfg['dynamic_scope']['min_ratio'] = v

    def on_dynamic_scope_min_scope_change(self, sender, app_data):
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        if 'dynamic_scope' not in key_cfg:
            key_cfg['dynamic_scope'] = {}
        try:
            v = int(app_data)
        except Exception:
            v = 0
        key_cfg['dynamic_scope']['min_scope'] = max(0, v)

    def on_dynamic_scope_shrink_ms_change(self, sender, app_data):
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        if 'dynamic_scope' not in key_cfg:
            key_cfg['dynamic_scope'] = {}
        try:
            v = int(app_data)
        except Exception:
            v = 300
        key_cfg['dynamic_scope']['shrink_duration_ms'] = max(0, v)

    def on_dynamic_scope_recover_ms_change(self, sender, app_data):
        key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
        if 'dynamic_scope' not in key_cfg:
            key_cfg['dynamic_scope'] = {}
        try:
            v = int(app_data)
        except Exception:
            v = 300
        key_cfg['dynamic_scope']['recover_duration_ms'] = max(0, v)

    def on_min_position_offset_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['min_position_offset'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['min_position_offset']}")

    def on_smoothing_factor_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smoothing_factor'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['smoothing_factor']}")

    def on_base_step_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['base_step'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['base_step']}")

    def on_distance_weight_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['distance_weight'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['distance_weight']}")

    def on_fov_angle_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['fov_angle'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['fov_angle']}")

    def on_history_size_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['history_size'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['history_size']}")

    def on_deadzone_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['deadzone'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['deadzone']}")

    def on_smoothing_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smoothing'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['smoothing']}")

    def on_velocity_decay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['velocity_decay'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['velocity_decay']}")

    def on_current_frame_weight_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['current_frame_weight'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['current_frame_weight']}")

    def on_last_frame_weight_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['last_frame_weight'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['last_frame_weight']}")

    def on_output_scale_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['output_scale_x'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['output_scale_x']}")

    def on_output_scale_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['output_scale_y'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['output_scale_y']}")

    def on_uniform_threshold_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['uniform_threshold'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['uniform_threshold']}")

    def on_min_velocity_threshold_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['min_velocity_threshold'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['min_velocity_threshold']}")

    def on_max_velocity_threshold_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['max_velocity_threshold'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['max_velocity_threshold']}")

    def on_compensation_factor_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['compensation_factor'] = round(app_data, 3)
        self.refresh_controller_params()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['compensation_factor']}")

    def on_overshoot_threshold_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_threshold'] = round(app_data, 1)
        self.refresh_controller_params()
        print(f"Overshoot detection threshold: {self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_threshold']}")

    def on_overshoot_x_factor_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_x_factor'] = round(app_data, 2)
        self.refresh_controller_params()
        print(f"X-axis overshoot suppression factor: {self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_x_factor']}")

    def on_overshoot_y_factor_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_y_factor'] = round(app_data, 2)
        self.refresh_controller_params()
        print(f"Y-axis overshoot suppression factor: {self.config['groups'][self.group]['aim_keys'][self.select_key]['overshoot_y_factor']}")

    def on_status_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['status'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['status']}")

    def on_continuous_trigger_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['continuous'] = app_data
        print(f'Continuous trigger set to: {app_data}')

    def on_trigger_recoil_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['recoil'] = app_data
        print(f'Trigger recoil set to: {app_data}')

    def on_start_delay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['start_delay'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['start_delay']}")

    def on_long_press_duration_change(self, sender, app_data):
        self.config['groups'][self.group]['long_press_duration'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['long_press_duration']}")

    def on_press_delay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['press_delay'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['press_delay']}")

    def on_end_delay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['end_delay'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['end_delay']}")

    def on_random_delay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['random_delay'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['random_delay']}")

    def on_x_trigger_scope_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_scope'] = app_data
        self.update_rect()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_scope']}")

    def on_y_trigger_scope_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_scope'] = app_data
        self.update_rect()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_scope']}")

    def on_x_trigger_offset_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_offset'] = app_data
        self.update_rect()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_offset']}")

    def on_y_trigger_offset_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_offset'] = app_data
        self.update_rect()
        print(f"changed to: {self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_offset']}")

    def update_rect(self):
        x_ratio = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_offset']
        y_ratio = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_offset']
        w_ratio = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_scope']
        h_ratio = self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_scope']
        x = x_ratio * 50
        y = y_ratio * 100
        w = w_ratio * 50
        h = h_ratio * 100
        dpg.configure_item('small_rect', pmin=[x, y], pmax=[x + w, y + h])

    def render_games_combo(self):
        if self.games_combo is not None:
            dpg.delete_item(self.games_combo)
        self.games_combo = dpg.add_combo(label='Game', items=list(self.config['games'].keys()), default_value=self.config['picked_game'], callback=self.on_games_change, width=self.scaled_width_large, parent=self.dpg_games_tag)

    def render_guns_combo(self):
        if self.guns_combo is not None:
            dpg.delete_item(self.guns_combo)
        guns = list(self.config['games'][self.picked_game].keys())
        if self.picked_gun not in guns:
            self.picked_gun = guns[0]
        self.guns_combo = dpg.add_combo(label='Gun', items=guns, default_value=self.picked_gun, callback=self.on_guns_change, width=self.scaled_width_large, parent=self.dpg_guns_tag)

    def render_stages_combo(self):
        if self.stages_combo is not None:
            dpg.delete_item(self.stages_combo)
        stages = self.config['games'][self.picked_game][self.picked_gun]
        stage_len = len(self.config['games'][self.picked_game][self.picked_gun])
        stages_obj = {}
        for i in range(stage_len):
            stages_obj[str(i)] = stages[i]
        if self.picked_stage not in stages_obj:
            self.picked_stage = '0'
        self.stages_combo = dpg.add_combo(label='Index', items=list(stages_obj.keys()), default_value=self.picked_stage, callback=self.on_stages_change, width=self.scaled_width_large, parent=self.dpg_stages_tag)

    def on_delete_game_click(self, sender, app_data):
        if len(self.config['games']) > 1:
            del self.config['games'][self.picked_game]
            self.picked_game = list(self.config['games'].keys())[0]
            self.config['picked_game'] = self.picked_game
            self.render_games_combo()

    def on_delete_gun_click(self, sender, app_data):
        if len(self.config['games'][self.picked_game]) > 1:
            del self.config['games'][self.picked_game][self.picked_gun]
            self.picked_gun = list(self.config['games'][self.picked_game].keys())[0]
            self.render_guns_combo()

    def on_delete_stage_click(self, sender, app_data):
        if len(self.config['games'][self.picked_game][self.picked_gun]) > 1:
            del self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]
            self.render_stages_combo()

    def on_game_name_change(self, sender, app_data):
        self.add_game_name = app_data

    def on_gun_name_change(self, sender, app_data):
        self.add_gun_name = app_data

    def on_number_change(self, sender, app_data):
        self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['number'] = app_data

    def on_x_change(self, sender, app_data):
        self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][0] = round(app_data, 3)

    def on_y_change(self, sender, app_data):
        self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][1] = round(app_data, 3)

    def on_add_game_click(self, sender, app_data):
        if self.add_game_name not in self.config['games'] and self.add_game_name != '':
            self.config['games'][self.add_game_name] = copy.deepcopy(self.config['games'][self.picked_game])
            self.picked_game = self.add_game_name
            self.config['picked_game'] = self.picked_game
            self.render_games_combo()

    def on_add_stage_click(self, sender, app_data):
        self.config['games'][self.picked_game][self.picked_gun].append({'number': 0, 'offset': [0, 0]})
        self.render_stages_combo()

    def on_add_gun_click(self, sender, app_data):
        if self.add_gun_name not in self.config['games'][self.picked_game] and self.add_gun_name != '':
            self.config['games'][self.picked_game][self.add_gun_name] = copy.deepcopy(self.config['games'][self.picked_game][self.picked_gun])
            self.picked_gun = self.add_gun_name
            self.render_guns_combo()
            self.render_stages_combo()
            self.refresh_stage()

    def on_games_change(self, sender, app_data):
        self.picked_game = app_data
        self.config['picked_game'] = self.picked_game
        self.render_guns_combo()
        self.render_stages_combo()
        self.refresh_stage()
        self._current_mouse_re_points = None
        if self.config.get('recoil', {}).get('use_mouse_re_trajectory', False):
            self._current_mouse_re_points = self._load_mouse_re_trajectory_for_current()

    def on_guns_change(self, sender, app_data):
        self.picked_gun = app_data
        self.render_stages_combo()
        self.refresh_stage()
        self._current_mouse_re_points = None
        if self.config.get('recoil', {}).get('use_mouse_re_trajectory', False):
            self._current_mouse_re_points = self._load_mouse_re_trajectory_for_current()

    def on_stages_change(self, sender, app_data):
        self.picked_stage = app_data
        self.refresh_stage()

    def refresh_stage(self):
        number = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['number']
        x = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][0]
        y = self.config['games'][self.picked_game][self.picked_gun][int(self.picked_stage)]['offset'][1]
        dpg.set_value(self.number_input, number)
        dpg.set_value(self.x_input, x)
        dpg.set_value(self.y_input, y)

    def reset_down_status(self):
        if self.config['is_show_down']:
            print(self.now_stage, self.now_num)
        self.now_num = 0
        self.now_stage = 0
        self.decimal_x = 0
        self.decimal_y = 0
        self.end = False

    def close_screenshot(self):
        """Close and release screenshot resources"""
        if self.screenshot_manager is not None:
            self.screenshot_manager.close()
            self.screenshot_manager = None

    def on_mask_left_change(self, sender, app_data):
        self.config['mask_left'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_left(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_left(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_left(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_left(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_left(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_left(0)

    def on_mask_right_change(self, sender, app_data):
        self.config['mask_right'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_right(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_right(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_right(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_right(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_right(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_right(0)

    def on_mask_middle_change(self, sender, app_data):
        self.config['mask_middle'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_middle(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_middle(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_middle(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_middle(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_middle(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_middle(0)

    def on_mask_side1_change(self, sender, app_data):
        self.config['mask_side1'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_side1(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_side1(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_side1(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_side1(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_side1(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_side1(0)

    def on_mask_side2_change(self, sender, app_data):
        self.config['mask_side2'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_side2(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_side2(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_side2(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_side2(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_side2(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_side2(0)

    def on_mask_x_change(self, sender, app_data):
        self.config['mask_x'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_x(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_x(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_x(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_x(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_x(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_x(0)

    def on_mask_y_change(self, sender, app_data):
        self.config['mask_y'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_y(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_y(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_y(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_y(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_y(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_y(0)

    def on_mask_wheel_change(self, sender, app_data):
        self.config['mask_wheel'] = app_data
        if self.config['move_method'] in ['km_net', 'dhz', 'catbox']:
            if app_data:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_wheel(1)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_wheel(1)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_wheel(1)
            else:
                if self.config['move_method'] == 'dhz':
                    self.dhz.mask_wheel(0)
                else:
                    if self.config['move_method'] == 'km_net':
                        kmNet.mask_wheel(0)
                    else:
                        if self.config['move_method'] == 'catbox':
                            catbox.mask_wheel(0)

    def on_aim_mask_x_change(self, sender, app_data):
        self.config['aim_mask_x'] = app_data

    def on_aim_mask_y_change(self, sender, app_data):
        self.config['aim_mask_y'] = app_data

    def _init_makcu_locks(self):
        """Initialize makcu button and axis lock states"""
        if self.makcu is None:
            return
        try:
            if self.config['mask_left']:
                self.makcu.lock_ml(1)
            if self.config['mask_right']:
                self.makcu.lock_mr(1)
            if self.config['mask_middle']:
                self.makcu.lock_mm(1)
            if self.config['mask_side1']:
                self.makcu.lock_ms1(1)
            if self.config['mask_side2']:
                self.makcu.lock_ms2(1)
            if self.config['mask_x']:
                self.makcu.lock_mx(1)
            if self.config['mask_y']:
                self.makcu.lock_my(1)
            if self.config['mask_wheel']:
                return
        except Exception as e:
            print(f'Failed to initialize Makcu lock states: {e}')

    def on_is_show_priority_debug_change(self, sender, app_data):
        self.config['is_show_priority_debug'] = app_data
        print(f'Class priority debug: {app_data}')

    def on_is_trt_change(self, sender, app_data):
        self.config['groups'][self.group]['is_trt'] = app_data
        if app_data:
            if not TENSORRT_AVAILABLE:
                print('TensorRT environment not installed or unavailable')
                print('Please install the following components:')
                print('1. CUDA Toolkit')
                print('2. cuDNN')
                print('3. TensorRT')
                self.config['groups'][self.group]['is_trt'] = False
                dpg.set_value(self.is_trt_checkbox, False)
                return
            current_model = self.config['groups'][self.group]['infer_model']
            if current_model.endswith('.onnx'):
                self.config['groups'][self.group]['original_infer_model'] = current_model
                print('TRT mode enabled, will detect and convert engine file on startup')
            elif current_model.endswith('.engine'):
                onnx_path = self.config['groups'][self.group].get('original_infer_model', None)
                if not onnx_path:
                    possible_onnx = os.path.splitext(current_model)[0] + '.onnx'
                    if os.path.exists(possible_onnx):
                        self.config['groups'][self.group]['original_infer_model'] = possible_onnx
                        print(f'Automatically inferred and set original model path: {possible_onnx}')
                    else:
                        print('Warning: Cannot find corresponding ONNX model, TRT switching may not work properly')
            else:
                print('Current model is not onnx or engine format, cannot properly handle TRT mode.')
                self.config['groups'][self.group]['is_trt'] = False
                dpg.set_value(self.is_trt_checkbox, False)
        else:
            current_model = self.config['groups'][self.group]['infer_model']
            if current_model.endswith('.engine'):
                onnx_path = self.config['groups'][self.group].get('original_infer_model', None)
                if onnx_path and os.path.exists(onnx_path):
                    self.config['groups'][self.group]['infer_model'] = onnx_path
                    self.refresh_engine()
                    dpg.set_value(self.infer_model_input, onnx_path)
                    is_v8 = self.config['groups'][self.group].get('is_v8', False)
                    dpg.set_value(self.is_v8_checkbox, is_v8)
                    print(f'Switched back to ONNX Runtime inference, V8 auto-check state: {is_v8}')
                else:
                    print('Original ONNX model path not found, please check configuration.')
        class_num = self.get_current_class_num()
        class_ary = list(range(class_num))
        self.create_checkboxes(class_ary)
        self.update_class_aim_combo()
        self.update_target_reference_class_combo()

    def on_show_infer_time_change(self, sender, app_data):
        self.config['show_infer_time'] = app_data
        print(f'Show inference time: {app_data}')

    def on_show_fov_change(self, sender, app_data):
        self.config['show_fov'] = app_data
        print(f'Show aim scope: {app_data}')

    def on_small_target_enabled_change(self, sender, app_data):
        self.config['small_target_enhancement']['enabled'] = app_data
        print(f"Small target recognition enhancement: {('enabled' if app_data else 'disabled')}")

    def on_small_target_smooth_change(self, sender, app_data):
        self.config['small_target_enhancement']['smooth_enabled'] = app_data
        print(f"Small target smoothing: {('enabled' if app_data else 'disabled')}")

    def on_small_target_nms_change(self, sender, app_data):
        self.config['small_target_enhancement']['adaptive_nms'] = app_data
        print(f"Adaptive NMS: {('enabled' if app_data else 'disabled')}")

    def on_small_target_boost_change(self, sender, app_data):
        self.config['small_target_enhancement']['boost_factor'] = app_data
        print(f'Small target boost factor set to: {app_data}')

    def on_small_target_frames_change(self, sender, app_data):
        self.config['small_target_enhancement']['smooth_frames'] = app_data
        self.target_history_max_frames = app_data
        print(f'Smooth history frames set to: {app_data}')

    def on_small_target_threshold_change(self, sender, app_data):
        self.config['small_target_enhancement']['threshold'] = app_data
        print(f'Small target threshold set to: {app_data:.3f}')

    def on_medium_target_threshold_change(self, sender, app_data):
        self.config['small_target_enhancement']['medium_threshold'] = app_data
        print(f'Medium target threshold set to: {app_data:.3f}')

    def _init_config_handlers(self):
        """
        Initialize configuration change handlers, register config items and handler functions
        """
        basic_group = ConfigItemGroup(self.config_handler)
        basic_group.register_item('infer_debug', 'infer_debug', bool)
        basic_group.register_item('is_curve', 'is_curve', bool)
        basic_group.register_item('is_curve_uniform', 'is_curve_uniform', bool)
        basic_group.register_item('print_fps', 'print_fps', bool)
        basic_group.register_item('show_motion_speed', 'show_motion_speed', bool, self.refresh_controller_params)
        basic_group.register_item('is_show_curve', 'is_show_curve', bool)
        basic_group.register_item('is_show_down', 'is_show_down', bool)
        basic_group.register_item('game_sensitivity', 'game_sensitivity', float)
        basic_group.register_item('mouse_dpi', 'mouse_dpi', int)
        basic_group.register_item('is_v8', 'is_v8', bool)
        basic_group.register_item('right_down', 'right_down', bool)
        scoring_group = ConfigItemGroup(self.config_handler)
        scoring_group.register_item('distance_scoring_weight', 'distance_scoring_weight', float, self.init_target_priority)
        scoring_group.register_item('center_scoring_weight', 'center_scoring_weight', float, self.init_target_priority)
        scoring_group.register_item('size_scoring_weight', 'size_scoring_weight', float, self.init_target_priority)
        screenshot_group = ConfigItemGroup(self.config_handler)
        screenshot_group.register_item('is_obs', 'is_obs', bool, lambda: self.screenshot_manager.update_config('is_obs', self.config['is_obs']) if self.screenshot_manager else None)
        screenshot_group.register_item('is_cjk', 'is_cjk', bool, lambda: self.screenshot_manager.update_config('is_cjk', self.config['is_cjk']) if self.screenshot_manager else None)
        screenshot_group.register_item('obs_ip', 'obs_ip', str, lambda: self.screenshot_manager.update_config('obs_ip', self.config['obs_ip']) if self.screenshot_manager else None)
        screenshot_group.register_item('obs_port', 'obs_port', int, lambda: self.screenshot_manager.update_config('obs_port', self.config['obs_port']) if self.screenshot_manager else None)
        screenshot_group.register_item('obs_fps', 'obs_fps', int, lambda: self.screenshot_manager.update_config('obs_fps', self.config['obs_fps']) if self.screenshot_manager else None)
        screenshot_group.register_item('cjk_device_id', 'cjk_device_id', int, lambda: self.screenshot_manager.update_config('cjk_device_id', self.config['cjk_device_id']) if self.screenshot_manager else None)
        screenshot_group.register_item('cjk_fps', 'cjk_fps', int, lambda: self.screenshot_manager.update_config('cjk_fps', self.config['cjk_fps']) if self.screenshot_manager else None)
        screenshot_group.register_item('cjk_resolution', 'cjk_resolution', int, lambda: self.screenshot_manager.update_config('cjk_resolution', self.config['cjk_resolution']) if self.screenshot_manager else None)
        screenshot_group.register_item('cjk_crop_size', 'cjk_crop_size', int, lambda: self.screenshot_manager.update_config('cjk_crop_size', self.config['cjk_crop_size']) if self.screenshot_manager else None)
        screenshot_group.register_item('enable_parallel_processing', 'enable_parallel_processing', bool, lambda: self.screenshot_manager.update_config('enable_parallel_processing', self.config['enable_parallel_processing']) if self.screenshot_manager else None)
        screenshot_group.register_item('turbo_mode', 'turbo_mode', bool, lambda: self.screenshot_manager.update_config('turbo_mode', self.config['turbo_mode']) if self.screenshot_manager else None)
        screenshot_group.register_item('skip_frame_processing', 'skip_frame_processing', bool, lambda: self.screenshot_manager.update_config('skip_frame_processing', self.config['skip_frame_processing']) if self.screenshot_manager else None)
        curve_group = ConfigItemGroup(self.config_handler)
        curve_group.register_item('offset_boundary_x', 'offset_boundary_x', int)
        curve_group.register_item('offset_boundary_y', 'offset_boundary_y', int)
        curve_group.register_item('knots_count', 'knots_count', int)
        curve_group.register_item('distortion_mean', 'distortion_mean', float)
        curve_group.register_item('distortion_st_dev', 'distortion_st_dev', float)
        curve_group.register_item('distortion_frequency', 'distortion_frequency', float)
        curve_group.register_item('target_points', 'target_points', int)
        move_group = ConfigItemGroup(self.config_handler)
        move_group.register_item('km_box_vid', 'km_box_vid', str)
        move_group.register_item('km_box_pid', 'km_box_pid', str)
        move_group.register_item('km_net_ip', 'km_net_ip', str)
        move_group.register_item('km_net_port', 'km_net_port', int)
        move_group.register_item('km_net_uuid', 'km_net_uuid', str)
        move_group.register_item('dhz_ip', 'dhz_ip', str)
        move_group.register_item('dhz_port', 'dhz_port', int)
        move_group.register_item('dhz_random', 'dhz_random', bool)
        move_group.register_item('km_com', 'km_com', str)
        move_group.register_item('move_method', 'move_method', str)
        key_group = ConfigItemGroup(self.config_handler)
        key_group.register_item('group', 'group', str, self.update_group_inputs)
        aim_key_group = ConfigItemGroup(self.config_handler, 'groups.{group}.aim_keys.{key}')
        aim_key_group.register_item('confidence_threshold', 'confidence_threshold', float)
        aim_key_group.register_item('iou_t', 'iou_t', float)
        aim_key_group.register_item('aim_bot_position', 'aim_bot_position', float)
        aim_key_group.register_item('aim_bot_position2', 'aim_bot_position2', float)
        aim_key_group.register_item('aim_bot_scope', 'aim_bot_scope', int)
        aim_key_group.register_item('min_position_offset', 'min_position_offset', int)
        aim_key_group.register_item('smoothing_factor', 'smoothing_factor', float, self.refresh_controller_params)
        aim_key_group.register_item('base_step', 'base_step', float, self.refresh_controller_params)
        aim_key_group.register_item('distance_weight', 'distance_weight', float, self.refresh_controller_params)
        aim_key_group.register_item('fov_angle', 'fov_angle', float, self.refresh_controller_params)
        aim_key_group.register_item('history_size', 'history_size', float, self.refresh_controller_params)
        aim_key_group.register_item('deadzone', 'deadzone', float, self.refresh_controller_params)
        aim_key_group.register_item('smoothing', 'smoothing', float, self.refresh_controller_params)
        aim_key_group.register_item('velocity_decay', 'velocity_decay', float, self.refresh_controller_params)
        aim_key_group.register_item('current_frame_weight', 'current_frame_weight', float, self.refresh_controller_params)
        aim_key_group.register_item('last_frame_weight', 'last_frame_weight', float, self.refresh_controller_params)
        aim_key_group.register_item('output_scale_x', 'output_scale_x', float, self.refresh_controller_params)
        aim_key_group.register_item('output_scale_y', 'output_scale_y', float, self.refresh_controller_params)
        aim_key_group.register_item('uniform_threshold', 'uniform_threshold', float)
        aim_key_group.register_item('min_velocity_threshold', 'min_velocity_threshold', float)
        aim_key_group.register_item('max_velocity_threshold', 'max_velocity_threshold', float)
        aim_key_group.register_item('compensation_factor', 'compensation_factor', float)
        aim_key_group.register_item('auto_y', 'auto_y', bool)
        aim_key_group.register_item('pid_kp_x', 'pid_kp_x', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_ki_x', 'pid_ki_x', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_kd_x', 'pid_kd_x', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_kp_y', 'pid_kp_y', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_ki_y', 'pid_ki_y', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_kd_y', 'pid_kd_y', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_integral_limit_x', 'pid_integral_limit_x', float, self.refresh_controller_params)
        aim_key_group.register_item('pid_integral_limit_y', 'pid_integral_limit_y', float, self.refresh_controller_params)
        aim_key_group.register_item('smooth_x', 'smooth_x', float, self.refresh_controller_params)
        aim_key_group.register_item('smooth_y', 'smooth_y', float, self.refresh_controller_params)
        aim_key_group.register_item('smooth_deadzone', 'smooth_deadzone', float, self.refresh_controller_params)
        aim_key_group.register_item('smooth_algorithm', 'smooth_algorithm', float, self.refresh_controller_params)
        aim_key_group.register_item('move_deadzone', 'move_deadzone', float)
        aim_key_group.register_item('target_switch_delay', 'target_switch_delay', int)
        aim_key_group.register_item('target_reference_class', 'target_reference_class', int)
        aim_key_group.register_item('dynamic_scope.enabled', 'dynamic_scope.enabled', bool)
        aim_key_group.register_item('dynamic_scope.min_ratio', 'dynamic_scope.min_ratio', float)
        aim_key_group.register_item('dynamic_scope.min_scope', 'dynamic_scope.min_scope', int)
        aim_key_group.register_item('dynamic_scope.shrink_duration_ms', 'dynamic_scope.shrink_duration_ms', int)
        aim_key_group.register_item('dynamic_scope.recover_duration_ms', 'dynamic_scope.recover_duration_ms', int)
        aim_key_group.register_item('status', 'status', bool)
        aim_key_group.register_item('start_delay', 'start_delay', float)
        aim_key_group.register_item('long_press_duration', 'long_press_duration', int)
        aim_key_group.register_item('press_delay', 'press_delay', float)
        aim_key_group.register_item('end_delay', 'end_delay', float)
        aim_key_group.register_item('random_delay', 'random_delay', float)
        aim_key_group.register_item('x_trigger_scope', 'x_trigger_scope', int)
        aim_key_group.register_item('y_trigger_scope', 'y_trigger_scope', int)
        aim_key_group.register_item('x_trigger_offset', 'x_trigger_offset', int)
        aim_key_group.register_item('y_trigger_offset', 'y_trigger_offset', int)
        infer_group = ConfigItemGroup(self.config_handler)
        infer_group.register_item('is_trt', 'is_trt', bool, None, self.on_is_trt_change)
        infer_group.register_item('show_infer_time', 'show_infer_time', bool)
        mask_group = ConfigItemGroup(self.config_handler)
        mask_group.register_item('mask_left', 'mask_left', bool, None, self.on_mask_left_change)
        mask_group.register_item('mask_right', 'mask_right', bool, None, self.on_mask_right_change)
        mask_group.register_item('mask_middle', 'mask_middle', bool, None, self.on_mask_middle_change)
        mask_group.register_item('mask_side1', 'mask_side1', bool, None, self.on_mask_side1_change)
        mask_group.register_item('mask_side2', 'mask_side2', bool, None, self.on_mask_side2_change)
        mask_group.register_item('mask_x', 'mask_x', bool, None, self.on_mask_x_change)
        mask_group.register_item('mask_y', 'mask_y', bool, None, self.on_mask_y_change)
        mask_group.register_item('mask_wheel', 'mask_wheel', bool, None, self.on_mask_wheel_change)
        mask_group.register_item('aim_mask_x', 'aim_mask_x', int)
        mask_group.register_item('aim_mask_y', 'aim_mask_y', int)
        self.config_handler.register_config_item('infer_model', 'groups.{group}.infer_model', None, None, self.on_infer_model_change)
        self.config_handler.register_config_item('key', 'key', None, None, self.on_key_change)
        self.config_handler.register_config_item('games', 'games', None, None, self.on_games_change)
        self.config_handler.register_config_item('guns', 'guns', None, None, self.on_guns_change)
        self.config_handler.register_config_item('stages', 'stages', None, None, self.on_stages_change)

    def on_gui_dpi_scale_change(self, sender, app_data):
        """DPI scale change callback"""
        self.config['gui_dpi_scale'] = app_data
        print(f'DPI scale changed to: {app_data:.2f}, will take effect after restart')

    def on_reset_dpi_scale_click(self, sender, app_data):
        """Reset DPI scale to auto-detected value"""
        auto_scale = self.get_system_dpi_scale()
        self.config['gui_dpi_scale'] = 0.0
        dpg.set_value(self.dpi_scale_slider, auto_scale)
        print(f'DPI scale reset to auto-detection: {auto_scale:.2f}, will take effect after restart')

    def on_change(self, sender, app_data):
        """
        Generic configuration change handler, forwards events to ConfigChangeHandler

        Args:
            sender: Sender ID
            app_data: New configuration value
        """
        self.config_handler.handle_change(sender, app_data)

    def on_controller_type_change(self, sender, app_data):
        """Controller type switch"""
        print('Current version only supports PID controller')

    def on_pid_kp_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_kp_x'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_ki_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_ki_x'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_kd_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_kd_x'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_kp_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_kp_y'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_ki_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_ki_y'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_kd_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_kd_y'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_integral_limit_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_integral_limit_x'] = round(app_data, 4)
        self._update_pid_params()

    def on_pid_integral_limit_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['pid_integral_limit_y'] = round(app_data, 4)
        self._update_pid_params()

    def on_smooth_x_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smooth_x'] = round(app_data, 4)
        self._update_pid_params()

    def on_smooth_y_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smooth_y'] = round(app_data, 4)
        self._update_pid_params()

    def on_smooth_deadzone_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smooth_deadzone'] = round(app_data, 4)
        self._update_pid_params()

    def on_smooth_algorithm_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['smooth_algorithm'] = round(app_data, 4)
        self._update_pid_params()

    def on_move_deadzone_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['move_deadzone'] = round(app_data, 4)

    def on_target_switch_delay_change(self, sender, app_data):
        self.config['groups'][self.group]['aim_keys'][self.select_key]['target_switch_delay'] = app_data

    def on_target_reference_class_change(self, sender, app_data):
        try:
            class_id = int(app_data.replace('Class', ''))
        except:
            class_id = 0
        self.config['groups'][self.group]['aim_keys'][self.select_key]['target_reference_class'] = class_id

    def _update_pid_params(self):
        """Update dual-axis PID controller parameters"""
        if hasattr(self, 'dual_pid'):
            self.refresh_controller_params()

    def _register_control_callback(self, control_id):
        """
        Register callback function for control

        Args:
            control_id: Control ID
        """
        dpg.set_item_callback(control_id, self.on_change)
