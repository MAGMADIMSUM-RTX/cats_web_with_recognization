#!/usr/bin/env python3
"""
全自动AI猫咪识别服务器
运行在端口 2255，接收图片文件，使用AI模型进行识别和匹配。
"""

import os
import uuid
import logging
import threading
import queue
import time
import sys

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# --- 引入我们之前编写的AI识别核心代码 ---
import cv2
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from ultralytics import YOLO
import numpy as np
import sqlite3
import pickle
from scipy.spatial.distance import cosine

# --- 1. 配置区域 ---

# 服务器配置
UPLOAD_FOLDER = 'temp_recognition'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
SERVER_PORT = 2255

# AI模型与数据库配置
DATABASE_FILE = '../cats_recognition.db'
YOLO_MODEL_PATH = '../models/best.pt'
SIMILARITY_THRESHOLD = 0.80  # 关键阈值：高于此值才确认为已知猫咪

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- 2. AI模型加载与核心功能 ---
# (这部分代码直接从 recognize_cat.py 移植过来)

def load_ai_models():
    """一次性加载所有AI模型到内存中。"""
    print("🤖 正在加载 AI 模型到内存...")
    try:
        yolo = YOLO(YOLO_MODEL_PATH)
        print("   - YOLOv8 模型加载成功。")
    except Exception as e:
        print(f"   - 错误: 无法加载YOLOv8模型 at {YOLO_MODEL_PATH}. Error: {e}")
        return None, None

    extractor = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    extractor.classifier[1] = torch.nn.Identity()
    extractor.eval()
    print("   - MobileNetV2 特征提取器加载成功。")

    return yolo, extractor


