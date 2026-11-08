import sys, os, time, math, ctypes
from ctypes import Structure, c_ushort, c_byte, c_short, byref
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import config
import vgamepad as vg
from input_controller import InputController
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

print("1. Initializing InputController...")
controller = InputController(mode="gamepad")

time.sleep(1)

print("2. Testing Direct Controller steering:")
for steer_test in [-1.0, -0.5, 0.0, 0.5, 1.0]:
    controller.apply_inputs(steer_val=steer_test, throttle_val=0.0, brake_val=0.0)
    time.sleep(0.1)
    state = XINPUT_STATE()
    res = xinput.XInputGetState(0, byref(state))
    print(f"   Input steer_val={steer_test:+.2f} -> XInput sThumbLX={state.Gamepad.sThumbLX}")

print("\n3. Testing AdvancedHandTracker direct hand angle calculation...")
tracker = AdvancedSteeringEngine()

# Let's test what happens when hands are tilted in tracker:
# We simulate landmarks for left hand and right hand
class MockLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

class MockResults:
    def __init__(self, hand_landmarks):
        self.hand_landmarks = hand_landmarks

def make_hand(wrist_x, wrist_y):
    lms = []
    for i in range(21):
        # thumb tip = 4, index tip = 8, wrist = 0, mcp = 9
        lms.append(MockLandmark(wrist_x + i*0.001, wrist_y + i*0.001))
    return lms

w, h = 1280, 720
# Neutral hands: Left at x=0.35, y=0.5. Right at x=0.65, y=0.5
hand_left = make_hand(0.35, 0.50)
hand_right = make_hand(0.65, 0.50)

# Feed frame through tracker
results = MockResults([hand_left, hand_right])

# We mock detector.detect
tracker.detector.detect = lambda img: results

dummy_frame = np.zeros((h, w, 3), dtype=np.uint8)

print("\n--- TEST A: Neutral Level Hands ---")
for _ in range(5):
    data = tracker.process_frame(dummy_frame)
    time.sleep(0.02)
print(f"   Neutral: wheel_angle={data['wheel_angle_deg']:.2f}°, steer={data['steer']:.3f}")

print("\n--- TEST B: Steering RIGHT (Right hand down y=0.62, Left hand up y=0.38) ---")
hand_left_up = make_hand(0.35, 0.38)
hand_right_dn = make_hand(0.65, 0.62)
tracker.detector.detect = lambda img: MockResults([hand_left_up, hand_right_dn])
for _ in range(10):
    data = tracker.process_frame(dummy_frame)
    controller.apply_inputs(steer_val=data['steer'], throttle_val=data['throttle'], brake_val=data['brake'])
    time.sleep(0.02)

state = XINPUT_STATE()
xinput.XInputGetState(0, byref(state))
print(f"   Steer Right: wheel_angle={data['wheel_angle_deg']:.2f}°, steer={data['steer']:.3f} -> XInput sThumbLX={state.Gamepad.sThumbLX}")

print("\n--- TEST C: Steering LEFT (Left hand down y=0.62, Right hand up y=0.38) ---")
hand_left_dn = make_hand(0.35, 0.62)
hand_right_up = make_hand(0.65, 0.38)
tracker.detector.detect = lambda img: MockResults([hand_left_dn, hand_right_up])
for _ in range(10):
    data = tracker.process_frame(dummy_frame)
    controller.apply_inputs(steer_val=data['steer'], throttle_val=data['throttle'], brake_val=data['brake'])
    time.sleep(0.02)

state = XINPUT_STATE()
xinput.XInputGetState(0, byref(state))
print(f"   Steer Left: wheel_angle={data['wheel_angle_deg']:.2f}°, steer={data['steer']:.3f} -> XInput sThumbLX={state.Gamepad.sThumbLX}")

print("\n--- TEST D: 1-Hand Steering (Move hand to right side x=0.75) ---")
hand_single_rt = make_hand(0.75, 0.50)
tracker.detector.detect = lambda img: MockResults([hand_single_rt])
for _ in range(10):
    data = tracker.process_frame(dummy_frame)
    controller.apply_inputs(steer_val=data['steer'], throttle_val=data['throttle'], brake_val=data['brake'])
    time.sleep(0.02)

state = XINPUT_STATE()
xinput.XInputGetState(0, byref(state))
print(f"   1-Hand Right: wheel_angle={data['wheel_angle_deg']:.2f}°, steer={data['steer']:.3f} -> XInput sThumbLX={state.Gamepad.sThumbLX}")

print("\nTEST COMPLETE!")
