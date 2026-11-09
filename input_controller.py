"""Game input controller supporting Virtual Xbox 360 Gamepad (vgamepad),
Simultaneous Physical Xbox Controller Pass-Through (XInput), and DirectInput Keyboard.
Stripped of horn and indicators; focused 100% on smooth Steering, Pedals, and Gear Shifting.
"""

import time
import ctypes
from ctypes import Structure, c_ushort, c_byte, c_short, byref
import config

# Try to import vgamepad (Virtual Xbox 360)
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

# XInput Structure for Physical Xbox Controller Pass-Through
class XINPUT_GAMEPAD(Structure):
    _fields_ = [
        ('wButtons', c_ushort),
        ('bLeftTrigger', c_byte),
        ('bRightTrigger', c_byte),
        ('sThumbLX', c_short),
        ('sThumbLY', c_short),
        ('sThumbRX', c_short),
        ('sThumbRY', c_short),
    ]

class XINPUT_STATE(Structure):
    _fields_ = [
        ('dwPacketNumber', ctypes.c_ulong),
        ('Gamepad', XINPUT_GAMEPAD)
    ]

try:
    xinput_dll = ctypes.windll.xinput1_4
except Exception:
    try:
        xinput_dll = ctypes.windll.xinput9_1_0
    except Exception:
        xinput_dll = None


