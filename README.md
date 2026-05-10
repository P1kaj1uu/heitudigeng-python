# 黑土智耕 - 技术实现方案

## 一、项目概述

### 1.1 项目背景

黑土智耕是一个面向东北小农户的保护性耕作AI全流程服务平台，旨在通过人工智能技术帮助农民科学地进行保护性耕作，提高土壤肥力，增加作物产量，减少水土流失和土地退化。

### 1.2 核心功能模块

| 模块           | 功能描述                                                         |
| -------------- | ---------------------------------------------------------------- |
| 黑土健康AI快诊 | 上传土壤图片，利用YOLOv8分析土壤有机质、耕层深度、健康评分等指标 |
| 保护性耕作日历 | 根据作物类型和地区生成全年农事活动指导                           |
| 病虫草害识别   | 图像识别病虫害种类，提供绿色防控方案                             |
| 智能问答助手   | 自然语言解答保护性耕作相关问题                                   |
| 农技共享社区   | 用户分享经验、互相帮助的社区平台                                 |

### 1.3 技术架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户端 (浏览器)                         │
│              HTML + CSS + JavaScript + Jinja2               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Flask Web 框架                          │
│              路由处理 / 请求分发 / 会话管理                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  SoilAnalyzer │    │   Calendar API  │    │  Community API  │
│   (YOLOv8)    │    │   (农事日历)     │    │   (社区功能)     │
└───────────────┘    └─────────────────┘    └─────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenCV      │    │   本地JSON数据   │    │   内存存储       │
│  图像处理      │    │   / 数据库       │    │   / 数据库       │
└───────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 二、技术选型详解

### 2.1 后端框架 - Flask

**选型理由：**

- 轻量级，学习曲线平缓，适合快速开发
- 原生支持 Jinja2 模板引擎
- 丰富的扩展生态（CORS、SQLAlchemy等）
- 支持 WSGI 协议，可与 Gunicorn 无缝配合

**版本锁定：**

- Flask==3.1.3
- Werkzeug==3.1.8

### 2.2 AI/ML 框架

**YOLOv8 (Ultralytics)：**

- 轻量级目标检测模型（yolov8n.pt 约 6MB）
- 支持图像分类、目标检测、分割等多任务
- Python 原生，API 简洁易用
- 可进行迁移学习，针对黑土场景微调

**PyTorch：**

- YOLOv8 的底层框架
- 支持 GPU 加速推理
- 动态图机制，便于模型调试

### 2.3 图像处理

**OpenCV (cv2)：**

- 读取/保存图像
- 色彩空间转换（BGR、HSV、LAB）
- 图像特征提取（纹理、边缘）
- 图像滤波与增强

**Pillow (PIL)：**

- 图像格式转换
- 缩放、裁剪等预处理

### 2.4 生产服务器

**Gunicorn：**

- Python WSGI HTTP 服务器
- 预fork工作模式，支持多并发
- 配合 Nginx 做反向代理
- 比 Flask 内置服务器稳定可靠

---

## 三、核心模块详细设计

### 3.1 土壤健康分析模块 (SoilAnalyzer)

#### 3.1.1 初始化流程

```python
class SoilAnalyzer:
    def __init__(self, model_path=None):
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        from ultralytics import YOLO
        if self.model_path and os.path.exists(self.model_path):
            self.model = YOLO(self.model_path)
        else:
            self.model = YOLO('yolov8n.pt')
```

**流程说明：**

1. 检查是否指定了自定义模型路径
2. 如果存在，加载自定义黑土专用模型
3. 否则使用预训练 YOLOv8n 作为基础模型
4. 加载失败时降级到传统CV分析方法

#### 3.1.2 图像特征提取

```python
def _extract_image_features(self, image):
    # 转换到HSV色彩空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    features = {
        'mean_brightness': np.mean(image),
        'std_brightness': np.std(image),
        'mean_hue': np.mean(hsv[:, :, 0]),
        'mean_saturation': np.mean(hsv[:, :, 1]),
        'mean_value': np.mean(hsv[:, :, 2]),
        'dark_pixels_ratio': self._count_dark_pixels(image),
        'organic_matter_indicator': self._calculate_organic_matter(image),
        'texture_variance': self._calculate_texture_variance(image),
        'moisture_level': self._estimate_moisture(hsv),
    }
    return features
```

**特征说明：**

