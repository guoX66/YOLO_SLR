import argparse

from ultralytics import YOLO

parser = argparse.ArgumentParser()
parser.add_argument('--model', type=str, default='yolov8n')
args = parser.parse_args()
# Load a models
model = YOLO(f"models/{args.model}/best.pt")  # load a custom trained models

# Export the models
model.export(format="openvino")
