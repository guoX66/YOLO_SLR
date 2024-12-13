import json
import os
import time
import cv2
from multiprocessing import Process, Queue
import socket
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm
from utils import read_cfg

size = 320


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


def web_send(iq, ADDRESS, wq, eq, sq):
    tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 连接远程ip
    tcpClient.connect(ADDRESS)
    tcpClient.send(b"img")

    while True:
        if not iq.empty():
            cv_image = iq.get()
            cv_image = cv2.resize(cv_image, [size, size], interpolation=cv2.INTER_LINEAR)

            # 压缩图像
            img_encode = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 99])[1]
            # 转换为字节流
            bytedata = img_encode.tobytes()
            # # 标志数据，包括待发送的字节流长度等数据，用‘,’隔开
            flag_data = 'flag,'.encode() + (str(len(bytedata))).encode() + ",".encode() + " ".encode()
            tcpClient.send(flag_data)
            data = tcpClient.recv(1024)
            if ("start" == data.decode()):
                # 服务端已经收到标志数据，开始发送图像字节流数据
                # 接收服务端的应答
                tcpClient.send(bytedata)
            data = tcpClient.recv(1024)
            if "end" == data.decode():
                sq.put(1)
            break

    while True:
        if not eq.empty():
            tcpClient.send(b'finish')
            tcpClient.shutdown(socket.SHUT_RDWR)
            tcpClient.close()
            break

        # 读取图像
        if not iq.empty():

            cv_image = iq.get()
            cv_image = cv2.resize(cv_image, [256, 256], interpolation=cv2.INTER_LINEAR)

            # 压缩图像
            img_encode = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 99])[1]
            # 转换为字节流
            bytedata = img_encode.tobytes()
            # # 标志数据，包括待发送的字节流长度等数据，用‘,’隔开
            flag_data = 'flag,'.encode() + (str(len(bytedata))).encode() + ",".encode() + " ".encode()
            tcpClient.send(flag_data)
            data = tcpClient.recv(1024)
            start = time.perf_counter()
            if ("start" == data.decode()):
                # 服务端已经收到标志数据，开始发送图像字节流数据
                # 接收服务端的应答
                tcpClient.send(bytedata)
            data = tcpClient.recv(1024)
            if "end" == data.decode():
                wt = (time.perf_counter() - start) * 1000
                if not wq.full():
                    wq.put(wt)
                # print("\r延时：{:.1f}ms".format(wt), end='')


def web_get(oq, ADDRESS, eq, sq):
    tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 连接远程ip
    tcpClient.connect(ADDRESS)
    tcpClient.send(b"res")
    sq.put(1)
    while True:
        if not eq.empty():
            break

        data = tcpClient.recv(1024)
        if data:
            data = data.decode('utf-8')
            try:
                res = json.loads(data)
            except:
                #print(data)
                res = ['None', 1]

            if not oq.full():
                oq.put(res)


def web_video_start(camera, iq, oq, wq, eq, sq):
    cap = cv2.VideoCapture(camera)
    ret, img = cap.read()
    iq.put(img)
    while True:
        if sq.full():
            break
    result_list = [('None', 0)]
    wt_list = [0]
    s_time = time.perf_counter()
    s1_time = time.perf_counter()
    while True:
        ret, img = cap.read()
        if img is None:
            cap.release()
            cv2.destroyAllWindows()
            eq.put(1)
            break
        if not iq.full():
            iq.put(img)
        if not wq.empty():
            wt = wq.get()
            e1_time = time.perf_counter()
            if e1_time - s1_time > 0.3:
                wt_list.append(wt)
                s1_time = e1_time

        if not oq.empty():
            res, conf = oq.get()
            e_time = time.perf_counter()
            # if e_time - s_time > 0.3:
            if res != 'None' and e_time - s_time > 0.1:
                s_time = e_time
                result_list.append((res, conf))

        last_word, last_conf = result_list[-1]
        frame = cv2.resize(img, (640, 480))
        Wt = str(round(wt_list[-1], 1)) + 'ms'
        frame = cv2.copyMakeBorder(frame, 80, 80, 0, 0, cv2.BORDER_CONSTANT)
        frame = cv2ImgAddText(frame, f"Delay: {Wt}", (500, 20), (0, 255, 0), 20)
        frame = cv2ImgAddText(frame, f"Detections: {last_word}", (10, 20), (0, 255, 0), 20)
        frame = cv2ImgAddText(frame, f"conf: {last_conf}", (10, 40), (0, 255, 0), 20)

        cv2.imshow('demo', frame)
        cv2.waitKey(1)
        if cv2.getWindowProperty('demo', cv2.WND_PROP_VISIBLE) < 1:
            eq.put(1)
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Done!")
    while not iq.empty():
        iq.get()
    while not oq.empty():
        oq.get()


def main(camera, IP, port):
    iq = Queue(10)  # 图片队列
    oq = Queue(10)  # 结果队列
    wq = Queue(10)  # 延迟队列
    eq = Queue(1)  # 结束标志队列
    sq = Queue(2)  # 开始标志队列
    ADDRESS = (IP, port)
    # 创建一个套接字

    p1 = Process(target=web_send,
                 args=(iq, ADDRESS, wq, eq, sq))
    p2 = Process(target=web_get,
                 args=(oq, ADDRESS, eq, sq))
    p1.daemon = True
    p1.start()
    p2.daemon = True
    p2.start()

    web_video_start(camera, iq, oq, wq, eq, sq)
    p1.join()
    p2.terminate()


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    off_Cfg, on_Cfg, Cfg = read_cfg(base_dir)
    main(on_Cfg['source'], on_Cfg['IP'], on_Cfg['port'])