| 特征名                   | 计算方法            | 农业意义                |
| ------------------------ | ------------------- | ----------------------- |
| dark_pixels_ratio        | 灰度值<80的像素占比 | 黑土有机质高时颜色偏深  |
| organic_matter_indicator | 100 - 平均L值       | L值越低，有机质可能越高 |
| texture_variance         | 拉普拉斯算子方差    | 纹理复杂表示土层结构好  |
| moisture_level           | 综合HSV的V和S通道   | 估算土壤湿润程度        |

#### 3.1.3 YOLOv8 分析流程

```python
def _analyze_with_yolo(self, image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = self.model(image_rgb, verbose=False)

    detections = []
    for box in results[0].boxes:
        detections.append({
            'class': result.names[int(box.cls[0])],
            'confidence': float(box.conf[0]),
            'bbox': box.xyxy[0].cpu().numpy().tolist()
        })

    return {
        'method': 'yolo',
        'detections': detections,
        'image_features': self._extract_image_features(image)
    }
```

#### 3.1.4 输出结果结构

```json
{
  "report_time": "2024-05-07 14:30",
  "health_score": 78.5,
  "health_level": "良好",
  "organic_matter": 3.82,
  "plowing_depth": 23.5,
  "degradation_risk": "中",
  "erosion_risk": "低",
  "image_analysis": {
    "dark_soil_ratio": 45.2,
    "texture_score": 8.5,
    "moisture_level": 62.3
  },
  "suggestions": [
    {
      "type": "免耕",
      "title": "建议采用保护性耕作",
      "content": "当前耕层较浅，建议免耕或浅耕..."
    }
  ],
  "plain_interpretation": [
    "咱家这地真不错！...",
    "有机质含量约3.82%，挺高的..."
  ]
}
```

### 3.2 农事日历模块

#### 3.2.1 作物日历生成

```python
def generate_calendar(self, location, crop, area):
    if crop == 'corn':
        return self._generate_corn_calendar(location)
    elif crop == 'soybean':
        return self._generate_soybean_calendar(location)
    elif crop == 'rice':
        return self._generate_rice_calendar(location)
```

#### 3.2.2 日历数据结构

```json
{
  "crop": "玉米",
  "location": "吉林省",
  "total_days": 210,
  "phases": [
    {
      "phase": "播前准备",
      "period": "2024年4月上旬",
      "tasks": [
        { "task": "秸秆处理", "method": "秸秆粉碎+全量还田", "detail": "..." }
      ],
      "key_point": "秸秆还田量要均匀，别成堆成堆的"
    }
  ],
  "tips": ["免耕不等于不管，播种质量要保证", "..."]
}
```

### 3.3 病虫害识别模块

#### 3.3.1 检测流程

```python
def detect_pest(self, image_path):
    image = cv2.imread(image_path)
    features = self._extract_image_features(image)
    pests = self._identify_pests_from_image(image, features)
    return pests
```

#### 3.3.2 输出结果

```json
{
  "detections": [
    {
      "name": "玉米螟",
      "type": "虫害",
      "severity": "中",
      "description": "玉米螟是玉米的主要害虫...",
      "symptoms": "叶片出现排孔，茎秆有虫孔...",
      "treatment": "生物防治：释放赤眼蜂..."
    }
  ],
  "warning_level": "注意监控",
  "recommendation": "发现病虫害要及时防治...",
  "climate_alert": "近期气温偏高，虫害可能多发..."
}
```

### 3.4 智能问答模块

#### 3.4.1 问答策略

```python
def chat(self, message):
    message = message.lower()

    if '免耕' in message:
        return self._answer_no_tillage(message)
    elif '秸秆' in message:
        return self._answer_straw_return(message)
    elif '轮作' in message:
        return self._answer_rotation(message)
    elif '播种' in message:
        return self._answer_sowing_time(message)
    elif '肥' in message:
        return self._answer_fertilizer(message)
    elif '虫' in message or '病' in message:
        return self._answer_pest(message)
    else:
        return self._default_answer(message)
```

#### 3.4.2 扩展方向

当前版本使用规则匹配，未来可接入：

- 豆包API（字节跳动）
- 文心一言（百度）

---

## 四、API 接口设计

### 4.1 土壤分析接口

**请求：**

```
POST /api/soil-analyze
Content-Type: multipart/form-data

image: [文件]
location: 地块位置
crop_history: 种植历史
yield_info: 产量情况
land_area: 土地面积
```

**响应：**

```json
{
  "success": true,
  "result": { ... },
  "image_url": "/static/uploads/20240507143000.jpg"
}
```

### 4.2 农事日历接口

**请求：**

```
POST /api/get-calendar
Content-Type: application/json

{"location": "吉林省", "crop": "corn", "area": "10公顷"}
```

