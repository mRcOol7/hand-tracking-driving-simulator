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

# Input Modes
DEFAULT_INPUT_MODE = "gamepad"     # "gamepad" (via vgamepad) or "keyboard"

# Virtual Gamepad Emulation Type:
# "ds4"     : Emulates Sony DualShock 4 ("Wireless Controller" in Windows joy.cpl & games).
#             *** RECOMMENDED when using alongside a physical Xbox Controller ***
#             Because Windows names the physical controller "Controller (XBOX 360)" and
#             the hand steering "Wireless Controller", they have COMPLETELY DISTINCT NAMES!
#             Games like ATS, Forza, Assetto Corsa will never confuse them!
# "xbox360" : Emulates Microsoft Xbox 360 ("Controller (XBOX 360 For Windows)").
VIRTUAL_GAMEPAD_TYPE = "ds4"

# Vehicle Driving Dynamics Profiles:
# "truck" : American Truck Simulator / Euro Truck Simulator 2 (Heavy Hauler)
#           70.0° angle, 3.5° deadzone, 2.4 S-curve exponent, rock-steady highway cruising.
# "sport" : Fast sports cars (Ford Mustang GT, Ferrari, Supercars, Forza, Assetto Corsa)
#           38.0° fast 14:1 steering rack, 1.8° tight deadzone, 1.6 S-curve exponent for crisp turn-in & drift.
# Switchable instantly on the fly anytime by pressing key [V]!
ACTIVE_PROFILE = "truck"

VEHICLE_PROFILES = {
    "truck": {
        "name": "TRUCK (Heavy Hauler - ATS / ETS2)",
        "short_name": "TRUCK",
        "max_steering_angle": 70.0,
        "deadzone": 3.5,
        "s_curve_exponent": 2.4,
        "linear_coeff": 0.20,
        "wheel_type": "truck",
        "wheel_radius": 130,
    },
    "sport": {
        "name": "SPORT (Mustang GT / Fast Supercars)",
        "short_name": "SPORT (MUSTANG)",
        "max_steering_angle": 38.0,
        "deadzone": 1.8,
        "s_curve_exponent": 1.6,
        "linear_coeff": 0.40,
        "wheel_type": "sport_mustang",
        "wheel_radius": 128,
    }
}

# Progressive Steering Response Curve (Anti-Twitch Formula: alpha*u + (1-alpha)*u^exponent)
MAX_STEERING_ANGLE = VEHICLE_PROFILES["truck"]["max_steering_angle"]
STEERING_DEADZONE = VEHICLE_PROFILES["truck"]["deadzone"]
STEERING_S_CURVE_EXPONENT = VEHICLE_PROFILES["truck"]["s_curve_exponent"]
STEERING_LINEAR_COEFF = VEHICLE_PROFILES["truck"]["linear_coeff"]
SMOOTHING_FACTOR = 0.25            # Smoothing factor (One Euro filter frequency tuning)
AUTO_CENTER_RATE = 0.15            # Caster self-centering speed when hands release wheel

# Physical Xbox Controller Simultaneous Support (Pass-Through)
# When a physical Xbox 360 / One controller is connected:
# Hand Tracking controls Steering (Left Stick X), while the physical controller's
# Triggers (RT/LT for Gas/Brake), Buttons (A/X/Y for Gears), and Right Stick (Look Around)
# pass straight through into games!
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
