import cv2
import face_recognition
import os
import time
import numpy as np
import subprocess
import sys
from datetime import datetime, timedelta
from config import (
    KNOWN_FACES_DIR, 
    UNKNOWN_FACES_DIR, 
    MATCH_THRESHOLD, 
    GREETING_COOLDOWN, 
    UNKNOWN_ALERT_COOLDOWN
)
from telegram_utils import send_message, send_photo

def load_known_faces():
    """Loads face encodings and names from the known_faces directory."""
    known_face_encodings = []
    known_face_names = []

    print("Loading known faces...")
    if not os.path.exists(KNOWN_FACES_DIR):
        print(f"Warning: {KNOWN_FACES_DIR} does not exist.")
        return known_face_encodings, known_face_names

    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            try:
                image = face_recognition.load_image_file(filepath)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    # Use filename (without extension) as the name
                    name = os.path.splitext(filename)[0]
                    known_face_names.append(name)
                    print(f"Loaded: {name}")
                else:
                    print(f"Warning: No face found in {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return known_face_encodings, known_face_names

def main():
    known_face_encodings, known_face_names = load_known_faces()
    
    if not known_face_encodings:
        print("No known faces loaded. Please run register_face.py first.")
        # We continue anyway to detect unknown faces, but everything will be unknown.

    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Error: Could not access the webcam.")
        return

    # Track last action times
    last_greet_time = datetime.min
    last_unknown_alert_time = datetime.min
    
    # Variables for processing every other frame to save CPU
    process_this_frame = True

    print("Starting Main Loop. Press 'q' to quit.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to capture frame")
            break

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        # Handle different opencv versions
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            
            # Check for Unknown Faces first to handle alerts
            unknown_detected = False
            user_detected = False
            
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=MATCH_THRESHOLD)
                name = "Unknown"

                # Use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        user_detected = True
                    else:
                        unknown_detected = True
                else:
                    # No known faces defined
                    unknown_detected = True

                face_names.append(name)

            current_time = datetime.now()

            # Handle Actions
            if user_detected:
                time_since_last_greet = (current_time - last_greet_time).total_seconds()
                if time_since_last_greet > GREETING_COOLDOWN:
                    msg = f"Hello {name}! Nice to see you."
                    print(f"Triggering Greeting: {msg}")
                    send_message(msg)
                    last_greet_time = current_time
                    print("Anush detected")
                    subprocess.run([sys.executable, "arora.py"])
                    exit()


            if unknown_detected:
                time_since_last_alert = (current_time - last_unknown_alert_time).total_seconds()
                if time_since_last_alert > UNKNOWN_ALERT_COOLDOWN:
                    print("Triggering Unknown Face Alert!")
                    
                    # specific message
                    alert_msg = "Alert: Unknown person detected!"
                    send_message(alert_msg)
                    
                    # Save and send photo
                    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
                    photo_filename = f"unknown_{timestamp}.jpg"
                    photo_path = os.path.join(UNKNOWN_FACES_DIR, photo_filename)
                    cv2.imwrite(photo_path, frame)
                    
                    send_photo(photo_path, caption=f"Unknown person at {current_time.strftime('%H:%M:%S')}")
                    
                    last_unknown_alert_time = current_time

        process_this_frame = not process_this_frame

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        cv2.imshow('Face Recognition Security System', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
