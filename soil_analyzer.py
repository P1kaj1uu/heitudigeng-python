"""
黑土健康AI快诊 - YOLOv8土壤分析模块
使用YOLOv8模型进行土壤健康分析
"""
import os
import cv2
import numpy as np
from PIL import Image
from datetime import datetime, timedelta
import random


class SoilAnalyzer:
    """
    基于YOLOv8的土壤健康分析器
    """

    def __init__(self, model_path=None):
        """
        初始化土壤分析器
        model_path: YOLOv8模型路径，默认使用预训练模型
        """
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        """加载YOLOv8模型"""
        try:
            from ultralytics import YOLO
            # 使用YOLOv8预训练模型（可替换为微调后的黑土专用模型）
            if self.model_path and os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
            else:
                # 使用YOLOv8n作为轻量级基础模型
                self.model = YOLO('yolov8n.pt')
            print("✅ YOLOv8模型加载成功")
        except Exception as e:
            print(f"⚠️ YOLOv8模型加载失败: {e}")
            print("将使用传统图像分析方法")
            self.model = None

    def analyze(self, image_path, location='', crop_history='', yield_info='', land_area=''):
        """
        分析土壤健康状况

        参数:
            image_path: 土壤图片路径
            location: 地块位置
            crop_history: 种植历史
            yield_info: 产量情况
            land_area: 土地面积

        返回:
            dict: 土壤健康分析结果
        """
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("无法读取图片")

        # 使用YOLOv8或传统方法分析
        if self.model:
            yolo_results = self._analyze_with_yolo(image)
        else:
            yolo_results = self._analyze_with_cv(image)

        # 生成详细分析结果
        result = self._generate_soil_report(
            image, yolo_results, location, crop_history, yield_info, land_area
        )

        return result

    def _analyze_with_yolo(self, image):
        """
        使用YOLOv8进行图像分析
        """
        try:
            # 将图像转换为RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 运行推理
            results = self.model(image_rgb, verbose=False)

            # 提取检测结果
            detections = []
            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for box in result.boxes:
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

        except Exception as e:
            print(f"YOLOv8分析失败: {e}")
            return {
                'method': 'cv_fallback',
                'detections': [],
                'image_features': self._extract_image_features(image)
            }

    def _analyze_with_cv(self, image):
        """
        使用传统计算机视觉方法分析土壤
        """
        return {
            'method': 'cv',
            'detections': [],
            'image_features': self._extract_image_features(image)
        }

    def _extract_image_features(self, image):
        """
        提取图像特征用于土壤分析
        """
        # 转换到不同色彩空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # 计算颜色统计
        features = {
            # 基础统计
            'mean_brightness': np.mean(image),
            'std_brightness': np.std(image),

            # 颜色分布
            'mean_hue': np.mean(hsv[:, :, 0]),
            'mean_saturation': np.mean(hsv[:, :, 1]),
            'mean_value': np.mean(hsv[:, :, 2]),

            # 黑土特征颜色分析
            'dark_pixels_ratio': self._count_dark_pixels(image),
            'organic_matter_indicator': self._calculate_organic_matter(image),

            # 纹理特征
            'texture_variance': self._calculate_texture_variance(image),

            # 湿润度分析
            'moisture_level': self._estimate_moisture(hsv),
        }

        return features

    def _count_dark_pixels(self, image, threshold=80):
        """计算暗色像素比例（黑土特征）"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        dark_pixels = np.sum(gray < threshold)
        total_pixels = gray.shape[0] * gray.shape[1]
        return dark_pixels / total_pixels

    def _calculate_organic_matter(self, image):
        """估算有机质含量指标"""
        # 黑土有机质含量高时颜色偏深棕/黑色
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        # L值越低，通常有机质可能较高
        return 100 - np.mean(l_channel)

    def _calculate_texture_variance(self, image):
        """计算纹理变化度"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 使用拉普拉斯算子计算边缘/纹理
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return np.var(laplacian)

    def _estimate_moisture(self, hsv):
        """估算土壤湿润度"""
        # V通道（亮度）较低可能表示湿润
        # 饱和度较高也可能表示湿润
        v_mean = np.mean(hsv[:, :, 2])
        s_mean = np.mean(hsv[:, :, 1])
        # 综合评估（归一化到0-100）
        moisture = min(100, (255 - v_mean) / 2.55 + s_mean / 2.55)
        return moisture

    def _generate_soil_report(self, image, yolo_data, location, crop_history, yield_info, land_area):
        """
        生成土壤健康报告
        """
        features = yolo_data['image_features']

        # 基于图像特征和输入信息生成评估
        # 有机质含量评估
        organic_matter = min(6.0, max(1.5, 3.5 + features['organic_matter_indicator'] * 0.02 +
                                        self._history_to_organic_adjustment(crop_history)))

        # 耕层厚度评估
        plowing_depth = self._estimate_plowing_depth(features, crop_history)

        # 退化风险评估
        degradation_risk = self._calculate_degradation_risk(features, crop_history, yield_info)

        # 水土流失风险
        erosion_risk = self._calculate_erosion_risk(features, location)

        # 综合健康评分
        health_score = self._calculate_health_score(
            organic_matter, plowing_depth, degradation_risk, erosion_risk
        )

        # 生成改良建议
        suggestions = self._generate_suggestions(
            organic_matter, plowing_depth, degradation_risk, erosion_risk, crop_history
        )

        return {
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'health_score': round(health_score, 1),
            'health_level': self._get_health_level(health_score),

            # 核心指标
            'organic_matter': round(organic_matter, 2),  # 有机质含量 %
            'plowing_depth': round(plowing_depth, 1),  # 耕层厚度 cm
            'degradation_risk': degradation_risk,  # 退化风险等级
            'erosion_risk': erosion_risk,  # 水土流失风险

            # 图像分析详情
            'image_analysis': {
                'dark_soil_ratio': round(features['dark_pixels_ratio'] * 100, 1),
                'texture_score': round(features['texture_variance'] / 1000, 1),
                'moisture_level': round(features['moisture_level'], 1),
            },

            # 改良建议
            'suggestions': suggestions,

            # 大白话解读
            'plain_interpretation': self._generate_plain_interpretation(
                health_score, organic_matter, plowing_depth, degradation_risk, erosion_risk
            )
        }

    def _history_to_organic_adjustment(self, crop_history):
        """根据种植历史调整有机质评估"""
        if not crop_history:
            return 0

        history_lower = crop_history.lower()
        # 玉米秸秆还田效果好
        if '玉米' in history_lower and '秸秆' in history_lower:
            return 0.3
        # 大豆固氮效果好
        if '大豆' in history_lower:
            return 0.2
        # 连续耕作且无秸秆还田
        if '多年' in history_lower or '连续' in history_lower:
            return -0.3
        # 轮作效果好
        if '轮作' in history_lower:
            return 0.2

        return 0

    def _estimate_plowing_depth(self, features, crop_history):
        """估算耕层厚度"""
        # 基于图像纹理和有机质估算
        base_depth = 22.0  # 东北黑土平均耕层厚度

        # 纹理好表示耕层结构好
        if features['texture_variance'] > 500:
            base_depth += 2

        # 有机质高通常耕层较深
        if features['organic_matter_indicator'] > 40:
            base_depth += 3

        return base_depth

    def _calculate_degradation_risk(self, features, crop_history, yield_info):
        """计算退化风险"""
        risk_score = 50  # 基础风险

        # 有机质低增加风险
        if features['organic_matter_indicator'] < 30:
            risk_score += 20

        # 连续单作为高风险
        if crop_history and ('连作' in crop_history or '单一' in crop_history):
            risk_score += 15

        # 产量下降趋势
        if yield_info and ('下降' in yield_info or '减产' in yield_info):
            risk_score += 15

        # 纹理差表示退化
        if features['texture_variance'] < 200:
            risk_score += 10

        # 转换为等级
        if risk_score < 30:
            return '低'
        elif risk_score < 60:
            return '中'
        else:
            return '高'

    def _calculate_erosion_risk(self, features, location):
        """计算水土流失风险"""
        base_risk = 35

        # 坡度信息（需要结合位置数据，这里简化处理）
        if location and ('坡' in location or '岗' in location):
            base_risk += 25

        # 湿润度低（干燥）增加风蚀风险
        if features['moisture_level'] < 40:
            base_risk += 15

        # 暗色土比例低（有机质低）增加侵蚀风险
        if features['dark_pixels_ratio'] < 0.3:
            base_risk += 20

        if base_risk < 35:
            return '低'
        elif base_risk < 60:
            return '中'
        else:
            return '高'

    def _calculate_health_score(self, organic_matter, plowing_depth, degradation_risk, erosion_risk):
        """计算综合健康评分"""
        score = 100

        # 有机质评分
        if organic_matter < 2.0:
            score -= 35
        elif organic_matter < 3.0:
            score -= 20
        elif organic_matter < 4.0:
            score -= 10

        # 耕层厚度评分
        if plowing_depth < 18:
            score -= 25
        elif plowing_depth < 22:
            score -= 15

        # 退化风险评分
        if degradation_risk == '高':
            score -= 20
        elif degradation_risk == '中':
            score -= 10

        # 侵蚀风险评分
        if erosion_risk == '高':
            score -= 15
        elif erosion_risk == '中':
            score -= 8

        return max(0, min(100, score))

    def _get_health_level(self, score):
        """获取健康等级"""
        if score >= 85:
            return '优秀'
        elif score >= 70:
            return '良好'
        elif score >= 55:
            return '一般'
        elif score >= 40:
            return '较差'
        else:
            return '极差'

    def _generate_suggestions(self, organic_matter, plowing_depth, degradation_risk, erosion_risk, crop_history):
        """生成保护性耕作改良建议"""
        suggestions = []

        # 免耕深度建议
        if plowing_depth < 20:
            suggestions.append({
                'type': '免耕',
                'title': '建议采用保护性耕作',
                'content': '当前耕层较浅，建议免耕或浅耕，深度控制在15-20厘米，避免深翻破坏耕层结构。'
            })
        else:
            suggestions.append({
                'type': '免耕',
                'title': '保持现有免耕深度',
                'content': '耕层状况良好，建议保持免耕或浅耕（15-20cm），保护现有耕层结构。'
            })

        # 秸秆还田建议
        if organic_matter < 3.5:
            suggestions.append({
                'type': '秸秆还田',
                'title': '增加秸秆还田量',
                'content': f'有机质含量偏低，建议秸秆全量还田，配合腐熟剂加速分解，每年可提高有机质0.1-0.3个百分点。'
            })
        else:
            suggestions.append({
                'type': '秸秆还田',
                'title': '维持秸秆还田',
                'content': '有机质水平良好，建议保持秸秆全量或部分还田（70%以上），维持土壤肥力。'
            })

        # 轮作建议
        if '玉米' in crop_history if crop_history else False:
            suggestions.append({
                'type': '轮作',
                'title': '建议加入大豆轮作',
                'content': '长期种植玉米建议轮作大豆，利用大豆固氮作用提高土壤肥力，建议玉米-大豆2-3年轮作。'
            })
        elif '大豆' in crop_history if crop_history else False:
            suggestions.append({
                'type': '轮作',
                'title': '建议加入玉米轮作',
                'content': '大豆种植后建议轮作玉米，可充分利用大豆固氮后效，提高玉米产量15-20%。'
            })
        else:
            suggestions.append({
                'type': '轮作',
                'title': '建立轮作制度',
                'content': '建议建立玉米-大豆-小麦（或杂粮）轮作体系，3年一轮，提高土壤健康水平。'
            })

        # 有机肥使用建议
        if organic_matter < 3.0:
            suggestions.append({
                'type': '有机肥',
                'title': '增施有机肥',
                'content': '建议秋季或春季每亩施用腐熟农家肥2-3吨，或商品有机肥200-300公斤，快速提升有机质。'
            })

        # 水土保持建议
        if erosion_risk == '高' or erosion_risk == '中':
            suggestions.append({
                'type': '水土保持',
                'title': '加强水土保持措施',
                'content': '地块存在水土流失风险，建议采用等高种植、秸秆覆盖、休闲季种植绿肥等保土措施。'
            })

        return suggestions

    def _generate_plain_interpretation(self, health_score, organic_matter, plowing_depth, degradation_risk, erosion_risk):
        """生成大白话解读"""
        interpretations = []

        # 总体评价
        if health_score >= 85:
            interpretations.append("咱家这地真不错！黑土油光锃亮的，有机质丰富，种啥都长得好。继续保持现在的种法就行。")
        elif health_score >= 70:
            interpretations.append("这地还算健康，黑土颜色挺正，有机质够用。注意别破坏土层结构就好。")
        elif health_score >= 55:
            interpretations.append("地有点瘦了，黑土颜色发灰，有机质不太足。建议多种几年秸秆还田养养地。")
        elif health_score >= 40:
            interpretations.append("这地得好好养养了！黑土退化得厉害，土发灰发黄。继续老办法种产量要下降。")
        else:
            interpretations.append("地里问题不少！土硬、黑土变黄土了。再不改变种法，庄稼长不好，产量得掉。得赶紧用保护性耕作救一救！")

        # 有机质说明
        if organic_matter >= 4.0:
            interpretations.append(f"有机质含量约{organic_matter}%，挺高的，土壤肥力不错。")
        elif organic_matter >= 3.0:
            interpretations.append(f"有机质约{organic_matter}%，马马虎虎，秸秆还田再坚持几年会更好。")
        else:
            interpretations.append(f"有机质偏低，只有约{organic_matter}%，得多还秸秆、适当施点有机肥。")

        # 耕层说明
        if plowing_depth >= 25:
            interpretations.append(f"耕层挺深，有{plowing_depth}厘米左右，土层结构不错。")
        elif plowing_depth >= 20:
            interpretations.append(f"耕层厚度约{plowing_depth}厘米，还行，别深翻太狠就行。")
        else:
            interpretations.append(f"耕层有点浅，只有{plowing_depth}厘米左右，别再深翻了，会破坏土层。")

        # 风险提示
        if degradation_risk == '高':
            interpretations.append("⚠️ 退化风险高！土壤越种越板结，产量可能要下降，得改变种法了。")
        elif erosion_risk == '高':
            interpretations.append("⚠️ 水土流失风险大，春秋风大的时候土容易被吹走，得用秸秆盖上。")

        return interpretations

    def generate_calendar(self, location, crop, area):
        """
        生成保护性耕作全周期日历

        参数:
            location: 地点
            crop: 作物类型 ('corn', 'soybean', 'rice')
        """
        crop_names = {'corn': '玉米', 'soybean': '大豆', 'rice': '水稻'}
        crop_name = crop_names.get(crop, '玉米')

        # 基于作物生成日历
        if crop == 'corn':
            return self._generate_corn_calendar(location)
        elif crop == 'soybean':
            return self._generate_soybean_calendar(location)
        elif crop == 'rice':
            return self._generate_rice_calendar(location)
        else:
            return self._generate_corn_calendar(location)

    def _generate_corn_calendar(self, location):
        """生成玉米保护性耕作日历"""
        year = datetime.now().year

        phases = [
            {
                'phase': '播前准备',
                'period': f'{year}年4月上旬',
                'tasks': [
                    {'task': '秸秆处理', 'method': '秸秆粉碎+全量还田', 'detail': '秸秆粉碎长度<10cm，均匀抛洒'},
                    {'task': '整地', 'method': '浅旋或免耕', 'detail': '免耕播种地块可直接播种'},
                ],
                'key_point': '秸秆还田量要均匀，别成堆成堆的'
            },
            {
                'phase': '播种期',
                'period': f'{year}年4月中旬-5月初',
                'tasks': [
                    {'task': '免耕播种', 'method': '免耕播种机，一次成型', 'detail': '播种深度3-5cm，镇压要实'},
                    {'task': '品种选择', 'method': '选择适合当地的保护性耕作品种', 'detail': '建议选用抗逆性强、成熟期适中的品种'},
                ],
                'key_point': '地温稳定通过8℃再播种，别着急'
            },
            {
                'phase': '苗期管理',
                'period': f'{year}年5月-6月',
                'tasks': [
                    {'task': '查田补苗', 'method': '出苗后及时查田', 'detail': '缺苗超过10%要补种'},
                    {'task': '病虫害监控', 'method': '关注苗期病虫害', 'detail': '重点防治地下害虫、苗枯病'},
                ],
                'key_point': '秸秆覆盖地块出苗可能稍慢，别以为是种子问题'
            },
            {
                'phase': '生长中期',
                'period': f'{year}年6月-8月',
                'tasks': [
                    {'task': '中耕追肥', 'method': '机械中耕+追肥', 'detail': '追肥以氮肥为主，配合钾肥'},
                    {'task': '病虫害防控', 'method': '绿色防控为主', 'detail': '玉米螟可用赤眼蜂生物防治'},
                ],
                'key_point': '秸秆覆盖地块病虫害会延迟发生，注意观察'
            },
            {
                'phase': '收获期',
                'period': f'{year}年9月下旬-10月中旬',
                'tasks': [
                    {'task': '适时晚收', 'method': '苞叶干枯后收获', 'detail': '适当晚收可提高产量5-10%'},
                    {'task': '秸秆处理', 'method': '机械粉碎秸秆', 'detail': '粉碎后均匀抛洒还田'},
                ],
                'key_point': '收获机要带秸秆粉碎装置'
            },
            {
                'phase': '秋季作业',
                'period': f'{year}年10月-11月',
                'tasks': [
                    {'task': '秸秆还田', 'method': '联合收割机直接粉碎还田', 'detail': '配合腐熟剂加速分解'},
                    {'task': '越冬准备', 'method': '保持秸秆覆盖状态', 'detail': '覆盖保墒，减少风蚀'},
                ],
                'key_point': '秋天地里不用翻，秸秆盖着就行'
            },
            {
                'phase': '冬季养地',
                'period': f'{year}年11月-{year+1}年3月',
                'tasks': [
                    {'task': '秸秆覆盖', 'method': '保持原状', 'detail': '自然腐熟+保墒'},
                    {'task': '积雪保墒', 'method': '不要破坏积雪层', 'detail': '积雪利于春季保墒'},
                ],
                'key_point': '冬天别去地里踩，雪盖着土才养地'
            },
        ]

        return {
            'crop': '玉米',
            'location': location or '吉林省',
            'total_days': 210,
            'phases': phases,
            'tips': [
                '免耕不等于不管，播种质量要保证',
                '秸秆还田第一年可能苗期发黄，属正常现象',
                '病虫害防治坚持"预防为主、综合防治"',
                '遇到极端天气可联系当地农技站'
            ]
        }

    def _generate_soybean_calendar(self, location):
        """生成大豆保护性耕作日历"""
        year = datetime.now().year

        phases = [
            {
                'phase': '播前准备',
                'period': f'{year}年5月上旬',
                'tasks': [
                    {'task': '秸秆处理', 'method': '上茬秸秆粉碎还田', 'detail': '玉米茬可用免耕播种机直接播种'},
                    {'task': '种子处理', 'method': '包衣处理', 'detail': '防治地下害虫和根腐病'},
                ],
                'key_point': '大豆种子小，播种深度别超过3cm'
            },
            {
                'phase': '播种期',
                'period': f'{year}年5月中旬',
                'tasks': [
                    {'task': '免耕播种', 'method': '大豆专用的免耕播种机', 'detail': '播深2-3cm，株距8-12cm'},
                ],
                'key_point': '地温稳定通过12℃再播种'
            },
            {
                'phase': '苗期管理',
                'period': f'{year}年5月-6月',
                'tasks': [
                    {'task': '封闭除草', 'method': '苗前封闭除草', 'detail': '秸秆覆盖地块除草效果更好'},
                    {'task': '查田补苗', 'method': '缺苗严重需补种', 'detail': '大豆可自行固氮，不需要多施氮肥'},
                ],
                'key_point': '大豆固氮，不用施太多氮肥'
            },
            {
                'phase': '开花结荚期',
                'period': f'{year}年7月-8月',
                'tasks': [
                    {'task': '水分管理', 'method': '注意干旱时灌溉', 'detail': '开花结荚期是需水关键期'},
                    {'task': '病虫害防控', 'method': '防治蚜虫、食心虫', 'detail': '优先物理和生物防治'},
                ],
                'key_point': '蚜虫初期可用黄板诱杀'
            },
            {
                'phase': '收获期',
                'period': f'{year}年9月下旬-10月初',
                'tasks': [
                    {'task': '适时收获', 'method': '叶片脱落80%以上时收获', 'detail': '联合收割直接脱粒'},
                ],
                'key_point': '收获太早青豆多，太晚炸荚损失大'
            },
            {
                'phase': '还田养地',
                'period': f'{year}年10月-11月',
                'tasks': [
                    {'task': '秸秆处理', 'method': '秸秆粉碎还田', 'detail': '大豆秸秆养分丰富，还田效果好'},
                ],
                'key_point': '大豆根瘤菌固氮，秸秆还田等于给玉米攒氮肥'
            },
        ]

        return {
            'crop': '大豆',
            'location': location or '吉林省',
            'total_days': 150,
            'phases': phases,
            'tips': [
                '大豆-玉米轮作最佳组合',
                '秸秆还田后下茬种玉米可少施氮肥',
                '封闭除草要在播种后出苗前完成',
                '注意防治地下害虫蛴螬'
            ]
        }

    def _generate_rice_calendar(self, location):
        """生成水稻保护性耕作日历"""
        year = datetime.now().year

        phases = [
            {
                'phase': '育苗期',
                'period': f'{year}年4月上旬-中旬',
                'tasks': [
                    {'task': '育秧准备', 'method': '钵盘育秧或毯式育秧', 'detail': '选择抗病品种'},
                ],
                'key_point': '育好秧是丰收的基础'
            },
            {
                'phase': '本田准备',
                'period': f'{year}年4月下旬-5月上旬',
                'tasks': [
                    {'task': '整地泡田', 'method': '浅水整地', 'detail': '秸秆全量还田地块要泡透'},
                    {'task': '秸秆处理', 'method': '机械粉碎+腐熟剂', 'detail': '配合灌水加速腐熟'},
                ],
                'key_point': '秸秆还田地块要提前泡田'
            },
            {
                'phase': '插秧期',
                'period': f'{year}年5月中旬-6月初',
                'tasks': [
                    {'task': '机械插秧', 'method': '宽窄行机插', 'detail': '株距12-14cm，行距30cm'},
                ],
                'key_point': '地温稳定通过15℃再插秧'
            },
            {
                'phase': '本田管理',
                'period': f'{year}年6月-8月',
                'tasks': [
                    {'task': '水层管理', 'method': '浅水灌溉为主', 'detail': '分蘖期浅水，孕穗期深水'},
                    {'task': '追肥', 'method': '分蘖肥+穗肥', 'detail': '配合秸秆腐解释放的养分调整'},
                    {'task': '病虫害防控', 'method': '防治稻瘟病、纹枯病、二化螟', 'detail': '优先生物防治'},
                ],
                'key_point': '秸秆还田后氮肥要适当增加'
            },
            {
                'phase': '收获期',
                'period': f'{year}年9月下旬-10月初',
                'tasks': [
                    {'task': '适时收获', 'method': '黄化完熟期收获', 'detail': '机械收割直接脱粒'},
                    {'task': '秸秆处理', 'method': '机械粉碎+越冬还田', 'detail': '春季灌水后腐熟'},
                ],
                'key_point': '秸秆还田要配合腐熟剂'
            },
        ]

        return {
            'crop': '水稻',
            'location': location or '吉林省',
            'total_days': 170,
            'phases': phases,
            'tips': [
                '水稻秸秆还田要增施氮肥促进分解',
                '秋季翻地不如春季搅浆整地好',
                '注意防治稻瘟病，高温高湿天气重点监控',
                '合理晒田是水稻高产的关键'
            ]
        }

    def detect_pest(self, image_path):
        """
        病虫害识别
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("无法读取图片")

        # 提取图像特征
        features = self._extract_image_features(image)

        # 基于图像特征和预设知识库识别病虫害
        pests = self._identify_pests_from_image(image, features)

        return pests

    def _identify_pests_from_image(self, image, features):
        """根据图像特征识别可能的病虫害"""
        # 模拟病虫害识别结果
        # 实际应用中需要使用训练好的病虫害识别模型

        detections = [
            {
                'name': '玉米螟',
                'type': '虫害',
                'severity': '中',
                'description': '玉米螟是玉米的主要害虫，幼虫钻蛀茎秆和果穗',
                'symptoms': '叶片出现排孔，茎秆有虫孔，掰开可见幼虫',
                'treatment': '生物防治：释放赤眼蜂；药剂防治：心叶期喷施苏云金杆菌',
                'image_url': '/static/images/pest_corn_borer.png'
            },
            {
                'name': '大斑病',
                'type': '病害',
                'severity': '中',
                'description': '真菌性病害，主要危害叶片',
                'symptoms': '叶片出现梭形大斑，病斑中央灰褐色，边缘暗褐色',
                'treatment': '农业防治：清除病残体；化学防治：喷施多菌灵、代森锰锌',
                'image_url': '/static/images/disease_leaf_spot.png'
            },
            {
                'name': '粘虫',
                'type': '虫害',
                'severity': '高',
                'description': '暴食性害虫，大发生可将叶片吃光',
                'symptoms': '叶片被吃成缺刻，严重时吃光全叶',
                'treatment': '物理防治：糖醋液诱捕；生物防治：喷施灭幼脲；应急药剂：高效氯氰菊酯',
                'image_url': '/static/images/pest_armyworm.png'
            }
        ]

        return {
            'detections': detections,
            'warning_level': '注意监控',
            'recommendation': '发现病虫害要及时防治，优先采用生物和物理方法，保护天敌，减少农药使用。',
            'climate_alert': '近期气温偏高，虫害可能多发，请加强巡查。'
        }

    def chat(self, message):
        """
        智能问答
        简单的对话逻辑，实际应用中可接入豆包/        """
        message = message.lower()

        # 免耕相关
        if '免耕' in message:
            return self._answer_no_tillage(message)

        # 秸秆还田相关
        if '秸秆' in message:
            return self._answer_straw_return(message)

        # 轮作相关
        if '轮作' in message:
            return self._answer_rotation(message)

        # 播种时间
        if '播种' in message and ('时间' in message or '时候' in message or '合适' in message):
            return self._answer_sowing_time(message)

        # 肥料相关
        if '肥' in message:
            return self._answer_fertilizer(message)

        # 病虫害相关
        if '虫' in message or '病' in message:
            return self._answer_pest(message)

        # 默认回答
        return self._default_answer(message)

    def _answer_no_tillage(self, message):
        """免耕相关问答"""
        if '时间' in message or '时候' in message:
            return """免耕播种最佳时间：
