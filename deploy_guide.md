# 黑土智耕 - 宝塔面板部署指南

## 一、宝塔服务器准备

### 1.1 环境要求
- 宝塔面板 7.0+
- Nginx 作为反向代理
- Python 3.8+ (建议 3.10)
- 至少 2GB 内存（YOLOv8模型需要）
- 至少 10GB 磁盘空间

### 1.2 安装Python项目管理器
1. 登录宝塔面板
2. 软件商店 → 搜索 "Python项目管理器" → 安装

### 1.3 创建网站
1. 网站 → 添加站点
2. 填写域名（如：heitudigeng.cn）
3. 选择"纯静态"（稍后配置）
4. 创建完成

---

## 二、项目上传

### 2.1 上传项目文件
在宝塔面板中：
1. 打开网站根目录：`/www/wwwroot/heitudigeng.cn/`
2. 上传本项目所有文件

或者使用FTP/SFTP上传：
```bash
# 在本地执行，上传整个项目
scp -r ./heitudigeng.zip root@你的服务器IP:/www/wwwroot/
```

### 2.2 解压文件
```bash
cd /www/wwwroot/heitudigeng.cn/
unzip heitudigeng.zip
# 确保文件直接在网站根目录下
```

---

## 三、安装依赖

### 3.1 使用Python项目管理器

1. 宝塔面板 → 软件商店 → Python项目管理器
2. 添加项目：
   - 项目类型：Python
   - 项目路径：`/www/wwwroot/heitudigeng.cn/`
   - Python版本：3.10
   - 框架：自定义
   - 启动方式：Gunicorn
   - 启动文件：`app.py`
   - 端口：5001

3. 点击"添加"后，在项目列表中点击"依赖管理"
4. 输入 `gunicorn` → 安装

### 3.2 或者使用终端安装

```bash
# 进入项目目录
cd /www/wwwroot/heitudigeng.cn/

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（国内建议用阿里云镜像）
pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

---

## 四、配置Gunicorn

### 4.1 创建Gunicorn配置文件

在项目目录下创建 `gunicorn.conf.py`：

```python
# gunicorn.conf.py
import multiprocessing

# 绑定地址
bind = "127.0.0.1:5001"

# 工作进程数（建议CPU核心数的2倍，但不超过8）
workers = 2

# 工作模式
worker_class = "sync"

# 每个worker的最大请求数
max_requests = 1000
max_requests_jitter = 50

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名
proc_name = "heitudigeng"

# 超时
timeout = 120
```

### 4.2 测试启动

```bash
cd /www/wwwroot/heitudigeng.cn/
source venv/bin/activate
gunicorn -c gunicorn.conf.py app:app
```

---

## 五、配置Nginx反向代理

### 5.1 修改网站配置

1. 宝塔面板 → 网站 → 找到你的网站 → 设置 → 配置
2. 在server块中添加反向代理：

```nginx
server
{
    listen 80;
    server_name heitudigeng.cn;  # 你的域名

    # Gzip压缩
    gzip on;
    gzip_min_length 1k;
    gzip_comp_level 4;
    gzip_types text/plain application/javascript application/json text/css;

    # 静态文件
    location /static/ {
        alias /www/wwwroot/heitudigeng.cn/static/;
        expires 30d;
    }

    # 上传文件
    location /static/uploads/ {
        alias /www/wwwroot/heitudigeng.cn/static/uploads/;
        expires -1;
    }

    # API反向代理到Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置（YOLOv8推理需要较长时间）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 5.2 保存并重载Nginx

```bash
nginx -t  # 测试配置
nginx -s reload
```

---

## 六、配置SSL证书（可选但建议）

1. 宝塔面板 → 网站 → 你的网站 → 设置 → SSL
2. 选择"Let's Encrypt"免费证书
3. 开启强制HTTPS

---

## 七、开机自启配置

### 7.1 创建systemd服务

```bash
sudo nano /etc/systemd/system/heitudigeng.service
```

写入以下内容：

```ini
[Unit]
Description=HeiTu DiGeng Web Service
After=network.target

[Service]
User=www
Group=www
WorkingDirectory=/www/wwwroot/heitudigeng.cn
Activateenvironment=/www/wwwroot/heitudigeng.cn/venv/bin/activate
ExecStart=/www/wwwroot/heitudigeng.cn/venv/bin/gunicorn -c /www/wwwroot/heitudigeng.cn/gunicorn.conf.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 7.2 启用服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable heitudigeng
sudo systemctl start heitudigeng
sudo systemctl status heitudigeng
```

---

## 八、验证部署

访问你的域名：`http://heitudigeng.cn`

测试API：
```bash
curl http://127.0.0.1:5001/api/community/posts
```

---

## 九、常见问题

### Q1: YOLOv8模型下载失败
```bash
# 手动下载模型
cd /www/wwwroot/heitudigeng.cn/
source venv/bin/activate
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Q2: 内存不足
- 增加swap分区
- 减少gunicorn workers数量
- 使用更小的模型 yolov8n.pt

### Q3: 上传文件权限
```bash
chown -R www:www /www/wwwroot/heitudigeng.cn/
chmod -R 755 /www/wwwroot/heitudigeng.cn/
```

### Q4: 端口被占用
```bash
# 查看端口占用
lsof -i:5001
# 杀掉进程
kill -9 <PID>
```

---

## 十、性能优化建议

1. **模型优化**：使用更小的 `yolov8n.pt` 模型
2. **缓存**：配置Nginx静态文件缓存
3. **图片压缩**：前端压缩后再上传
4. **异步处理**：使用Celery处理YOLOv8推理（可选）

---

## 十一、目录结构（部署后）

```
/www/wwwroot/heitudigeng.cn/
├── app.py                 # Flask主应用
├── soil_analyzer.py       # YOLOv8分析模块
├── gunicorn.conf.py       # Gunicorn配置
├── requirements.txt       # Python依赖
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── uploads/          # 上传文件目录
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── diagnosis.html
│   ├── calendar.html
│   ├── pest.html
│   └── community.html
└── venv/                 # Python虚拟环境
```

---

## 快速命令汇总

```bash
# 重启服务
sudo systemctl restart heitudigeng

# 查看日志
sudo journalctl -u heitudigeng -f

# 查看端口
lsof -i:5001
```
