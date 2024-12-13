# YOLO_SLR

### 使用YOLO进行在各平台上进行手语识别（包括有nvidia和无nvidia的windows，树莓派5+AI Kit）

### 演示视频：

![gif](https://github.com/guoX66/YOLO_SLR/blob/main/assets/demo.gif)

### 模型训练参考：[guoX66/simple_YOLO](https://github.com/guoX66/simple_YOLO)

### 模型转换到树莓派5+AI Kit所需的HEF文件参考：[树莓派5B+AI_KIT基于hailo模块转换重新训练的YOLO模型_hailo8 yolo-CSDN博客](https://blog.csdn.net/2301_76725922/article/details/143829506)



# 一. 环境搭建

## 1、windows

安装python>=3.10.2

使用以下命令查看nvidia服务和cuda版本

```
nvidia-smi
```

在有nvidia服务的设备上，使用以下命令安装pytorch

```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

在没有有nvidia服务的设备上，使用以下命令安装pytorch

```bash
pip3 install torch torchvision torchaudio
```

检查 torch 和 cuda 的版本

```bash
python -c "import torch;print(torch.__version__);print(torch.version.cuda)"
```

安装依赖

```bash
pip install -r requirements
```

## 2、树莓派5

参考[树莓派5B+AI_KIT基于hailo模块转换重新训练的YOLO模型_hailo8 yolo-CSDN博客](https://blog.csdn.net/2301_76725922/article/details/143829506) ，完成四-1部分，git下载hailo-rpi5-examples项目：

```bash
git clone https://github.com/hailo-ai/hailo-rpi5-examples.git
```

并将本项目中的hailo-rpi5-examples/basic_pipelines文件夹复制到git下载的hailo-rpi5-examples目录下，选择覆盖已有文件

将复制后的hailo-rpi5-examples项目复制到本项目YOLO_SLR路径下，再进行hailo环境安装操作：

```bash
cd hailo-rpi5-examples
source setup_env.sh
pip install -r requirements.txt
sudo apt install -y rapidjson-dev
./download_resources.sh
./compile_postprocess.sh
```

# 二. 模型和文件放置

将一中得到的模型和文件按以下方式放置（model1、model2改为对应模型名称）

```
--YOLO_SLR
    --models
        --model1
            --best.onnx
            --best.pt
            --best.hef
            --class.json
        --model2
        ... 
```

要使用openvino进行推理可以用export.py进行模型转换：

```bash
python export.py --model model1
```

将手语视频放置hand_video文件夹下，并命名为对应语义，注意需要为mp4格式，语义最好为英文

```
--YOLO_SLR
    --hand_video
        --0.mp4
        --hello.mp4
        ...
```

# 三、运行手语识别系统

运行以下程序：

```bash
python main.py
```

选择学习后，在下拉框选择对应语义再点击学习即可完成手语视频重复播放

选择翻译以后

对于离线翻译，models输入二中放入model的名称，这里默认为yolov8n；source输入0为摄像头，也可以输入其他视频文件路径

对于在线翻译，IP和port输入远端服务器的IP和端口即可；source则与离线翻译相同

# *四、远程服务端开启

在服务器上按照步骤一中的第1点部署好环境并放置好模型文件后，修改好Cfg.yaml中Server的IP、port、model并保存

运行以下程序：

```
python server.py
```