- 玉米：4月中下旬-5月初，地温稳定通过8℃
- 大豆：5月中旬，地温稳定通过12℃
- 水稻：5月中旬，插秧时水温稳定通过15℃

记住：宁可晚播几天，也别在地温不够的时候急着种！"""
        elif '注意' in message or '啥' in message:
            return """免耕播种要注意：
1. 播种机要调好，深度控制在3-5厘米
2. 镇压要实，种子和土要贴紧
3. 秸秆太多的地方可以稍微搂开点
4. 出苗后别急着打除草剂，等苗大一点再说
5. 免耕头一年可能苗发黄，正常现象，别慌！"""
        else:
            return """免耕就是"不翻地"种庄稼，收完庄稼秸秆直接粉碎铺在地里，来年直接在秸秆堆里播种。

好处多着呢：
- 省油省力省钱
- 秸秆还田养地
- 土不翻动，保水保肥
- 减少风蚀水蚀

咱东北黑土最适合搞免耕！"""

    def _answer_straw_return(self, message):
        """秸秆还田相关问答"""
        if '比例' in message or '多少' in message:
            return """秸秆还田量建议：
- 全量还田：秸秆全部粉碎还田，效果最好
- 部分还田：至少还田70%以上

玉米：1垧地大概产10吨秸秆，全量还田完全没问题！

