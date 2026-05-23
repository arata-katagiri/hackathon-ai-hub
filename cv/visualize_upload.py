# cv/visualize_and_upload.py
import cv2
import json
import time
import os
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

API_KEY = os.getenv("API_KEY", "")
STREAM_URL = "https://webcam.elcat.kg/Bishkek_Ala-Too_Square/index.m3u8"
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
BACKEND_BASE = "https://parking-bishkek.onrender.com/api/parkings"
IMAGE_ENDPOINT = "https://parking-bishkek.onrender.com/api/scheme/image"
INTERVAL = 30
CONFIDENCE_THRESHOLD = 0.85

model = YOLO(MODEL_PATH)
with open(SPOTS_PATH) as f:
    spots = json.load(f)

print(f"Loaded {len(spots)} spots")

def analyze_and_draw(frame):
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
            "confidence": round(confidence, 3),
            "coords": [x, y, w, h]
        })

    for r in results:
        x, y, w, h = r["coords"]
        color = (0, 255, 0) if r["status"] == "Empty" else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        label = f"#{r['id']}"
        label_y = max(y - 5, 15)
        cv2.putText(frame, label, (x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    free = sum(1 for r in results if r["status"] == "Empty")
    cv2.putText(frame, f"Free: {free}/{len(results)}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame, results

def upload_to_cloudinary(frame):
    tmp_path = "/tmp/parking_annotated.jpg"
    cv2.imwrite(tmp_path, frame)
    response = cloudinary.uploader.upload(
        tmp_path,
        public_id="parking/ala_too_live",
        overwrite=True,
        invalidate=True
    )
    return response["secure_url"]

def push_image_url(image_url):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    try:
        resp = requests.put(
            IMAGE_ENDPOINT,
            json={"imageUrl": image_url},
            headers=headers
        )
        print(f"  → Image URL posted: {resp.status_code}")
    except Exception as e:
        print(f"  → Image URL error: {e}")

def push_to_backend(results, image_url):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    for r in results:
        payload = {
            "available": r["status"] == "Empty",
            "confidence": r["confidence"],
            "imageUrl": image_url
        }
        url = f"{BACKEND_BASE}/ala-too-spot-{r['id']}/status"
        try:
            requests.put(url, json=payload, headers=headers)
        except Exception as e:
            print(f"  → Error spot {r['id']}: {e}")

    free = sum(1 for r in results if r["status"] == "Empty")
    print(f"  → Pushed {len(results)} spots | Free: {free}/{len(results)}")
    print(f"  → Image: {image_url}")

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
    annotated_frame, results = analyze_and_draw(frame)

    cv2.namedWindow("Parking Live", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Parking Live", 1280, 720)
    cv2.imshow("Parking Live", annotated_frame)
    cv2.waitKey(1)

    print("  → Uploading to Cloudinary...")
    image_url = upload_to_cloudinary(annotated_frame)

    push_image_url(image_url)
    push_to_backend(results, image_url)

    time.sleep(INTERVAL)

cv2.destroyAllWindows()