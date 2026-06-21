# inference_loop.py — статусы мест + схема (через Cloudinary)
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
from backend_config import (
    _env,
    auth_headers,
    location_url,
    parking_id,
    parking_status_url,
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
INTERVAL = 30

if not os.path.isfile(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}\n"
        "Copy models/best.pt into the project or run from the folder that contains it."
    )
if not os.path.isfile(SPOTS_PATH):
    raise FileNotFoundError(f"spots.json not found: {SPOTS_PATH}")

model = YOLO(MODEL_PATH)
with open(SPOTS_PATH) as f:
    spots = json.load(f)

print(f"Loaded {len(spots)} spots")
print(f"Location: {location_url()}")
print(f"Interval: {INTERVAL}s\n")


def analyze_frame(frame):
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
                "confidence": confidence,
                "coords": [x, y, w, h],
            }
        )
    return results


def draw_annotations(frame, results):
    annotated = frame.copy()
    for r in results:
        x, y, w, h = r["coords"]
        color = (0, 255, 0) if r["status"] == "Empty" else (0, 0, 255)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        label_y = max(y - 5, 15)
        cv2.putText(
            annotated,
            f"#{r['id']}",
            (x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )
    free = sum(1 for r in results if r["status"] == "Empty")
    cv2.putText(
        annotated,
        f"Free: {free}/{len(results)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2,
    )
    return annotated


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
    resp = requests.put(
        url,
        json={"imageUrl": image_url},
        headers=auth_headers(),
        timeout=30,
    )
    print(f"  → Scheme image PUT {url}: {resp.status_code}")
    if not resp.ok:
        print(f"  → Response: {resp.text[:200]}")


def push_to_backend(results):
    headers = auth_headers()

    for r in results:
        pid = r["parking_id"]
        url = parking_status_url(pid)
        payload = {
            "available": r["status"] == "Empty",
            "confidence": round(r["confidence"], 4),
        }
        try:
            resp = requests.put(url, json=payload, headers=headers, timeout=30)
            if not resp.ok:
                print(f"  → Error {pid}: HTTP {resp.status_code} {resp.text[:120]}")
        except Exception as e:
            print(f"  → Error {pid}: {e}")

    free = sum(1 for r in results if r["status"] == "Empty")
    print(f"  → Pushed {len(results)} spots | Free: {free}/{len(results)}")


cloudinary_ready = all(
    os.getenv(k)
    for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
)
if cloudinary_ready:
    print("Image upload: enabled (Cloudinary → PUT .../locations/.../image)")
else:
    print("Image upload: disabled — set CLOUDINARY_* in .env")

if not _env("API_KEY"):
    print("Warning: API_KEY not set — protected endpoints may return 401")

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

    if cloudinary_ready:
        print("  → Uploading scheme image...")
        annotated = draw_annotations(frame, results)
        image_url = upload_to_cloudinary(annotated)
        push_image_url(image_url)
        print(f"  → Image: {image_url}")

    push_to_backend(results)

    time.sleep(INTERVAL)
