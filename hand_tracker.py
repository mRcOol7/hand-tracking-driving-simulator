"""Hand tracking and steering angle computation using modern MediaPipe Tasks HandLandmarker."""

import os
import math
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")


class HandTracker:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"MediaPipe model file not found at: {MODEL_PATH}")

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=config.MAX_NUM_HANDS,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_TRACKING_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Internal state
        self.current_steer = 0.0          # Current smoothed steering value: -1.0 (left) to +1.0 (right)
        self.raw_angle = 0.0              # Current raw geometric angle in degrees
        self.calibration_offset = 0.0     # Angle offset set by pressing 'C'
        self.is_two_hands = False         # True when both hands are visible
        self.hands_detected = 0

        # Pedals state
        self.throttle = 0.0               # 0.0 to 1.0
        self.brake = 0.0                  # 0.0 to 1.0

        # Cached positions (pixels)
        self.left_hand_pt = None
        self.right_hand_pt = None
        self.wheel_center_pt = None

    def calibrate_center(self):
        """Set the current raw angle as the new center (0 degrees)."""
        self.calibration_offset = self.raw_angle
        print(f"[HandTracker] Calibrated center offset to: {self.calibration_offset:.2f}°")

    def reset_calibration(self):
        """Reset calibration offset to 0."""
        self.calibration_offset = 0.0
        print("[HandTracker] Calibration reset to 0°")

    def _calculate_pinch_distance(self, landmarks, width, height):
        """Return normalized Euclidean distance between thumb tip and index finger tip."""
        thumb_tip = landmarks[4]   # Landmark 4: THUMB_TIP
        index_tip = landmarks[8]   # Landmark 8: INDEX_FINGER_TIP
        
        dx = (thumb_tip.x - index_tip.x) * width
        dy = (thumb_tip.y - index_tip.y) * height
        dist = math.hypot(dx, dy)
        
        # Normalize roughly by palm size (wrist to middle MCP)
        wrist = landmarks[0]       # Landmark 0: WRIST
        mcp = landmarks[9]         # Landmark 9: MIDDLE_FINGER_MCP
        ref = math.hypot((wrist.x - mcp.x) * width, (wrist.y - mcp.y) * height) + 1e-6
        return dist / ref

    def process_frame(self, frame_bgr):
        """
        Process a video frame, detect hands, calculate steering angle and gestures.
        Returns processed info dict.
        """
        h, w, _ = frame_bgr.shape
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.detector.detect(mp_image)

        target_steer = 0.0
        self.is_two_hands = False
        self.left_hand_pt = None
        self.right_hand_pt = None
        self.wheel_center_pt = None
        target_throttle = 0.0
        target_brake = 0.0

        if results and results.hand_landmarks:
            self.hands_detected = len(results.hand_landmarks)
            hand_positions = []

            for landmarks in results.hand_landmarks:
                # Use landmark 0 (wrist) and landmark 9 (middle MCP) for robust grip position
                wrist = landmarks[0]
                mcp = landmarks[9]
                
                # Center of the hand grip
                cx = int(((wrist.x + mcp.x) / 2.0) * w)
                cy = int(((wrist.y + mcp.y) / 2.0) * h)
                hand_positions.append({
                    "pos": (cx, cy),
                    "landmarks": landmarks
                })

            # Sort hands horizontally on screen (left-to-right)
            hand_positions.sort(key=lambda item: item["pos"][0])

            if len(hand_positions) >= 2:
                self.is_two_hands = True
                left_hand = hand_positions[0]
                right_hand = hand_positions[1]

                self.left_hand_pt = left_hand["pos"]
                self.right_hand_pt = right_hand["pos"]
                self.wheel_center_pt = (
                    (self.left_hand_pt[0] + self.right_hand_pt[0]) // 2,
                    (self.left_hand_pt[1] + self.right_hand_pt[1]) // 2,
                )

                # Calculate angle of vector from left hand to right hand
                dx = self.right_hand_pt[0] - self.left_hand_pt[0]
                dy = self.right_hand_pt[1] - self.left_hand_pt[1]

                # In OpenCV y is downwards:
                # If right hand is lower than left hand (dy > 0), user is steering RIGHT.
                # If right hand is higher than left hand (dy < 0), user is steering LEFT.
                angle_rad = math.atan2(dy, dx)
                self.raw_angle = math.degrees(angle_rad)

                # Apply calibration offset
                effective_angle = self.raw_angle - self.calibration_offset

                # Apply deadzone
                deadzone = config.STEERING_DEADZONE
                max_angle = config.MAX_STEERING_ANGLE

                if abs(effective_angle) <= deadzone:
                    target_steer = 0.0
                else:
                    sign = 1.0 if effective_angle > 0 else -1.0
                    magnitude = (abs(effective_angle) - deadzone) / max(1.0, (max_angle - deadzone))
                    target_steer = sign * min(1.0, magnitude)

                # Gesture pedals check (paddle shifter style pinch)
                if config.ENABLE_GESTURE_PEDALS:
                    # Right hand pinch = Throttle (Gas)
                    right_pinch = self._calculate_pinch_distance(right_hand["landmarks"], w, h)
                    if right_pinch < 0.40:
                        target_throttle = 1.0

                    # Left hand pinch = Brake
                    left_pinch = self._calculate_pinch_distance(left_hand["landmarks"], w, h)
                    if left_pinch < 0.40:
                        target_brake = 1.0

            elif len(hand_positions) == 1:
                # 1 hand detected: keep slight auto-centering
                target_steer = self.current_steer * (1.0 - config.AUTO_CENTER_RATE)
        else:
            self.hands_detected = 0
            # No hands detected: auto-center smoothly
            target_steer = self.current_steer * (1.0 - config.AUTO_CENTER_RATE)
            if abs(target_steer) < 0.01:
                target_steer = 0.0

        # Apply exponential moving average (EMA) smoothing filter
        alpha = config.SMOOTHING_FACTOR
        self.current_steer = alpha * target_steer + (1.0 - alpha) * self.current_steer

        # Smooth pedals
        self.throttle = 0.4 * target_throttle + 0.6 * self.throttle
        self.brake = 0.4 * target_brake + 0.6 * self.brake

        return {
            "steer": float(np.clip(self.current_steer, -1.0, 1.0)),
            "raw_angle": float(self.raw_angle),
            "calibrated_angle": float(self.raw_angle - self.calibration_offset),
            "is_two_hands": self.is_two_hands,
            "hands_detected": self.hands_detected,
            "left_pt": self.left_hand_pt,
            "right_pt": self.right_hand_pt,
            "center_pt": self.wheel_center_pt,
            "throttle": float(self.throttle),
            "brake": float(self.brake),
            "landmarks": results.hand_landmarks if results else None,
        }

    def close(self):
        try:
            self.detector.close()
        except Exception:
            pass
