"""Game input controller supporting Virtual Xbox 360 Gamepad (vgamepad) and Keyboard (pydirectinput).
Now includes ATS Horn and Left/Right Turn Indicators support.
"""

import time
import config

# Try to import vgamepad (may raise RuntimeError if ViGEmBus driver is not installed)
try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except Exception as e:
    vg = None
    VGAMEPAD_AVAILABLE = False
    print(f"[InputController] Note: Virtual Gamepad driver not detected ({e}). Using DirectInput Keyboard mode.")

# Try to import pydirectinput
try:
    import pydirectinput
    PYDIRECTINPUT_AVAILABLE = True
except ImportError:
    pydirectinput = None
    PYDIRECTINPUT_AVAILABLE = False


class InputController:
    def __init__(self, mode=config.DEFAULT_INPUT_MODE):
        self.mode = mode
        self.gamepad = None
        self.is_paused = False
        self.active_keys = set()
        self.last_ind_left_time = 0.0
        self.last_ind_right_time = 0.0

        if self.mode == "gamepad":
            self._init_gamepad()
        else:
            print("[InputController] Initialized in KEYBOARD mode.")

    def _init_gamepad(self):
        if not VGAMEPAD_AVAILABLE:
            print("[InputController] WARNING: vgamepad not available. Falling back to KEYBOARD mode.")
            self.mode = "keyboard"
            return

        try:
            self.gamepad = vg.VX360Gamepad()
            print("[InputController] Virtual Xbox 360 Controller connected successfully!")
        except Exception as e:
            print(f"[InputController] Failed to initialize virtual gamepad: {e}")
            print("[InputController] Falling back to KEYBOARD mode.")
            self.mode = "keyboard"

    def toggle_mode(self):
        """Toggle between Gamepad and Keyboard modes."""
        self.reset_all()
        if self.mode == "gamepad":
            self.mode = "keyboard"
            print("[InputController] Switched to KEYBOARD mode (DirectInput A/D/W/S/[/]/H).")
        else:
            if VGAMEPAD_AVAILABLE:
                self.mode = "gamepad"
                if self.gamepad is None:
                    self._init_gamepad()
                print("[InputController] Switched to GAMEPAD mode (Analog Xbox 360).")
            else:
                print("[InputController] Gamepad mode unavailable (vgamepad not installed).")

    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.reset_all()
            print("[InputController] PAUSED: Input delivery suspended.")
        else:
            print("[InputController] RESUMED: Input delivery active.")
        return self.is_paused

    def apply_inputs(self, steer_val, throttle_val=0.0, brake_val=0.0, horn=False, ind_left=False, ind_right=False):
        """
        Apply steer (-1.0 to 1.0), throttle, brake, horn, and indicators to game.
        """
        if self.is_paused:
            return

        if self.mode == "gamepad" and self.gamepad is not None:
            self._apply_gamepad(steer_val, throttle_val, brake_val, horn, ind_left, ind_right)
        elif self.mode == "keyboard":
            self._apply_keyboard(steer_val, throttle_val, brake_val, horn, ind_left, ind_right)

    def _apply_gamepad(self, steer, throttle, brake, horn, ind_left, ind_right):
        try:
            # Steering on Left Stick X-axis
            self.gamepad.left_joystick_float(x_value_float=float(steer), y_value_float=0.0)

            # Gas & Brake Triggers
            if config.ENABLE_GESTURE_PEDALS:
                self.gamepad.right_trigger_float(value_float=float(throttle))
                self.gamepad.left_trigger_float(value_float=float(brake))

            # Horn (Left Thumbstick Click)
            if horn:
                self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
            else:
                self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)

            # Indicators (D-Pad Left / Right) with debounce
            now = time.time()
            if ind_left and (now - self.last_ind_left_time > 0.6):
                self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                self.last_ind_left_time = now
            else:
                self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)

            if ind_right and (now - self.last_ind_right_time > 0.6):
                self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
                self.last_ind_right_time = now
            else:
                self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

            self.gamepad.update()
        except Exception as e:
            print(f"[InputController] Gamepad update error: {e}")

    def _apply_keyboard(self, steer, throttle, brake, horn, ind_left, ind_right):
        if not PYDIRECTINPUT_AVAILABLE:
            return

        # Steering: threshold-based with deadzone
        if steer < -0.15:
            self._press_key(config.KEY_STEER_LEFT)
            self._release_key(config.KEY_STEER_RIGHT)
        elif steer > 0.15:
            self._press_key(config.KEY_STEER_RIGHT)
            self._release_key(config.KEY_STEER_LEFT)
        else:
            self._release_key(config.KEY_STEER_LEFT)
            self._release_key(config.KEY_STEER_RIGHT)

        # Pedals
        if config.ENABLE_GESTURE_PEDALS:
            if throttle > 0.4:
                self._press_key(config.KEY_ACCEL)
            else:
                self._release_key(config.KEY_ACCEL)

            if brake > 0.4:
                self._press_key(config.KEY_BRAKE)
            else:
                self._release_key(config.KEY_BRAKE)

        # Horn ('H')
        if horn:
            self._press_key(config.KEY_HORN)
        else:
            self._release_key(config.KEY_HORN)

        # Indicators ('[' and ']') with debounce
        now = time.time()
        if ind_left and (now - self.last_ind_left_time > 0.6):
            self._tap_key(config.KEY_INDICATOR_LEFT)
            self.last_ind_left_time = now

        if ind_right and (now - self.last_ind_right_time > 0.6):
            self._tap_key(config.KEY_INDICATOR_RIGHT)
            self.last_ind_right_time = now

    def _press_key(self, key):
        if key not in self.active_keys:
            try:
                pydirectinput.keyDown(key)
                self.active_keys.add(key)
            except Exception:
                pass

    def _release_key(self, key):
        if key in self.active_keys:
            try:
                pydirectinput.keyUp(key)
                self.active_keys.discard(key)
            except Exception:
                pass

    def _tap_key(self, key):
        try:
            pydirectinput.press(key)
        except Exception:
            pass

    def reset_all(self):
        """Release all inputs and reset virtual axes to neutral."""
        if self.gamepad is not None:
            try:
                self.gamepad.left_joystick_float(0.0, 0.0)
                self.gamepad.right_trigger_float(0.0)
                self.gamepad.left_trigger_float(0.0)
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass

        if PYDIRECTINPUT_AVAILABLE:
            for key in list(self.active_keys):
                try:
                    pydirectinput.keyUp(key)
                except Exception:
                    pass
            self.active_keys.clear()

    def close(self):
        """Clean teardown."""
        self.reset_all()
        if self.gamepad is not None:
            try:
                del self.gamepad
                self.gamepad = None
            except Exception:
                pass
