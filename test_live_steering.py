"""
Live Diagnostic Test Tool for ATS Hand Steering
Displays camera, detects hands, sets gamepad, and reads back XInput in real-time.
"""

import sys, os, time, math, ctypes
from ctypes import Structure, c_ushort, c_byte, c_short, byref
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import config
import vgamepad as vg
from advanced_tracker import AdvancedSteeringEngine

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
    xinput = ctypes.windll.xinput1_4
except:
    xinput = ctypes.windll.xinput9_1_0

print("=" * 60)
print("  ATS HAND STEERING - LIVE DIAGNOSTIC & AXIS TEST")
print("=" * 60)

try:
    pad = vg.VX360Gamepad()
    print("[OK] Virtual Xbox 360 Gamepad connected to Windows!")
except Exception as e:
    print(f"[ERROR] Failed to connect gamepad: {e}")
    pad = None

tracker = AdvancedSteeringEngine()
print("[OK] Advanced Hand Tracker initialized!")

cap = cv2.VideoCapture(config.CAMERA_SOURCE)
if not cap.isOpened():
    print("[ERROR] Camera could not be opened!")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

win_name = "LIVE STEERING & GAMEPAD DIAGNOSTIC (Press Q to quit)"
cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(win_name, 960, 540)

print("\nCamera started! Look at the on-screen display:")
print("Tilt your hands left/right to steer. Press 'Q' or 'ESC' to exit.\n")

xinput_lx = 0
xinput_rt = 0
xinput_lt = 0

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    if config.FLIP_CAMERA:
        frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    # Process hand tracking
    data = tracker.process_frame(frame)
    steer = data["steer"]
    throttle = data.get("throttle", 0.0)
    brake = data.get("brake", 0.0)
    angle = data.get("calibrated_angle", 0.0)

    # Apply to gamepad
    if pad:
        pad.left_joystick_float(x_value_float=float(steer), y_value_float=0.0)
        pad.right_trigger_float(value_float=float(throttle))
        pad.left_trigger_float(value_float=float(brake))
        pad.update()

        # Read back actual Windows XInput state
        state = XINPUT_STATE()
        res = xinput.XInputGetState(0, byref(state))
        if res == 0:
            xinput_lx = state.Gamepad.sThumbLX
            xinput_rt = state.Gamepad.bRightTrigger
            xinput_lt = state.Gamepad.bLeftTrigger

    # Draw Diagnostic HUD Overlay
    cv2.rectangle(frame, (20, 20), (w - 20, 160), (0, 0, 0), -1)
    cv2.rectangle(frame, (20, 20), (w - 20, 160), (0, 255, 200), 2)

    # 1. Hands status
    hands_cnt = data.get("hands_detected", 0)
    if hands_cnt >= 2:
        h_status = "2 HANDS DETECTED (WHEEL TILT ACTIVE)"
        h_col = (0, 255, 120)
    elif hands_cnt == 1:
        h_status = "1 HAND DETECTED (MOVE HAND LEFT/RIGHT)"
        h_col = (0, 220, 255)
    else:
        h_status = "NO HANDS DETECTED (RAISE BOTH HANDS)"
        h_col = (0, 0, 255)

    cv2.putText(frame, h_status, (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.75, h_col, 2, cv2.LINE_AA)

    # 2. Angle and Steer
    info_str = f"Wheel Angle: {angle:+5.1f} deg  |  Steer Output: {steer:+5.2f} (-1.0 to +1.0)"
    cv2.putText(frame, info_str, (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    # 3. Windows XInput State
    xinput_str = f"WINDOWS GAMEPAD X-AXIS: {xinput_lx:+6d} / 32767   [LT: {xinput_lt} | RT: {xinput_rt}]"
    col_x = (0, 255, 120) if abs(xinput_lx) > 1000 else (180, 180, 180)
    cv2.putText(frame, xinput_str, (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.75, col_x, 2, cv2.LINE_AA)

    # Draw bottom visual bar
    bar_w = 600
    bx1 = (w - bar_w) // 2
    by1 = h - 60
    cv2.rectangle(frame, (bx1, by1), (bx1 + bar_w, by1 + 30), (30, 30, 30), -1)
    cv2.rectangle(frame, (bx1, by1), (bx1 + bar_w, by1 + 30), (120, 120, 120), 2)
    center_bx = bx1 + bar_w // 2
    cv2.line(frame, (center_bx, by1 - 5), (center_bx, by1 + 35), (255, 255, 255), 2)

    cur_x = center_bx + int(steer * (bar_w // 2))
    fill_col = (0, 255, 120) if abs(steer) < 0.05 else ((255, 200, 0) if steer > 0 else (255, 50, 200))
    cv2.rectangle(frame, (min(center_bx, cur_x), by1 + 2), (max(center_bx, cur_x), by1 + 28), fill_col, -1)
    cv2.circle(frame, (cur_x, by1 + 15), 10, (255, 255, 255), -1)

    cv2.imshow(win_name, frame)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), ord('Q'), 27):
        break

cap.release()
cv2.destroyAllWindows()
print("[OK] Test finished successfully.")

