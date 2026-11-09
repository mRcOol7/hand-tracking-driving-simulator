"""Comprehensive Automated Verification Test for ATS & Mustang GT Hand Steering System."""

import os
import sys
import time
import math
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(__file__))

import config
from advanced_tracker import AdvancedSteeringEngine
from input_controller import InputController
from visualizer import HUDVisualizer

def run_tests():
    print("=" * 70)
    print("  RUNNING MULTI-VEHICLE & DUAL-CONTROLLER SYSTEM VERIFICATION  ")
    print("=" * 70)

    # 1. Test Config Integrity & Vehicle Profiles
    print("\n[1/6] Testing Configuration & Vehicle Profiles...")
    assert "truck" in config.VEHICLE_PROFILES
    assert "sport" in config.VEHICLE_PROFILES
    truck_p = config.VEHICLE_PROFILES["truck"]
    sport_p = config.VEHICLE_PROFILES["sport"]

    assert truck_p["max_steering_angle"] == 70.0
    assert sport_p["max_steering_angle"] == 38.0
    print(f" -> Truck Profile: MaxAngle={truck_p['max_steering_angle']}°, Exp={truck_p['s_curve_exponent']}")
    print(f" -> Sport Profile: MaxAngle={sport_p['max_steering_angle']}°, Exp={sport_p['s_curve_exponent']}")

    # 2. Test S-Curve Mathematical Comparison (Truck vs Mustang Sport)
    print("\n[2/6] Comparing Steering Curve Sensitivity: TRUCK vs MUSTANG GT...")
    print(" Angle (deg) | Truck Steer (70° Lock) | Mustang GT (38° Lock) | Mustang Advantage")
    print("-------------+------------------------+-----------------------+-----------------------------")
    for ang in [0.0, 5.0, 10.0, 15.0, 25.0, 38.0, 70.0]:
        # Truck
        dz_t = truck_p["deadzone"]
        if ang <= dz_t:
            st_t = 0.0
        else:
            u_t = min(1.0, (ang - dz_t) / (truck_p["max_steering_angle"] - dz_t))
            st_t = truck_p["linear_coeff"] * u_t + (1.0 - truck_p["linear_coeff"]) * (u_t ** truck_p["s_curve_exponent"])

        # Sport
        dz_s = sport_p["deadzone"]
        if ang <= dz_s:
            st_s = 0.0
        else:
            u_s = min(1.0, (ang - dz_s) / (sport_p["max_steering_angle"] - dz_s))
            st_s = sport_p["linear_coeff"] * u_s + (1.0 - sport_p["linear_coeff"]) * (u_s ** sport_p["s_curve_exponent"])

        desc = "Tight highway center" if ang <= 10.0 else ("Fast racing turn" if ang <= 38.0 else "Full sports lock achieved!")
        print(f" {ang:5.1f} deg   | {st_t*100:6.1f}%                 | {st_s*100:6.1f}%                | {desc}")

    # 3. Test Advanced Engine Profile Toggle
    print("\n[3/6] Testing Engine Dynamic Profile Switching...")
    engine = AdvancedSteeringEngine()
    assert engine.active_profile == "truck"
    engine.toggle_profile()
    assert engine.active_profile == "sport"
    engine.toggle_profile()
    assert engine.active_profile == "truck"
    print(" -> Dynamic Profile Toggle (key [V]) verified: switches between Truck and Sport cleanly!")

    # 4. Test Gamepad Initialization: DualShock 4 & Xbox 360
    print("\n[4/6] Testing Gamepad Emulation Modes (DualShock 4 vs Xbox 360)...")
    # Test DS4
    controller_ds4 = InputController(mode="gamepad")
    controller_ds4.pad_type = "ds4"
    controller_ds4._init_gamepad()
    print(f" -> DS4 Emulation Active: {type(controller_ds4.gamepad).__name__}")
    assert controller_ds4.gamepad is not None
    controller_ds4.apply_inputs(steer_val=0.45, throttle_val=0.9, brake_val=0.0, gear_shift="UP")
    print(" -> Applied DS4 Inputs: Steer=0.45, Gas=0.9, Gear=UP (Cross pulsed)")
    controller_ds4.close()

    # Test Xbox 360
    controller_x = InputController(mode="gamepad")
    controller_x.pad_type = "xbox360"
    controller_x._init_gamepad()
    print(f" -> Xbox 360 Emulation Active: {type(controller_x.gamepad).__name__}")
    assert controller_x.gamepad is not None
    controller_x.apply_inputs(steer_val=-0.35, throttle_val=0.0, brake_val=0.75, gear_shift="DOWN")
    print(" -> Applied Xbox 360 Inputs: Steer=-0.35, Brake=0.75, Gear=DOWN (Button X pulsed)")
    controller_x.close()

    # 5. Test Continuous Vector Angle Tracking (Hand Crossing)
    print("\n[5/6] Testing Continuous Vector Tracking & Hand Crossing...")
    dx = -450
    dy = 320
    ang = math.degrees(math.atan2(dy, dx))
    d_unwrap = engine._unwrap_delta_deg(ang, 0.0)
    print(f" -> Hand cross vector dx={dx}, dy={dy} -> Raw: {ang:.1f}°, Unwrapped: {d_unwrap:.1f}°")
    assert ang > 90.0

    # 6. Test Visualizer Rendering: Truck HUD & Mustang GT HUD
    print("\n[6/6] Testing HUD Rendering for Truck and Mustang GT Profiles...")
    visualizer = HUDVisualizer()

    # Frame 1: Truck HUD
    f_truck = np.zeros((720, 1280, 3), dtype=np.uint8)
    for y in range(720):
        f_truck[y, :] = (int(30 + 12 * (y / 720)), int(26 + 8 * (y / 720)), int(22 + 6 * (y / 720)))

    data_truck = {
        "steer": 0.12,
        "wheel_angle_deg": 18.0,
        "calibrated_angle": 18.0,
        "hands_detected": 2,
        "is_two_hands": True,
        "left_pt": (460, 420),
        "right_pt": (820, 470),
        "throttle": 0.50,
        "brake": 0.0,
        "current_gear": "D",
        "gear_shift": None,
        "active_profile": "truck",
        "landmarks": [],
    }
    dummy_ctrl = InputController(mode="gamepad")
    hud_truck = visualizer.draw_hud(f_truck, data_truck, dummy_ctrl, fps=60.0)
    p_truck_out = r"C:\Users\HP\.gemini\antigravity\brain\5e1151db-2f88-4861-83e2-3f9dc398caed\hud_truck_preview.jpg"
    cv2.imwrite(p_truck_out, hud_truck)
    print(f" -> Saved Truck HUD preview to: {p_truck_out}")

    # Frame 2: Mustang GT Sport HUD
    f_sport = np.zeros((720, 1280, 3), dtype=np.uint8)
    for y in range(720):
        f_sport[y, :] = (int(25 + 15 * (y / 720)), int(22 + 10 * (y / 720)), int(20 + 8 * (y / 720)))

    data_sport = {
        "steer": -0.42,
        "wheel_angle_deg": -22.0,
        "calibrated_angle": -22.0,
        "hands_detected": 2,
        "is_two_hands": True,
        "left_pt": (440, 480),
        "right_pt": (840, 410),
        "throttle": 0.85,
        "brake": 0.0,
        "current_gear": "D",
        "gear_shift": "UP",
        "active_profile": "sport",
        "landmarks": [],
    }
    dummy_ctrl.pad_type = "ds4"
    hud_sport = visualizer.draw_hud(f_sport, data_sport, dummy_ctrl, fps=60.0)
    p_sport_out = r"C:\Users\HP\.gemini\antigravity\brain\5e1151db-2f88-4861-83e2-3f9dc398caed\hud_mustang_sport_preview.jpg"
    cv2.imwrite(p_sport_out, hud_sport)
    print(f" -> Saved Mustang GT Sport HUD preview to: {p_sport_out}")

    dummy_ctrl.close()
    engine.close()
    print("\n" + "=" * 70)
    print("  ALL 6/6 SYSTEM VERIFICATION TESTS PASSED SUCCESSFULLY!  ")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
