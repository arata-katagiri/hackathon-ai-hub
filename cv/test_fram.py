import cv2
import matplotlib.pyplot as plt

url = "https://webcam.elcat.kg/Naryn/index.m3u8"
cap = cv2.VideoCapture(url)
ret, frame = cap.read()
cap.release()

if ret:
    cv2.imwrite("naryn_frame.jpg", frame)
    print(f"Frame saved: {frame.shape}")
    plt.figure(figsize=(14, 8))
    plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.show()
else:
    print("Failed")