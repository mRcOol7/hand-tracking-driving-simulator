"""
Advanced Hand Steering Engine for American Truck Simulator.
Features:
- Anatomical Handedness Tracking (Left vs. Right hand anatomy).
- Seamless Cross-Hand (Hand-Over-Hand) Multi-Turn Rotation without direction inversion.
- Progressive S-Curve Anti-Twitch Highway Stability (Calm Center, Powerful Lock).
- Intuitive Hand Gear Shifter (Push forward -> Drive D, Pull back -> Reverse R).
- Single-Hand Reach Steering and Dual-Hand Wheel Tilt.
- 1 Euro Adaptive Low-Pass Filter for Jitter-Free Response.
"""

import os
import time
import math
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")


# ==============================================================================
# 1. One Euro Filter (Adaptive Low-Pass Filter)
# ==============================================================================
def _smoothing_factor(t_e, cutoff):
    r = 2.0 * math.pi * cutoff * t_e
    return r / (r + 1.0)


def _exponential_smoothing(a, x, x_prev):
    return a * x + (1.0 - a) * x_prev


class OneEuroFilter:
    """Adaptive low-pass filter designed for human motion tracking.
    Eliminates jitter at low velocities while minimizing lag at high velocities.
    Reference: Casiez et al., CHI 2012.
    """
    def __init__(self, freq=60.0, mincutoff=0.8, beta=0.015, dcutoff=1.0):
        self.freq = float(freq)
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def filter(self, x, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        if self.t_prev is None:
            t_e = 1.0 / self.freq
        else:
            t_e = max(0.0001, timestamp - self.t_prev)

        # 1. Estimate derivative
        a_d = _smoothing_factor(t_e, self.dcutoff)
        dx = (x - self.x_prev) / t_e if self.x_prev is not None else 0.0
        dx_hat = _exponential_smoothing(a_d, dx, self.dx_prev)

        # 2. Compute dynamic cutoff based on speed
        cutoff = self.mincutoff + self.beta * abs(dx_hat)

        # 3. Filter signal
        a = _smoothing_factor(t_e, cutoff)
        x_hat = _exponential_smoothing(a, x, self.x_prev) if self.x_prev is not None else x

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = timestamp
        return x_hat


# ==============================================================================
# 2. Advanced Steering Engine
# ==============================================================================
class AdvancedSteeringEngine:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"MediaPipe model file not found at: {MODEL_PATH}")

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Adaptive filters
        self.angle_filter = OneEuroFilter(freq=60.0, mincutoff=0.6, beta=0.02)
        self.steer_output_filter = OneEuroFilter(freq=60.0, mincutoff=0.4, beta=0.03)

        # Wheel State
        self.wheel_angle_deg = 0.0
        self.prev_vector_angle_deg = None
        self.calibration_offset = 0.0
        self.hub_center = None

        # Persistent Hand Positions
        self.last_left_pt = None
        self.last_right_pt = None

        # Pedals
        self.throttle = 0.0
        self.brake = 0.0

        # Gear Selector State ('D' = Drive, 'N' = Neutral, 'R' = Reverse)
        self.current_gear = "D"
        self.gear_shift_event = None       # "UP", "DOWN", "NEUTRAL"
        self.last_gear_shift_time = 0.0

        # Hand Depth & Y Tracking for Gear Shifting
        self.prev_r_hand_size = None
        self.prev_l_hand_y = None

        # Vehicle Driving Profile ("truck" or "sport")
        self.active_profile = getattr(config, "ACTIVE_PROFILE", "truck")

    def toggle_profile(self):
        """Toggle between TRUCK (ATS) and SPORT (Mustang GT) profiles."""
        self.active_profile = "sport" if self.active_profile == "truck" else "truck"
        prof_info = config.VEHICLE_PROFILES[self.active_profile]
        print(f"\n[VehicleProfile] Switched to: {prof_info['name']}")
        print(f" -> Max Angle: {prof_info['max_steering_angle']}° | Deadzone: {prof_info['deadzone']}° | S-Curve Exp: {prof_info['s_curve_exponent']}")
        return self.active_profile

    def calibrate_center(self):
        """Set current wheel angle as dead center (0°)."""
        self.calibration_offset = self.wheel_angle_deg
        print(f"[AdvancedEngine] Calibrated Center: offset = {self.calibration_offset:.2f}°")

    def reset_calibration(self):
        """Reset calibration back to zero."""
        self.wheel_angle_deg = 0.0
        self.calibration_offset = 0.0
        self.prev_vector_angle_deg = None
        self.angle_filter.reset()
        self.steer_output_filter.reset()
        print("[AdvancedEngine] Reset Center to 0.0°")

    def _unwrap_delta_deg(self, curr_deg, prev_deg):
        """Computes shortest angular distance (-180° to +180°)."""
        d = curr_deg - prev_deg
        while d > 180.0:
            d -= 360.0
        while d < -180.0:
            d += 360.0
        return d

    def _calculate_pinch(self, landmarks, w, h):
        """Normalized pinch distance between thumb and index."""
        t_tip = landmarks[4]
        i_tip = landmarks[8]
        wrist = landmarks[0]
        mcp = landmarks[9]
        d_pinch = math.hypot((t_tip.x - i_tip.x) * w, (t_tip.y - i_tip.y) * h)
        ref_len = math.hypot((wrist.x - mcp.x) * w, (wrist.y - mcp.y) * h) + 1e-6
        return d_pinch / ref_len

    def process_frame(self, frame_bgr):
        """Processes camera frame and returns complete driving telemetry."""
        h, w, _ = frame_bgr.shape
        now = time.time()

        if self.hub_center is None:
            self.hub_center = (w // 2, int(h * 0.58))

        # MediaPipe Detection
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.detector.detect(mp_image)

        left_hand = None       # (pos, landmarks, hand_size)
        right_hand = None
        raw_landmarks = []
        target_throttle = 0.0
        target_brake = 0.0
        self.gear_shift_event = None

        if results and results.hand_landmarks:
            raw_landmarks = results.hand_landmarks
            num_detected = len(results.hand_landmarks)

            # 1. Identify Left and Right hands using anatomical handedness
            for i, lms in enumerate(results.hand_landmarks):
                wrist = lms[0]
                mcp = lms[9]
                cx = ((wrist.x + mcp.x) / 2.0) * w
                cy = ((wrist.y + mcp.y) / 2.0) * h
                pos = (cx, cy)
                hand_size = math.hypot((mcp.x - wrist.x) * w, (mcp.y - wrist.y) * h)

                category = "Unknown"
                if hasattr(results, "handedness") and i < len(results.handedness):
                    category = results.handedness[i][0].category_name

                # In horizontally flipped frame (FLIP_CAMERA=True):
                # "Right" label corresponds to the driver's Right Hand.
                # "Left" label corresponds to the driver's Left Hand.
                if category == "Right":
                    right_hand = (pos, lms, hand_size)
                elif category == "Left":
                    left_hand = (pos, lms, hand_size)
                else:
                    # Fallback if category ambiguous: assign by horizontal position
                    if cx > self.hub_center[0]:
                        right_hand = (pos, lms, hand_size)
                    else:
                        left_hand = (pos, lms, hand_size)

            # If both were assigned to the same hand due to detection quirk, separate by X
            if num_detected >= 2 and (left_hand is None or right_hand is None):
                p1 = ((results.hand_landmarks[0][0].x + results.hand_landmarks[0][9].x) / 2.0 * w,
                      (results.hand_landmarks[0][0].y + results.hand_landmarks[0][9].y) / 2.0 * h)
                p2 = ((results.hand_landmarks[1][0].x + results.hand_landmarks[1][9].x) / 2.0 * w,
                      (results.hand_landmarks[1][0].y + results.hand_landmarks[1][9].y) / 2.0 * h)
                s1 = math.hypot((results.hand_landmarks[0][9].x - results.hand_landmarks[0][0].x) * w,
                                (results.hand_landmarks[0][9].y - results.hand_landmarks[0][0].y) * h)
                s2 = math.hypot((results.hand_landmarks[1][9].x - results.hand_landmarks[1][0].x) * w,
                                (results.hand_landmarks[1][9].y - results.hand_landmarks[1][0].y) * h)
                if p1[0] < p2[0]:
                    left_hand = (p1, results.hand_landmarks[0], s1)
                    right_hand = (p2, results.hand_landmarks[1], s2)
                else:
                    left_hand = (p2, results.hand_landmarks[1], s2)
                    right_hand = (p1, results.hand_landmarks[0], s1)

            # 2. Gesture Pedals Check (Pinch Gas/Brake)
            if config.ENABLE_GESTURE_PEDALS:
                if right_hand is not None:
                    pinch_r = self._calculate_pinch(right_hand[1], w, h)
                    if pinch_r < 0.38:
                        target_throttle = 1.0
                if left_hand is not None:
                    pinch_l = self._calculate_pinch(left_hand[1], w, h)
                    if pinch_l < 0.38:
                        target_brake = 1.0

            # 3. Gear Shifting Movement Detection
            if config.ENABLE_GEAR_GESTURES and (now - self.last_gear_shift_time > 0.8):
                # A. Shift to DRIVE (D): Push right hand forward toward screen (hand size expands)
                if right_hand is not None and self.prev_r_hand_size is not None:
                    size_growth = (right_hand[2] - self.prev_r_hand_size) / max(1.0, self.prev_r_hand_size)
                    if size_growth > 0.28:
                        self.current_gear = "D"
                        self.gear_shift_event = "UP"
                        self.last_gear_shift_time = now
                        print("[GearShift] Gesture detected -> DRIVE (D)")

                # B. Shift to REVERSE (R): Pull left hand downward rapidly
                if left_hand is not None and self.prev_l_hand_y is not None:
                    y_drop = left_hand[0][1] - self.prev_l_hand_y
                    if y_drop > 45.0:
                        self.current_gear = "R"
                        self.gear_shift_event = "DOWN"
                        self.last_gear_shift_time = now
                        print("[GearShift] Gesture detected -> REVERSE (R)")

            if right_hand:
                self.prev_r_hand_size = right_hand[2]
            if left_hand:
                self.prev_l_hand_y = left_hand[0][1]

        # 4. Continuous Vector Steering Calculation (Handles Crossing Hands!)
        hands_detected = (1 if left_hand else 0) + (1 if right_hand else 0)

        if left_hand and right_hand:
            # Vector from Left Hand to Right Hand
            pt_l = left_hand[0]
            pt_r = right_hand[0]
            self.last_left_pt = pt_l
            self.last_right_pt = pt_r

            dx = pt_r[0] - pt_l[0]
            dy = pt_r[1] - pt_l[1]

            # In screen coordinates, y increases downward.
            # When right hand is lower than left hand (dy > 0), user turns RIGHT.
            # When right hand crosses to the left (dx < 0), angle smoothly continues into 90°..180°!
            raw_vector_deg = math.degrees(math.atan2(dy, dx))

            # Phase-unwrap delta relative to previous frame to prevent 180°/360° flips
            if self.prev_vector_angle_deg is not None:
                d_deg = self._unwrap_delta_deg(raw_vector_deg, self.prev_vector_angle_deg)
                # Apply angular accumulation
                self.wheel_angle_deg += d_deg
            else:
                self.wheel_angle_deg = raw_vector_deg

            self.prev_vector_angle_deg = raw_vector_deg

        elif left_hand or right_hand:
            # Single-Hand Steering Mode (Offset from hub center)
            single_pos = (left_hand or right_hand)[0]
            dx_from_hub = single_pos[0] - self.hub_center[0]
            reach = 160.0
            single_angle = (dx_from_hub / reach) * config.MAX_STEERING_ANGLE
            single_angle = float(np.clip(single_angle, -config.MAX_STEERING_ANGLE, config.MAX_STEERING_ANGLE))
            # Smooth tracking towards single hand angle
            self.wheel_angle_deg = 0.4 * single_angle + 0.6 * self.wheel_angle_deg
            self.prev_vector_angle_deg = None
        else:
            # No hands: self-aligning caster return to center
            self.wheel_angle_deg *= (1.0 - config.AUTO_CENTER_RATE)
            if abs(self.wheel_angle_deg) < 0.2:
                self.wheel_angle_deg = 0.0
            self.prev_vector_angle_deg = None

        # 5. Progressive S-Curve Anti-Twitch Calculation based on Active Vehicle Profile
        prof = config.VEHICLE_PROFILES.get(self.active_profile, config.VEHICLE_PROFILES["truck"])
        prof_max_angle = prof["max_steering_angle"]
        deadzone = prof["deadzone"]
        alpha = prof["linear_coeff"]
        exp = prof["s_curve_exponent"]

        effective_angle = self.wheel_angle_deg - self.calibration_offset
        filtered_angle = self.angle_filter.filter(effective_angle, timestamp=now)

        if abs(filtered_angle) <= deadzone:
            target_steer = 0.0
        else:
            sign = 1.0 if filtered_angle > 0 else -1.0
            usable_range = max(1.0, prof_max_angle - deadzone)
            # Normalized input u in [0.0, 1.0]
            u = min(1.0, (abs(filtered_angle) - deadzone) / usable_range)

            # Progressive S-Curve Formula:
            steer_magnitude = alpha * u + (1.0 - alpha) * (u ** exp)
            target_steer = sign * float(np.clip(steer_magnitude, 0.0, 1.0))

        smoothed_steer = self.steer_output_filter.filter(target_steer, timestamp=now)

        # Smooth pedals
        self.throttle = 0.3 * target_throttle + 0.7 * self.throttle
        self.brake = 0.3 * target_brake + 0.7 * self.brake

        return {
            "steer": float(np.clip(smoothed_steer, -1.0, 1.0)),
            "wheel_angle_deg": float(self.wheel_angle_deg),
            "calibrated_angle": float(filtered_angle),
            "hands_detected": hands_detected,
            "is_two_hands": (hands_detected >= 2),
            "left_pt": self.last_left_pt if left_hand else None,
            "right_pt": self.last_right_pt if right_hand else None,
            "throttle": float(self.throttle),
            "brake": float(self.brake),
            "current_gear": self.current_gear,
            "gear_shift": self.gear_shift_event,
            "active_profile": self.active_profile,
            "landmarks": raw_landmarks,
        }

    def close(self):
        try:
            self.detector.close()
        except Exception:
            pass
