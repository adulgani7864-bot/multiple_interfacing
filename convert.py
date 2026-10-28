from ultralytics import YOLO
import torch

model = YOLO("yolov8n.pt")

# THIS is the correct internal model
state_dict = model.model.state_dict()

torch.save(state_dict, "v8_n.pth")

print("Saved clean v8_n.pth")