# -*- coding: UTF-8 -*-
import argparse
import json
import os
import socket
import time
from multiprocessing import Process, Queue

from ultralytics import YOLO

from utils import read_cfg
import cv2
import numpy as np
import torch

parser = argparse.ArgumentParser()
parser.add_argument('--iq_num', type=int, default=100)
parser.add_argument('--size', type=int, default=640)
parser.add_argument('--conf', type=float, default=0.2)
parser.add_argument('--device', type=str, default='CUDA GPU', choices=('CUDA GPU', 'openvino'))
args = parser.parse_args()


def ser_Multiprocess(client_socket1, iq, model):
    while True:
        if not iq.empty():
            frame = iq.get()
            results = model(frame, conf=args.conf, verbose=False, imgsz=args.size)
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
            res = [max_conf_label, max_conf]
            print(res)
            result = json.dumps(res)
            client_socket1.send(bytes(result.encode('utf-8')))


def get_img(client_socket2, iq):
    while True:
        # 接收标志数据
        # try:
        data = client_socket2.recv(1024)
        if data.decode() == 'finish':
            client_socket2.close()
            break
        if data:
            # 通知客户端“已收到标志数据，可以发送图像数据”
            client_socket2.send(b"start")
            # 处理标志数据

            flag = data.decode().split(",")

            # 图像字节流数据的总长度
            if flag[0] != 'flag':
                continue
            total = int(flag[1])
            # 接收到的数据计数
            cnt = 0
            # 存放接收到的数据
            img_bytes = b""
            while cnt < total:
                # 当接收到的数据少于数据总长度时，则循环接收图像数据，直到接收完毕
                data = client_socket2.recv(256000)
                img_bytes += data
                cnt += len(data)
            # 通知客户端“已经接收完毕，可以开始下一帧图像的传输”
            client_socket2.send(b"end")
            # 解析接收到的字节流数据，并显示图像
            img = np.asarray(bytearray(img_bytes), dtype="uint8")
            img = cv2.imdecode(img, cv2.IMREAD_COLOR)
            if not iq.full():
                iq.put(img)
        # except:
        #     client_socket2.close()
        #     break


def main(iq_num):
    off_Cfg, on_Cfg, Cfg = read_cfg(os.getcwd())
    HOST = Cfg['server']['IP']
    PORT = Cfg['server']['port']
    model_type = Cfg['server']['model']
    if args.device == 'openvino':
        model_path = f'models/{model_type}/best_openvino_model'
    else:
        model_path = f'models/{model_type}/best.pt'
    model = YOLO(model_path, task='detect')

    iq = Queue(iq_num)
    ADDRESS = (HOST, PORT)
    # 创建一个套接字
    tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    # 绑定本地ip
    tcpServer.bind(ADDRESS)
    # 开始监听
    tcpServer.listen(5)
    print(f'端口{ADDRESS} 正在等待连接')
    while True:
        num = 0
        while num != 2:
            client_socket, client_address1 = tcpServer.accept()
            mode = client_socket.recv(1024)
            if mode.decode() == 'img':
                print(f"图片通道连接{client_address1}成功！")
                p1 = Process(target=get_img,
                             args=(client_socket, iq,))
                num += 1
            elif mode.decode() == 'res':
                print(f"结果通道连接{client_address1}成功！")
                p2 = Process(target=ser_Multiprocess,
                             args=(
                                 client_socket, iq, model))
                num += 1

        p1.start()
        # p2.daemon = True
        p2.start()
        p1.join()
        # p2.join()
        p2.terminate()
        print('本次连接结束')


if __name__ == '__main__':
    main(args.iq_num)