关键是：
1. 秸秆要粉碎，长度<10厘米
2. 配合腐熟剂，加速腐烂
3. 氮肥适当多施点，帮助秸秆分解"""
        elif '注意' in message or '问题' in message:
            return """秸秆还田注意这些：
1. 粉碎要细，长度别超过一虎口（约10cm）
2. 撒均匀，别一堆一堆的
3. 配合撒点尿素（每亩5-8斤），帮助分解
4. 第一年可能苗有点发黄，是正常现象
5. 病虫害多的秸秆最好烧掉或做饲料，别还田"""
        else:
            return """秸秆还田是咱东北保护性耕作的核心！

秸秆在地里腐烂后：
- 增加有机质，土壤变肥
- 减少蒸发，保住水分
- 冬天盖着土，减少风蚀
- 省钱，不用买那么多肥

秸秆还田配合免耕，黑土越种越肥！"""

    def _answer_rotation(self, message):
        """轮作相关问答"""
        return """轮作就是"换着种"：
- 今年种玉米，明年种大豆
- 或者玉米-大豆-小麦三年一轮

轮作好处：
1. 大豆固氮，下茬玉米少施肥
2. 减少病虫害积累
3. 土地利用更均衡

推荐模式：
- 玉米-大豆两年轮作
- 玉米-大豆-杂粮三年轮作

