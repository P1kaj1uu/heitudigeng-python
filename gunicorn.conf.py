# gunicorn.conf.py - 黑土智耕生产环境配置
import multiprocessing

# 绑定地址和端口
bind = "127.0.0.1:5001"

# 工作进程数（建议CPU核心数的2倍，最大不超过8）
workers = multiprocessing.cpu_count() * 2
if workers > 8:
    workers = 8

# 工作模式
worker_class = "sync"

# 每个worker的最大请求数，防止内存泄漏
max_requests = 1000
max_requests_jitter = 50

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名
proc_name = "heitudigeng"

# 超时设置（YOLOv8推理可能需要较长时间）
timeout = 300
keepalive = 5

# 预加载应用（共享内存，减少内存使用）
preload_app = True
