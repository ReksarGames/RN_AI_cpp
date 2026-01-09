"""Model management mixin.

!!! IMPORTANT !!!
ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS
"""
import copy
import ctypes
import os
import time
from ctypes import CDLL
from queue import Queue
from threading import Thread

import dearpygui.dearpygui as dpg
import pydirectinput
import kmNet

from infer_class import OnnxRuntimeDmlEngine
from makcu import MakcuController
from pykm2 import i_KM
from dhz import DHZBOX
from catbox_wrapper import init_catbox, catbox_move

from .utils import TENSORRT_AVAILABLE

from inference_engine import TensorRTInferenceEngine


class ModelMixin:
    """Mixin class for model management methods."""

    def render_group_combo(self):
        if self.move_group_tag is not None:
            dpg.delete_item(self.move_group_tag)
        self.move_group_tag = dpg.add_combo(label='Parameter Group', items=list(self.config['groups'].keys()), default_value=self.config['group'], callback=self.on_group_change, width=self.scaled_width_large, parent=self.dpg_group_tag)
        self.refresh_engine()

    def render_key_combo(self):
        if self.key_tag is not None:
            dpg.delete_item(self.key_tag)
        default_value = ''
        if len(self.aim_key) > 0:
            default_value = self.aim_key[0]
            if self.select_key in self.aim_key and self.select_key!= default_value:
                default_value = self.select_key
        self.select_key = default_value
        self.key_tag = dpg.add_combo(label='Key', items=self.aim_key, default_value=default_value, callback=self.on_key_change, width=self.scaled_width_large, parent=self.aim_key_combo_group)
        self.update_checkboxes_state(self.config['groups'][self.group]['aim_keys'][self.select_key]['classes'])

    def on_key_change(self, sender, app_data):
        self.select_key = app_data
        self.update_key_inputs()
        self.update_checkboxes_state(self.config['groups'][self.group]['aim_keys'][self.select_key]['classes'])
        print(f'changed to: {self.select_key}')

    def update_key_inputs(self):
        if len(self.aim_key) > 0:
            self.update_class_aim_combo()
            self.update_target_reference_class_combo()
            self.update_class_aim_inputs()
            if self.class_priority_input is not None:
                priority_order = self.get_class_priority_order()
                priority_text = self.format_class_priority(priority_order)
                dpg.set_value(self.class_priority_input, priority_text)
            dpg.set_value(self.aim_bot_scope_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['aim_bot_scope'])
            dpg.set_value(self.min_position_offset_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['min_position_offset'])
            dpg.set_value(self.status_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['status'])
            dpg.set_value(self.continuous_trigger_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger'].get('continuous', False))
            dpg.set_value(self.trigger_recoil_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger'].get('recoil', False))
            dpg.set_value(self.start_delay_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['start_delay'])
            dpg.set_value(self.press_delay_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['press_delay'])
            dpg.set_value(self.end_delay_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['end_delay'])
            dpg.set_value(self.random_delay_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['random_delay'])
            dpg.set_value(self.x_trigger_scope_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_scope'])
            dpg.set_value(self.y_trigger_scope_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_scope'])
            dpg.set_value(self.x_trigger_offset_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['x_trigger_offset'])
            dpg.set_value(self.y_trigger_offset_input, self.config['groups'][self.group]['aim_keys'][self.select_key]['trigger']['y_trigger_offset'])
            self.update_rect()
            if self.auto_y_checkbox is not None:
                dpg.set_value(self.auto_y_checkbox, self.config['groups'][self.group]['aim_keys'][self.select_key].get('auto_y', False))
                dpg.show_item(self.pid_params_group)
            key_cfg = self.config['groups'][self.group]['aim_keys'][self.select_key]
            dpg.set_value(self.pid_kp_x_input, key_cfg.get('pid_kp_x', 0.4))
            dpg.set_value(self.pid_kp_y_input, key_cfg.get('pid_kp_y', 0.4))
            dpg.set_value(self.pid_ki_x_input, key_cfg.get('pid_ki_x', 0.02))
            dpg.set_value(self.pid_ki_y_input, key_cfg.get('pid_ki_y', 0.02))
            dpg.set_value(self.pid_kd_x_input, key_cfg.get('pid_kd_x', 0.12))
            dpg.set_value(self.pid_kd_y_input, key_cfg.get('pid_kd_y', 0.12))
            dpg.set_value(self.pid_integral_limit_x_input, key_cfg.get('pid_integral_limit_x', 0.0))
            dpg.set_value(self.pid_integral_limit_y_input, key_cfg.get('pid_integral_limit_y', 0.0))
            dpg.set_value(self.smooth_x_input, key_cfg.get('smooth_x', 0.0))
            dpg.set_value(self.smooth_y_input, key_cfg.get('smooth_y', 0))
            dpg.set_value(self.smooth_deadzone_input, key_cfg.get('smooth_deadzone', 0.0))
            dpg.set_value(self.smooth_algorithm_input, key_cfg.get('smooth_algorithm', 1.0))
            dpg.set_value(self.move_deadzone_input, key_cfg.get('move_deadzone', 1.0))
            dpg.set_value(self.target_switch_delay_input, key_cfg.get('target_switch_delay', 0))
            reference_class = key_cfg.get('target_reference_class', 0)
            dpg.set_value(self.target_reference_class_combo, f'Class{reference_class}')
            dyn = key_cfg.get('dynamic_scope', {}) or {}
            if self.dynamic_scope_enabled_input is not None:
                dpg.set_value(self.dynamic_scope_enabled_input, bool(dyn.get('enabled', False)))
            if self.dynamic_scope_min_scope_input is not None:
                if 'min_scope' in dyn:
                    dpg.set_value(self.dynamic_scope_min_scope_input, int(dyn.get('min_scope', 0)))
                else:
                    base_scope = int(key_cfg.get('aim_bot_scope', 0))
                    ratio = float(dyn.get('min_ratio', 0.5))
                    dpg.set_value(self.dynamic_scope_min_scope_input, int(base_scope * max(0.0, min(1.0, ratio))))
            if self.dynamic_scope_shrink_ms_input is not None:
                dpg.set_value(self.dynamic_scope_shrink_ms_input, int(dyn.get('shrink_duration_ms', 300)))
            if self.dynamic_scope_recover_ms_input is not None:
                dpg.set_value(self.dynamic_scope_recover_ms_input, int(dyn.get('recover_duration_ms', 300)))

    def update_group_inputs(self):
        dpg.set_value(self.infer_model_input, self.config['groups'][self.group]['infer_model'])
        dpg.set_value(self.is_trt_checkbox, self.config['groups'][self.group]['is_trt'])
        dpg.set_value(self.is_v8_checkbox, self.config['groups'][self.group]['is_v8'])
        dpg.set_value(self.right_down_checkbox, self.config['groups'][self.group]['right_down'])
        self.update_key_inputs()

    def create_checkboxes(self, options):
        self.remove_checkboxes()
        for option in options:
            checkbox_tag = dpg.add_checkbox(label=str(option), callback=self.on_checkbox_change, parent=self.checkbox_group_tag)
            self.checkboxes.append(checkbox_tag)
            if option in self.selected_items:
                dpg.set_value(checkbox_tag, True)

    def remove_checkboxes(self):
        for checkbox in self.checkboxes:
            dpg.delete_item(checkbox)
        self.checkboxes.clear()

    def on_checkbox_change(self, sender, app_data):
        if app_data:
            self.selected_items.append(int(dpg.get_item_label(sender)))
        else:
            self.selected_items.remove(int(dpg.get_item_label(sender)))
        self.config['groups'][self.group]['aim_keys'][self.select_key]['classes'] = self.selected_items
        print(f'Current selection: {self.selected_items}')
        if hasattr(self, 'old_pressed_aim_key') and self.old_pressed_aim_key:
            self.refresh_pressed_key_config(self.old_pressed_aim_key)
            print(f'Refreshed key {self.old_pressed_aim_key} class configuration, inference will take effect in real-time')

    def update_checkboxes_state(self, new_selection):
        for checkbox in self.checkboxes:
            option = int(dpg.get_item_label(checkbox))
            should_be_selected = option in new_selection
            dpg.set_value(checkbox, should_be_selected)
        self.selected_items = new_selection

    def on_delete_group_click(self, sender, app_data):
        if len(self.config['groups']) > 1:
            del self.config['groups'][self.group]
            self.group = list(self.config['groups'].keys())[0]
            self.config['group'] = self.group
            self.render_group_combo()
            self.refresh_engine()
            class_num = self.get_current_class_num()
            class_ary = list(range(class_num))
            self.create_checkboxes(class_ary)
            self.update_class_aim_combo()
            self.update_target_reference_class_combo()
            self.aim_keys_dist = self.config['groups'][self.group]['aim_keys']
            self.aim_key = list(self.aim_keys_dist.keys())
            self.render_key_combo()
            self.update_group_inputs()

    def on_group_name_change(self, sender, app_data):
        self.add_group_name = app_data

    def on_add_group_click(self, sender, app_data):
        if self.add_group_name not in self.config['groups'] and self.add_group_name!= '':
            self.config['groups'][self.add_group_name] = copy.deepcopy(self.config['groups'][self.group])
            self.group = self.add_group_name
            self.config['group'] = self.group
            self.render_group_combo()

    def on_delete_key_click(self, sender, app_data):
        if len(self.config['groups'][self.group]['aim_keys']) > 1:
            del self.config['groups'][self.group]['aim_keys'][self.select_key]
            self.aim_keys_dist = self.config['groups'][self.group]['aim_keys']
            self.aim_key = list(self.aim_keys_dist.keys())
            self.select_key = self.aim_key[0]
            self.render_key_combo()
            self.update_key_inputs()

    def on_key_name_change(self, sender, app_data):
        self.add_key_name = app_data

    def on_add_key_click(self, sender, app_data):
        if self.add_key_name not in self.config['groups'][self.group]['aim_keys'] and self.add_key_name!= '':
            self.config['groups'][self.group]['aim_keys'][self.add_key_name] = copy.deepcopy(self.config['groups'][self.group]['aim_keys'][self.select_key])
            self.init_class_aim_positions_for_key(self.add_key_name)
            self.aim_keys_dist = self.config['groups'][self.group]['aim_keys']
            self.aim_key = list(self.aim_keys_dist.keys())
            self.select_key = self.add_key_name
            self.render_key_combo()
            self.update_class_aim_combo()
            self.update_target_reference_class_combo()

    def init_class_aim_positions_for_key(self, key_name):
        """Initialize class aim position configuration for specified key"""
        try:
            class_num = self.get_current_class_num()
            key_config = self.config['groups'][self.group]['aim_keys'][key_name]
            if 'class_aim_positions' not in key_config:
                key_config['class_aim_positions'] = {}
            if 'class_priority_order' not in key_config:
                key_config['class_priority_order'] = list(range(class_num))
            for i in range(class_num):
                class_str = str(i)
                if class_str not in key_config['class_aim_positions']:
                    key_config['class_aim_positions'][class_str] = {'aim_bot_position': 0.0, 'aim_bot_position2': 0.0, 'confidence_threshold': 0.5, 'iou_t': 1.0}
        except Exception as e:
            print(f'Initialize class aim position configuration failed: {e}')

    def init_mouse(self):
        try:
            if self.config['move_method'] == 'makcu':
                if getattr(self, 'makcu', None) is None:
                    self.makcu = MakcuController()
                else:
                    try:
                        self.makcu.disconnect()
                    except Exception:
                        pass
                    self.makcu = MakcuController()
                if self.makcu is not None:
                    self._makcu_move_queue = Queue(maxsize=1024)
                    self._makcu_send_interval = 0.0015
                    self._makcu_last_send_ts = 0.0

                    def _makcu_sender_worker():
                        last_ts = 0.0
                        while not getattr(self, 'end', False):
                            try:
                                dx, dy = self._makcu_move_queue.get(timeout=0.1)
                            except Exception:
                                continue
                            try:
                                while True:
                                    nx, ny = self._makcu_move_queue.get_nowait()
                                    dx += int(nx)
                                    dy += int(ny)
                            except Exception:
                                pass
                            now = time.perf_counter()
                            wait_s = self._makcu_send_interval - (now - last_ts)
                            if wait_s > 0:
                                time.sleep(wait_s)
                            send_ok = False
                            for _ in range(2):
                                try:
                                    if self.makcu is not None:
                                        self.makcu.move(int(dx), int(dy))
                                        send_ok = True
                                        break
                                except Exception as e:
                                    try:
                                        if self.makcu is not None:
                                            self.makcu.disconnect()
                                            time.sleep(0.05)
                                            self.makcu = MakcuController()
                                    except:
                                        time.sleep(0.05)
                            if not send_ok:
                                time.sleep(0.01)
                            last_ts = time.perf_counter()

                    def move_enqueue(x, y):
                        if self.makcu is None:
                            return
                        try:
                            self._makcu_move_queue.put_nowait((int(x), int(y)))
                        except Exception:
                            try:
                                _ = self._makcu_move_queue.get_nowait()
                            except Exception:
                                pass
                            try:
                                self._makcu_move_queue.put_nowait((int(x), int(y)))
                            except Exception:
                                return None
                    self.move_r = move_enqueue
                    if not hasattr(self, '_makcu_sender_started') or not self._makcu_sender_started:
                        t = Thread(target=_makcu_sender_worker, daemon=True)
                        t.start()
                        self._makcu_sender_started = True
                    self._init_makcu_locks()
                else:
                    print('makcu not connected')
        except Exception as e:
            print(f'Makcu initialization failed: {e}')
            self.makcu = None
        if self.config['move_method'] == 'km_box_a':
            print('km_box_a mode')
            km_box_pid = int(self.config['km_box_pid'], 16)
            km_box_vid = int(self.config['km_box_vid'], 16)
            self.move_dll = CDLL('./km.dll')
            res = self.move_dll.KM_init(ctypes.c_ushort(km_box_vid), ctypes.c_ushort(km_box_pid))
            print('km_box_a initialization:{}'.format(res))
            self.move_r = self.move_dll.KM_move
        if self.config['move_method'] == 'send_input':
            print('send_input mode')
            self.move_dll = None
            self.move_r = pydirectinput.moveRel
        if self.config['move_method'] == 'logitech':
            print('logitech mode')
            self.move_dll = CDLL('./logitech.dll')
            self.move_r = self.move_dll.moveR
        if self.config['move_method'] == 'km_net':
            print('km_net mode')
            result = kmNet.init(self.config['km_net_ip'], self.config['km_net_port'], self.config['km_net_uuid'])
            if result == 0:
                print('Initialization successful')
                self.move_dll = None
                self.move_r = kmNet.move
                if self.config['mask_left']:
                    kmNet.mask_left(1)
                if self.config['mask_right']:
                    kmNet.mask_right(1)
                if self.config['mask_middle']:
                    kmNet.mask_middle(1)
                if self.config['mask_side1']:
                    kmNet.mask_side1(1)
                if self.config['mask_side2']:
                    kmNet.mask_side2(1)
                if self.config['mask_x']:
                    kmNet.mask_x(1)
                if self.config['mask_y']:
                    kmNet.mask_y(1)
                if self.config['mask_wheel']:
                    kmNet.mask_wheel(1)
            else:
                print('Initialization failed')
        if self.config['move_method'] == 'dhz':
            print('dhz mode')
            self.dhz = DHZBOX(self.config['dhz_ip'], self.config['dhz_port'], self.config['dhz_random'])
            if self.config['mask_left']:
                self.dhz.mask_left(1)
            if self.config['mask_right']:
                self.dhz.mask_right(1)
            if self.config['mask_middle']:
                self.dhz.mask_middle(1)
            if self.config['mask_side1']:
                self.dhz.mask_side1(1)
            if self.config['mask_side2']:
                self.dhz.mask_side2(1)
            if self.config['mask_x']:
                self.dhz.mask_x(1)
            if self.config['mask_y']:
                self.dhz.mask_y(1)
            if self.config['mask_wheel']:
                self.dhz.mask_wheel(1)
            self.move_r = self.dhz.move
        if self.config['move_method'] == 'pnmh':
            if self.pnmh is not None and self.pnmh.IsOpen():
                self.pnmh.Close()
                del self.pnmh
            self.pnmh = i_KM()
            ret = self.pnmh.OpenDevice(self.config['km_com'])
            if not ret:
                print('Rebel magic box not connected')
            else:
                print('Rebel magic box connected')
                print('Model:', chr(self.pnmh.GetModel() + 64))
                print('Version:', self.pnmh.GetVersion())
                print('Serial number:', self.pnmh.GetChipID())
                print('Storage size:', self.pnmh.GetStorageSize())
                self.pnmh.SetWaitRespon(False)
            self.move_r = self.pnmh.MoveR
        if self.config['move_method'] == 'catbox':
            print('catbox mode')
            result = init_catbox(self.config['catbox_ip'], self.config['catbox_port'], self.config['catbox_uuid'])
            if result:
                print('CatBox initialization successful')
                self.move_dll = None
                self.move_r = catbox_move
                if self.config['mask_left']:
                    catbox.mask_left(1)
                if self.config['mask_right']:
                    catbox.mask_right(1)
                if self.config['mask_middle']:
                    catbox.mask_middle(1)
                if self.config['mask_side1']:
                    catbox.mask_side1(1)
                if self.config['mask_side2']:
                    catbox.mask_side2(1)
                if self.config['mask_x']:
                    catbox.mask_x(1)
                if self.config['mask_y']:
                    catbox.mask_y(1)
                if self.config['mask_wheel']:
                    catbox.mask_wheel(1)
            else:
                print('CatBox initialization failed')
        if self.config['move_method'] == 'dhz':
            listen_thread = Thread(target=self.start_listen_dhz)
        else:
            if self.config['move_method'] == 'km_net':
                listen_thread = Thread(target=self.start_listen_km_net)
            else:
                if self.config['move_method'] == 'pnmh':
                    listen_thread = Thread(target=self.start_listen_pnmh)
                else:
                    if self.config['move_method'] == 'makcu':
                        listen_thread = Thread(target=self.start_listen_makcu)
                    else:
                        if self.config['move_method'] == 'catbox':
                            listen_thread = Thread(target=self.start_listen_catbox)
                        else:
                            listen_thread = Thread(target=self.start_listen)
        listen_thread.setDaemon(True)
        listen_thread.start()

    def _clear_queues(self):
        """Clear all queues, ensure queue state is correct after switching models"""
        try:
            while not self.que_aim.empty():
                try:
                    self.que_aim.get_nowait()
                except:
                    break
            while not self.que_trigger.empty():
                try:
                    self.que_trigger.get_nowait()
                except:
                    return
        except Exception as e:
            print(f'[Queue cleanup] Error clearing queues: {e}')

    def _reset_aim_states(self):
        """Reset aim-related states, ensure state is correct after switching models"""
        try:
            self.old_pressed_aim_key = ''
            self.aim_key_status = False
            self.reset_pid()
            if hasattr(self, 'reset_target_lock'):
                for key in getattr(self, 'aim_key', []):
                    self.reset_target_lock(key)
        except Exception as e:
            print(f'[State reset] Error resetting states: {e}')

    def refresh_engine(self):
        self._clear_queues()
        self._reset_aim_states()
        is_trt = self.config['groups'][self.group].get('is_trt', False)
        model_path = self.config['groups'][self.group]['infer_model']
        if not os.path.exists(model_path):
            print(f'Model file does not exist: {model_path}')
            return
        if is_trt and (not TENSORRT_AVAILABLE):
            is_trt = False
            self.config['groups'][self.group]['is_trt'] = False
            if model_path.endswith('.engine'):
                original_path = self.config['groups'][self.group].get('original_infer_model')
                if original_path and os.path.exists(original_path):
                    model_path = original_path
                    self.config['groups'][self.group]['infer_model'] = original_path
                else:
                    possible_onnx = os.path.splitext(model_path)[0] + '.onnx'
                    if os.path.exists(possible_onnx):
                        model_path = possible_onnx
                        self.config['groups'][self.group]['infer_model'] = possible_onnx
                        self.config['groups'][self.group]['original_infer_model'] = possible_onnx
                    else:
                        return None
        if model_path.endswith('.engine') and is_trt and TENSORRT_AVAILABLE:
            try:
                self.engine = TensorRTInferenceEngine(model_path)
                print(f'Loaded TensorRT .engine file: {model_path}')
            except Exception as e:
                print(f'TensorRT engine load failed: {e}, trying to switch back to original model')
                original_path = self.config['groups'][self.group].get('original_infer_model', None)
                if original_path and os.path.exists(original_path):
                    self.config['groups'][self.group]['infer_model'] = original_path
                    self.config['groups'][self.group]['is_trt'] = False
                    self.refresh_engine()
                    return
                print('Original model not found, cannot fall back')
                return None
        engine_path = os.path.splitext(model_path)[0] + '.engine'
        if is_trt and TENSORRT_AVAILABLE and (TensorRTInferenceEngine is not None) and os.path.exists(engine_path):
            try:
                self.engine = TensorRTInferenceEngine(engine_path)
                print('Automatically switched to TensorRT .engine inference.')
            except Exception as e:
                print(f'TensorRT engine load failed: {e}, automatically switched to ONNX inference')
                self.config['groups'][self.group]['is_trt'] = False
                if model_path.endswith('data'):
                    self.engine = OnnxRuntimeDmlEngine(model_path, is_trt=False)
                else:
                    self.engine = OnnxRuntimeDmlEngine(model_path, True, is_trt=False)
        if model_path.endswith('data'):
            self.engine = OnnxRuntimeDmlEngine(model_path, is_trt=False)
        else:
            self.engine = OnnxRuntimeDmlEngine(model_path, True, is_trt=False)
        self.identify_rect_left = self.screen_center_x - self.engine.get_input_shape()[3] / 2
        self.identify_rect_top = self.screen_center_y - self.engine.get_input_shape()[2] / 2
        if isinstance(self.engine, TensorRTInferenceEngine):
            try:
                use_graph = self.config['groups'][self.group].get('use_cuda_graph', True)
            except Exception:
                use_graph = True
            if use_graph and hasattr(self.engine, 'enable_cuda_graph'):
                try:
                    self.engine.enable_cuda_graph()
                except Exception as e:
                    print(f'Failed to enable CUDA Graph: {e}')
            if hasattr(self.engine, 'disable_cuda_graph'):
                try:
                    self.engine.disable_cuda_graph()
                except Exception:
                    return

    def _create_engine_from_bytes(self, model_bytes, is_trt=False):
        """Create inference engine from byte data"""
        try:
            import onnxruntime as rt
            import warnings
            warnings.filterwarnings('ignore', message='.*pagelocked_host_allocation.*')
            warnings.filterwarnings('ignore', message='.*device_allocation.*')
            warnings.filterwarnings('ignore', message='.*stream.*out-of-thread.*')
            warnings.filterwarnings('ignore', message='.*could not be cleaned up.*')
            warnings.filterwarnings('ignore', message='.*stream.*')
            available = rt.get_available_providers()
            providers = []
            if is_trt:
                if 'TensorrtExecutionProvider' in available:
                    providers.append('TensorrtExecutionProvider')
                if 'CUDAExecutionProvider' in available:
                    providers.append('CUDAExecutionProvider')
                if 'DmlExecutionProvider' in available:
                    providers.append('DmlExecutionProvider')
                if 'CPUExecutionProvider' in available:
                    providers.append('CPUExecutionProvider')
                if not providers:
                    providers = available
            else:
                if 'DmlExecutionProvider' in available:
                    providers.append('DmlExecutionProvider')
                if 'CPUExecutionProvider' in available:
                    providers.append('CPUExecutionProvider')
                if not providers:
                    providers = available
            session = rt.InferenceSession(model_bytes, providers=providers)

            class DecryptedModelEngine:
                def __init__(self, session):
                    import threading
                    self.session = session
                    self.input_name = self.session.get_inputs()[0].name
                    self.output_names = [output.name for output in self.session.get_outputs()]
                    self.input_shape = self.session.get_inputs()[0].shape
                    self._lock = threading.Lock()

                def get_input_shape(self):
                    return self.input_shape

                def infer(self, img_input):
                    with self._lock:
                        outputs = self.session.run(self.output_names, {self.input_name: img_input})
                        return outputs
                        return outputs

                def get_class_num(self):
                    outputs_meta = self.session.get_outputs()
                    output_shapes = outputs_meta[0].shape
                    return output_shapes[2] - 5

                def get_class_num_v8(self):
                    outputs_meta = self.session.get_outputs()
                    output_shapes = outputs_meta[0].shape
                    return output_shapes[1] - 4

                def __del__(self):
                    """Destructor, ensure resources are properly cleaned up"""
                    try:
                        if hasattr(self, 'session'):
                            del self.session
                    except:
                        return None
            self.engine = DecryptedModelEngine(session)
            print('Decrypted model engine created successfully')
            self.identify_rect_left = self.screen_center_x - self.engine.get_input_shape()[3] / 2
            self.identify_rect_top = self.screen_center_y - self.engine.get_input_shape()[2] / 2
        except Exception as e:
            print(f'Failed to create engine from byte data: {e}')
            self.engine = None

    def on_is_v8_change(self, sender, app_data):
        self.config['groups'][self.group]['is_v8'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['is_v8']}")

    def on_auto_y_change(self, sender, app_data):
        if len(self.aim_key) > 0:
            self.config['groups'][self.group]['aim_keys'][self.select_key]['auto_y'] = app_data
            print(f'Key {self.select_key} long press left button no lock Y axis setting changed to: {app_data}')

    def on_right_down_change(self, sender, app_data):
        self.config['groups'][self.group]['right_down'] = app_data
        print(f"changed to: {self.config['groups'][self.group]['right_down']}")

    def init_target_priority(self):
        self.target_priority = {'distance_scoring_weight': self.config['distance_scoring_weight'], 'center_scoring_weight': self.config['center_scoring_weight'], 'size_scoring_weight': self.config['size_scoring_weight']}

    def get_trt_class_num(self):
        if not TENSORRT_AVAILABLE:
            print('TensorRT environment unavailable, trying to infer class count from ONNX')
            return self.get_onnx_class_num()
        if not hasattr(self.engine, 'engine'):
            print('Current inference engine is not TensorRTInferenceEngine, cannot get class count.')
            return self.get_onnx_class_num()
        try:
            binding = self.engine.engine[1]
            shape = self.engine.engine.get_tensor_shape(binding)
        except Exception as e:
            return self.get_onnx_class_num()
        if len(shape) == 3 and shape[0] == 1 and (shape[1] == 5):
            trt_class_num = self.config['groups'][self.group].get('trt_class_num', None)
            if trt_class_num is not None:
                print(f'Using preset TRT class count from config: {trt_class_num}')
                return trt_class_num
            return self.get_onnx_class_num()
        c = shape[(-1)]
        if 1 <= c - 4 <= 200:
            return c - 4
        if 1 <= c - 5 <= 200:
            return c - 5
        if len(shape) == 2 and 1 <= shape[1] <= 200:
            return shape[1]
        else:
            return self.get_onnx_class_num()

    def get_onnx_class_num(self):
        """Infer class count from ONNX model"""
        onnx_path = self.config['groups'][self.group].get('original_infer_model', '')
        if not onnx_path:
            current_model = self.config['groups'][self.group]['infer_model']
            if current_model.endswith('.engine'):
                onnx_path = os.path.splitext(current_model)[0] + '.onnx'
            else:
                onnx_path = current_model
        try:
            import onnxruntime as ort
            session = None
            if onnx_path and os.path.exists(onnx_path):
                providers = ['DmlExecutionProvider', 'CPUExecutionProvider'] if 'DmlExecutionProvider' in ort.get_available_providers() else ['CPUExecutionProvider']
                session = ort.InferenceSession(onnx_path, providers=providers)
            if session is not None:
                outputs = session.get_outputs()
                if len(outputs) > 0:
                    onnx_shape = outputs[0].shape
                    if len(onnx_shape) >= 2:
                        if onnx_shape[(-2)] > 4:
                            class_num = onnx_shape[(-2)] - 4
                            return class_num
                        if onnx_shape[(-1)] > 5:
                            class_num = onnx_shape[(-1)] - 5
                            return class_num
                del session
                return 5
            return 5
        except Exception as e:
            print(f'Failed to infer class count from ONNX: {e}')
            return 5

    def get_current_class_num(self):
        try:
            if self.engine is None:
                return 5
            if self.config['groups'][self.group]['infer_model'].endswith('.engine'):
                if not TENSORRT_AVAILABLE:
                    result = self.get_onnx_class_num()
                    return result
                result = self.get_trt_class_num()
                return result
            if self.config['groups'][self.group]['is_v8']:
                result = self.engine.get_class_num_v8()
                if isinstance(result, (int, float)) and result > 0:
                    return int(result)
                return 5
            result = self.engine.get_class_num()
            if isinstance(result, (int, float)) and result > 0:
                return int(result)
            return 5
        except Exception as e:
            import traceback
            print(f'Error getting class count: {e}')
            traceback.print_exc()
            return 1

    def is_using_dopa_model(self):
        """
        Check if currently using ZTX model - always returns False as ZTX support removed
        """
        return False

    def is_using_encrypted_model(self):
        """
        Check if currently using encrypted model - always returns False as ZTX support removed
        """
        return False
