# inference_loop.py
import cv2
import json
import time
import requests
import os
from dotenv import load_dotenv
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("API_KEY", "")

# Config
STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
BACKEND_BASE = "https://parking-bishkek.onrender.com/api/parkings"
INTERVAL = 30

# Load model and spots
model = YOLO(MODEL_PATH)
with open(SPOTS_PATH) as f:
    spots = json.load(f)

print(f"Loaded {len(spots)} spots")
print(f"Pushing to: {BACKEND_BASE}")
print(f"Interval: {INTERVAL}s\n")

def analyze_frame(frame):
    results = []
    for i, (x, y, w, h) in enumerate(spots):
        crop = frame[y:y+h, x:x+w]
        if crop.size == 0:
            continue
        crop_path = f"/tmp/crop_{i}.jpg"
        cv2.imwrite(crop_path, crop)
        result = model(crop_path, verbose=False)[0]
        status = result.names[result.probs.top1]
        confidence = result.probs.top1conf.item()
        results.append({
            "id": i,
            "status": status,
            "confidence": confidence
        })
    return results

def push_to_backend(results):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    for r in results:
        payload = {
            "available": r["status"] == "Empty",
            "confidence": r["confidence"]
        }
        url = f"{BACKEND_BASE}/ala-too-spot-{r['id']}/status"
        try:
            requests.put(url, json=payload, headers=headers)
        except Exception as e:
            print(f"  → Error spot {r['id']}: {e}")

    free = sum(1 for r in results if r["status"] == "Empty")
    print(f"  → Pushed {len(results)} spots | Free: {free}/{len(results)}")

# Main loop
while True:
    print(f"[{time.strftime('%H:%M:%S')}] Capturing frame...")
    cap = cv2.VideoCapture(STREAM_URL)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("  → Failed to grab frame, retrying...")
        time.sleep(5)
        continue

    print(f"  → Frame grabbed {frame.shape}, analyzing {len(spots)} spots...")
    results = analyze_frame(frame)
    push_to_backend(results)

    time.sleep(INTERVAL)