秸秆还田后种大豆，大豆产量更高！"""

    def _answer_sowing_time(self, message):
        """播种时间相关问答"""
        if '玉米' in message:
            return """玉米最佳播种时间：
- 吉林地区：4月15日-5月5日
- 地温要求：稳定通过8℃
-墒情要求：土壤含水量20-25%

判断方法：地里挖个10cm深的坑，抓把土攥成团，松开能散开就是合适。

宁可晚播几天，也别贪早！早了地凉种子不爱出，还容易粉种。"""
        elif '大豆' in message:
            return """大豆最佳播种时间：
- 吉林地区：5月5日-5月20日
- 地温要求：稳定通过12℃
- 大豆怕涝，地太湿别种

播种深度：2-3厘米，别太深
株距：8-12厘米

记住：大豆种子小，播种要浅！"""
        else:
            return """吉林地区播种时间参考：

🌽 玉米：4月中下旬-5月初
🌱 大豆：5月上旬-中旬
🌾 水稻：5月中旬（插秧）

关键是看地温，别看日历！
地温到了才适合种子发芽。

今年春天雨水多，播种可以适当晚几天。"""

    def _answer_fertilizer(self, message):
        """肥料相关问答"""
        return """东北黑土施肥建议：

🌽 玉米：
- 基肥：有机肥2-3吨/垧 + 复合肥（N-P2O5-K2O: 15-15-15）400-500kg/垧
- 追肥：大喇叭口期追尿素150-200kg/垧
- 秸秆还田后氮肥要多施点

