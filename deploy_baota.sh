#!/bin/bash
#==========================================
# 黑土智耕 - 宝塔面板自动部署脚本
# 适用于宝塔Linux面板 + Python项目管理器
#==========================================

set -e

# 配置变量
PROJECT_NAME="heitudigeng"
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
VENV_DIR="${PROJECT_DIR}/venv"
PORT=5001

# 检测可用的Python版本
detect_python() {
    for py in python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v $py &> /dev/null; then
            PYTHON_CMD=$py
            PYTHON_VERSION=$($py --version 2>&1 | awk '{print $2}')
            return 0
        fi
    done
    log_error "未找到可用的Python"
    exit 1
}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
}

# 检查宝塔面板
check_baota() {
    log_info "检查宝塔面板环境..."
    if command -v bt &> /dev/null; then
        log_info "检测到宝塔面板 ✓"
    else
        log_warn "未检测到宝塔面板，将进行标准Linux部署"
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."

    # 检测包管理器
    if command -v yum &> /dev/null; then
        # CentOS/RHEL
        log_info "检测到 yum 包管理器（CentOS/RHEL）..."

        # 安装rsync
        yum install -y rsync

        # 安装Python（如果不存在）
        if ! command -v python${PYTHON_VERSION} &> /dev/null; then
            log_info "安装 Python ${PYTHON_VERSION}..."
            yum install -y https://centos${CENTOS_VERSION}.almalinux.org/vault/centos/8.5.2111/extras/x86_64/os/Packages/python3-pip-9.0.3-22.el8.noarch.rpm 2>/dev/null || true
            yum install -y python3 python3-devel python3-pip || true
        fi

        # 安装开发工具和依赖
        yum groupinstall -y "Development Tools" 2>/dev/null || true
        yum install -y gcc gcc-c++ make zlib-devel bzip2-devel openssl-devel \
            sqlite-devel readline-devel gdbm-devel libffi-devel \
            wget curl git libjpeg-turbo-devel freetype-devel rsync 2>/dev/null

        log_info "系统依赖安装完成 ✓"

    elif command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        log_info "检测到 apt 包管理器（Debian/Ubuntu）..."
        apt-get update
        apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-dev \
            python${PYTHON_VERSION}-venv python3-pip \
            build-essential python3-dev zlib1g-dev libjpeg-dev libffi-dev rsync
        log_info "系统依赖安装完成 ✓"
    else
        log_error "未检测到支持的包管理器（yum/apt）"
        exit 1
    fi
}

# 创建项目目录
create_dirs() {
    log_info "创建项目目录..."
    mkdir -p ${PROJECT_DIR}
    mkdir -p ${PROJECT_DIR}/static/uploads
    mkdir -p ${PROJECT_DIR}/logs
}

# 复制项目文件
copy_files() {
    log_info "复制项目文件..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # 确保目标目录存在
    mkdir -p ${PROJECT_DIR}/static
    mkdir -p ${PROJECT_DIR}/templates

    # 复制所有文件（使用rsync如果可用，否则用cp）
    if command -v rsync &> /dev/null; then
        rsync -av --exclude='venv' \
                 --exclude='__pycache__' \
                 --exclude='*.pyc' \
                 --exclude='yolov8n.pt' \
                 --exclude='.claude' \
                 --exclude='.git' \
                 --exclude='deploy_baota.sh' \
                 --exclude='DEPLOY_GUIDE_BAOTA.md' \
                 "${SCRIPT_DIR}/" "${PROJECT_DIR}/"
    else
        # 备用方案：使用cp + find过滤
        find "${SCRIPT_DIR}" -maxdepth 1 -type f ! -name '*.pyc' ! -name 'yolov8n.pt' ! -name 'deploy_baota.sh' ! -name 'DEPLOY_GUIDE_BAOTA.md' -exec cp {} "${PROJECT_DIR}/" \;
        find "${SCRIPT_DIR}/static" -type f -exec cp {} "${PROJECT_DIR}/static/" \; 2>/dev/null || true
        find "${SCRIPT_DIR}/templates" -type f -exec cp {} "${PROJECT_DIR}/templates/" \; 2>/dev/null || true
    fi

    log_info "项目文件复制完成"
}

