"""Input handlers and device listeners mixin.

!!! IMPORTANT !!!
ON REFACTORING DONT CHANGE ANY LOGIC, JUST TRANSLATE ALL COMMENTS TO ENGLISH
REFACTORING IS JUST SEPARATE SINGLE LARGE FILE TO MULTIPLE
DO NOT REFACTOR CODE - NO MATTER HOW BAD IT LOOKS
"""
import time
from threading import Timer
from pynput import keyboard, mouse
import kmNet
from catbox_wrapper import catbox, catbox_disconnect
from makcu import MakcuController
from queue import Queue
from threading import Thread

from .utils import key2str


class InputMixin:
    """Mixin class for input handlers and device listeners."""

    def down_func(self, u_timer_id, u_msg, dw_user, dw1, dw2):
        """Original recoil control logic, coexists with mouse_re"""
        if self.config.get('recoil', {}).get('use_mouse_re_trajectory', False):
            return
        left_press_valid = self.left_pressed and self.down_switch
        trigger_press_valid = self.trigger_recoil_pressed
        if left_press_valid or trigger_press_valid:
            if not self.end:
                if self.config['groups'][self.group]['right_down'] and (not self.right_pressed):
                    return
                if self.now_num >= self.config['games'][self.picked_game][self.picked_gun][self.now_stage]['number']:
                    self.now_num = 0
                    if self.now_stage + 1 < len(self.config['games'][self.picked_game][self.picked_gun]):
                        self.now_stage = self.now_stage + 1
                if self.now_stage + 1 <= len(self.config['games'][self.picked_game][self.picked_gun]):
                    x = self.config['games'][self.picked_game][self.picked_gun][self.now_stage]['offset'][0]
                    y = self.config['games'][self.picked_game][self.picked_gun][self.now_stage]['offset'][1]
                    int_x = int(x)
                    int_y = int(y)
                    self.decimal_x = self.decimal_x + x - int_x
                    self.decimal_y = self.decimal_y + y - int_y
                    if self.decimal_x > 0.7:
                        self.decimal_x -= 1
                        int_x += 1
                    if self.decimal_y > 0.7:
                        self.decimal_y -= 1
                        int_y += 1
                    if int_x > 0 or int_y > 0:
                        self.move_r(round(int_x), round(int_y))
                    self.now_num = self.now_num + 1
                if self.now_stage + 1 == len(self.config['games'][self.picked_game][self.picked_gun]) and self.now_num >= self.config['games'][self.picked_game][self.picked_gun][self.now_stage]['number']:
                    self.end = True

    def screenshot(self, left, top, right, bottom):
        """Deprecated: use self.screenshot_manager.get_screenshot instead"""
        return self.screenshot_manager.get_screenshot((left, top, right, bottom))

    def on_click(self, x, y, button, pressed):
        if pressed:
            if button == mouse.Button.left:
                key = 'mouse_left'
                if not self.left_pressed:
                    self.left_press()
            else:
                if button == mouse.Button.right:
                    key = 'mouse_right'
                    if not self.right_pressed:
                        self.right_pressed = True
                else:
                    if button == mouse.Button.middle:
                        key = 'mouse_middle'
                    else:
                        if button == mouse.Button.x1:
                            key = 'mouse_x1'
                        else:
                            if button == mouse.Button.x2:
                                key = 'mouse_x2'
            if key in self.aim_key and self.old_pressed_aim_key == '':
                self.refresh_pressed_key_config(key)
                self.old_pressed_aim_key = key
                self.aim_key_status = True
                self.reset_dynamic_aim_scope(key)
        else:
            if button == mouse.Button.left:
                key = 'mouse_left'
                if self.left_pressed:
                    self.left_release()
            else:
                if button == mouse.Button.right:
                    key = 'mouse_right'
                    if self.right_pressed:
                        self.right_pressed = False
                else:
                    if button == mouse.Button.middle:
                        key = 'mouse_middle'
                    else:
                        if button == mouse.Button.x1:
                            key = 'mouse_x1'
                        else:
                            if button == mouse.Button.x2:
                                key = 'mouse_x2'
            if key in self.aim_key and key == self.old_pressed_aim_key:
                self.old_pressed_aim_key = ''
                self.aim_key_status = False
                self.reset_pid()

    def on_scroll(self, x, y, dx, dy):
        if dy == 1:
            return
        if dy == (-1):
            pass

    def on_press(self, key):
        key = key2str(key)
        if key in self.aim_key and key not in self.pressed_key and (self.old_pressed_aim_key == ''):
            self.refresh_pressed_key_config(key)
            self.reset_pid()
            self.old_pressed_aim_key = key
            self.aim_key_status = True
        if key not in self.pressed_key:
            self.pressed_key.append(key)

    def on_release(self, key):
        key = key2str(key)
        if key == self.config['down_switch_key']:
            self.down_switch = not self.down_switch
            if self.down_switch:
                if not self.config.get('recoil', {}).get('use_mouse_re_trajectory', False):
                    self.timer_id2 = self.time_set_event(self.delay, 1, self.down, 0, 1)
            else:
                if self.timer_id2!= 0:
                    self.time_kill_event(self.timer_id2)
                    self.timer_id2 = 0
                if getattr(self, '_recoil_is_replaying', False):
                    self._stop_mouse_re_recoil()
            print('Recoil ON' if self.down_switch else 'Recoil OFF')
            self.update_mouse_re_ui_status()
        if key in self.aim_key and key == self.old_pressed_aim_key:
            self.old_pressed_aim_key = ''
            self.aim_key_status = False
            self.reset_pid()
            self.reset_target_lock(key)
        if key in self.pressed_key:
            self.pressed_key.remove(key)

    def reset_target_lock(self, key=None):
        # Reset target lock related state, ensure next key press can reselect target
        # This method only clears state, no blocking operations; all fields check existence for compatibility
        try:
            if hasattr(self, 'is_waiting_for_switch'):
                self.is_waiting_for_switch = False
            if hasattr(self, 'target_switch_time'):
                self.target_switch_time = 0
            possible_attrs_to_none = ['current_target', 'locked_target', 'selected_target', 'target', 'target_bbox', 'target_box', 'last_target', 'best_target', 'last_best_target', 'current_target_id', 'locked_track_id', 'track_id', 'last_target_id']
            for attr_name in possible_attrs_to_none:
                if hasattr(self, attr_name):
                    try:
                        setattr(self, attr_name, None)
                    except Exception:
                        pass
            for tracker_like in ('tracker', 'kalman_filter'):
                if hasattr(self, tracker_like):
                    try:
                        setattr(self, tracker_like, None)
                    except Exception:
                        pass
            if hasattr(self, 'target_history') and isinstance(self.target_history, dict):
                try:
                    self.target_history.clear()
                except Exception:
                    pass
            if hasattr(self, '_clear_queues') and callable(self._clear_queues):
                try:
                    self._clear_queues()
                except Exception:
                    pass
            for flag_name in ('trigger_status', 'continuous_trigger_active', 'trigger_recoil_active'):
                if hasattr(self, flag_name):
                    try:
                        setattr(self, flag_name, False)
                    except Exception:
                        pass
        except Exception:
            return

    def start_listen(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.mouse_listener = mouse.Listener(on_scroll=self.on_scroll, on_click=self.on_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def start_listen_km_net(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.keyboard_listener.start()
        kmNet.monitor(9031)
        self.time_begin_period(1)
        self.km_listen_switch = True
        while self.km_listen_switch:
            if kmNet.isdown_left():
                if not self.left_pressed:
                    self.left_press()
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_left' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_left')
                    self.old_pressed_aim_key = 'mouse_left'
                    self.aim_key_status = True
                    self.reset_dynamic_aim_scope('mouse_left')
            else:
                if self.left_pressed:
                    self.left_release()
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_left':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if kmNet.isdown_right():
                if not self.right_pressed:
                    self.right_pressed = True
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_right' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_right')
                    self.old_pressed_aim_key = 'mouse_right'
                    self.aim_key_status = True
                    self.reset_dynamic_aim_scope('mouse_right')
            else:
                if self.right_pressed:
                    self.right_pressed = False
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_right':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if kmNet.isdown_side1():
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_x1' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_x1')
                    self.old_pressed_aim_key = 'mouse_x1'
                    self.aim_key_status = True
                    self.reset_dynamic_aim_scope('mouse_x1')
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x1':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if not kmNet.isdown_side2() or (not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_x2' in self.aim_key)):
                self.refresh_pressed_key_config('mouse_x2')
                self.old_pressed_aim_key = 'mouse_x2'
                self.aim_key_status = True
                self.reset_dynamic_aim_scope('mouse_x2')
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x2':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if kmNet.isdown_middle():
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_middle' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_middle')
                    self.old_pressed_aim_key = 'mouse_middle'
                    self.aim_key_status = True
                    self.reset_dynamic_aim_scope('mouse_middle')
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_middle':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            time.sleep(0.005)

    def check_long_press(self):
        """Check if long press duration reached"""
        if self.left_pressed:
            self.left_pressed_long = True

    def left_press(self):
        self.left_pressed = True
        if self.config.get('recoil', {}).get('use_mouse_re_trajectory', False) and getattr(self, 'down_switch', False):
            try:
                self._start_mouse_re_recoil()
            except Exception as e:
                print(f'mouse_re trajectory replay failed to start: {e}')
        long_press_duration = self.config['groups'][self.group]['long_press_duration']
        if long_press_duration > 0:
            self.press_timer = Timer(long_press_duration / 1000, self.check_long_press)
            self.press_timer.start()

    def left_release(self):
        self.left_pressed = False
        self.left_pressed_long = False
        self.reset_down_status()
        if self._recoil_is_replaying:
            self._stop_mouse_re_recoil()
        if self.press_timer:
            self.press_timer.cancel()
            self.press_timer = None

    def start_listen_pnmh(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.keyboard_listener.start()
        self.pnmh_listen_switch = True
        self.pnmh.Notify_Mouse(63)

        def parse_mouse_button(data):
            btn_map = {4: 'mouse_x1', 5: 'mouse_x2'}
            if len(data) >= 3 and data[0] == 7:
                return {'button': btn_map.get(data[1], 'none'), 'action': data[2]}
            btn_map = {1: 'mouse_left', 2: 'mouse_right', 4: 'mouse_middle'}
            return {'button': btn_map.get(data[0], 'none'), 'action': data[1]}
        while self.pnmh_listen_switch:
            ret = self.pnmh.Read_Notify(10)
            if ret:
                data = list(ret)
                data = parse_mouse_button(data)
                if data['button']!= 'none':
                    if data['action'] == 1:
                        if data['button'] == 'mouse_left' and (not self.left_pressed):
                            self.left_press()
                        if not self.aim_key_status and self.old_pressed_aim_key == '':
                            if data['button'] in self.aim_key:
                                self.refresh_pressed_key_config(data['button'])
                                self.old_pressed_aim_key = data['button']
                                self.aim_key_status = True
                    else:
                        if data['action'] == 0:
                            if data['button'] == 'mouse_left' and self.left_pressed:
                                self.left_release()
                            if self.aim_key_status and self.old_pressed_aim_key == data['button']:
                                self.old_pressed_aim_key = ''
                                self.aim_key_status = False
                                self.reset_pid()
        self.pnmh.Notify_Mouse(0)

    def start_listen_makcu(self):
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
                    self.makcu_listen_switch = True
                    while self.makcu_listen_switch:
                        try:
                            states = getattr(self.makcu, 'button_states', {})
                            left_state = bool(states.get(0, False))
                            right_state = bool(states.get(1, False))
                            middle_state = bool(states.get(2, False))
                            side1_state = bool(states.get(3, False))
                            side2_state = bool(states.get(4, False))
                            if left_state:
                                if not self.left_pressed:
                                    self.left_press()
                                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_left' in self.aim_key):
                                    self.refresh_pressed_key_config('mouse_left')
                                    self.old_pressed_aim_key = 'mouse_left'
                                    self.aim_key_status = True
                            else:
                                if self.left_pressed:
                                    self.left_release()
                                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_left':
                                    self.old_pressed_aim_key = ''
                                    self.aim_key_status = False
                                    self.reset_pid()
                            if right_state:
                                if not self.right_pressed:
                                    self.right_pressed = True
                                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_right' in self.aim_key):
                                    self.refresh_pressed_key_config('mouse_right')
                                    self.old_pressed_aim_key = 'mouse_right'
                                    self.aim_key_status = True
                            else:
                                if self.right_pressed:
                                    self.right_pressed = False
                                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_right':
                                    self.old_pressed_aim_key = ''
                                    self.aim_key_status = False
                                    self.reset_pid()
                            if not side1_state or not self.aim_key_status:
                                if self.old_pressed_aim_key == '' and 'mouse_x1' in self.aim_key:
                                    self.refresh_pressed_key_config('mouse_x1')
                                    self.old_pressed_aim_key = 'mouse_x1'
                                    self.aim_key_status = True
                            else:
                                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x1':
                                    self.old_pressed_aim_key = ''
                                    self.aim_key_status = False
                                    self.reset_pid()
                            if not side2_state or (not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_x2' in self.aim_key)):
                                self.refresh_pressed_key_config('mouse_x2')
                                self.old_pressed_aim_key = 'mouse_x2'
                                self.aim_key_status = True
                            else:
                                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x2':
                                    self.old_pressed_aim_key = ''
                                    self.aim_key_status = False
                                    self.reset_pid()
                        except Exception:
                            pass
                        time.sleep(0.01)
                else:
                    print('makcu not connected')
        except Exception as e:
            print(f'Makcu listen failed: {e}')
            self.makcu = None

    def start_listen_catbox(self):
        """CatBox listen thread - uses standard listening method"""
        print('CatBox listen thread started')
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.keyboard_listener.start()
            self.mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)
            self.mouse_listener.start()
            print('CatBox: Standard keyboard/mouse listening started')
            while True:
                if not catbox.is_connected:
                    time.sleep(1)
                else:
                    time.sleep(0.01)
        except Exception as e:
            print(f'CatBox listen initialization failed: {e}')

    def start_listen_dhz(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.keyboard_listener.start()
        self.dhz.monitor(7654)
        self.time_begin_period(1)
        self.dhz_listen_switch = True
        while self.dhz_listen_switch:
            if self.dhz.isdown_left():
                if not self.left_pressed:
                    self.left_press()
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_left' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_left')
                    self.old_pressed_aim_key = 'mouse_left'
                    self.aim_key_status = True
            else:
                if self.left_pressed:
                    self.left_release()
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_left':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if self.dhz.isdown_right():
                if not self.right_pressed:
                    self.right_pressed = True
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_right' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_right')
                    self.old_pressed_aim_key = 'mouse_right'
                    self.aim_key_status = True
            else:
                if self.right_pressed:
                    self.right_pressed = False
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_right':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if self.dhz.isdown_side1():
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_x1' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_x1')
                    self.old_pressed_aim_key = 'mouse_x1'
                    self.aim_key_status = True
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x1':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if self.dhz.isdown_side2():
                if not self.aim_key_status and self.old_pressed_aim_key == '' and ('mouse_x2' in self.aim_key):
                    self.refresh_pressed_key_config('mouse_x2')
                    self.old_pressed_aim_key = 'mouse_x2'
                    self.aim_key_status = True
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_x2':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            if self.dhz.isdown_middle():
                if not self.aim_key_status and self.old_pressed_aim_key == '':
                    if 'mouse_middle' in self.aim_key:
                        self.refresh_pressed_key_config('mouse_middle')
                        self.old_pressed_aim_key = 'mouse_middle'
                        self.aim_key_status = True
            else:
                if self.aim_key_status and self.old_pressed_aim_key == 'mouse_middle':
                    self.old_pressed_aim_key = ''
                    self.aim_key_status = False
                    self.reset_pid()
            time.sleep(0.001)
        self.dhz.RECEIVER_FLAG = False

    def stop_listen(self):
        if self.keyboard_listener is not None and self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
            self.keyboard_listener.join()
        if self.mouse_listener is not None and self.mouse_listener.is_alive():
            self.mouse_listener.stop()
            self.mouse_listener.join()
        self.km_listen_switch = False
        if self.dhz is not None and self.dhz.RECEIVER_FLAG:
            self.dhz.RECEIVER_FLAG = False
        self.dhz_listen_switch = False
        self.pnmh_listen_switch = False
        self.makcu_listen_switch = False

    def disconnect_device(self):
        try:
            if getattr(self, 'keyboard_listener', None) is not None and self.keyboard_listener.is_alive():
                try:
                    self.keyboard_listener.stop()
                    self.keyboard_listener.join()
                except Exception:
                    pass
            if getattr(self, 'mouse_listener', None) is not None and self.mouse_listener.is_alive():
                try:
                    self.mouse_listener.stop()
                    self.mouse_listener.join()
                except Exception:
                    pass
            self.km_listen_switch = False
            self.dhz_listen_switch = False
            self.pnmh_listen_switch = False
            self.makcu_listen_switch = False
            self.unmask_all()
            move_method = self.config.get('move_method')
            if move_method == 'makcu':
                if getattr(self, 'makcu', None) is not None:
                    try:
                        try:
                            self.makcu.disconnect()
                        except Exception as e:
                            print('Disconnect Makcu failed: ' + f'{e}')
                    finally:
                        if hasattr(self, '_makcu_move_queue') and self._makcu_move_queue is not None:
                            try:
                                while True:
                                    self._makcu_move_queue.get_nowait()
                            except Exception:
                                pass
                        self.makcu = None
            elif move_method == 'dhz':
                if getattr(self, 'dhz', None) is not None:
                    try:
                        self.dhz.monitor(0)
                    except Exception:
                        pass
                    self.dhz.RECEIVER_FLAG = False
            elif move_method == 'km_net':
                try:
                    if hasattr(kmNet, 'monitor'):
                        try:
                            kmNet.monitor(0)
                        except Exception:
                            pass
                    if hasattr(kmNet, 'unmask_all'):
                        kmNet.unmask_all()
                except Exception as e:
                    print('Disconnect KM Net failed: ' + f'{e}')
            elif move_method == 'catbox':
                try:
                    catbox_disconnect()
                except Exception as e:
                    print('Disconnect CatBox failed: ' + f'{e}')
            elif move_method == 'pnmh':
                if getattr(self, 'pnmh', None) is not None:
                    try:
                        self.pnmh.Lock_Mouse(0)
                        self.pnmh.Notify_Mouse(0)
                    except Exception:
                        pass
            self.left_pressed = False
            self.right_pressed = False
            self.aim_key_status = False
            self.old_pressed_aim_key = ''
        except Exception as e:
            print('Disconnect device failed: ' + f'{e}')

    def unmask_all(self):
        """Remove all input masks"""
        if self.config['move_method'] == 'makcu':
            if self.makcu is not None:
                try:
                    self.makcu.lock_ml(0)
                    self.makcu.lock_mr(0)
                    self.makcu.lock_mm(0)
                    self.makcu.lock_ms1(0)
                    self.makcu.lock_ms2(0)
                    self.makcu.lock_mx(0)
                    self.makcu.lock_my(0)
                except Exception as e:
                    print(f'Remove Makcu mask failed: {e}')
        else:
            if self.config['move_method'] == 'dhz':
                if self.dhz is not None:
                    self.dhz.mask_left(0)
                    self.dhz.mask_right(0)
                    self.dhz.mask_middle(0)
                    self.dhz.mask_side1(0)
                    self.dhz.mask_side2(0)
                    self.dhz.mask_x(0)
                    self.dhz.mask_y(0)
                    self.dhz.mask_wheel(0)
            else:
                if self.config['move_method'] == 'km_net':
                    kmNet.unmask_all()
                else:
                    if self.config['move_method'] == 'pnmh' and self.pnmh is not None:
                        self.pnmh.Lock_Mouse(0)