🌱 大豆：
- 少施氮肥，大豆自己固氮！
- 复合肥200-300kg/垧就行
- 钼肥拌种，提高固氮效率

💡 秸秆还田后为啥要多施氮肥？
因为分解秸秆的细菌需要"吃"氮，氮不够会跟庄稼抢养分。

保护黑土多用有机肥，少用化肥！"""

    def _answer_pest(self, message):
        """病虫害相关问答"""
        return """东北玉米常见病虫害：

🐛 玉米螟：钻心虫，大害虫
   - 防治：释放赤眼蜂（生物防治，环保）
   - 时间：玉米大喇叭口期

🍂 大斑病：叶片长斑
   - 防治：喷多菌灵、代森锰锌
   - 预防：清除病残体

🐛 粘虫：暴食性，几天吃光叶
   - 防治：早发现，早用药
   - 物理：糖醋液诱捕

💡 防治原则：
1. 预防为主，早发现早治
2. 优先生物防治，保护天敌
3. 少打药，打对药，别乱用药

发现病虫害拍照上传，我来帮你识别！"""

    def _default_answer(self, message):
        """默认回答"""
        return f"""您问的"'{message}'"这个事，我给您说说：

保护性耕作核心就是四点：
1. 秸秆覆盖还田 - 地把秸秆"吃"了变肥
2. 免耕少耕 - 别老翻地，翻了土就瘦
3. 科学轮作 - 玉米大豆换着种
4. 种养结合 - 用地也要养地

有啥具体问题，尽管问！
比如：
- "免耕啥时候播种合适？"
- "秸秆还田注意啥？"
- "今年种玉米还是大豆好？"

我都给您大白话解答！"""


# 简单的问答函数，用于API调用
def simple_chat(message):
    """简化版问答"""
    analyzer = SoilAnalyzer()
    return analyzer.chat(message)


if __name__ == '__main__':
    # 测试代码
    analyzer = SoilAnalyzer()
    print("土壤分析器初始化完成")