# 创建Python虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    log_info "使用 Python: ${PYTHON_VERSION}"

    # 检查虚拟环境是否有效
    VENV_PYTHON="${VENV_DIR}/bin/python"
    if [[ -f "${VENV_PYTHON}" ]]; then
        # 检查Python解释器是否可用
        if ${VENV_PYTHON} --version &>/dev/null; then
            log_info "虚拟环境有效，跳过创建"
            return
        else
            log_warn "虚拟环境Python解释器无效，将重新创建"
            rm -rf ${VENV_DIR}
        fi
    else
        log_info "虚拟环境不存在，将创建新环境"
    fi

    ${PYTHON_CMD} -m venv ${VENV_DIR}
    log_info "虚拟环境创建完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."

    # 检查虚拟环境pip
    local PIP="${VENV_DIR}/bin/pip"
    local VENV_PYTHON="${VENV_DIR}/bin/python"

    # 如果虚拟环境无效，重新创建
    if [[ ! -f "${VENV_PYTHON}" ]] || ! ${VENV_PYTHON} --version &>/dev/null; then
        log_warn "虚拟环境无效，重新创建..."
        rm -rf ${VENV_DIR}
        ${PYTHON_CMD} -m venv ${VENV_DIR}
        PIP="${VENV_DIR}/bin/pip"
    fi

    # 升级pip
    log_info "升级pip..."
    ${PIP} install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 先安装PyTorch（国内镜像加速）
    log_info "安装PyTorch（CPU版本）..."
    ${PIP} install torch torchvision --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 安装其他依赖
    log_info "安装其他依赖..."
    ${PIP} install -r ${PROJECT_DIR}/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 下载YOLOv8模型（如果不存在）
    if [[ ! -f "${PROJECT_DIR}/yolov8n.pt" ]]; then
        log_info "下载YOLOv8模型..."
        ${VENV_DIR}/bin/python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
        mv yolov8n.pt ${PROJECT_DIR}/ 2>/dev/null || true
    fi

    log_info "Python依赖安装完成"
}

# 创建Systemd服务
create_service() {
    log_info "创建Systemd服务..."

    cat > /etc/systemd/system/${PROJECT_NAME}.service << EOF
[Unit]
Description=HeituDigiGeng - Black Soil Smart Farming AI Service
After=network.target

[Service]
Type=notify
User=www
Group=www
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin"
Environment="PYTHONPATH=${PROJECT_DIR}"
ExecStart=${VENV_DIR}/bin/gunicorn -c ${PROJECT_DIR}/gunicorn.conf.py app:app
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# 日志
StandardOutput=append:${PROJECT_DIR}/logs/gunicorn.log
StandardError=append:${PROJECT_DIR}/logs/gunicorn_error.log

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载systemd
    systemctl daemon-reload

    log_info "Systemd服务创建完成"
}

