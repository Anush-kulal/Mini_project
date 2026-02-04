import cv2
import os
import time
from config import KNOWN_FACES_DIR

def register_face():
    """Captures a frame from the webcam and saves it as the user's face."""
    print("Starting webcam...")
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Error: Could not access the webcam.")
        return

    print("Please look at the camera. Press 's' to save your face, or 'q' to quit.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Draw a guide rectangle (optional, but helpful)
        height, width, _ = frame.shape
        start_point = (width // 4, height // 4)
        end_point = (3 * width // 4, 3 * height // 4)
        color = (255, 0, 0)
        thickness = 2
        
        display_frame = frame.copy()
        cv2.rectangle(display_frame, start_point, end_point, color, thickness)
        cv2.putText(display_frame, "Position face in box and press 's'", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Register Face', display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            # Save the original frame (without rectangle)
            filename = "known_faces.jpg"
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            cv2.imwrite(filepath, frame)
            print(f"Face saved successfully to {filepath}!")
            break
        elif key == ord('q'):
            print("Registration cancelled.")
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    register_face()