preprocess_transform = transforms.Compose([
    transforms.ToPILImage(), transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def extract_feature_from_image(image_path, yolo_model, feature_extractor):
    """从图片中提取特征向量。"""
    img = cv2.imread(image_path)
    if img is None: return None
    results = yolo_model.predict(source=img, verbose=False, conf=0.5)
    best_box = None;
    max_conf = 0
    if results[0].boxes:
        for box in results[0].boxes:
            if box.conf > max_conf: max_conf = box.conf; best_box = box.xyxy[0].cpu().numpy().astype(int)
    if best_box is not None:
        x1, y1, x2, y2 = best_box
        cropped_face = img[y1:y2, x1:x2]
        if cropped_face.size == 0: return None
        rgb_image = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
        input_tensor = preprocess_transform(rgb_image)
        input_batch = input_tensor.unsqueeze(0)
        with torch.no_grad():
            feature_vector = feature_extractor(input_batch)
        return feature_vector.squeeze().cpu().numpy()
    return None


def deserialize_data(data_blob):
    return pickle.loads(data_blob)


def find_most_similar_cat(query_vector, db_path):
    """在数据库中搜索最相似的猫。"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, feature_vectors FROM cats")
        all_cats = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        return None, -1.0, f"数据库错误: {e}"
    if not all_cats: return None, -1.0, "数据库为空"
    best_match_name = None;
    highest_similarity = -1.0
    for name, vectors_blob in all_cats:
        known_vectors = deserialize_data(vectors_blob)
        similarities = [1 - cosine(query_vector, vec) for vec in known_vectors]
        max_sim_for_this_cat = np.max(similarities)
        if max_sim_for_this_cat > highest_similarity:
            highest_similarity = max_sim_for_this_cat
            best_match_name = name
    return best_match_name, highest_similarity, None


# --- 3. Flask服务器与工作线程 ---

app = Flask(__name__)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 识别队列和结果字典
recognition_queue = queue.Queue()
recognition_results = {}

# 全局加载AI模型
YOLO_MODEL, FEATURE_EXTRACTOR = load_ai_models()
if not YOLO_MODEL:
    print("关键AI模型加载失败，服务器无法启动。")
    sys.exit(1)


def ai_recognition_worker():
    """
    全自动AI识别工作线程。
    它会从队列中获取任务，调用AI模型进行识别，并将结果存入字典。
    """
    print("✅ AI识别工作线程已启动，等待处理任务...")
    while True:
        try:
            task_id, image_path, filename = recognition_queue.get()
            if task_id is None: break  # 退出信号

            logger.info(f"开始处理任务 {task_id} ({filename})...")

            # 1. 提取查询向量
            query_vector = extract_feature_from_image(image_path, YOLO_MODEL, FEATURE_EXTRACTOR)

            if query_vector is None:
                logger.warning(f"任务 {task_id}: 未能在图片 {filename} 中检测到猫脸。")
                recognition_results[task_id] = {'error': 'face_not_detected'}
                continue

            # 2. 在数据库中匹配
            cat_name, similarity, db_error = find_most_similar_cat(query_vector, DATABASE_FILE)

            if db_error:
                logger.error(f"任务 {task_id}: {db_error}")
                recognition_results[task_id] = {'error': db_error}
                continue

            # 3. 根据置信度给出不同的提示词
            # 这是我们实现新需求的核心逻辑
            if similarity >= SIMILARITY_THRESHOLD:
                status = "matched"
                message = f"识别成功！这很可能是 {cat_name}。"
                if similarity > 0.85:
                    message += " (置信度: 非常高)"
                elif similarity > 0.75:
                    message += " (置信度: 较高)"
                else:
                    message += " (置信度: 可信)"
                result_name = cat_name
            else:
                status = "unmatched"
                message = f"未在数据库中找到足够相似的猫。最接近的是 {cat_name} (相似度 {similarity:.2f})，但未达到阈值 {SIMILARITY_THRESHOLD}。"
                result_name = "待定 (Unknown)"  # 低于阈值，显示为待定

            # 4. 将包含丰富信息的结果存入字典
            recognition_results[task_id] = {
                'status': status,
                'cat_name': result_name,
                'similarity': float(f"{similarity:.4f}"),
                'message': message,
                'matched_cat': cat_name if similarity >= SIMILARITY_THRESHOLD else None
            }

        except Exception as e:
            logger.error(f"AI工作线程发生严重错误: {e}", exc_info=True)
            # 确保即使出错也能给前端一个响应
            if 'task_id' in locals() and task_id not in recognition_results:
                recognition_results[task_id] = {'error': 'worker_exception'}
        finally:
            # 清理临时文件
            if 'image_path' in locals() and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError as e:
                    logger.error(f"无法删除临时文件 {image_path}: {e}")
            if 'task_id' in locals():
                recognition_queue.task_done()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/recognize', methods=['POST'])
def recognize_api():
    """识别猫咪的API端点"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        file = request.files['image']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file format or no file selected'}), 400

        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{os.path.splitext(filename)[1].lower()}")
        file.save(temp_path)
        logger.info(f"收到识别请求: {filename}，已保存至 {temp_path}")

        task_id = str(uuid.uuid4())
        recognition_queue.put((task_id, temp_path, filename))

        # 等待识别结果（最多30秒）
        timeout_seconds = 30
        for _ in range(timeout_seconds * 10):
            if task_id in recognition_results:
                result = recognition_results.pop(task_id)

                # 检查worker是否出错
                if result.get('error'):
                    error_msg = result['error']
                    logger.error(f"识别失败: {error_msg}")
                    return jsonify({'success': False, 'error': error_msg}), 500

                logger.info(f"返回识别结果: {result}")
                return jsonify({'success': True, 'data': result})

            time.sleep(0.1)

        logger.error("识别超时")
        return jsonify({'success': False, 'error': 'timeout'}), 408

    except Exception as e:
        logger.error(f"API /recognize 发生错误: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'server_error'}), 500


# --- 其他辅助API端点 (健康检查等) ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'AI Cat Recognition Server'})


@app.route('/status', methods=['GET'])
def status():
    return jsonify({'queue_size': recognition_queue.qsize(), 'threshold': SIMILARITY_THRESHOLD})


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 启动全自动AI猫咪识别服务器...")
    print(f"   服务器地址: http://localhost:{SERVER_PORT}")
    print(f"   API端点: POST /recognize")
    print(f"   识别阈值 (Threshold): {SIMILARITY_THRESHOLD}")
    print("=" * 60)

    # 启动AI识别工作线程
    recognition_thread = threading.Thread(target=ai_recognition_worker, daemon=True)
    recognition_thread.start()

    try:
        # 推荐在生产环境中使用 waitress 或 gunicorn 代替 app.run
        app.run(host='0.0.0.0', port=SERVER_PORT)
    except KeyboardInterrupt:
        print("\n👋 服务器正在关闭...")
        recognition_queue.put((None, None, None))  # 发送退出信号
        sys.exit(0)