"""Integration smoke test for ATS Hand Steering components."""

import numpy as np
import config
from hand_tracker import HandTracker
from input_controller import InputController
from visualizer import HUDVisualizer

def test_pipeline():
    print("1. Initializing HandTracker...")
    tracker = HandTracker()

    print("2. Initializing InputController...")
    controller = InputController()

    print("3. Initializing HUDVisualizer...")
    visualizer = HUDVisualizer()

    print("4. Creating dummy 720p frame...")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    print("5. Processing frame through tracker...")
    data = tracker.process_frame(frame)
    print(f"   Data: steer={data['steer']}, raw_angle={data['raw_angle']}, hands={data['hands_detected']}")

    print("6. Applying inputs...")
    controller.apply_inputs(data["steer"], data["throttle"], data["brake"])

    print("7. Rendering HUD overlay...")
    hud_frame = visualizer.draw_hud(frame, data, controller, fps=60.0)
    assert hud_frame.shape == (720, 1280, 3), "HUD frame shape mismatch!"

    print("8. Testing Calibrate Center...")
    tracker.calibrate_center()
    tracker.reset_calibration()

    print("9. Testing Mode Toggle...")
    controller.toggle_mode()
    controller.toggle_mode()

    print("10. Testing Pause...")
    controller.toggle_pause()
    controller.toggle_pause()

    print("11. Closing components...")
    controller.close()
    tracker.close()

    print("\nALL INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline()

