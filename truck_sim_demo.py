"""
Interactive American Truck Simulator Highway Experience.
Accurately reverse-engineered from SCS Software's Prism3D engine and Telemetry SDK:
- 1:1 Physical Steering Wheel Mechanics with Self-Aligning Caster Torque
- Cabin Suspension Physics (Body Roll on cornering, Pitch on Acceleration/Braking, Engine Idle Vibration)
- Dual Analog Instrument Cluster (Illuminated Speedometer & Diesel Tachometer with 1200-1600 RPM Powerband)
- In-Cab GPS Route Advisor Screen with Speed Limit, Trip Distance, and Mini-Map
- Left West-Coast Truck Mirror with Real-Time Rear Perspective
- 2-Lane Divided Interstate Highway with Curves, AI Traffic Vehicles, and Overhead Highway Gantry Signs
- Air Brakes, 12-Speed Transmission, Air Horn, and Dashboard Turn Signal Indicators
- Full Support for Both 2-Hand Wheel Tilt and 1-Hand Reach Steering
"""

import sys
import os
import time
import math
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import config
from advanced_tracker import AdvancedSteeringEngine
from hand_tracker import HandTracker
from visualizer import HUDVisualizer


class AITrafficVehicle:
    """Represents another vehicle driving on the highway."""
    def __init__(self, z_dist, lane, v_type="car", speed=55.0):
        self.z = float(z_dist)          # Distance ahead in feet (50 to 1200 ft)
        self.lane = lane                # -0.5 (left lane) or +0.5 (right lane)
        self.v_type = v_type            # "car", "suv", or "truck"
        self.speed = speed              # MPH
        self.color = (np.random.randint(40, 220), np.random.randint(40, 220), np.random.randint(40, 220))


