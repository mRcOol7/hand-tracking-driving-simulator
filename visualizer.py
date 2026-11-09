"""Visual HUD, rotating steering wheel graphic, and gauges for ATS Hand Steering."""

import math
import cv2
import numpy as np
import config

# Hand skeleton connections (standard 21 landmarks)
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (5, 9), (9, 10), (10, 11), (11, 12),
    # Ring
    (9, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]


class HUDVisualizer:
    def __init__(self):
        pass

    def draw_hud(self, frame, tracking_data, input_controller, fps=0.0):
        """Render complete HUD onto frame."""
        h, w, _ = frame.shape

        # 1. Draw hand landmarks if enabled
        if config.SHOW_LANDMARKS and tracking_data.get("landmarks"):
            for hand_lms in tracking_data["landmarks"]:
                pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms]
                # Draw skeleton connections
                for p1_idx, p2_idx in HAND_CONNECTIONS:
                    if p1_idx < len(pts) and p2_idx < len(pts):
                        cv2.line(frame, pts[p1_idx], pts[p2_idx], (0, 220, 255), 2, cv2.LINE_AA)
                # Draw landmark nodes
                for i, pt in enumerate(pts):
                    node_color = (0, 0, 255) if i in (4, 8) else (0, 255, 0)
                    cv2.circle(frame, pt, 4, node_color, -1, cv2.LINE_AA)

        # 2. Draw steering line between hands
        left_pt = tracking_data.get("left_pt")
        right_pt = tracking_data.get("right_pt")
        steer = tracking_data.get("steer", 0.0)
        is_two_hands = tracking_data.get("is_two_hands", False)

        if is_two_hands and left_pt and right_pt:
            # Color based on steering
            if abs(steer) < 0.05:
                line_color = (0, 255, 120)       # Clean green (centered)
            elif steer > 0:
                line_color = (255, 200, 0)       # Cyan/Yellow (turning right)
            else:
                line_color = (255, 50, 200)      # Magenta (turning left)

            # Draw thick steering connector line
            cv2.line(frame, left_pt, right_pt, line_color, 4, cv2.LINE_AA)
            cv2.circle(frame, left_pt, 16, (50, 50, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, left_pt, 18, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, right_pt, 16, (50, 50, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, right_pt, 18, (255, 255, 255), 2, cv2.LINE_AA)

        # 3. Draw Virtual Rotating Steering Wheel HUD
        if config.SHOW_STEERING_WHEEL_HUD:
            center_x = w // 2
            center_y = int(h * 0.70)
            self._draw_steering_wheel(frame, center_x, center_y, steer, tracking_data.get("calibrated_angle", 0.0))

        # 4. Draw Linear Gauge at bottom
        self._draw_steering_gauge(frame, w, h, steer)

        # 5. Draw Pedals (Throttle & Brake) if enabled
        if config.ENABLE_GESTURE_PEDALS:
            self._draw_pedals(frame, w, h, tracking_data.get("throttle", 0.0), tracking_data.get("brake", 0.0))

        # 6. Draw Gear Selector HUD & Physical Controller Status
        self._draw_gear_hud(frame, w, h, tracking_data)

        # 7. Draw Info Card (Top-Left)
        self._draw_info_card(frame, tracking_data, input_controller, fps)

        # 8. Draw Hotkeys Guide (Bottom)
        self._draw_hotkeys(frame, w, h)

        return frame

    def _draw_steering_wheel(self, frame, cx, cy, steer, angle_deg):
        """Draw an authentic rotating virtual steering wheel with top red center strip."""
        radius = config.WHEEL_RADIUS

        # Outer rim glow and circle
        cv2.circle(frame, (cx, cy), radius + 2, (40, 40, 40), 10, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), radius, (200, 200, 200), 4, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 28, (60, 60, 60), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 28, (220, 220, 220), 2, cv2.LINE_AA)

        # Center logo / icon
        cv2.circle(frame, (cx, cy), 12, (0, 140, 255), -1, cv2.LINE_AA)

        # 3 Spokes (left, right, bottom) rotated by angle
        for base_deg in [0, 180, 90]:
            rad = math.radians(base_deg + angle_deg)
            spoke_x = int(cx + (radius - 5) * math.cos(rad))
            spoke_y = int(cy + (radius - 5) * math.sin(rad))
            inner_x = int(cx + 28 * math.cos(rad))
            inner_y = int(cy + 28 * math.sin(rad))
            cv2.line(frame, (inner_x, inner_y), (spoke_x, spoke_y), (180, 180, 180), 5, cv2.LINE_AA)

        # Top racing center strip (normally at -90 degrees, i.e. 12 o'clock)
        top_rad = math.radians(-90 + angle_deg)
        top_x = int(cx + radius * math.cos(top_rad))
        top_y = int(cy + radius * math.sin(top_rad))
        cv2.circle(frame, (top_x, top_y), 8, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (top_x, top_y), 8, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_steering_gauge(self, frame, w, h, steer):
        """Draw horizontal bar gauge showing current steer position and deadzone."""
        bar_w = 400
        bar_h = 20
        x1 = (w - bar_w) // 2
        y1 = h - 65
        x2 = x1 + bar_w
        y2 = y1 + bar_h
        center_x = (x1 + x2) // 2

        # Background bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 120, 120), 2)

        # Deadzone markers
        dz_ratio = config.STEERING_DEADZONE / max(1.0, config.MAX_STEERING_ANGLE)
        dz_px = int(dz_ratio * (bar_w // 2))
        cv2.line(frame, (center_x - dz_px, y1 - 3), (center_x - dz_px, y2 + 3), (0, 200, 255), 2)
        cv2.line(frame, (center_x + dz_px, y1 - 3), (center_x + dz_px, y2 + 3), (0, 200, 255), 2)

        # Center line
        cv2.line(frame, (center_x, y1 - 5), (center_x, y2 + 5), (255, 255, 255), 2)

        # Current indicator fill
        target_x = center_x + int(steer * (bar_w // 2))
        fill_color = (0, 255, 120) if abs(steer) < 0.05 else ((255, 200, 0) if steer > 0 else (255, 50, 200))
        cv2.rectangle(frame, (min(center_x, target_x), y1 + 2), (max(center_x, target_x), y2 - 2), fill_color, -1)
        cv2.circle(frame, (target_x, (y1 + y2) // 2), 10, (255, 255, 255), -1)
        cv2.circle(frame, (target_x, (y1 + y2) // 2), 8, fill_color, -1)

    def _draw_pedals(self, frame, w, h, throttle, brake):
        """Draw Brake (left) and Gas (right) indicators."""
        pedal_w = 26
        pedal_h = 100
        y_bottom = h - 65

        # Brake bar (Left side)
        bx1 = 30
        by1 = y_bottom - pedal_h
        cv2.rectangle(frame, (bx1, by1), (bx1 + pedal_w, y_bottom), (30, 30, 30), -1)
        cv2.rectangle(frame, (bx1, by1), (bx1 + pedal_w, y_bottom), (100, 100, 100), 2)
        brake_fill = int(brake * pedal_h)
        if brake_fill > 0:
            cv2.rectangle(frame, (bx1, y_bottom - brake_fill), (bx1 + pedal_w, y_bottom), (0, 0, 255), -1)
        cv2.putText(frame, "BRAKE", (bx1 - 5, by1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)

        # Gas / Throttle bar (Right side)
        gx1 = w - 30 - pedal_w
        gy1 = y_bottom - pedal_h
        cv2.rectangle(frame, (gx1, gy1), (gx1 + pedal_w, y_bottom), (30, 30, 30), -1)
        cv2.rectangle(frame, (gx1, gy1), (gx1 + pedal_w, y_bottom), (100, 100, 100), 2)
        gas_fill = int(throttle * pedal_h)
        if gas_fill > 0:
            cv2.rectangle(frame, (gx1, y_bottom - gas_fill), (gx1 + pedal_w, y_bottom), (0, 255, 0), -1)
        cv2.putText(frame, "GAS", (gx1 + 2, gy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

    def _draw_gear_hud(self, frame, w, h, tracking_data):
        """Draw transmission gear selector [R] [N] [D] in top right."""
        current_gear = tracking_data.get("current_gear", "D")
        gear_shift = tracking_data.get("gear_shift")

        # Top-right gear box
        box_w, box_h = 240, 50
        bx1 = w - box_w - 20
        by1 = 20
        bx2 = bx1 + box_w
        by2 = by1 + box_h

        overlay = frame.copy()
        cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (100, 100, 100), 1)

        # Draw R, N, D slots
        gears = [("R", "REV", (0, 0, 255)), ("N", "NEUT", (0, 220, 255)), ("D", "DRIVE", (0, 255, 120))]
        slot_w = box_w // 3

        for i, (g_code, g_label, g_color) in enumerate(gears):
            sx1 = bx1 + i * slot_w
            sx2 = sx1 + slot_w
            is_active = (current_gear == g_code)

            if is_active:
                cv2.rectangle(frame, (sx1 + 4, by1 + 4), (sx2 - 4, by2 - 4), g_color, -1)
                cv2.putText(frame, g_code, (sx1 + slot_w // 2 - 10, by1 + 33), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
            else:
                cv2.rectangle(frame, (sx1 + 4, by1 + 4), (sx2 - 4, by2 - 4), (40, 40, 40), -1)
                cv2.putText(frame, g_code, (sx1 + slot_w // 2 - 10, by1 + 33), cv2.FONT_HERSHEY_DUPLEX, 0.8, (140, 140, 140), 1, cv2.LINE_AA)

        # Shift alert banner if shift triggered
        if gear_shift == "UP":
            cv2.putText(frame, "SHIFT -> DRIVE [D]", (w // 2 - 120, int(h * 0.40)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 120), 2, cv2.LINE_AA)
        elif gear_shift == "DOWN":
            cv2.putText(frame, "SHIFT -> REVERSE [R]", (w // 2 - 130, int(h * 0.40)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        elif gear_shift == "NEUTRAL":
            cv2.putText(frame, "SHIFT -> NEUTRAL [N]", (w // 2 - 130, int(h * 0.40)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2, cv2.LINE_AA)

    def _draw_info_card(self, frame, tracking_data, input_controller, fps):
        """Draw top-left status card with mode, angle, gear, and physical controller status."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 15), (340, 235), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (15, 15), (340, 235), (80, 80, 80), 1)

        # Title
        cv2.putText(frame, "ATS VIRTUAL STEERING", (28, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)

        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (255, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

        # Mode
        mode_text = f"Mode: {input_controller.mode.upper()}"
        mode_color = (0, 255, 120) if input_controller.mode == "gamepad" else (255, 200, 0)
        cv2.putText(frame, mode_text, (28, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.52, mode_color, 2, cv2.LINE_AA)

        # Physical Xbox Controller merged status
        has_phys = getattr(input_controller, "physical_controller_active", False)
        if has_phys:
            phys_text = "Physical Gamepad: MERGED (Active)"
            phys_color = (0, 255, 200)
        else:
            phys_text = "Physical Gamepad: Standby"
            phys_color = (130, 130, 130)
        cv2.putText(frame, phys_text, (28, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.46, phys_color, 1, cv2.LINE_AA)

        # Status
        if input_controller.is_paused:
            status_text = "PAUSED"
            status_color = (0, 165, 255)
        elif tracking_data.get("is_two_hands"):
            status_text = "STEERING: 2 HANDS ACTIVE"
            status_color = (0, 255, 120)
        elif tracking_data.get("hands_detected") == 1:
            status_text = "STEERING: 1 HAND (RAISE 2 FOR FULL WHEEL)"
            status_color = (0, 200, 255)
        else:
            status_text = "LOOKING FOR HANDS"
            status_color = (0, 0, 255)

        cv2.putText(frame, f"Status: {status_text}", (28, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.46, status_color, 1, cv2.LINE_AA)

        # Angle & Steering output
        cal_angle = tracking_data.get("calibrated_angle", 0.0)
        steer = tracking_data.get("steer", 0.0)
        cv2.putText(frame, f"Angle: {cal_angle:+.1f} deg", (28, 144), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (230, 230, 230), 1, cv2.LINE_AA)

        steer_pct = steer * 100
        direction = "RIGHT" if steer > 0.03 else ("LEFT" if steer < -0.03 else "CENTER")
        cv2.putText(frame, f"Steer: {steer_pct:+.1f}% ({direction})", (28, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

        # Live Gamepad X-Axis Value
        lx_val = int(steer * 32767)
        x_col = (0, 255, 120) if abs(lx_val) > 1000 else (180, 180, 180)
        cv2.putText(frame, f"X-Axis: {lx_val:+6d} / 32767", (28, 196), cv2.FONT_HERSHEY_SIMPLEX, 0.52, x_col, 2, cv2.LINE_AA)

        # Current Gear
        gear = tracking_data.get("current_gear", "D")
        cv2.putText(frame, f"Active Gear: [{gear}]", (28, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 1, cv2.LINE_AA)

    def _draw_hotkeys(self, frame, w, h):
        """Draw bottom hotkey shortcuts bar."""
        bar_text = "[C] Calibrate Center  |  [N] Neutral  |  [M] Mode  |  [P] Pause  |  [O] Mini PiP  |  [Q] Quit"
        cv2.putText(frame, bar_text, (w // 2 - 340, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1, cv2.LINE_AA)
