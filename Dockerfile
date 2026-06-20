# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System libraries:
#  - ffmpeg                : decode the HLS (.m3u8) webcam stream via OpenCV
#  - libgl1, libglib2.0-0  : runtime shared libs required by opencv-python / ultralytics
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch first so ultralytics does NOT pull the large CUDA build.
# This worker has no GPU, and the CPU wheels keep the image ~1.5 GB smaller.
RUN pip install --no-cache-dir \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

# Background worker: grabs a frame, runs inference on the 41 spots,
# and pushes statuses (+ optional scheme image) to the backend every 30s.
CMD ["python", "cv/inference_loop.py"]
