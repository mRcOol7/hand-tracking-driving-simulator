"""Interactive American Truck Simulator Highway Demo.
Test your hand-tracking steering wheel with real physics, curving roads, and truck cockpit view!
"""

import sys
import time
import math
import cv2
import numpy as np
import config
from advanced_tracker import AdvancedSteeringEngine
from hand_tracker import HandTracker
from visualizer import HUDVisualizer


class TruckSimulatorDemo:
    def __init__(self, width=1280, height=720):
        self.w = width
        self.h = height

        # Truck Physics & State
        self.truck_x = 0.0              # -1.0 (far left shoulder) to +1.0 (far right shoulder)
        self.speed_mph = 0.0            # 0 to 75 MPH
        self.target_speed = 0.0
        self.engine_rpm = 700.0
        self.current_gear = 1
        self.odometer_miles = 0.0

        # Road Environment
        self.road_pos = 0.0
        self.road_curve = 0.0           # -1.0 to 1.0 (highway curvature)
        self.target_curve = 0.0
        self.curve_timer = 0.0

        # Horn & Turn Signals
        self.horn_active = False
        self.ind_left = False
        self.ind_right = False
        self.blinker_timer = 0.0
        self.blinker_on = False

    def update(self, steer_input, throttle_input, brake_input, dt, horn=False, ind_left_trig=False, ind_right_trig=False):
        """Update physics, road dynamics, horn, and indicators."""
        self.horn_active = horn

        # Toggle turn indicators on trigger
        if ind_left_trig:
            self.ind_left = not self.ind_left
            if self.ind_left:
                self.ind_right = False
        if ind_right_trig:
            self.ind_right = not self.ind_right
            if self.ind_right:
                self.ind_left = False

        # Blinker flash timer (flash every 0.35s)
        self.blinker_timer += dt
        if self.blinker_timer > 0.35:
            self.blinker_timer = 0.0
            self.blinker_on = not self.blinker_on
        # 1. Throttle and Braking
        if throttle_input > 0.1:
            max_accel = 22.0  # MPH per second
            self.speed_mph += throttle_input * max_accel * dt
        elif brake_input > 0.1:
            max_decel = 45.0  # MPH per second
            self.speed_mph -= brake_input * max_decel * dt
        else:
            # Natural coasting / air resistance
            self.speed_mph -= 4.0 * dt

        self.speed_mph = float(np.clip(self.speed_mph, 0.0, 75.0))

        # 2. Transmission & RPM Simulation (12-speed diesel)
        if self.speed_mph > 0.1:
            gear_ratio = max(1, min(12, int(self.speed_mph / 6.0) + 1))
            self.current_gear = gear_ratio
            base_rpm = 800 + (self.speed_mph % 6.0) * 200
            self.engine_rpm = min(2100, base_rpm + (throttle_input * 300))
        else:
            self.current_gear = 1
            self.engine_rpm = 700 + (throttle_input * 400)

        # 3. Steering & Lane Movement
        # Lateral movement is proportional to speed and steering input
        speed_factor = min(1.0, self.speed_mph / 25.0)
        self.truck_x += (steer_input * 1.6 - self.road_curve * 0.8) * speed_factor * dt
        self.truck_x = float(np.clip(self.truck_x, -1.2, 1.2))

        # 4. Road Scroll and Curvature Generator
        self.road_pos += (self.speed_mph * 1.46667) * dt * 2.0  # Scroll rate
        self.odometer_miles += (self.speed_mph / 3600.0) * dt

        # Random gentle highway curves every 6 seconds
        self.curve_timer += dt
        if self.curve_timer > 5.0:
            self.curve_timer = 0.0
            self.target_curve = np.random.uniform(-0.5, 0.5)

        self.road_curve += (self.target_curve - self.road_curve) * 0.5 * dt

    def render(self, frame_camera, tracking_data):
        """Draw complete 3D Highway simulation scene."""
        scene = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        horizon_y = int(self.h * 0.42)

        # 1. Sky & Arizona Desert Mountains
        cv2.rectangle(scene, (0, 0), (self.w, horizon_y), (230, 160, 100), -1)  # Warm sky
        # Distant mountain silhouettes
        for i in range(5):
            mx = int(self.w * 0.25 * i - (self.truck_x * 50))
            pts = np.array([[mx, horizon_y], [mx + 160, horizon_y - 70], [mx + 320, horizon_y]], np.int32)
            cv2.fillPoly(scene, [pts], (140, 90, 70))

        # 2. Ground / Desert Sand
        cv2.rectangle(scene, (0, horizon_y), (self.w, self.h), (70, 120, 160), -1)

        # 3. 3D Perspective Road
        cam_offset_x = int(self.truck_x * (self.w * 0.40))
        curve_offset_x = int(self.road_curve * 220)

        road_top_w = 90
        road_bot_w = 950
        road_center_top = (self.w // 2) + curve_offset_x - int(cam_offset_x * 0.1)
        road_center_bot = (self.w // 2) - cam_offset_x

        # Road Asphalt polygon
        p1 = (road_center_top - road_top_w // 2, horizon_y)
        p2 = (road_center_top + road_top_w // 2, horizon_y)
        p3 = (road_center_bot + road_bot_w // 2, self.h)
        p4 = (road_center_bot - road_bot_w // 2, self.h)
        road_poly = np.array([p1, p2, p3, p4], np.int32)
        cv2.fillPoly(scene, [road_poly], (50, 50, 50))

        # White Side Lines
        cv2.line(scene, p1, p4, (240, 240, 240), 5, cv2.LINE_AA)
        cv2.line(scene, p2, p3, (240, 240, 240), 5, cv2.LINE_AA)

        # Dashed Yellow Center Line
        num_segments = 14
        for seg in range(num_segments):
            t1 = (seg + (self.road_pos % 10) / 10.0) / float(num_segments)
            t2 = t1 + 0.04
            if t1 > 1.0 or t2 > 1.0:
                continue

            y_start = int(horizon_y + (self.h - horizon_y) * (t1 ** 2))
            y_end = int(horizon_y + (self.h - horizon_y) * (t2 ** 2))
            x_start = int(road_center_top + (road_center_bot - road_center_top) * t1)
            x_end = int(road_center_top + (road_center_bot - road_center_top) * t2)

            line_w = max(2, int(10 * t1))
            cv2.line(scene, (x_start, y_start), (x_end, y_end), (0, 215, 255), line_w, cv2.LINE_AA)

        # 4. Truck Windshield Frame & Cabin Dashboard (First-Person View)
        self._draw_truck_interior(scene, tracking_data.get("calibrated_angle", 0.0))

        # 5. Dashboard Gauges HUD
        self._draw_dashboard_gauges(scene)

        # 6. Picture-In-Picture Webcam Feed (Top Right)
        if frame_camera is not None:
            pip_w = 300
            pip_h = 170
            pip_thumb = cv2.resize(frame_camera, (pip_w, pip_h))
            # Border
            cv2.rectangle(scene, (self.w - pip_w - 22, 18), (self.w - 18, 18 + pip_h + 4), (0, 200, 255), 2)
            scene[20:20 + pip_h, self.w - pip_w - 20:self.w - 20] = pip_thumb
            cv2.putText(scene, "HAND TRACKING FEED", (self.w - pip_w - 15, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # 7. Hotkey Guides
        bar_text = "[W/Gas Pinch] Accel   |   [S/Brake Pinch] Brake   |   [C] Calibrate 0 deg   |   [R] Reset Lane   |   [Q] Quit"
        cv2.putText(scene, bar_text, (self.w // 2 - 390, self.h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1, cv2.LINE_AA)

        return scene

    def _draw_truck_interior(self, scene, angle_deg):
        """Draw realistic truck cab interior and rotating steering wheel."""
        cab_top_y = int(self.h * 0.62)
        # Dashboard base
        cv2.rectangle(scene, (0, cab_top_y), (self.w, self.h), (30, 30, 32), -1)
        cv2.line(scene, (0, cab_top_y), (self.w, cab_top_y), (60, 60, 65), 3)

        # Windshield A-Pillars (Left and Right cab frame)
        pillar_l = np.array([[0, 0], [90, 0], [130, cab_top_y], [0, cab_top_y]], np.int32)
        pillar_r = np.array([[self.w - 90, 0], [self.w, 0], [self.w, cab_top_y], [self.w - 130, cab_top_y]], np.int32)
        cv2.fillPoly(scene, [pillar_l], (45, 45, 48))
        cv2.fillPoly(scene, [pillar_r], (45, 45, 48))

        # Truck Steering Wheel (Centered in driver's view: around x=420, y=560)
        wc_x = int(self.w * 0.36)
        wc_y = int(self.h * 0.76)
        radius = 135

        # Steering wheel rim
        cv2.circle(scene, (wc_x, wc_y), radius, (20, 20, 20), 18, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), radius, (70, 70, 75), 4, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), 36, (40, 40, 42), -1, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), 36, (120, 120, 120), 2, cv2.LINE_AA)

        # Spokes
        for base_deg in [0, 180, 90]:
            rad = math.radians(base_deg + angle_deg)
            sx = int(wc_x + (radius - 8) * math.cos(rad))
            sy = int(wc_y + (radius - 8) * math.sin(rad))
            ix = int(wc_x + 36 * math.cos(rad))
            iy = int(wc_y + 36 * math.sin(rad))
            cv2.line(scene, (ix, iy), (sx, sy), (60, 60, 65), 10, cv2.LINE_AA)
            cv2.line(scene, (ix, iy), (sx, sy), (180, 180, 180), 2, cv2.LINE_AA)

        # Red Center Stripe at 12 o'clock
        top_rad = math.radians(-90 + angle_deg)
        tx = int(wc_x + radius * math.cos(top_rad))
        ty = int(wc_y + radius * math.sin(top_rad))
        cv2.circle(scene, (tx, ty), 10, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(scene, (tx, ty), 10, (255, 255, 255), 2, cv2.LINE_AA)

    def _draw_dashboard_gauges(self, scene):
        """Draw digital speed, gear, RPM, and lane guidance."""
        dash_x = int(self.w * 0.58)
        dash_y = int(self.h * 0.67)

        # Cluster Box
        cv2.rectangle(scene, (dash_x, dash_y), (dash_x + 400, dash_y + 160), (15, 18, 22), -1)
        cv2.rectangle(scene, (dash_x, dash_y), (dash_x + 400, dash_y + 160), (0, 200, 255), 2)

        # Turn Signal Indicators on Dashboard
        left_color = (0, 255, 0) if (self.ind_left and self.blinker_on) else (30, 60, 30)
        right_color = (0, 255, 0) if (self.ind_right and self.blinker_on) else (30, 60, 30)
        cv2.putText(scene, "<<", (dash_x + 25, dash_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, left_color, 3, cv2.LINE_AA)
        cv2.putText(scene, ">>", (dash_x + 160, dash_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, right_color, 3, cv2.LINE_AA)

        # Horn Banner
        if self.horn_active:
            cv2.putText(scene, "HOOOONK!! [H]", (self.w // 2 - 170, int(self.h * 0.35)), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 255), 4, cv2.LINE_AA)

        # Speed (Large Digital)
        cv2.putText(scene, f"{int(self.speed_mph)}", (dash_x + 30, dash_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(scene, "MPH", (dash_x + 150, dash_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA)

        # Gear Display
        cv2.putText(scene, f"GEAR: D{self.current_gear}", (dash_x + 240, dash_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 120), 2, cv2.LINE_AA)

        # RPM Bar
        cv2.putText(scene, f"RPM: {int(self.engine_rpm)}", (dash_x + 240, dash_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
        rpm_ratio = (self.engine_rpm - 600) / 1600.0
        cv2.rectangle(scene, (dash_x + 240, dash_y + 90), (dash_x + 380, dash_y + 102), (40, 40, 40), -1)
        cv2.rectangle(scene, (dash_x + 240, dash_y + 90), (dash_x + 240 + int(rpm_ratio * 140), dash_y + 102), (0, 255, 0), -1)

        # Lane Indicator / Warning
        if abs(self.truck_x) > 0.85:
            lane_status = "LANE DEPARTURE ALERT!"
            status_color = (0, 0, 255)
        elif abs(self.truck_x) < 0.25:
            lane_status = "PERFECT LANE KEEPING"
            status_color = (0, 255, 120)
        else:
            lane_status = "LANE CENTERED"
            status_color = (0, 220, 255)

        cv2.putText(scene, lane_status, (dash_x + 30, dash_y + 138), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2, cv2.LINE_AA)


def run_demo():
    print("=" * 60)
    print("      AMERICAN TRUCK SIMULATOR - HIGHWAY ROAD DEMO          ")
    print("=" * 60)
    print("Starting simulated driving experience with hand-tracking steering...\n")

    # Initialize Camera
    source = getattr(config, "CAMERA_SOURCE", 0)
    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://") or source.startswith("rtsp://")):
        print(f"[Demo] Connecting to phone camera stream: {source}")
        cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(int(source))
        if not cap.isOpened():
            for idx in [0, 1, 2, 3]:
                test_cap = cv2.VideoCapture(idx)
                if test_cap.isOpened():
                    cap = test_cap
                    break

    has_camera = cap.isOpened()
    if has_camera:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        print("[Demo] Camera connected successfully!")
    else:
        print("[Demo] Notice: No camera found. Running simulation with Keyboard (A/D to steer, W/S for gas/brake).")

    if has_camera:
        if getattr(config, "ENGINE_MODE", "advanced") == "advanced":
            print("[Demo] Using Enterprise Polar Tangent Engine (Full 360°/900° Continuous Rotation)...")
            tracker = AdvancedSteeringEngine()
        else:
            print("[Demo] Using Standard Hand Tracker...")
            tracker = HandTracker()
    else:
        tracker = None
    hud = HUDVisualizer() if has_camera else None
    sim = TruckSimulatorDemo(1280, 720)

    window_name = "ATS Hand Steering - Highway Driving Demo"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    prev_time = time.time()

    # Fallback keyboard inputs
    kb_steer = 0.0
    kb_gas = 0.0
    kb_brake = 0.0
    kb_horn = False
    kb_ind_l = False
    kb_ind_r = False

    try:
        while True:
            curr_time = time.time()
            dt = max(0.001, min(0.1, curr_time - prev_time))
            prev_time = curr_time

            cam_frame = None
            tracking_data = {"steer": 0.0, "throttle": 0.0, "brake": 0.0, "calibrated_angle": 0.0}

            if has_camera:
                ret, raw_frame = cap.read()
                if ret and raw_frame is not None:
                    if config.FLIP_CAMERA:
                        raw_frame = cv2.flip(raw_frame, 1)
                    tracking_data = tracker.process_frame(raw_frame)
                    # Render small HUD on camera thumbnail
                    cam_frame = hud.draw_hud(raw_frame.copy(), tracking_data, input_controller=type('obj', (object,), {'mode': 'GAME DEMO', 'is_paused': False})(), fps=1.0 / dt)

            # Combine hand inputs and keyboard controls
            effective_steer = tracking_data["steer"] if has_camera and tracking_data.get("is_two_hands") else kb_steer
            effective_throttle = max(tracking_data.get("throttle", 0.0), kb_gas)
            effective_brake = max(tracking_data.get("brake", 0.0), kb_brake)
            effective_horn = tracking_data.get("horn", False) or kb_horn
            effective_ind_l = tracking_data.get("ind_left", False) or kb_ind_l
            effective_ind_r = tracking_data.get("ind_right", False) or kb_ind_r

            # Update Truck physics & road
            sim.update(
                effective_steer, effective_throttle, effective_brake, dt,
                horn=effective_horn, ind_left_trig=effective_ind_l, ind_right_trig=effective_ind_r
            )

            # Render scene
            scene = sim.render(cam_frame, tracking_data)
            cv2.imshow(window_name, scene)

            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            elif key in (ord('c'), ord('C')) and tracker:
                tracker.calibrate_center()
            elif key in (ord('r'), ord('R')):
                sim.truck_x = 0.0
                sim.speed_mph = 35.0
            elif key in (ord('w'), ord('W')):
                kb_gas = 1.0
            elif key in (ord('s'), ord('S')):
                kb_brake = 1.0
            elif key in (ord('a'), ord('A')):
                kb_steer = -0.7
            elif key in (ord('d'), ord('D')):
                kb_steer = 0.7
            elif key in (ord('h'), ord('H')):
                kb_horn = True
            elif key == ord('['):
                kb_ind_l = True
            elif key == ord(']'):
                kb_ind_r = True
            else:
                kb_gas = 0.0
                kb_brake = 0.0
                kb_steer = 0.0
                kb_horn = False
                kb_ind_l = False
                kb_ind_r = False

    finally:
        if has_camera:
            cap.release()
            tracker.close()
        cv2.destroyAllWindows()
        print("[Demo] Closed.")


if __name__ == "__main__":
    run_demo()

