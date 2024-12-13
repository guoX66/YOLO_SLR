import argparse
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from utils import read_cfg
from ultralytics import YOLO
parser = argparse.ArgumentParser()
parser.add_argument('--size', type=int, default=640)
parser.add_argument('--conf', type=float, default=0.2)
parser.add_argument('--device', type=str, default='CUDA GPU', choices=('CUDA GPU', 'openvino'))

args = parser.parse_args()


# cv2.namedWindow('frame', cv2.WINDOW_FREERATIO)

def cv2ImgAddText(img, text, position, textColor, textSize=20):
    if (isinstance(img, np.ndarray)):  # 判断是否OpenCV图片类型
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # 创建一个可以在给定图像上绘图的对象
    draw = ImageDraw.Draw(img)
    # 字体的格式
    fontStyle = ImageFont.truetype(
        "simsun.ttc", textSize, encoding="utf-8")
    # 绘制文本
    draw.text(position, text, textColor, font=fontStyle)
    # 转换回OpenCV格式
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


off_Cfg, on_Cfg, Cfg = read_cfg(os.getcwd())
model_type = off_Cfg['model']
source = off_Cfg['source']
cap = cv2.VideoCapture(source)
print(cap.isOpened())

if args.device == 'openvino':
    model_path = f'models/{model_type}/best_openvino_model'
else:
    model_path = f'models/{model_type}/best.pt'

model = YOLO(model_path, task='detect')

result_list = [('None', 0)]

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Done!")
        break
    # 检测
    results = model(frame, conf=args.conf, verbose=False, imgsz=args.size, task='detect')
    lc = []
    result = results[0]
    boxes = result.boxes  # Boxes object for bbox outputs
    for j in range(boxes.shape[0]):
        label = result.names[int(boxes.cls[j])]
        conf = float(boxes.conf[j])
        lc.append((label, conf))
    if len(lc) > 0:
        max_conf_piece = max(lc, key=lambda x: x[1])
        max_conf_label = max_conf_piece[0]
        max_conf = max_conf_piece[1]
    else:
        max_conf_label = 'None'
        max_conf = 0

    if max_conf_label != 'None':
        result_list.append((max_conf_label, max_conf))

    frame = cv2.resize(frame, (640, 480))
    frame = cv2.copyMakeBorder(frame, 80, 80, 0, 0, cv2.BORDER_CONSTANT)
    frame = cv2ImgAddText(frame, f"Detections: {result_list[-1][0]}", (10, 20), (255, 0, 0), 20)
    frame = cv2ImgAddText(frame, f"conf: {result_list[-1][1]}", (10, 40), (255, 0, 0), 20)

    # img = results[0].plot()

    cv2.imshow("frame", frame)
    cv2.waitKey(1)

    if cv2.getWindowProperty('frame', cv2.WND_PROP_VISIBLE) < 1:
        break

    # 释放摄像头
print("Done!")
cap.release()
