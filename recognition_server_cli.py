#!/usr/bin/env python3
"""
命令行猫咪识别服务器
运行在端口 2255，接收图片文件并通过命令行手动输入猫咪名字
"""

from flask import Flask, request, jsonify
import os
import uuid
import logging
from werkzeug.utils import secure_filename
import threading
import queue
import time
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = 'temp_recognition'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# 确保临时目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 识别队列和结果字典
recognition_queue = queue.Queue()
recognition_results = {}

def get_file_info(image_path):
    """获取文件信息"""
    try:
        file_size = os.path.getsize(image_path)
        file_size_mb = file_size / (1024 * 1024)
        return f"{file_size_mb:.2f} MB"
    except:
        return "未知大小"

def interactive_recognition_worker():
    """交互式识别工作线程"""
    print("\n" + "="*60)
    print("🤖 命令行猫咪识别服务已启动！")
    print("📝 当有图片需要识别时，请在此处输入猫咪名字...")
    print("💡 可用命令:")
    print("   - 输入猫咪名字: 完成识别")
    print("   - 输入 'skip': 跳过当前图片")
    print("   - 输入 'quit': 退出服务")
    print("="*60)
    
    while True:
        try:
            # 从队列获取识别任务
            task = recognition_queue.get(timeout=1)
            if task is None:  # 退出信号
                break
                
            task_id, image_path, filename = task
            
            # 显示图片信息
            file_size = get_file_info(image_path)
            print(f"\n" + "="*60)
            print(f"📷 新图片待识别")
            print(f"   文件名: {filename}")
            print(f"   完整路径: {image_path}")
            print(f"   文件大小: {file_size}")
            print("="*60)
            
            # 获取用户输入
            while True:
                try:
                    user_input = input("\n🐱 请输入猫咪名字 (或 'skip' 跳过, 'quit' 退出): ").strip()
                    
                    if user_input.lower() == 'quit':
                        print("👋 识别服务即将退出...")
                        recognition_results[task_id] = None
                        # 清理临时文件
                        try:
                            os.remove(image_path)
                        except:
                            pass
                        recognition_queue.put(None)  # 发送退出信号给其他任务
                        return
                    elif user_input.lower() == 'skip':
                        print("⏭️  跳过当前图片")
                        recognition_results[task_id] = None
                        break
                    elif user_input:
                        print(f"✅ 识别结果: {user_input}")
                        recognition_results[task_id] = user_input
                        break
                    else:
                        print("❌ 请输入有效的猫咪名字")
                except KeyboardInterrupt:
                    print("\n👋 识别服务即将退出...")
                    recognition_results[task_id] = None
                    # 清理临时文件
                    try:
                        os.remove(image_path)
                    except:
                        pass
                    return
                except EOFError:
                    print("\n👋 识别服务即将退出...")
                    recognition_results[task_id] = None
                    # 清理临时文件
                    try:
                        os.remove(image_path)
                    except:
                        pass
                    return
            
            # 清理临时文件
            try:
                os.remove(image_path)
            except:
                pass
                
            recognition_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Recognition worker error: {e}")
            continue

def allowed_file(filename):
    """检查文件是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/recognize', methods=['POST'])
def recognize():
    """识别猫咪的API端点"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No image file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file format'
            }), 400
        
        # 保存文件到临时目录
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1].lower()
        temp_filename = f"{file_id}{file_ext}"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        
        file.save(temp_path)
        logger.info(f"收到识别请求: {filename}")
        
        # 添加到识别队列
        task_id = str(uuid.uuid4())
        recognition_queue.put((task_id, temp_path, filename))
        
        # 等待识别结果（最多60秒）
        timeout_seconds = 60
        for _ in range(timeout_seconds * 10):  # 60秒，每0.1秒检查一次
            if task_id in recognition_results:
                cat_name = recognition_results.pop(task_id)
                
                if cat_name:
                    logger.info(f"识别成功: {cat_name}")
                    return jsonify({
                        'success': True,
                        'cat_name': cat_name,
                        'message': f'Successfully recognized as {cat_name}'
                    })
                else:
                    logger.info("识别失败: 跳过或未检测到猫咪")
                    return jsonify({
                        'success': False,
                        'error': 'notfound',
                        'message': 'Recognition skipped or no cat detected'
                    }), 404
            
            time.sleep(0.1)
        
        # 超时处理
        logger.error("识别超时")
        # 清理临时文件
        try:
            os.remove(temp_path)
        except:
            pass
        return jsonify({
            'success': False,
            'error': 'timeout',
            'message': 'Recognition timeout'
        }), 408
            
    except Exception as e:
        logger.error(f"识别服务错误: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'Internal server error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'CLI Cat Recognition Server',
        'version': '1.0.0',
        'mode': 'command_line_interactive'
    })

@app.route('/status', methods=['GET'])
def status():
    """状态检查端点"""
    return jsonify({
        'queue_size': recognition_queue.qsize(),
        'pending_results': len(recognition_results),
        'temp_folder': UPLOAD_FOLDER
    })

if __name__ == '__main__':
    print("🐱 启动命令行猫咪识别服务器...")
    print("服务器地址: http://localhost:2255")
    print("API端点: POST /recognize")
    print("健康检查: GET /health")
    print("状态检查: GET /status")
    print("=" * 60)
    
    # 启动交互式识别工作线程
    recognition_thread = threading.Thread(target=interactive_recognition_worker, daemon=True)
    recognition_thread.start()
    
    try:
        # 关闭Flask的debug模式和重载功能，避免干扰命令行交互
        app.run(debug=False, host='0.0.0.0', port=2255, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 服务器即将关闭...")
        recognition_queue.put(None)  # 发送退出信号
        sys.exit(0)