**响应：**

```json
{
  "success": true,
  "calendar": { ... }
}
```

### 4.3 病虫害检测接口

**请求：**

```
POST /api/pest-detect
Content-Type: multipart/form-data

image: [文件]
```

**响应：**

```json
{
  "success": true,
  "detection": { ... },
  "image_url": "/static/uploads/20240507143000_pest.jpg"
}
```

### 4.4 智能问答接口

**请求：**

```
POST /api/chat
Content-Type: application/json

{"message": "免耕什么时候播种合适？"}
```

**响应：**

```json
{
  "success": true,
  "response": "免耕播种最佳时间：玉米4月中下旬..."
}
```

---

## 五、前端实现

### 5.1 页面结构

```
templates/
├── index.html      # 首页
├── diagnosis.html  # 黑土健康AI快诊
├── calendar.html   # 农事日历
├── pest.html       # 病虫害识别
└── community.html  # 社区
```

### 5.2 技术选型

- 纯 HTML/CSS/JavaScript（无前端框架）
- Jinja2 模板继承（减少代码重复）
- Fetch API 调用后端接口
- CSS Grid/Flexbox 布局

---

## 六、部署方案

### 6.1 开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python app.py
# 访问 http://localhost:5001
```

### 6.2 生产环境

```bash
# 使用 Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

**gunicorn.conf.py 配置：**

```python
workers = 4
worker_class = "sync"
bind = "0.0.0.0:5001"
timeout = 120
```

### 6.3 宝塔面板部署

详见 [DEPLOY_GUIDE_BAOTA.md](./DEPLOY_GUIDE_BAOTA.md)

---

## 七、模型优化路径

### 7.1 当前状态

- 使用 YOLOv8n 预训练模型
- 土壤分析主要依赖传统CV特征

### 7.2 优化方向

1. **数据采集**
   - 收集东北黑土图像数据集
   - 标注土壤类型、有机质含量等标签

2. **模型微调**
   - 使用东北黑土数据微调 YOLOv8
   - 针对土壤健康分类、缺陷检测进行训练

3. **功能扩展**
   - 土壤养分（N/P/K）预测
   - 病虫害识别模型
   - 产量预估模型

### 7.3 预期效果

| 指标             | 当前 | 优化后 |
| ---------------- | ---- | ------ |
| 有机质识别准确率 | ~70% | ~90%   |
| 耕层深度评估误差 | ±3cm | ±1cm   |
| 病虫害识别种类   | 3种  | 50+种  |

---

## 八、依赖说明

```
Flask==3.1.3              # Web框架
Werkzeug==3.1.8           # WSGI工具库
flask-cors==6.0.2         # 跨域支持
gunicorn==24.0.0          # 生产服务器
ultralytics==8.4.47       # YOLOv8框架
torch==2.11.0             # 深度学习框架
torchvision==0.26.0       # 视觉工具
Pillow==12.2.0            # 图像处理
opencv-python==4.10.0.84  # 计算机视觉
numpy<2,>=1.23.0          # 数值计算
pandas==2.2.0             # 数据分析
requests==2.33.1          # HTTP请求
python-docx==1.2.0        # Word文档处理
```

---

## 九、项目结构

```
heitudigeng/
├── app.py                 # Flask主应用入口
├── soil_analyzer.py       # 土壤分析核心模块
├── requirements.txt       # Python依赖
├── gunicorn.conf.py       # Gunicorn配置
├── heitudigeng.service    # Systemd服务文件
├── deploy_baota.sh        # 宝塔部署脚本
├── templates/             # HTML模板
│   ├── index.html
│   ├── diagnosis.html
│   ├── calendar.html
│   ├── pest.html
│   └── community.html
├── static/                # 静态资源
│   ├── uploads/           # 上传文件
│   ├── css/
│   ├── js/
│   └── images/
├── yolov8n.pt             # YOLOv8模型权重
└── venv/                  # Python虚拟环境
```

---

## 十、未来扩展方向

### 10.1 功能扩展

- [ ] 接入大语言模型（豆包/ [ ] 增加地块管理功能，支持多地块管理
- [ ] 增加产量记录与历史对比
- [ ] 增加天气预警与农事提醒
- [ ] 开发移动端APP

### 10.2 数据存储

- [ ] 从内存存储迁移到数据库（SQLite/PostgreSQL）
- [ ] 用户注册与登录系统
- [ ] 历史分析记录查询

### 10.3 性能优化

- [ ] 模型推理GPU加速
- [ ] 图片上传CDN存储
- [ ] API响应缓存
