"""
黑土智耕 - 东北小农户保护性耕作AI全流程服务网站
Flask主应用入口
"""
import os
import base64
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 导入自定义模块
from soil_analyzer import SoilAnalyzer

app = Flask(__name__)
app.secret_key = 'heitu-zhigeng-secret-key-2024'
CORS(app)

# 配置
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 初始化土壤分析器
soil_analyzer = SoilAnalyzer()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/diagnosis')
def diagnosis():
    """黑土健康AI快诊页面"""
    return render_template('diagnosis.html')


@app.route('/calendar')
def calendar():
    """保护性耕作全周期AI农艺管家页面"""
    return render_template('calendar.html')


@app.route('/pest')
def pest():
    """病虫草害AI精准识别与绿色防控页面"""
    return render_template('pest.html')


@app.route('/community')
def community():
    """新农人互助与农技共享社区页面"""
    return render_template('community.html')


@app.route('/api/soil-analyze', methods=['POST'])
def analyze_soil():
    """
    黑土健康AI快诊API
    接收土壤图片和地块信息，返回分析结果
    """
    try:
        # 检查是否有图片
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '请上传土壤图片'})

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': '请选择图片'})

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '支持的格式: JPG, PNG, WEBP'})

        # 获取表单数据
        location = request.form.get('location', '')
        crop_history = request.form.get('crop_history', '')
        yield_info = request.form.get('yield_info', '')
        land_area = request.form.get('land_area', '')

        # 保存上传的图片
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 使用YOLOv8进行土壤分析
        analysis_result = soil_analyzer.analyze(
            image_path=filepath,
            location=location,
            crop_history=crop_history,
            yield_info=yield_info,
            land_area=land_area
        )

        return jsonify({
            'success': True,
            'result': analysis_result,
            'image_url': f'/static/uploads/{filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/soil-analyze-base64', methods=['POST'])
def analyze_soil_base64():
    """
    黑土健康AI快诊API (Base64图片)
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': '请提供图片数据'})

        # 解码Base64图片
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        image = io.BytesIO(image_bytes)

        # 获取表单数据
        location = data.get('location', '')
        crop_history = data.get('crop_history', '')
        yield_info = data.get('yield_info', '')
        land_area = data.get('land_area', '')

        # 保存图片
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_upload.png")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)

        # 使用YOLOv8进行土壤分析
        analysis_result = soil_analyzer.analyze(
            image_path=filepath,
            location=location,
            crop_history=crop_history,
            yield_info=yield_info,
            land_area=land_area
        )

        return jsonify({
            'success': True,
            'result': analysis_result,
            'image_url': f'/static/uploads/{filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    AI问答接口
    """
    try:
        data = request.get_json()
        message = data.get('message', '')

        if not message:
            return jsonify({'success': False, 'error': '请输入问题'})

        # 简单的对话逻辑（可扩展接入豆包API）
        response = soil_analyzer.chat(message)

        return jsonify({
            'success': True,
            'response': response
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get-calendar', methods=['POST'])
def get_calendar():
    """
    获取保护性耕作日历
    """
    try:
        data = request.get_json()
        location = data.get('location', '')
        crop = data.get('crop', 'corn')
        area = data.get('area', '')

        # 生成日历
        calendar_data = soil_analyzer.generate_calendar(location, crop, area)

        return jsonify({
            'success': True,
            'calendar': calendar_data
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/pest-detect', methods=['POST'])
def detect_pest():
    """
    病虫害识别API
    """
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '请上传图片'})

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': '请选择图片'})

        # 保存图片
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_pest_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 检测病虫害
        detection = soil_analyzer.detect_pest(filepath)

        return jsonify({
            'success': True,
            'detection': detection,
            'image_url': f'/static/uploads/{filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/community/posts', methods=['GET'])
def get_posts():
    """
    获取社区帖子
    """
    # 模拟数据
    posts = [
        {
            'id': 1,
            'author': '老王（玉米种植大户）',
            'avatar': '/static/images/avatar1.png',
            'content': '今年用免耕播种机，省了3遍整地钱，秋天测产还增产了5%，秸秆还田真的管用！',
            'time': '2小时前',
            'likes': 23,
            'comments': 5
        },
        {
            'id': 2,
            'author': '农技员小李',
            'avatar': '/static/images/avatar2.png',
            'content': '提醒大家：今年雨水大，玉米螟可能要重发，发现叶子有虫眼赶紧打生物制剂，别等！',
            'time': '5小时前',
            'likes': 45,
            'comments': 12
        },
        {
            'id': 3,
            'author': '返乡新农人小张',
            'avatar': '/static/images/avatar3.png',
            'content': '刚学种地第一年，用这个网站学会了秸秆覆盖，出苗率比邻居老把式还高！',
            'time': '1天前',
            'likes': 67,
            'comments': 18
        }
    ]
    return jsonify({'success': True, 'posts': posts})


@app.route('/api/community/post', methods=['POST'])
def create_post():
    """
    发布帖子
    """
    try:
        data = request.get_json()
        content = data.get('content', '')

        if not content:
            return jsonify({'success': False, 'error': '内容不能为空'})

        return jsonify({
            'success': True,
            'post': {
                'id': int(datetime.now().timestamp()),
                'author': '匿名用户',
                'content': content,
                'time': '刚刚',
                'likes': 0,
                'comments': 0
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║     🌾 黑土智耕 - 东北小农户保护性耕作AI全流程服务     ║
    ║                                                       ║
    ║     开发模式: python app.py                           ║
    ║     生产模式: gunicorn -c gunicorn.conf.py app:app   ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    # 开发模式直接运行
    app.run(debug=True, host='0.0.0.0', port=5001)
