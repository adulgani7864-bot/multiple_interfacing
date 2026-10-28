import os
import cv2

current_dir = os.getcwd()
# Targeting your actual video file from the directory list
video_name = '401_pickitem_s_14_april_2.mp4'

video_path = os.path.join(current_dir, 'ucf24', 'videos', video_name)
img_dir = os.path.join(current_dir, 'ucf24', 'rgb-images', 'BaseketballDunk', 'v_BasketballDunk_g01_c01')
lbl_dir = os.path.join(current_dir, 'ucf24', 'labels', 'BaseketballDunk', 'v_BasketballDunk_g01_c01')

print(f"Checking video file at: {video_path}")
if not os.path.exists(video_path):
    print("❌ ERROR: Video file not found! Double-check file spelling.")
    exit()

os.makedirs(img_dir, exist_ok=True)
os.makedirs(lbl_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("❌ ERROR: OpenCV could not open the video.")
    exit()

print("OpenCV opened video successfully! Extracting frames, please wait...")
count = 1
lines = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: 
        break
    
    img_name = f"{count:05d}.jpg"
    lbl_name = f"{count:05d}.txt"
    
    cv2.imwrite(os.path.join(img_dir, img_name), frame)
    
    # Standard dummy annotations so the script reader validates frames flawlessly
    with open(os.path.join(lbl_dir, lbl_name), 'w') as lf: 
        lf.write('2 0.5 0.5 0.4 0.4\n')
        
    lines.append(f"labels/BaseketballDunk/v_BasketballDunk_g01_c01/{lbl_name}\n")
    count += 1

cap.release()

with open('ucf24/testlist.txt', 'w') as sf: 
    sf.writelines(lines)

print(f"==== SUCCESS: Extracted {count-1} frames from {video_name}! ====")