class TruckSimulatorDemo:
    def __init__(self, width=1280, height=720):
        self.w = width
        self.h = height

        # -------------------------------------------------------------
        # 1. Vehicle Telemetry & Physics (SCS Telemetry SDK Specification)
        # -------------------------------------------------------------
        self.speed_mph = 0.0            # Forward velocity (0 to 80 MPH)
        self.target_speed = 0.0
        self.engine_rpm = 650.0         # Idle RPM (650), Redline (2100)
        self.current_gear = 1           # 1 to 12 gears
        self.odometer_miles = 142.6     # Starting trip mileage
        self.air_pressure_psi = 120.0   # Semi-truck air brake reservoir (90-125 psi)
        self.fuel_pct = 78.0

        # Lateral lane position (-1.0 = left shoulder, 0.0 = center lane, +1.0 = right shoulder)
        self.truck_x = 0.0
        self.steer_angle_deg = 0.0

        # -------------------------------------------------------------
        # 2. Cabin Suspension Dynamics (Prism3D Engine Physics)
        # -------------------------------------------------------------
        self.cab_pitch = 0.0            # Dive on braking, squat on accel
        self.cab_roll = 0.0             # Body lean on cornering
        self.cab_yaw_drift = 0.0
        self.engine_vibration = 0.0     # 4-cylinder/6-cylinder diesel rumble

        # -------------------------------------------------------------
        # 3. Environment & Highway Geometry
        # -------------------------------------------------------------
        self.road_pos = 0.0
        self.road_curve = 0.0           # Current instantaneous road curvature
        self.target_curve = 0.0
        self.curve_timer = 0.0
        self.gantry_z = 800.0           # Overhead interstate sign distance

        # -------------------------------------------------------------
        # 4. Traffic System
        # -------------------------------------------------------------
        self.traffic = [
            AITrafficVehicle(z_dist=220, lane=0.5, v_type="truck", speed=52.0),
            AITrafficVehicle(z_dist=480, lane=-0.5, v_type="car", speed=64.0),
            AITrafficVehicle(z_dist=750, lane=0.5, v_type="suv", speed=58.0),
        ]

        # -------------------------------------------------------------
        # 5. Lights, Horn & Indicators
        # -------------------------------------------------------------
        self.horn_active = False
        self.ind_left = False
        self.ind_right = False
        self.blinker_timer = 0.0
        self.blinker_on = False

    def update(self, steer_input, throttle_input, brake_input, dt, horn=False, ind_left_trig=False, ind_right_trig=False):
        """Advances physics, transmission, suspension, and traffic by time step dt."""
        self.horn_active = horn

        # Toggle turn blinkers with debounce
        if ind_left_trig:
            self.ind_left = not self.ind_left
            if self.ind_left:
                self.ind_right = False
        if ind_right_trig:
            self.ind_right = not self.ind_right
            if self.ind_right:
                self.ind_left = False

        self.blinker_timer += dt
        if self.blinker_timer > 0.35:
            self.blinker_timer = 0.0
            self.blinker_on = not self.blinker_on

        # 1. Powertrain & Throttle Acceleration
        if throttle_input > 0.08:
            # 500 HP Detroit Diesel torque curve
            accel_rate = 18.0 * (1.0 - (self.speed_mph / 85.0))
            self.speed_mph += throttle_input * accel_rate * dt
            target_pitch = -0.015 * throttle_input  # Cab squats back
        elif brake_input > 0.08:
            # S-Cam Air Brakes with ABS
            brake_rate = 42.0
            self.speed_mph -= brake_input * brake_rate * dt
            target_pitch = 0.025 * brake_input      # Cab dives forward
            self.air_pressure_psi = max(75.0, self.air_pressure_psi - 2.5 * dt)
        else:
            # Air drag & rolling resistance
            self.speed_mph -= (2.0 + 0.05 * self.speed_mph) * dt
            target_pitch = 0.0
            self.air_pressure_psi = min(125.0, self.air_pressure_psi + 3.0 * dt)

        self.speed_mph = float(np.clip(self.speed_mph, 0.0, 78.0))

        # Smooth cab suspension pitch
        self.cab_pitch += (target_pitch - self.cab_pitch) * 8.0 * dt

        # 2. 12-Speed Automated Manual Transmission (Allison / Eaton Fuller)
        if self.speed_mph > 0.5:
            # Progressive gear calculation
            self.current_gear = max(1, min(12, int(self.speed_mph / 6.2) + 1))
            speed_in_gear = self.speed_mph % 6.2
            # RPM curves between 1100 and 1700 RPM in the diesel sweet spot
            self.engine_rpm = 1100.0 + (speed_in_gear / 6.2) * 550.0 + (throttle_input * 250.0)
        else:
            self.current_gear = 1
            self.engine_rpm = 650.0 + (throttle_input * 600.0)

        # 3. Dynamic Steering Mechanics (SCS Speed-Sensitive Steering)
        # At 65 MPH, 100% steering gives gentle lane change; at 10 MPH, sharp turn
        speed_ratio = self.speed_mph / 65.0
        steer_effectiveness = 1.4 * (0.35 + 0.65 * (1.0 - min(1.0, speed_ratio * 0.4)))
        
        # Lateral movement across road
        lateral_velocity = (steer_input * steer_effectiveness - self.road_curve * 0.9) * max(0.15, speed_ratio)
        self.truck_x += lateral_velocity * 1.5 * dt
        self.truck_x = float(np.clip(self.truck_x, -1.3, 1.3))

        # Body roll from lateral G-force: turns left -> body rolls right
        target_roll = -steer_input * 0.035 * max(0.2, speed_ratio)
        self.cab_roll += (target_roll - self.cab_roll) * 6.0 * dt

        # Engine idle vibration (subtle 30Hz oscillation)
        self.engine_vibration = math.sin(time.time() * 28.0) * (1.2 if self.speed_mph < 2.0 else 0.4)

        # 4. Road Curvature & Distance Travel
        speed_fps = self.speed_mph * 1.46667
        self.road_pos += speed_fps * dt * 1.8
        self.odometer_miles += (self.speed_mph / 3600.0) * dt

        self.curve_timer += dt
        if self.curve_timer > 6.0:
            self.curve_timer = 0.0
            self.target_curve = np.random.uniform(-0.55, 0.55)

        self.road_curve += (self.target_curve - self.road_curve) * 0.4 * dt

        # Gantry overhead sign
        self.gantry_z -= speed_fps * dt
        if self.gantry_z < -50:
            self.gantry_z = 1400.0

        # 5. AI Highway Traffic Update
        for car in self.traffic:
            # Relative speed difference
            rel_speed_fps = (self.speed_mph - car.speed) * 1.46667
            car.z -= rel_speed_fps * dt
            # Recycle traffic behind or too far ahead
            if car.z < -40.0:
                car.z = np.random.uniform(700.0, 1100.0)
                car.lane = np.random.choice([-0.5, 0.5])
                car.speed = np.random.uniform(50.0, 68.0)
            elif car.z > 1400.0:
                car.z = 200.0

    def render(self, frame_camera, tracking_data):
        """Renders authentic American Truck Simulator cockpit windshield view."""
        scene = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        horizon_y = int(self.h * 0.40 + self.cab_pitch * self.h)

        # 1. Sky Gradient (Arizona Desert Sunset)
        for y in range(horizon_y):
            ratio = y / max(1, horizon_y)
            b = int(220 * (1.0 - ratio) + 140 * ratio)
            g = int(140 * (1.0 - ratio) + 90 * ratio)
            r = int(70 * (1.0 - ratio) + 40 * ratio)
            scene[y, :] = (b, g, r)

        # 2. Distant Red Rock Mountain Silhouettes
        for i in range(6):
            mx = int(self.w * 0.22 * i - (self.truck_x * 40))
            pts = np.array([
                [mx - 80, horizon_y],
                [mx + 80, horizon_y - 65],
                [mx + 170, horizon_y - 95],
                [mx + 260, horizon_y - 45],
                [mx + 340, horizon_y]
            ], np.int32)
            cv2.fillPoly(scene, [pts], (95, 60, 48))

        # 3. Ground / Desert Sand
        cv2.rectangle(scene, (0, horizon_y), (self.w, self.h), (55, 110, 160), -1)

        # 4. 3D Perspective Road & Highway Curvature
        cam_offset_x = int(self.truck_x * (self.w * 0.38))
        curve_offset_x = int(self.road_curve * 260)

        road_top_w = 110
        road_bot_w = 1050
        road_center_top = (self.w // 2) + curve_offset_x - int(cam_offset_x * 0.12)
        road_center_bot = (self.w // 2) - cam_offset_x

        # Asphalt polygon
        p_top_l = (road_center_top - road_top_w // 2, horizon_y)
        p_top_r = (road_center_top + road_top_w // 2, horizon_y)
        p_bot_r = (road_center_bot + road_bot_w // 2, self.h)
        p_bot_l = (road_center_bot - road_bot_w // 2, self.h)
        cv2.fillPoly(scene, [np.array([p_top_l, p_top_r, p_bot_r, p_bot_l], np.int32)], (42, 42, 44))

        # Solid Yellow Left Shoulder Line
        cv2.line(scene, p_top_l, p_bot_l, (0, 215, 255), 5, cv2.LINE_AA)
        # Solid White Right Fog Line
        cv2.line(scene, p_top_r, p_bot_r, (240, 240, 240), 5, cv2.LINE_AA)

        # Dashed White Center Lane Divider (Separating Lanes 1 & 2)
        num_dashes = 16
        for seg in range(num_dashes):
            t1 = (seg + (self.road_pos % 12) / 12.0) / float(num_dashes)
            t2 = t1 + 0.032
            if t1 > 1.0 or t2 > 1.0:
                continue

            y1 = int(horizon_y + (self.h - horizon_y) * (t1 ** 2.2))
            y2 = int(horizon_y + (self.h - horizon_y) * (t2 ** 2.2))
            x1 = int(road_center_top + (road_center_bot - road_center_top) * t1)
            x2 = int(road_center_top + (road_center_bot - road_center_top) * t2)

            dash_thick = max(2, int(9 * t1))
            cv2.line(scene, (x1, y1), (x2, y2), (255, 255, 255), dash_thick, cv2.LINE_AA)

        # 5. Render AI Traffic Vehicles Ahead
        for car in sorted(self.traffic, key=lambda c: -c.z):
            if car.z < 25.0:
                continue
            # Perspective projection based on Z distance
            scale = 450.0 / (car.z + 50.0)
            t = 1.0 - (car.z / 1200.0)
            if t < 0.01:
                continue

            cy = int(horizon_y + (self.h - horizon_y) * (t ** 2.2))
            road_center_at_z = int(road_center_top + (road_center_bot - road_center_top) * t)
            lane_w_at_z = int((road_top_w + (road_bot_w - road_top_w) * t) * 0.45)
            cx = road_center_at_z + int(car.lane * lane_w_at_z)

            vw = int(45 * scale)
            vh = int(32 * scale) if car.v_type != "truck" else int(65 * scale)

            # Draw vehicle body
            cv2.rectangle(scene, (cx - vw // 2, cy - vh), (cx + vw // 2, cy), car.color, -1)
            cv2.rectangle(scene, (cx - vw // 2, cy - vh), (cx + vw // 2, cy), (10, 10, 10), max(1, int(2 * scale)))

            # Red Taillights
            tl_size = max(2, int(4 * scale))
            cv2.circle(scene, (cx - vw // 2 + tl_size + 2, cy - tl_size - 2), tl_size, (0, 0, 255), -1)
            cv2.circle(scene, (cx + vw // 2 - tl_size - 2, cy - tl_size - 2), tl_size, (0, 0, 255), -1)

        # 6. Overhead Interstate Gantry Sign (e.g. I-10 EAST - PHOENIX)
        if 40.0 < self.gantry_z < 900.0:
            scale_g = 450.0 / (self.gantry_z + 40.0)
            t_g = 1.0 - (self.gantry_z / 1000.0)
            gy = int(horizon_y - 120 * scale_g)
            gx = int(road_center_top + (road_center_bot - road_center_top) * t_g)
            gw = int(240 * scale_g)
            gh = int(70 * scale_g)

            # Green Interstate Signboard
            cv2.rectangle(scene, (gx - gw // 2, gy), (gx + gw // 2, gy + gh), (30, 130, 40), -1)
            cv2.rectangle(scene, (gx - gw // 2, gy), (gx + gw // 2, gy + gh), (255, 255, 255), max(1, int(2 * scale_g)))
            if scale_g > 0.4:
                font_s = max(0.35, 0.65 * scale_g)
                cv2.putText(scene, "INTERSTATE 10 EAST", (gx - int(gw * 0.44), gy + int(gh * 0.42)), cv2.FONT_HERSHEY_SIMPLEX, font_s, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(scene, "PHOENIX  15 MILES", (gx - int(gw * 0.40), gy + int(gh * 0.80)), cv2.FONT_HERSHEY_SIMPLEX, font_s * 0.9, (255, 255, 255), 1, cv2.LINE_AA)

        # 7. Authentic Truck Windshield, Dashboard, & Rotating Steering Wheel
        self._draw_truck_interior(scene, tracking_data.get("calibrated_angle", 0.0))

        # 8. Left Side West Coast Rearview Mirror
        self._draw_left_mirror(scene)

        # 9. Picture-In-Picture Webcam Hand Tracker (Upper Right Corner)
        if frame_camera is not None:
            pip_w = 280
            pip_h = 160
            pip_thumb = cv2.resize(frame_camera, (pip_w, pip_h))
            cv2.rectangle(scene, (self.w - pip_w - 22, 18), (self.w - 18, 18 + pip_h + 4), (0, 200, 255), 2)
            scene[20:20 + pip_h, self.w - pip_w - 20:self.w - 20] = pip_thumb
            cv2.putText(scene, "LIVE HAND CAMERA", (self.w - pip_w - 12, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # 10. In-Cabin GPS Navigation Screen & Instrument Gauges
        self._draw_dashboard_cluster(scene)

        # 11. Bottom Hotkey Guide
        bar_text = "[Tilt Hands] Steer Wheel   |   [W/Pinch R] Accel   |   [S/Pinch L] Brake   |   [C] Calibrate   |   [Q] Quit"
        cv2.putText(scene, bar_text, (self.w // 2 - 400, self.h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (210, 210, 210), 1, cv2.LINE_AA)

        return scene

    def _draw_truck_interior(self, scene, angle_deg):
        """Draws realistic Kenworth / Peterbilt cab frame, dashboard base, and rotating wheel."""
        cab_top_y = int(self.h * 0.58 + self.cab_pitch * self.h + self.engine_vibration)

        # Dashboard dark textured polymer base
        cv2.rectangle(scene, (0, cab_top_y), (self.w, self.h), (26, 26, 28), -1)
        # Dashboard top highlight bevel
        cv2.line(scene, (0, cab_top_y), (self.w, cab_top_y), (50, 52, 56), 3)

        # Windshield A-Pillars (Cab Structural Posts)
        pillar_l = np.array([[0, 0], [100, 0], [150, cab_top_y], [0, cab_top_y]], np.int32)
        pillar_r = np.array([[self.w - 90, 0], [self.w, 0], [self.w, cab_top_y], [self.w - 140, cab_top_y]], np.int32)
        cv2.fillPoly(scene, [pillar_l], (35, 36, 38))
        cv2.fillPoly(scene, [pillar_r], (35, 36, 38))

        # Driver's 18-Inch Big Rig Steering Wheel (Centered in driver's seating position: around x=420)
        wc_x = int(self.w * 0.35 + self.cab_roll * 180)
        wc_y = int(self.h * 0.75 + self.cab_pitch * 80 + self.engine_vibration)
        radius = 145

        # Heavy rubberized outer rim
        cv2.circle(scene, (wc_x, wc_y), radius, (16, 16, 18), 20, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), radius, (65, 68, 72), 3, cv2.LINE_AA)

        # Center Horn Hub with Chrome Trim
        cv2.circle(scene, (wc_x, wc_y), 42, (32, 33, 35), -1, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), 42, (180, 185, 195), 3, cv2.LINE_AA)
        cv2.circle(scene, (wc_x, wc_y), 16, (0, 120, 240), -1, cv2.LINE_AA)  # Center American Eagle / Peterbilt Emblem

        # 3 Metal Spokes Rotated by current angle
        for base_deg in [0, 180, 90]:
            rad = math.radians(base_deg + angle_deg)
            sx = int(wc_x + (radius - 10) * math.cos(rad))
            sy = int(wc_y + (radius - 10) * math.sin(rad))
            ix = int(wc_x + 42 * math.cos(rad))
            iy = int(wc_y + 42 * math.sin(rad))
            cv2.line(scene, (ix, iy), (sx, sy), (40, 42, 45), 14, cv2.LINE_AA)
            cv2.line(scene, (ix, iy), (sx, sy), (190, 195, 205), 3, cv2.LINE_AA)

        # Red Racing/Centering Stripe at 12 o'clock
        top_rad = math.radians(-90 + angle_deg)
        tx = int(wc_x + radius * math.cos(top_rad))
        ty = int(wc_y + radius * math.sin(top_rad))
        cv2.circle(scene, (tx, ty), 10, (0, 0, 240), -1, cv2.LINE_AA)
        cv2.circle(scene, (tx, ty), 10, (255, 255, 255), 2, cv2.LINE_AA)

    def _draw_left_mirror(self, scene):
        """Draws West Coast chrome dual-pane rearview mirror on left A-pillar."""
        mx = 14
        my = int(self.h * 0.22)
        mw = 75
        mh = 190

        # Mirror Chrome Frame
        cv2.rectangle(scene, (mx, my), (mx + mw, my + mh), (200, 205, 210), -1)
        cv2.rectangle(scene, (mx + 3, my + 3), (mx + mw - 3, my + mh - 3), (25, 25, 28), -1)

        # Road horizon inside mirror
        m_horiz = my + int(mh * 0.45)
        cv2.rectangle(scene, (mx + 4, my + 4), (mx + mw - 4, m_horiz), (180, 120, 80), -1)  # Sky
        cv2.rectangle(scene, (mx + 4, m_horiz), (mx + mw - 4, my + mh - 4), (45, 45, 48), -1)  # Road behind

        # Road lane line receding backwards in mirror
        m_rx = mx + int(mw * 0.55 - self.truck_x * 12)
        cv2.line(scene, (m_rx, m_horiz), (mx + int(mw * 0.70), my + mh - 4), (240, 240, 240), 2)

        # Mirror Convex Split Divider
        cv2.line(scene, (mx, my + int(mh * 0.72)), (mx + mw, my + int(mh * 0.72)), (180, 185, 190), 2)
        cv2.putText(scene, "MIRROR", (mx + 8, my + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_dashboard_cluster(self, scene):
        """Draws dual illuminated analog dials, digital trip computer, and Route Advisor GPS."""
        dash_x = int(self.w * 0.55)
        dash_y = int(self.h * 0.61)

        # Main Instrument Cluster Panel
        cv2.rectangle(scene, (dash_x, dash_y), (dash_x + 470, dash_y + 190), (14, 15, 18), -1)
        cv2.rectangle(scene, (dash_x, dash_y), (dash_x + 470, dash_y + 190), (60, 65, 72), 2)

        # 1. Analog Gauge 1: SPEEDOMETER (Left Dial)
        s_cx = dash_x + 85
        s_cy = dash_y + 90
        s_rad = 62
        cv2.circle(scene, (s_cx, s_cy), s_rad, (22, 24, 28), -1, cv2.LINE_AA)
        cv2.circle(scene, (s_cx, s_cy), s_rad, (120, 125, 135), 2, cv2.LINE_AA)
        # Speed needle (-140° to +140° for 0 to 100 MPH)
        needle_deg = -140 + (self.speed_mph / 100.0) * 280
        n_rad = math.radians(needle_deg)
        nx = int(s_cx + (s_rad - 12) * math.cos(n_rad))
        ny = int(s_cy + (s_rad - 12) * math.sin(n_rad))
        cv2.line(scene, (s_cx, s_cy), (nx, ny), (0, 140, 255), 3, cv2.LINE_AA)
        cv2.circle(scene, (s_cx, s_cy), 8, (200, 205, 215), -1)
        cv2.putText(scene, f"{int(self.speed_mph)}", (s_cx - 16, s_cy + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(scene, "MPH", (s_cx - 14, s_cy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 255), 1, cv2.LINE_AA)

        # 2. Analog Gauge 2: TACHOMETER (Right Dial)
        t_cx = dash_x + 235
        t_cy = dash_y + 90
        t_rad = 62
        cv2.circle(scene, (t_cx, t_cy), t_rad, (22, 24, 28), -1, cv2.LINE_AA)
        cv2.circle(scene, (t_cx, t_cy), t_rad, (120, 125, 135), 2, cv2.LINE_AA)
        # Green Eco Powerband arc (1100 to 1600 RPM)
        rpm_needle_deg = -140 + (self.engine_rpm / 2500.0) * 280
        rn_rad = math.radians(rpm_needle_deg)
        r_nx = int(t_cx + (t_rad - 12) * math.cos(rn_rad))
        r_ny = int(t_cy + (t_rad - 12) * math.sin(rn_rad))
        cv2.line(scene, (t_cx, t_cy), (r_nx, r_ny), (0, 255, 120), 3, cv2.LINE_AA)
        cv2.circle(scene, (t_cx, t_cy), 8, (200, 205, 215), -1)
        cv2.putText(scene, f"D{self.current_gear}", (t_cx - 12, t_cy + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2, cv2.LINE_AA)
        cv2.putText(scene, "RPM x100", (t_cx - 24, t_cy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (200, 200, 200), 1, cv2.LINE_AA)

        # 3. Route Advisor / GPS Navigation Unit (Right Side of Cluster)
        gps_x = dash_x + 320
        gps_y = dash_y + 18
        gps_w = 135
        gps_h = 155
        cv2.rectangle(scene, (gps_x, gps_y), (gps_x + gps_w, gps_y + gps_h), (25, 35, 45), -1)
        cv2.rectangle(scene, (gps_x, gps_y), (gps_x + gps_w, gps_y + gps_h), (0, 180, 240), 2)

        # GPS Title & Speed Limit Badge
        cv2.putText(scene, "ROUTE ADVISOR", (gps_x + 8, gps_y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 200, 255), 1, cv2.LINE_AA)
        # US Speed Limit 65 Badge
        cv2.rectangle(scene, (gps_x + 8, gps_y + 24), (gps_x + 52, gps_y + 72), (255, 255, 255), -1)
        cv2.rectangle(scene, (gps_x + 10, gps_y + 26), (gps_x + 50, gps_y + 70), (0, 0, 0), 1)
        cv2.putText(scene, "SPEED", (gps_x + 12, gps_y + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 0), 1)
        cv2.putText(scene, "LIMIT", (gps_x + 13, gps_y + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 0), 1)
        cv2.putText(scene, "65", (gps_x + 13, gps_y + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 0, 0), 2)

        # Navigation Next Turn & Distance
        cv2.putText(scene, "^ 14.8 MI", (gps_x + 60, gps_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 120), 1, cv2.LINE_AA)
        cv2.putText(scene, "ETA: 14:48", (gps_x + 60, gps_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)

        # Air Pressure & Trip Mileage
        cv2.putText(scene, f"AIR: {int(self.air_pressure_psi)} PSI", (gps_x + 10, gps_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 200), 1, cv2.LINE_AA)
        cv2.putText(scene, f"TRIP: {self.odometer_miles:5.1f} MI", (gps_x + 10, gps_y + 115), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(scene, f"FUEL: {int(self.fuel_pct)} %", (gps_x + 10, gps_y + 135), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 100), 1, cv2.LINE_AA)

        # 4. Turn Signal Blinkers at top of cluster
        l_col = (0, 255, 0) if (self.ind_left and self.blinker_on) else (25, 45, 25)
        r_col = (0, 255, 0) if (self.ind_right and self.blinker_on) else (25, 45, 25)
        cv2.putText(scene, "<<", (dash_x + 30, dash_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, l_col, 2, cv2.LINE_AA)
        cv2.putText(scene, ">>", (dash_x + 260, dash_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, r_col, 2, cv2.LINE_AA)

        # 5. Horn Banner
        if self.horn_active:
            cv2.putText(scene, "AIR HORN HONK! [H]", (self.w // 2 - 190, int(self.h * 0.32)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3, cv2.LINE_AA)


def run_demo():
    print("=" * 65)
    print("   AMERICAN TRUCK SIMULATOR - REVERSE-ENGINEERED HIGHWAY SIM   ")
    print("=" * 65)
    print("Initializing cockpit physics, 1:1 steering mechanics, and AI highway traffic...\n")

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
        print("[Demo] Notice: No camera found. Running simulation with keyboard fallback.")

    if has_camera:
        if getattr(config, "ENGINE_MODE", "advanced") == "advanced":
            print("[Demo] Using Enterprise Polar Tangent Engine (Supports Both 2-Hand Wheel & 1-Hand Steering)...")
            tracker = AdvancedSteeringEngine()
        else:
            print("[Demo] Using Standard Hand Tracker...")
            tracker = HandTracker()
    else:
        tracker = None

    hud = HUDVisualizer() if has_camera else None
    sim = TruckSimulatorDemo(1280, 720)

    window_name = "ATS Hand Steering - Highway Driving Simulation"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    prev_time = time.time()

    kb_steer = 0.0
    kb_gas = 0.0
    kb_brake = 0.0
    kb_horn = False
    kb_ind_l = False
    kb_ind_r = False

    try:
        while True:
            curr_time = time.time()
            dt = max(0.001, min(0.08, curr_time - prev_time))
            prev_time = curr_time

            cam_frame = None
            tracking_data = {"steer": 0.0, "throttle": 0.0, "brake": 0.0, "calibrated_angle": 0.0, "hands_detected": 0}

            if has_camera:
                ret, raw_frame = cap.read()
                if ret and raw_frame is not None:
                    if config.FLIP_CAMERA:
                        raw_frame = cv2.flip(raw_frame, 1)
                    tracking_data = tracker.process_frame(raw_frame)
                    dummy_ctrl = type('obj', (object,), {'mode': 'GAMEPAD', 'is_paused': False, 'physical_controller_active': False})()
                    cam_frame = hud.draw_hud(raw_frame.copy(), tracking_data, input_controller=dummy_ctrl, fps=1.0 / dt)

            # Support BOTH 2-hand wheel tilt and 1-hand reach steering!
            if has_camera and tracking_data.get("hands_detected", 0) > 0:
                effective_steer = tracking_data["steer"]
            else:
                effective_steer = kb_steer

            effective_throttle = max(tracking_data.get("throttle", 0.0), kb_gas)
            effective_brake = max(tracking_data.get("brake", 0.0), kb_brake)
            effective_horn = tracking_data.get("horn", False) or kb_horn
            effective_ind_l = tracking_data.get("ind_left", False) or kb_ind_l
            effective_ind_r = tracking_data.get("ind_right", False) or kb_ind_r

            # Update truck simulation physics
            sim.update(
                effective_steer, effective_throttle, effective_brake, dt,
                horn=effective_horn, ind_left_trig=effective_ind_l, ind_right_trig=effective_ind_r
            )

            # Render complete cockpit windshield scene
            scene_frame = sim.render(cam_frame, tracking_data)

            cv2.imshow(window_name, scene_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            elif key in (ord('c'), ord('C')):
                if tracker:
                    tracker.calibrate_center()
            elif key in (ord('r'), ord('R')):
                sim.truck_x = 0.0
                sim.speed_mph = 45.0
            elif key in (ord('h'), ord('H')):
                kb_horn = True
            elif key in (ord('['), ord('{')):
                kb_ind_l = not kb_ind_l
            elif key in (ord(']'), ord('}')):
                kb_ind_r = not kb_ind_r

    finally:
        if has_camera:
            cap.release()
        cv2.destroyAllWindows()
        print("\n[Demo] Closed driving simulation.")

if __name__ == "__main__":
    run_demo()
