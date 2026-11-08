"""Quick utility script to test webcam connectivity and resolution."""

import cv2
import config

def test_camera():
    source = getattr(config, "CAMERA_SOURCE", 0)
    print(f"Testing camera source: {source}...")

    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://") or source.startswith("rtsp://")):
        print(f"Attempting connection to phone IP webcam stream: {source}")
        cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(int(source))
        if not cap.isOpened():
            for idx in [0, 1, 2, 3]:
                test_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not test_cap.isOpened():
                    test_cap = cv2.VideoCapture(idx)
                if test_cap.isOpened():
                    cap = test_cap
                    print(f"Auto-detected working camera at index {idx}")
                    break

    if not cap.isOpened():
        print("ERROR: No camera detected. Please check if webcam is connected or used by another application.")
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    ret, frame = cap.read()
    if ret and frame is not None:
        h, w, c = frame.shape
        print(f"SUCCESS: Camera connected! Captured test frame: {w}x{h} ({c} channels).")
        cap.release()
        return True
    else:
        print("WARNING: Camera opened, but failed to capture a valid frame.")
        cap.release()
        return False

if __name__ == "__main__":
    test_camera()

