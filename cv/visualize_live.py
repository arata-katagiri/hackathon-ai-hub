# cv/visualize_live.py
import cv2
import json
import os
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"

model = YOLO(MODEL_PATH)
with open(SPOTS_PATH) as f:
    spots = json.load(f)

print(f"Loaded {len(spots)} spots. Press Q to quit.")

while True:
    cap = cv2.VideoCapture(STREAM_URL)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Failed to grab frame, retrying...")
        continue

    for i, (x, y, w, h) in enumerate(spots):
        crop = frame[y:y+h, x:x+w]
        if crop.size == 0:
            continue
        crop_path = f"/tmp/crop_{i}.jpg"
        cv2.imwrite(crop_path, crop)
        result = model(crop_path, verbose=False)[0]
        status = result.names[result.probs.top1]
        confidence = result.probs.top1conf.item()

        color = (0, 255, 0) if status == "Empty" else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, f"#{i}", (x+2, y+12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    free = sum(1 for s in spots
               if model(f"/tmp/crop_{spots.index(s)}.jpg",
               verbose=False)[0].names[
               model(f"/tmp/crop_{spots.index(s)}.jpg",
               verbose=False)[0].probs.top1] == "Empty")

    cv2.putText(frame, f"Free: {free}/{len(spots)}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.namedWindow("Live Parking", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Live Parking", 1280, 720)
    cv2.imshow("Live Parking", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()