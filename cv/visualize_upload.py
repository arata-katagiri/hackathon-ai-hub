# visualize_upload.py — то же API + окно предпросмотра
import io
import json
import os
import time

import cloudinary
import cloudinary.uploader
import cv2
import requests
from dotenv import load_dotenv
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend_config import auth_headers, location_url, parking_id, parking_status_url

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
INTERVAL = 30

model = YOLO(MODEL_PATH)
with open(SPOTS_PATH) as f:
    spots = json.load(f)

print(f"Loaded {len(spots)} spots | {location_url()}")


def analyze_and_draw(frame):
    results = []
    for i, (x, y, w, h) in enumerate(spots):
        crop = frame[y : y + h, x : x + w]
        if crop.size == 0:
            continue
        result = model(crop, verbose=False)[0]
        status = result.names[result.probs.top1]
        confidence = result.probs.top1conf.item()
        results.append(
            {
                "id": i,
                "parking_id": parking_id(i),
                "status": status,
                "confidence": round(confidence, 3),
                "coords": [x, y, w, h],
            }
        )

    for r in results:
        x, y, w, h = r["coords"]
        color = (0, 255, 0) if r["status"] == "Empty" else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        label_y = max(y - 5, 15)
        cv2.putText(
            frame,
            r["parking_id"],
            (x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    free = sum(1 for r in results if r["status"] == "Empty")
    cv2.putText(
        frame,
        f"Free: {free}/{len(results)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2,
    )
    return frame, results


def upload_to_cloudinary(frame):
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")
    response = cloudinary.uploader.upload(
        io.BytesIO(buf.tobytes()),
        public_id="parking/ala_too_live",
        overwrite=True,
        invalidate=True,
    )
    return response["secure_url"]


def push_image_url(image_url: str):
    url = location_url("image")
    resp = requests.put(url, json={"imageUrl": image_url}, headers=auth_headers(), timeout=30)
    print(f"  → Scheme image PUT: {resp.status_code}")


def push_to_backend(results):
    headers = auth_headers()
    for r in results:
        url = parking_status_url(r["parking_id"])
        payload = {"available": r["status"] == "Empty"}
        try:
            requests.put(url, json=payload, headers=headers, timeout=30)
        except Exception as e:
            print(f"  → Error {r['parking_id']}: {e}")

    free = sum(1 for r in results if r["status"] == "Empty")
    print(f"  → Pushed {len(results)} spots | Free: {free}/{len(results)}")


while True:
    print(f"[{time.strftime('%H:%M:%S')}] Capturing frame...")
    cap = cv2.VideoCapture(STREAM_URL)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("  → Failed to grab frame, retrying...")
        time.sleep(5)
        continue

    annotated_frame, results = analyze_and_draw(frame.copy())

    cv2.namedWindow("Parking Live", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Parking Live", 1280, 720)
    cv2.imshow("Parking Live", annotated_frame)
    cv2.waitKey(1)

    print("  → Uploading to Cloudinary...")
    image_url = upload_to_cloudinary(annotated_frame)
    push_image_url(image_url)
    push_to_backend(results)
    print(f"  → Image: {image_url}")

    time.sleep(INTERVAL)

cv2.destroyAllWindows()
