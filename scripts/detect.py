import torch
import cv2
import os
import sys
import numpy as np
from PIL import Image

sys.path.append(os.getcwd())
from cus_datasets.ucf.transforms import UCF_transform
from model.TSN.YOWOv3 import build_yowov3

def detect(config):
    device = torch.device("cpu")
    print("Using Device: CPU")

    model = build_yowov3(config)
    
    weight_path = config.get('weight') or config.get('weights') or config.get('resume')
    if weight_path is not None:
        print(f"Loading weights from: {weight_path}")
        checkpoint = torch.load(weight_path, map_location=device)
        if isinstance(checkpoint, dict) and 'model' in checkpoint:
            model.load_state_dict(checkpoint['model'])
        else:
            model.load_state_dict(checkpoint)
    else:
        print("No weight path found in config, proceeding with pretrained backbones.")
    
    model = model.to(device)
    model.eval()

    transform = UCF_transform(img_size=config['img_size'])
    
    # -------------------------------------------------------------
    # CHANGE THIS: Put a path to a real video file here, or use 0 for Webcam!
    # For example: video_source = "C:/Users/BK/Desktop/test_video.mp4"
    # -------------------------------------------------------------
    video_source = 0  # 0 activates your laptop webcam instantly for testing!
    
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Error: Could not open video source {video_source}")
        return

    print("Starting continuous live inference... Press 'q' on the video window to stop.")
    
    clip = []
    while True:
        ret, orig_image = cap.read()
        if not ret:
            print("Video ended or failed to fetch frame.")
            break
            
        rgb_image = cv2.cvtColor(orig_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_image)
        
        clip.append(pil_img)
        if len(clip) < config['clip_length']:
            # Show a loading screen while buffer builds up
            cv2.putText(orig_image, "Building frame buffer...", (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.imshow('YOWOv3 Spatio-Temporal Action Detection', orig_image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
            
        if len(clip) > config['clip_length']:
            clip.pop(0)

        dummy_targets = np.zeros((1, 5))
        transformed_clip, _ = transform(clip, dummy_targets)
        input_tensor = transformed_clip.unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(input_tensor)
            
        # Display the live feed
        cv2.putText(orig_image, "YOWOv3 Active - Processing Stream", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('YOWOv3 Spatio-Temporal Action Detection', orig_image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Inference session closed cleanly.")