class InputController:
    def __init__(self, mode=config.DEFAULT_INPUT_MODE):
        self.mode = mode
        self.gamepad = None
        self.is_paused = False
        self.active_keys = set()

        # Physical Controller Pass-Through State
        self.physical_slot = None
        self.physical_controller_active = False

        # Gear Shift Timing
        self.gear_pulse_end_time = 0.0
        self.gear_pulse_button = None

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
            print("[InputController] Switched to KEYBOARD mode (DirectInput A/D/W/S/Shift/Ctrl).")
        else:
            if VGAMEPAD_AVAILABLE:
                self.mode = "gamepad"
                if self.gamepad is None:
                    self._init_gamepad()
                print("[InputController] Switched to GAMEPAD mode (Analog Xbox 360 + Physical Pass-Through).")
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

    def _poll_physical_controller(self):
        """Polls connected physical Xbox controllers for triggers, buttons, and right stick."""
        if not xinput_dll or not getattr(config, "ENABLE_PHYSICAL_CONTROLLER", True):
            return None

        state = XINPUT_STATE()
        # Scan slots 0 to 3
        for slot in range(4):
            res = xinput_dll.XInputGetState(slot, byref(state))
            if res == 0:
                gp = state.Gamepad
                # If physical controller has any user interaction (triggers pulled or buttons pressed)
                # or if we have locked onto this physical slot
                if self.physical_slot == slot or gp.wButtons != 0 or gp.bRightTrigger > 10 or gp.bLeftTrigger > 10 or abs(gp.sThumbRX) > 3000:
                    self.physical_slot = slot
                    self.physical_controller_active = True
                    return gp

        return None

    def apply_inputs(self, steer_val, throttle_val=0.0, brake_val=0.0, gear_shift=None):
        """
        Apply steer (-1.0 to 1.0), throttle, brake, and gear shifts to game.
        Combines hand tracking with simultaneous physical Xbox controller pass-through!
        """
        if self.is_paused:
            return

        if self.mode == "gamepad" and self.gamepad is not None:
            self._apply_gamepad(steer_val, throttle_val, brake_val, gear_shift)
        elif self.mode == "keyboard":
            self._apply_keyboard(steer_val, throttle_val, brake_val, gear_shift)

    def _apply_gamepad(self, steer, throttle, brake, gear_shift):
        try:
            now = time.time()
            phys_gp = self._poll_physical_controller()

            # 1. Throttle & Brake: Physical Triggers take priority if pressed, else hand gesture pedals
            final_throttle = float(throttle)
            final_brake = float(brake)
            final_buttons = 0
            rx = 0
            ry = 0

            if phys_gp:
                # Read physical RT (Gas) and LT (Brake)
                phys_rt = phys_gp.bRightTrigger / 255.0
                phys_lt = phys_gp.bLeftTrigger / 255.0
                if phys_rt > 0.05:
                    final_throttle = max(final_throttle, phys_rt)
                if phys_lt > 0.05:
                    final_brake = max(final_brake, phys_lt)

                # Pass through physical right thumbstick (Look Around in ATS)
                rx = phys_gp.sThumbRX
                ry = phys_gp.sThumbRY

                # Pass through physical buttons
                final_buttons = phys_gp.wButtons

            # 2. Hand Steering: Always mapped to Left Stick X-axis (-1.0 to +1.0)
            self.gamepad.left_joystick_float(x_value_float=float(steer), y_value_float=0.0)

            # 3. Gas & Brake Triggers
            if config.ENABLE_GESTURE_PEDALS or phys_gp:
                self.gamepad.right_trigger_float(value_float=float(final_throttle))
                self.gamepad.left_trigger_float(value_float=float(final_brake))

            # 4. Right Stick Pass-Through
            if phys_gp:
                self.gamepad.right_joystick(x_value=rx, y_value=ry)

            # 5. Gear Shifting Pulse (Button A for Drive, Button X for Reverse, Button Y for Neutral)
            if gear_shift == "UP":
                # Shift to Drive (D) -> Pulse Button A
                self.gear_pulse_button = vg.XUSB_BUTTON.XUSB_GAMEPAD_A
                self.gear_pulse_end_time = now + 0.18
            elif gear_shift == "DOWN":
                # Shift to Reverse (R) -> Pulse Button X
                self.gear_pulse_button = vg.XUSB_BUTTON.XUSB_GAMEPAD_X
                self.gear_pulse_end_time = now + 0.18
            elif gear_shift == "NEUTRAL":
                # Shift to Neutral (N) -> Pulse Button Y
                self.gear_pulse_button = vg.XUSB_BUTTON.XUSB_GAMEPAD_Y
                self.gear_pulse_end_time = now + 0.18

            # Combine active gear pulse button with physical buttons
            if now < self.gear_pulse_end_time and self.gear_pulse_button:
                final_buttons |= self.gear_pulse_button

            # Apply buttons to virtual report
            self.gamepad.report.wButtons = final_buttons

            # 6. Flush state report to Windows driver
            self.gamepad.update()
        except Exception as e:
            print(f"[InputController] Gamepad update error: {e}")

    def _apply_keyboard(self, steer, throttle, brake, gear_shift):
        if not PYDIRECTINPUT_AVAILABLE:
            return

        # Steering: threshold-based with deadzone
        if steer < -0.12:
            self._press_key(config.KEY_STEER_LEFT)
            self._release_key(config.KEY_STEER_RIGHT)
        elif steer > 0.12:
            self._press_key(config.KEY_STEER_RIGHT)
            self._release_key(config.KEY_STEER_LEFT)
        else:
            self._release_key(config.KEY_STEER_LEFT)
            self._release_key(config.KEY_STEER_RIGHT)

        # Pedals
        if config.ENABLE_GESTURE_PEDALS:
            if throttle > 0.35:
                self._press_key(config.KEY_ACCEL)
            else:
                self._release_key(config.KEY_ACCEL)

            if brake > 0.35:
                self._press_key(config.KEY_BRAKE)
            else:
                self._release_key(config.KEY_BRAKE)

        # Gear Shifting Key Pulses
        if gear_shift == "UP":
            self._tap_key(config.KEY_GEAR_DRIVE)
        elif gear_shift == "DOWN":
            self._tap_key(config.KEY_GEAR_REVERSE)
        elif gear_shift == "NEUTRAL":
            self._tap_key(config.KEY_GEAR_NEUTRAL)

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
        """Release all pressed buttons and center axes."""
        if self.mode == "gamepad" and self.gamepad is not None:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass

        if PYDIRECTINPUT_AVAILABLE:
            for k in list(self.active_keys):
                try:
                    pydirectinput.keyUp(k)
                except Exception:
                    pass
            self.active_keys.clear()

    def close(self):
        """Clean up resources, reset buttons, and disconnect virtual gamepad."""
        self.reset_all()
        if self.gamepad is not None:
            try:
                del self.gamepad
                self.gamepad = None
            except Exception:
                pass
