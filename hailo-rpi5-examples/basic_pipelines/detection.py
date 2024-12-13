import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
from hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from detection_pipeline import GStreamerDetectionApp
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example

    def new_function(self):  # New function example
        return "The meaning of life is: "


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


# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Parse the detections
    detection_count = 0
    lb = []
    result_list = [('None', 0)]
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        lb.append((label, confidence, bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()))
    if user_data.use_frame:
        # Note: using imshow will not work here, as the callback function is not running in the main thread
        # Let's print the detection count to the frame
        # cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # # Example of how to use the new_variable and new_function from the user_data
        # # Let's print the new_variable and the result of the new_function to the frame
        # cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
        #             1, (0, 255, 0), 2)
        # # Convert the frame to BGR
        # for i in lb:
        #     label, xmin, ymin, xmax, ymax = i
        #     x_min, x_max, y_min, y_max = int(xmin * frame.shape[1]), int(xmax * frame.shape[1]), int(
        #         ymin * frame.shape[0]), int(ymax * frame.shape[0])
        #
        #     cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
        #     cv2.putText(frame, label, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
        if len(lb) > 0:
            max_conf_piece = max(lb, key=lambda x: x[1])
            max_conf_label = max_conf_piece[0]
            max_conf = max_conf_piece[1]
        else:
            max_conf_label = 'None'
            max_conf = 0

        if max_conf_label != 'None':
            result_list.append((max_conf_label, max_conf))
        print(result_list)

        frame = cv2.resize(frame, (640, 480))
        frame = cv2.copyMakeBorder(frame, 80, 80, 0, 0, cv2.BORDER_CONSTANT)
        frame = cv2ImgAddText(frame, f"Detections: {result_list[-1][0]}", (10, 20), (0, 255, 0), 20)
        frame = cv2ImgAddText(frame, f"conf: {result_list[-1][1]}", (10, 40), (0, 255, 0), 20)

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        user_data.set_frame(frame)

    # print(string_to_print)
    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
