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
            # Ensure integer coordinates for OpenCV 5.x strict typing
            left_pt = (int(left_pt[0]), int(left_pt[1]))
            right_pt = (int(right_pt[0]), int(right_pt[1]))

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
            active_profile = tracking_data.get("active_profile", getattr(config, "ACTIVE_PROFILE", "truck"))
            self._draw_steering_wheel(frame, center_x, center_y, steer, tracking_data.get("calibrated_angle", 0.0), profile=active_profile)

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

    def _rotate_pt(self, x, y, rad, cx, cy):
        """Rotate local (x, y) around (cx, cy) by angle in radians."""
        rx = x * math.cos(rad) - y * math.sin(rad)
        ry = x * math.sin(rad) + y * math.cos(rad)
        return int(cx + rx), int(cy + ry)

    def _draw_steering_wheel(self, frame, cx, cy, steer, angle_deg, profile="truck"):
        """Draw realistic steering wheel matching the active vehicle profile."""
        if profile == "sport":
            self._draw_sport_wheel(frame, cx, cy, angle_deg)
        else:
            self._draw_truck_wheel(frame, cx, cy, angle_deg)

    def _draw_sport_wheel(self, frame, cx, cy, angle_deg, radius=128):
        """Draw authentic Ford Mustang GT / Supercar flat-bottom racing wheel."""
        rad = math.radians(angle_deg)
        rim_thick = 24
        flat_cutoff_y = int(radius * 0.76)

        pts_outer = []
        pts_inner = []
        for deg in range(0, 360, 4):
            d_rad = math.radians(deg)
            local_x = radius * math.cos(d_rad)
            local_y = radius * math.sin(d_rad)
            if local_y > flat_cutoff_y:
                local_y = flat_cutoff_y

            inner_r = radius - rim_thick
            in_x = inner_r * math.cos(d_rad)
            in_y = inner_r * math.sin(d_rad)
            if in_y > flat_cutoff_y - rim_thick:
                in_y = flat_cutoff_y - rim_thick

            pts_outer.append(self._rotate_pt(local_x, local_y, rad, cx, cy))
            pts_inner.append(self._rotate_pt(in_x, in_y, rad, cx, cy))

        # Drop shadow
        pts_shadow = [(p[0] + 2, p[1] + 6) for p in pts_outer]
        cv2.polylines(frame, [np.array(pts_shadow, np.int32)], True, (12, 12, 12), 10, cv2.LINE_AA)

        # Rim Polygon (Perforated leather dark gray)
        rim_poly = pts_outer + pts_inner[::-1]
        cv2.fillPoly(frame, [np.array(rim_poly, np.int32)], (38, 38, 42), cv2.LINE_AA)
        cv2.polylines(frame, [np.array(pts_outer, np.int32)], True, (65, 65, 70), 2, cv2.LINE_AA)
        cv2.polylines(frame, [np.array(pts_inner, np.int32)], True, (80, 80, 85), 2, cv2.LINE_AA)

        # Ergonomic 10-and-2 Contoured Thumb Rests
        for thumb_ang in [-138, -42]:
            t_rad = math.radians(thumb_ang)
            tx = (radius - rim_thick // 2) * math.cos(t_rad)
            ty = (radius - rim_thick // 2) * math.sin(t_rad)
            pt = self._rotate_pt(tx, ty, rad, cx, cy)
            cv2.circle(frame, pt, 14, (32, 32, 35), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 14, (100, 100, 110), 1, cv2.LINE_AA)

        # Metallic 3-Spoke Assembly with Weight-Reduction Speed Holes
        hub_r = 38
        spoke_angles = [180, 0, 90]
        spoke_w_inner = 24
        spoke_w_outer = 32

        for sang in spoke_angles:
            s_rad = math.radians(sang)
            nx = -math.sin(s_rad)
            ny = math.cos(s_rad)
            dx = math.cos(s_rad)
            dy = math.sin(s_rad)

            r_out = radius - rim_thick
            if sang == 90:
                r_out = flat_cutoff_y - rim_thick

            p1 = self._rotate_pt(hub_r * dx + (spoke_w_inner / 2) * nx, hub_r * dy + (spoke_w_inner / 2) * ny, rad, cx, cy)
            p2 = self._rotate_pt(hub_r * dx - (spoke_w_inner / 2) * nx, hub_r * dy - (spoke_w_inner / 2) * ny, rad, cx, cy)
            p3 = self._rotate_pt(r_out * dx - (spoke_w_outer / 2) * nx, r_out * dy - (spoke_w_outer / 2) * ny, rad, cx, cy)
            p4 = self._rotate_pt(r_out * dx + (spoke_w_outer / 2) * nx, r_out * dy + (spoke_w_outer / 2) * ny, rad, cx, cy)

            spoke_poly = np.array([p1, p2, p3, p4], np.int32)
            cv2.fillPoly(frame, [spoke_poly], (65, 65, 72), cv2.LINE_AA)
            cv2.polylines(frame, [spoke_poly], True, (160, 160, 175), 2, cv2.LINE_AA)

            mid_r = (hub_r + r_out) / 2.0
            hole_pt = self._rotate_pt(mid_r * dx, mid_r * dy, rad, cx, cy)
            cv2.circle(frame, hole_pt, 7, (20, 20, 22), -1, cv2.LINE_AA)
            cv2.circle(frame, hole_pt, 7, (120, 120, 130), 1, cv2.LINE_AA)

        # Center Hub & Hex Fasteners
        cv2.circle(frame, (cx, cy), hub_r + 3, (25, 25, 28), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), hub_r, (85, 85, 95), 3, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), hub_r - 4, (40, 40, 45), -1, cv2.LINE_AA)

        for b_deg in range(0, 360, 60):
            b_rad = math.radians(b_deg)
            bx = (hub_r - 9) * math.cos(b_rad)
            by = (hub_r - 9) * math.sin(b_rad)
            b_pt = self._rotate_pt(bx, by, rad, cx, cy)
            cv2.circle(frame, b_pt, 3, (190, 190, 200), -1, cv2.LINE_AA)
            cv2.circle(frame, b_pt, 1, (40, 40, 40), -1, cv2.LINE_AA)

        # Mustang GT Center Horn Button Emblem
        emblem_r = 18
        cv2.circle(frame, (cx, cy), emblem_r, (20, 20, 22), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), emblem_r, (0, 180, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "GT", (cx - 10, cy + 5), cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

        # Top 12 O'Clock Racing Alignment Stripe (Mustang Race Red + White Pinstripe)
        for offset_ang, width, color in [(-90, 8, (255, 255, 255)), (-90, 5, (30, 30, 230))]:
            t_rad = math.radians(offset_ang)
            p_top_out = self._rotate_pt(radius * math.cos(t_rad), radius * math.sin(t_rad), rad, cx, cy)
            p_top_in = self._rotate_pt((radius - rim_thick) * math.cos(t_rad), (radius - rim_thick) * math.sin(t_rad), rad, cx, cy)
            cv2.line(frame, p_top_out, p_top_in, color, width, cv2.LINE_AA)

    def _draw_truck_wheel(self, frame, cx, cy, angle_deg, radius=130):
        """Draw heavy commercial semi-truck steering wheel (Peterbilt / Kenworth style)."""
        rad = math.radians(angle_deg)
        rim_thick = 22

        # Drop shadow
        cv2.circle(frame, (cx + 2, cy + 6), radius, (15, 15, 18), 12, cv2.LINE_AA)

        # Outer Rim - Deep commercial charcoal / woodgrain
        cv2.circle(frame, (cx, cy), radius, (50, 45, 40), rim_thick, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), radius + rim_thick // 2, (75, 70, 65), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), radius - rim_thick // 2, (90, 85, 80), 2, cv2.LINE_AA)

        # 4 Heavy-duty Commercial Spokes (Cruiser layout: 35°, 145°, 215°, 325°)
        hub_r = 40
        spoke_angles = [35, 145, 215, 325]
        for sang in spoke_angles:
            s_rad = math.radians(sang)
            dx = math.cos(s_rad)
            dy = math.sin(s_rad)
            p_in = self._rotate_pt(hub_r * dx, hub_r * dy, rad, cx, cy)
            p_out = self._rotate_pt((radius - rim_thick // 2) * dx, (radius - rim_thick // 2) * dy, rad, cx, cy)
            cv2.line(frame, p_in, p_out, (180, 180, 190), 8, cv2.LINE_AA)
            cv2.line(frame, p_in, p_out, (230, 230, 240), 3, cv2.LINE_AA)

        # Chrome Center Hub with Commercial Truck Horn Cap
        cv2.circle(frame, (cx, cy), hub_r, (160, 160, 170), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), hub_r, (240, 240, 250), 3, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), hub_r - 8, (35, 35, 40), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), hub_r - 8, (190, 190, 200), 2, cv2.LINE_AA)

        # ATS Commercial Eagle / Truck Star in center
        cv2.circle(frame, (cx, cy), 14, (0, 180, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 14, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "ATS", (cx - 13, cy + 4), cv2.FONT_HERSHEY_DUPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

        # 12 o'clock center bead
        top_pt = self._rotate_pt(0, -radius, rad, cx, cy)
        cv2.circle(frame, top_pt, 7, (0, 200, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, top_pt, 7, (255, 255, 255), 1, cv2.LINE_AA)

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
        """Draw top-left status card with mode, profile, device type, angle, gear, and physical controller status."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 15), (360, 275), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (15, 15), (360, 275), (80, 80, 80), 1)

        # Title
        cv2.putText(frame, "HAND STEERING WHEEL", (28, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)

        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (275, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

        # Active Vehicle Profile (Truck vs Mustang Sport)
        active_prof = tracking_data.get("active_profile", getattr(config, "ACTIVE_PROFILE", "truck"))
        prof_info = config.VEHICLE_PROFILES.get(active_prof, config.VEHICLE_PROFILES["truck"])
        prof_color = (0, 255, 120) if active_prof == "sport" else (0, 220, 255)
        cv2.putText(frame, f"[V] Profile: {prof_info['short_name']}", (28, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.50, prof_color, 2, cv2.LINE_AA)

        # Gamepad Emulation Type (DualShock 4 vs Xbox 360)
        pad_type = getattr(input_controller, "pad_type", "ds4").upper()
        if pad_type == "DS4":
            emu_label = "DS4 (Wireless Controller)"
            emu_col = (0, 255, 200)
        else:
            emu_label = "Xbox 360 Controller"
            emu_col = (0, 200, 255)
        cv2.putText(frame, f"[G] Device: {emu_label}", (28, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.46, emu_col, 1, cv2.LINE_AA)

        # Physical Xbox Controller merged status
        has_phys = getattr(input_controller, "physical_controller_active", False)
        if has_phys:
            phys_text = "Physical Gamepad: MERGED (Active)"
            phys_color = (0, 255, 200)
        else:
            phys_text = "Physical Gamepad: Standby"
            phys_color = (130, 130, 130)
        cv2.putText(frame, phys_text, (28, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.46, phys_color, 1, cv2.LINE_AA)

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
            status_text = "LOOKING FOR HANDS (Raise hands to wheel)"
            status_color = (80, 120, 255)

        cv2.putText(frame, f"Status: {status_text}", (28, 138), cv2.FONT_HERSHEY_SIMPLEX, 0.46, status_color, 1, cv2.LINE_AA)

        # Angle & Steering output
        cal_angle = tracking_data.get("calibrated_angle", 0.0)
        steer = tracking_data.get("steer", 0.0)
        cv2.putText(frame, f"Angle: {cal_angle:+.1f} deg", (28, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (230, 230, 230), 1, cv2.LINE_AA)

        steer_pct = steer * 100
        direction = "RIGHT" if steer > 0.03 else ("LEFT" if steer < -0.03 else "CENTER")
        cv2.putText(frame, f"Steer: {steer_pct:+.1f}% ({direction})", (28, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

        # Live Gamepad X-Axis Value
        lx_val = int(steer * 32767)
        x_col = (0, 255, 120) if abs(lx_val) > 1000 else (180, 180, 180)
        cv2.putText(frame, f"X-Axis: {lx_val:+6d} / 32767", (28, 216), cv2.FONT_HERSHEY_SIMPLEX, 0.52, x_col, 2, cv2.LINE_AA)

        # Current Gear
        gear = tracking_data.get("current_gear", "D")
        cv2.putText(frame, f"Active Gear: [{gear}]", (28, 242), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 1, cv2.LINE_AA)

    def _draw_hotkeys(self, frame, w, h):
        """Draw bottom hotkey shortcuts bar."""
        bar_text = "[V] Vehicle (Truck/Sport) | [G] Device (DS4/Xbox) | [C] Calibrate | [N] Neutral | [P] Pause | [Q] Quit"
        cv2.putText(frame, bar_text, (w // 2 - 390, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 200, 200), 1, cv2.LINE_AA)