# 配置Nginx反向代理
setup_nginx() {
    log_info "配置Nginx反向代理..."

    # 确定Nginx配置目录
    if [[ -d "/etc/nginx/conf.d" ]]; then
        NGINX_CONF_DIR="/etc/nginx/conf.d"
    elif [[ -d "/www/server/nginx/conf/vhost" ]]; then
        NGINX_CONF_DIR="/www/server/nginx/conf/vhost"
    else
        NGINX_CONF_DIR="/etc/nginx/conf.d"
    fi

    mkdir -p ${NGINX_CONF_DIR}
    mkdir -p /www/wwwlogs

    cat > ${NGINX_CONF_DIR}/${PROJECT_NAME}.conf << EOF
server {
    listen 80;
    server_name localhost;

    client_max_body_size 20M;

    # 日志
    access_log /www/wwwlogs/${PROJECT_NAME}_access.log;
    error_log /www/wwwlogs/${PROJECT_NAME}_error.log;

    location /static/ {
        alias ${PROJECT_DIR}/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # 超时设置（YOLOv8推理需要更长时间）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # WebSocket支持（如需）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    log_info "Nginx配置文件已创建: ${NGINX_CONF_DIR}/${PROJECT_NAME}.conf"

    # 测试nginx配置
    if command -v nginx &> /dev/null; then
        nginx -t && systemctl restart nginx
        log_info "Nginx配置完成"
    else
        log_warn "Nginx未安装，请在宝塔面板中配置反向代理"
    fi
}

# 配置SSL（可选）
setup_ssl() {
    log_info "配置SSL证书（可选）..."

    read -p "是否配置SSL证书? (y/n): " setup_ssl_choice
    if [[ "$setup_ssl_choice" == "y" || "$setup_ssl_choice" == "Y" ]]; then
        read -p "请输入域名: " domain
        read -p "证书路径: " cert_path
        read -p "密钥路径: " key_path

        cat > /etc/nginx/conf.d/${PROJECT_NAME}_ssl.conf << EOF
server {
    listen 443 ssl http2;
    server_name ${domain};

    ssl_certificate ${cert_path};
    ssl_certificate_key ${key_path};
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    client_max_body_size 20M;

    location /static/ {
        alias ${PROJECT_DIR}/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

        systemctl restart nginx
        log_info "SSL配置完成"
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."

    # 给予www用户权限
    chown -R www:www ${PROJECT_DIR}

    # 启动gunicorn
    systemctl enable ${PROJECT_NAME}.service
    systemctl start ${PROJECT_NAME}.service
    systemctl status ${PROJECT_NAME}.service --no-pager

    # 检查服务状态
    if systemctl is-active --quiet ${PROJECT_NAME}.service; then
        log_info "服务启动成功 ✓"
    else
        log_error "服务启动失败，请检查日志"
        journalctl -u ${PROJECT_NAME}.service -n 50 --no-pager
        exit 1
    fi
}

# 防火墙设置
setup_firewall() {
    log_info "配置防火墙..."

    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=${PORT}/tcp
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        log_info "防火墙配置完成"
    elif command -v ufw &> /dev/null; then
        ufw allow ${PORT}/tcp
        ufw allow http
        ufw allow https
        log_info "UFW防火墙配置完成"
    fi
}

# 宝塔面板配置
baota_setup() {
    if command -v bt &> /dev/null; then
        log_info "配置宝塔面板..."

        # 添加Python项目
        log_info "请在宝塔面板中完成以下操作："
        log_info "1. 软件商店 -> Python项目管理器 -> 添加项目"
        log_info "2. 项目路径: ${PROJECT_DIR}"
        log_info "3. Python版本: ${PYTHON_VERSION}"
        log_info "4. 框架: 自定义"
        log_info "5. 启动方式: gunicorn"
        log_info "6. 启动文件/命令: ${VENV_DIR}/bin/gunicorn -c ${PROJECT_DIR}/gunicorn.conf.py app:app"
        log_info "7. 端口: ${PORT}"
        log_info ""
        log_info "或使用命令行方式部署（如本脚本所示）"
    fi
}

# 显示部署信息
show_info() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                          ║"
    echo "║          🌾 黑土智耕 - 部署完成                           ║"
    echo "║                                                          ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  项目路径: ${PROJECT_DIR}"
    echo "║  服务端口: ${PORT}"
    echo "║  访问地址: http://你的服务器IP/"
    echo "║                                                          ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  常用命令:                                                ║"
    echo "║  systemctl start ${PROJECT_NAME}   # 启动服务"
    echo "║  systemctl stop ${PROJECT_NAME}    # 停止服务"
    echo "║  systemctl restart ${PROJECT_NAME}  # 重启服务"
    echo "║  systemctl status ${PROJECT_NAME}   # 查看状态"
    echo "║  journalctl -u ${PROJECT_NAME} -f   # 查看日志"
    echo "║                                                          ║"
    echo "║  更新部署:                                                ║"
    echo "║  cd ${PROJECT_DIR} && git pull"
    echo "║  source ${VENV_DIR}/bin/activate"
    echo "║  pip install -r requirements.txt"
    echo "║  systemctl restart ${PROJECT_NAME}"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "  黑土智耕 - 宝塔面板自动部署脚本"
    echo "=========================================="
    echo ""

    check_root
    check_baota
    detect_python
    install_system_deps
    create_dirs
    copy_files
    create_venv
    install_python_deps
    create_service
    setup_nginx
    setup_firewall
    start_service
    baota_setup
    show_info
}

# 运行主函数
main "$@"
