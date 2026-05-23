# cv/grab_frame.py
import cv2
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"
SAVE_PATH = os.path.join(BASE_DIR, "ala_too_frame.jpg")

cap = cv2.VideoCapture(STREAM_URL)
ret, frame = cap.read()
cap.release()

if ret:
    cv2.imwrite(SAVE_PATH, frame)
    print(f"Frame saved: {frame.shape}")
else:
    print("Failed to grab frame")