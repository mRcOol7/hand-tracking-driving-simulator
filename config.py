"""Configuration settings for ATS Hand Tracking Steering Wheel."""

# Camera Settings
CAMERA_SOURCE = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FLIP_CAMERA = True  # Mirror video so turning right on screen matches your natural hand movement

# MediaPipe Hand Tracking Settings
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
MAX_NUM_HANDS = 2

# Tracking Engine Architecture:
# "advanced" : Enterprise Polar Orbit Tangent Engine with Anatomical Handedness,
#              Seamless Cross-Hand (Hand-over-Hand) Multi-Turn Rotation,
#              and Progressive S-Curve Anti-Twitch Highway Stability.
ENGINE_MODE = "advanced"

# Progressive Steering Response Curve (Anti-Twitch Formula: alpha*u + (1-alpha)*u^exponent)
# Near center (0-15°): Ultra-forgiving, calm, rock-steady lane keeping on highways.
# At full tilt (60-70°): Smoothly ramps up to 100% full lock for sharp city turns & parking.
MAX_STEERING_ANGLE = 70.0          # Degrees of hand tilt for 100% steering lock
STEERING_DEADZONE = 3.5            # Degrees near center treated as perfectly straight (0.0)
STEERING_S_CURVE_EXPONENT = 2.4    # Exponent for non-linear curve (higher = calmer center)
STEERING_LINEAR_COEFF = 0.20       # Linear blend component for natural progressive response
SMOOTHING_FACTOR = 0.25            # Smoothing factor (One Euro filter frequency tuning)
AUTO_CENTER_RATE = 0.15            # Caster self-centering speed when hands release wheel

# Input Modes
DEFAULT_INPUT_MODE = "gamepad"     # "gamepad" (Xbox 360 controller via vgamepad) or "keyboard"

# Physical Xbox Controller Simultaneous Support (Pass-Through)
# When a physical Xbox 360 / One controller is connected:
# Hand Tracking controls Steering (Left Stick X), while the physical controller's
# Triggers (RT/LT for Gas/Brake), Buttons (A/X/Y for Gears), and Right Stick (Look Around)
# pass straight through into ATS!
ENABLE_PHYSICAL_CONTROLLER = True

# Gear Shifting Settings (Drive / Neutral / Reverse)
ENABLE_GEAR_GESTURES = True        # Push right hand forward -> Drive (D); Pull left hand down -> Reverse (R)
KEY_GEAR_DRIVE = "shift"           # ATS default Shift Up (Drive D)
KEY_GEAR_REVERSE = "ctrl"          # ATS default Shift Down (Reverse R)
KEY_GEAR_NEUTRAL = "n"             # ATS default Neutral (N)

# Hand Gesture Pedals (if not using physical controller triggers)
ENABLE_GESTURE_PEDALS = True
KEY_ACCEL = "w"
KEY_BRAKE = "s"

# Visual UI / HUD Settings
SHOW_LANDMARKS = True
SHOW_STEERING_WHEEL_HUD = True
SHOW_METRICS = True
WHEEL_RADIUS = 125
