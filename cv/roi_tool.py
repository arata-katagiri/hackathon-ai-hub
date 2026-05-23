# cv/roi_tool.py
import cv2
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_PATH = os.path.join(BASE_DIR, "ala_too_frame.jpg")
SPOTS_PATH = os.path.join(BASE_DIR, "spots.json")

# Load existing spots
if os.path.exists(SPOTS_PATH):
    with open(SPOTS_PATH) as f:
        spots = json.load(f)
    print(f"Loaded {len(spots)} existing spots from {SPOTS_PATH}")
else:
    spots = []
    print("No existing spots found, starting fresh.")

drawing = False
start_x, start_y = -1, -1

def draw_spots(frame):
    for i, (x, y, w, h) in enumerate(spots):
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        label_y = max(y - 5, 15)
        cv2.putText(frame, f"#{i}", (x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

def mouse_callback(event, x, y, flags, param):
    global drawing, start_x, start_y

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_x, start_y = x, y

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        temp = param.copy()
        draw_spots(temp)
        cv2.rectangle(temp, (start_x, start_y), (x, y), (0, 200, 255), 2)
        cv2.imshow("ROI Tool", temp)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        x1, y1 = min(start_x, x), min(start_y, y)
        w, h = abs(x - start_x), abs(y - start_y)
        if w > 5 and h > 5:
            spots.append([x1, y1, w, h])
            print(f"Spot #{len(spots)-1} added: x={x1} y={y1} w={w} h={h}")

frame = cv2.imread(IMAGE_PATH)
if frame is None:
    print(f"ERROR: Could not load {IMAGE_PATH}")
    print("Run grab_frame.py first to capture a frame.")
    exit(1)

clone = frame.copy()
cv2.namedWindow("ROI Tool", cv2.WINDOW_NORMAL)
cv2.resizeWindow("ROI Tool", 1280, 720)
cv2.setMouseCallback("ROI Tool", mouse_callback, clone)

print("Draw rectangles over parking spots.")
print("Keys: [s] save  [u] undo  [r] reset  [q] quit")

while True:
    display = clone.copy()
    draw_spots(display)
    cv2.imshow("ROI Tool", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        with open(SPOTS_PATH, 'w') as f:
            json.dump(spots, f)
        print(f"Saved {len(spots)} spots to {SPOTS_PATH}")
    elif key == ord('u') and spots:
        spots.pop()
        print(f"Undone. {len(spots)} spots remaining.")
    elif key == ord('r'):
        spots.clear()
        print("Reset.")
    elif key == ord('q'):
        break

cv2.destroyAllWindows()