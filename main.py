"""Main application loop for ATS Visual Hand-Tracking Steering Wheel."""

import sys
import time
import cv2
import config
from advanced_tracker import AdvancedSteeringEngine
from hand_tracker import HandTracker
from input_controller import InputController
from visualizer import HUDVisualizer


def open_camera():
    """Try opening camera from index or phone stream URL, with auto-detection."""
    source = getattr(config, "CAMERA_SOURCE", 0)

    # If user configured a phone IP stream (e.g. "http://192.168.1.50:8080/video")
    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://") or source.startswith("rtsp://")):
        print(f"[Main] Connecting to Phone IP Webcam stream at: {source}")
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            print("[Main] Successfully connected to phone camera stream!")
            return cap
        else:
            print("[Main] Failed to connect to IP camera URL. Falling back to camera auto-detection...")
            source = 0

    # Try configured index with DSHOW and default
    cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(int(source))

    # Auto-scan indices 0, 1, 2, 3 if not opened (e.g. for DroidCam / Iriun virtual devices)
    if not cap.isOpened():
        print(f"[Main] Camera index {source} not accessible. Scanning available camera devices...")
        for idx in [0, 1, 2, 3]:
            if idx == int(source):
                continue
            test_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not test_cap.isOpened():
                test_cap = cv2.VideoCapture(idx)
            if test_cap.isOpened():
                print(f"[Main] Found working camera device at Index {idx} (e.g. DroidCam / Iriun / USB)")
                cap = test_cap
                break

    if not cap.isOpened():
        print("\n" + "!" * 60)
        print("[Main] ERROR: No camera detected on your laptop!")
        print("To use your PHONE as a camera for ATS steering:")
        print("  1. (Recommended - Ultra Low Latency):")
        print("     Install 'DroidCam' or 'Iriun Webcam' on phone & laptop (free).")
        print("     Connect phone with USB cable or Wi-Fi.")
        print("  2. (Wireless IP Stream):")
        print("     Install 'IP Webcam' on phone, click 'Start Server', and")
        print("     set CAMERA_SOURCE = 'http://<your-phone-ip>:8080/video' in config.py")
        print("!" * 60 + "\n")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 60)
    return cap


def main():
    print("=" * 60)
    print("   AMERICAN TRUCK SIMULATOR - VIRTUAL HAND STEERING WHEEL   ")
    print("=" * 60)

    cap = open_camera()
    if cap is None:
        sys.exit(1)

    if getattr(config, "ENGINE_MODE", "advanced") == "advanced":
        print("[Main] Initializing Enterprise Polar Tangent Engine (Full 360°/900° Multi-Turn + 1€ Filter)...")
        tracker = AdvancedSteeringEngine()
    else:
        print("[Main] Initializing Standard MediaPipe Hand Tracker...")
        tracker = HandTracker()

    print(f"[Main] Initializing Input Controller in '{config.DEFAULT_INPUT_MODE}' mode...")
    controller = InputController(mode=config.DEFAULT_INPUT_MODE)

    visualizer = HUDVisualizer()

    window_name = "ATS Hand Steering Wheel"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    is_mini_overlay = False

    print("\n[Controls & Driving Guide]")
    print("  Hold both hands up like gripping a steering wheel.")
    print("  Tilt hands left / right   -> Smooth authentic steering (Progressive S-Curve)")
    print("  Cross hands completely    -> Continuous multi-turn angle without reversing")
    print("  Single-hand fallback      -> Steers smoothly when shifting or resting one hand")
    print("  Push Right Hand forward   -> Gear Shift to DRIVE [D]")
    print("  Pull Left Hand downward   -> Gear Shift to REVERSE [R]")
    print("  Physical Xbox Controller  -> Connect physical gamepad anytime! Triggers/buttons merge seamlessly")
    print("  [V] : Toggle Vehicle Profile (TRUCK <-> SPORT MUSTANG GT)")
    print("  [G] : Toggle Gamepad Device (DualShock 4 'Wireless' <-> Xbox 360)")
    print("  [N] : Shift to NEUTRAL [N]")
    print("  [O] : Toggle Always-On-Top Mini PiP (floats over ATS on a single screen!)")
    print("  [C] : Calibrate Center (sets current hand pose to 0°)")
    print("  [R] : Reset Calibration")
    print("  [M] : Toggle Gamepad / Keyboard mode")
    print("  [P] : Pause / Resume steering input")
    print("  [Q] or [ESC] : Quit\n")

    # FPS calculation
    prev_time = time.time()
    fps = 30.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[Main] Warning: Empty frame received from webcam. Retrying...")
                time.sleep(0.01)
                continue

            # Calculate FPS
            curr_time = time.time()
            dt = curr_time - prev_time
            prev_time = curr_time
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            # Flip frame horizontally for natural mirror behavior
            if config.FLIP_CAMERA:
                frame = cv2.flip(frame, 1)

            # Process hand tracking & angle calculation
            data = tracker.process_frame(frame)

            # Apply steering, pedals, and gear shifts to game
            controller.apply_inputs(
                steer_val=data["steer"],
                throttle_val=data.get("throttle", 0.0),
                brake_val=data.get("brake", 0.0),
                gear_shift=data.get("gear_shift"),
            )

            # Render visual HUD
            hud_frame = visualizer.draw_hud(frame, data, controller, fps=fps)

            # Display window
            cv2.imshow(window_name, hud_frame)

            # Keyboard handling
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # 'q' or ESC
                print("[Main] Exiting application...")
                break
            elif key in (ord('c'), ord('C')):
                tracker.calibrate_center()
            elif key in (ord('r'), ord('R')):
                tracker.reset_calibration()
            elif key in (ord('n'), ord('N')):
                if hasattr(tracker, "current_gear"):
                    tracker.current_gear = "N"
                controller.apply_inputs(steer_val=data["steer"], gear_shift="NEUTRAL")
                print("[Main] Shifted to NEUTRAL [N]")
            elif key in (ord('v'), ord('V')):
                if hasattr(tracker, "toggle_profile"):
                    tracker.toggle_profile()
            elif key in (ord('g'), ord('G')):
                if hasattr(controller, "toggle_gamepad_type"):
                    controller.toggle_gamepad_type()
            elif key in (ord('m'), ord('M')):
                controller.toggle_mode()
            elif key in (ord('p'), ord('P')):
                controller.toggle_pause()
            elif key in (ord('o'), ord('O'), ord('t'), ord('T')):
                is_mini_overlay = not is_mini_overlay
                if is_mini_overlay:
                    cv2.resizeWindow(window_name, 360, 220)
                    cv2.moveWindow(window_name, 25, 25)
                    try:
                        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
                    except Exception:
                        pass
                    print("[Main] Switched to Always-On-Top Mini PiP Overlay (floats over ATS)!")
                else:
                    cv2.resizeWindow(window_name, 1280, 720)
                    try:
                        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 0)
                    except Exception:
                        pass
                    print("[Main] Switched to Full Window mode.")

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user.")
    finally:
        print("[Main] Cleaning up resources...")
        controller.close()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[Main] Done. Happy trucking!")


if __name__ == "__main__":
    main()

