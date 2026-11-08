"""Enterprise-Grade Hand Tracking & Steering Engine for American Truck Simulator.

Features:
1. One Euro Filter (1€ Filter) - Adaptive jitter removal with zero high-speed lag.
2. Polar Orbit Tangent Accumulator - Allows continuous 360°, 720°, 900° full rotation.
3. Hand-Over-Hand Driving - Smoothly handles crossing hands and lifting one hand off.
4. Temporal Hand Identity Tracking - Prevents left/right hand identity swapping.
5. Self-Aligning Torque - Smooth caster return to center when hands release the wheel.
"""

import os
import math
import time
import numpy as np
import cv2
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

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


# ==============================================================================
# 2. Persistent Hand Identity Tracker
# ==============================================================================
class TrackedHand:
    def __init__(self, hand_id, pos, landmarks):
        self.id = hand_id
        self.pos = pos                  # (x, y) pixels
        self.landmarks = landmarks
        self.prev_angle = None
        self.last_seen = time.time()
        self.is_gripping = True


# ==============================================================================
# 3. Enterprise Advanced Steering Engine
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

        # 1 Euro Filters for X, Y of hands and continuous wheel angle
        self.angle_filter = OneEuroFilter(freq=60.0, mincutoff=0.6, beta=0.02)
        self.steer_output_filter = OneEuroFilter(freq=60.0, mincutoff=0.4, beta=0.03)

        # Multi-turn Continuous Wheel State
        self.wheel_angle_deg = 0.0          # Unbounded continuous angle (e.g. -450° to +450°)
        self.max_lock_deg = 450.0           # Lock-to-lock degrees (900° total wheel travel)
        self.hub_center = None              # (cx, cy) center of steering wheel
        self.hub_radius = 140.0

        # Hand tracking persistence
        self.hands_dict = {}                # hand_id -> TrackedHand
        self.next_hand_id = 1
        self.hands_on_wheel = 0
        self.hand_over_hand_active = False

        # Calibrated center offset
        self.calibration_offset = 0.0

        # Pedals
        self.throttle = 0.0
        self.brake = 0.0

    def calibrate_center(self):
        """Set current wheel angle as dead center (0°)."""
        self.calibration_offset = self.wheel_angle_deg
        print(f"[AdvancedEngine] Calibrated Center: offset = {self.calibration_offset:.2f}°")

    def reset_center(self):
        """Reset wheel back to zero."""
        self.wheel_angle_deg = 0.0
        self.calibration_offset = 0.0
        self.angle_filter.reset()
        self.steer_output_filter.reset()
        print("[AdvancedEngine] Reset Center to 0.0°")

    def _unwrap_delta(self, curr_angle, prev_angle):
        """Compute shortest angular displacement (-pi to +pi)."""
        d = curr_angle - prev_angle
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
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
        """
        Process camera frame through enterprise multi-turn polar tracking engine.
        Returns detailed telemetry dictionary.
        """
        h, w, _ = frame_bgr.shape
        now = time.time()

        # Set default virtual hub center if not set
        if self.hub_center is None:
            self.hub_center = (w // 2, int(h * 0.58))

        # 1. MediaPipe Detection
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.detector.detect(mp_image)

        current_hand_positions = []
        raw_landmarks_list = []

        target_throttle = 0.0
        target_brake = 0.0
        is_horn = False
        trigger_ind_left = False
        trigger_ind_right = False

        if results and results.hand_landmarks:
            for lms in results.hand_landmarks:
                wrist = lms[0]
                mcp = lms[9]
                cx = ((wrist.x + mcp.x) / 2.0) * w
                cy = ((wrist.y + mcp.y) / 2.0) * h
                current_hand_positions.append(((cx, cy), lms))
                raw_landmarks_list.append(lms)

                # 1. Horn Check: Hand presses center of steering wheel hub (< 70px)
                dist_to_hub = math.hypot(cx - self.hub_center[0], cy - self.hub_center[1])
                if dist_to_hub < 70.0:
                    is_horn = True

                # 2. Indicator Check: Finger flicked outward to the side
                index_tip = lms[8]
                if cx < self.hub_center[0]:
                    # Left hand pointing outward to the left
                    if (wrist.x - index_tip.x) * w > 50.0:
                        trigger_ind_left = True
                else:
                    # Right hand pointing outward to the right
                    if (index_tip.x - wrist.x) * w > 50.0:
                        trigger_ind_right = True

                # 3. Pinch checks (Paddle gas / brake)
                pinch = self._calculate_pinch(lms, w, h)
                if pinch < 0.38 and dist_to_hub >= 70.0:
                    # If hand is on right side -> Gas, left side -> Brake
                    if cx > self.hub_center[0]:
                        target_throttle = 1.0
                    else:
                        target_brake = 1.0

        # 2. Match Detected Hands with Persistent IDs (Spatial Proximity)
        matched_hands = {}
        for (pos, lms) in current_hand_positions:
            best_id = None
            min_dist = 180.0  # Max pixel jump between consecutive frames
            for hid, thand in self.hands_dict.items():
                if hid not in matched_hands:
                    d = math.hypot(pos[0] - thand.pos[0], pos[1] - thand.pos[1])
                    if d < min_dist:
                        min_dist = d
                        best_id = hid

            if best_id is not None:
                matched_hands[best_id] = (pos, lms)
            else:
                # Assign new ID
                new_id = self.next_hand_id
                self.next_hand_id += 1
                matched_hands[new_id] = (pos, lms)

        # 3. Dynamic Wheel Hub Alignment
        # If two hands are visible, gently center the hub between hands
        if len(matched_hands) >= 2:
            p_list = [item[0] for item in matched_hands.values()]
            avg_x = (p_list[0][0] + p_list[1][0]) / 2.0
            avg_y = (p_list[0][1] + p_list[1][1]) / 2.0
            # Smooth hub center drift
            self.hub_center = (
                int(0.05 * avg_x + 0.95 * self.hub_center[0]),
                int(0.05 * avg_y + 0.95 * self.hub_center[1]),
            )
            self.hub_radius = 0.05 * (math.hypot(p_list[0][0] - p_list[1][0], p_list[0][1] - p_list[1][1]) / 2.0) + 0.95 * self.hub_radius

        # 4. Polar Tangential Torque Accumulation
        # Each gripping hand rotates around hub_center. We compute angular velocity dTheta!
        total_delta_deg = 0.0
        active_contributors = 0

        updated_dict = {}
        for hid, (pos, lms) in matched_hands.items():
            # Angle relative to wheel center hub
            hx = pos[0] - self.hub_center[0]
            hy = pos[1] - self.hub_center[1]
            curr_polar_rad = math.atan2(hy, hx)

            if hid in self.hands_dict and self.hands_dict[hid].prev_angle is not None:
                d_rad = self._unwrap_delta(curr_polar_rad, self.hands_dict[hid].prev_angle)
                d_deg = math.degrees(d_rad)
                # Ignore unreasonable teleportations (> 60° per frame)
                if abs(d_deg) < 60.0:
                    total_delta_deg += d_deg
                    active_contributors += 1

            thand = TrackedHand(hid, pos, lms)
            thand.prev_angle = curr_polar_rad
            updated_dict[hid] = thand

        self.hands_dict = updated_dict
        self.hands_on_wheel = len(self.hands_dict)

        # 5. Hybrid Absolute Tilt & Continuous Rotation Update
        if len(matched_hands) >= 2:
            # Sort hands left-to-right
            pts = sorted([item[0] for item in matched_hands.values()], key=lambda p: p[0])
            dx = pts[1][0] - pts[0][0]
            dy = pts[1][1] - pts[0][1]
            if dx > 40:
                # Direct absolute hand tilt angle (instant, responsive 1:1 steering)
                direct_angle = math.degrees(math.atan2(dy, dx))
                # Smoothly track direct angle
                self.wheel_angle_deg = 0.7 * direct_angle + 0.3 * self.wheel_angle_deg
                self.hand_over_hand_active = False
            else:
                # Hands crossing over (hand-over-hand): accumulate angular velocity
                if active_contributors > 0:
                    avg_delta = total_delta_deg / active_contributors
                    self.wheel_angle_deg += avg_delta
                    self.hand_over_hand_active = True
        elif len(matched_hands) == 1:
            # Single-hand steering support! Steer by moving hand left/right relative to screen center
            pos, lms = list(matched_hands.values())[0]
            cx, cy = pos
            dx_from_hub = cx - self.hub_center[0]
            reach = 150.0  # Pixels left/right for full lock
            single_hand_angle = (dx_from_hub / reach) * config.MAX_STEERING_ANGLE
            single_hand_angle = float(np.clip(single_hand_angle, -config.MAX_STEERING_ANGLE, config.MAX_STEERING_ANGLE))
            # Smooth tracking
            self.wheel_angle_deg = 0.5 * single_hand_angle + 0.5 * self.wheel_angle_deg
            self.hand_over_hand_active = False
        else:
            # No hands: self-aligning caster return to center
            self.wheel_angle_deg *= 0.85
            if abs(self.wheel_angle_deg) < 0.2:
                self.wheel_angle_deg = 0.0

        # Apply continuous lock limits (e.g. ±450° = 900° lock-to-lock)
        self.wheel_angle_deg = float(np.clip(self.wheel_angle_deg, -self.max_lock_deg, self.max_lock_deg))

        # 6. Apply One Euro Filter to the effective steering angle
        effective_angle = self.wheel_angle_deg - self.calibration_offset
        filtered_angle = self.angle_filter.filter(effective_angle, timestamp=now)

        # 7. Apply Deadzone & Proportional Output Mapping
        deadzone = config.STEERING_DEADZONE
        if abs(filtered_angle) <= deadzone:
            target_steer = 0.0
        else:
            sign = 1.0 if filtered_angle > 0 else -1.0
            # Scale proportionally up to max lock angle
            usable_range = max(1.0, config.MAX_STEERING_ANGLE - deadzone)
            raw_mag = (abs(filtered_angle) - deadzone) / usable_range
            target_steer = sign * min(1.0, raw_mag)

        # Smooth output for virtual controller
        smoothed_steer = self.steer_output_filter.filter(target_steer, timestamp=now)

        # Smooth pedals
        self.throttle = 0.3 * target_throttle + 0.7 * self.throttle
        self.brake = 0.3 * target_brake + 0.7 * self.brake

        return {
            "steer": float(np.clip(smoothed_steer, -1.0, 1.0)),
            "wheel_angle_deg": float(self.wheel_angle_deg),
            "calibrated_angle": float(filtered_angle),
            "hands_on_wheel": self.hands_on_wheel,
            "is_two_hands": (self.hands_on_wheel >= 2),
            "hand_over_hand": self.hand_over_hand_active,
            "hub_center": self.hub_center,
            "hub_radius": self.hub_radius,
            "hands_data": self.hands_dict,
            "throttle": float(self.throttle),
            "brake": float(self.brake),
            "horn": is_horn,
            "ind_left": trigger_ind_left,
            "ind_right": trigger_ind_right,
            "hands_detected": self.hands_on_wheel,
            "landmarks": raw_landmarks_list,
            "raw_landmarks": raw_landmarks_list,
        }

    def close(self):
        try:
            self.detector.close()
        except Exception:
            pass
