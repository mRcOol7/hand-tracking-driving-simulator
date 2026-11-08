"""Configuration settings for ATS Hand Tracking Steering Wheel."""

# Camera Settings
# Set to an integer (0, 1, 2) for USB webcams or Phone Virtual Webcam apps (DroidCam / Iriun)
# OR set to an RTSP/HTTP URL string (e.g. "http://192.168.1.50:8080/video") for wireless IP Webcam apps
CAMERA_SOURCE = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FLIP_CAMERA = True  # Mirror video so turning right on screen matches your natural hand movement

# MediaPipe Hand Tracking Settings
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
MAX_NUM_HANDS = 2

# Tracking Engine Architecture:
# "advanced" : Enterprise Polar Orbit Tangent Engine (Supports Full 360°/900° continuous rotation,
#              Hand-Over-Hand maneuvers, 1 Euro Adaptive Filtering, and Self-Aligning Caster Force)
# "standard" : Basic 2-hand angle slope engine (±45° tilt range)
ENGINE_MODE = "advanced"

# Multi-Turn Steering Lock (Degrees)
# Set to 45.0° for natural, responsive hand steering where 45° tilt = 100% full steering lock
MAX_STEERING_ANGLE = 45.0
STEERING_DEADZONE = 3.0        # Degrees near center treated as perfectly straight (0.0)
SMOOTHING_FACTOR = 0.25        # 0.0 to 1.0 (Lower = smoother & less jitter, Higher = faster reaction)
AUTO_CENTER_RATE = 0.20        # Speed at which steering returns to 0 when hands are not detected

# Input Modes
# "gamepad"  : Emulates an Xbox 360 Controller via vgamepad (recommended for ATS analog steering)
# "keyboard" : Simulates DirectInput key presses (A / D) via pydirectinput
DEFAULT_INPUT_MODE = "gamepad"

# Keyboard Mode Settings (ATS Defaults)
KEY_STEER_LEFT = "a"
KEY_STEER_RIGHT = "d"
KEY_ACCEL = "w"
KEY_BRAKE = "s"
KEY_INDICATOR_LEFT = "["       # ATS default left turn signal
KEY_INDICATOR_RIGHT = "]"      # ATS default right turn signal
KEY_HORN = "h"                 # ATS default city horn
KEY_AIR_HORN = "n"             # ATS default air horn

# Gestures for Horn and Indicators
ENABLE_HORN_GESTURE = True      # Press center of virtual wheel hub to HONK
ENABLE_INDICATOR_GESTURES = True # Extend index finger outward to flick turn signal lever


# Gestures for Acceleration and Braking
# Enable if you want hand-based gas and brake triggers
ENABLE_GESTURE_PEDALS = True
THROTTLE_THRESHOLD_Y = 0.35    # Raising hands above this relative height engages throttle (or pinch)
BRAKE_PINCH_DISTANCE = 0.05    # Pinching thumb and index finger triggers brake

# Visual UI / HUD Settings
SHOW_LANDMARKS = True
SHOW_STEERING_WHEEL_HUD = True
SHOW_METRICS = True
WHEEL_RADIUS = 120

