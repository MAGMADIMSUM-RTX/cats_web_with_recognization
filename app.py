from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import requests
import sqlite3
import os
from datetime import datetime
import logging
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import uuid
import re
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 上传配置
# 使用绝对路径，确保路径的准确性
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cats')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 数据库配置
SOURCE_DATABASE = 'cats.db'
FAVRITE_DATABASE = 'favcats.db'

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_name(name):
    """清理文件名，移除特殊字符"""
    # 移除或替换特殊字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name if name else 'unnamed'

def create_cat_directory(cat_name):
    """为猫咪创建专用目录"""
    sanitized_name = sanitize_name(cat_name)
    cat_dir = os.path.join(UPLOAD_FOLDER, sanitized_name)
    os.makedirs(cat_dir, exist_ok=True)
    return cat_dir

def normalize_path(path):
    """将路径标准化为使用正斜杠"""
    return path.replace('\\', '/')

def init_db():
    """初始化数据库"""
    # 初始化收藏数据库
    conn = sqlite3.connect(FAVRITE_DATABASE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    # 初始化源数据库
    conn = sqlite3.connect(SOURCE_DATABASE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """获取收藏数据库连接"""
    conn = sqlite3.connect(FAVRITE_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_source_db_connection():
    """获取源数据库连接"""
    conn = sqlite3.connect(SOURCE_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_multiple_cats(count=5):
    """从源数据库获取多张猫咪图片，包含名字"""
    try:
        conn = get_source_db_connection()
        cats = conn.execute(
            'SELECT id, name, file_path, time FROM cats ORDER BY RANDOM() LIMIT ?',
            (count,)
        ).fetchall()
        conn.close()
        
        cat_data = []
        for cat in cats:
            file_path = normalize_path(cat['file_path'])
            
            if file_path.startswith('cats/'):
                relative_path = file_path[5:]
            else:
                relative_path = file_path
            
            cat_data.append({
                'name': cat['name'],
                'url': f"/cats/{relative_path}"
            })
        
        logger.info(f"Requested {count} cats, received {len(cat_data)} cats from source database")
        return cat_data
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch cat images from source database: {e}")
        return []

@app.route('/')
def home():
    """主页 - 猫咪图片流"""
    return render_template('index.html')

@app.route('/favorites')
def favorites():
    """收藏页面"""
    return render_template('favorites.html')

@app.route('/recent')
def recent():
    """最近上传页面"""
    return render_template('recent.html')

@app.route('/search')
def search():
    """搜索页面"""
    return render_template('search.html')

@app.route('/cats/<path:filepath>')
def serve_cat_image(filepath):
    """提供猫咪图片文件（支持多级子目录）"""
    # 直接使用 UPLOAD_FOLDER，让 send_from_directory 处理路径
    # 它能安全地处理子目录和防止路径穿越
    return send_from_directory(UPLOAD_FOLDER, filepath)

@app.route('/api/add_cat_to_source', methods=['POST'])
def api_add_cat_to_source():
    """API: 向源数据库添加猫咪图片"""
    data = request.get_json()
    name = data.get('name')
    file_path = data.get('file_path')
    
    if not name or not file_path:
        return jsonify({'success': False, 'error': 'Missing name or file_path'}), 400
    
    try:
        conn = get_source_db_connection()
        # 检查文件路径是否已经存在
        existing = conn.execute('SELECT id FROM cats WHERE file_path = ?', (file_path,)).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'success': False, 'error': 'File path already exists'})
        
        # 添加到源数据库
        conn.execute('INSERT INTO cats (name, file_path) VALUES (?, ?)', (name, file_path))
        conn.commit()
        conn.close()
        
        logger.info(f"Added cat to source database: {name} - {file_path}")
        return jsonify({'success': True, 'message': 'Cat added to source database'})
    
    except sqlite3.Error as e:
        logger.error(f"SOURCE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'SOURCE_DATABASE error'}), 500

@app.route('/api/cats')
def api_get_cats():
    """API: 获取随机猫咪图片"""
    count = request.args.get('count', 5, type=int)
    count = min(count, 20)  # 限制最大数量
    
    cat_data = fetch_multiple_cats(count)
    return jsonify({
        'success': True,
        'cats': cat_data,
        'count': len(cat_data)
    })

@app.route('/api/save_cat', methods=['POST'])
def api_save_cat():
    """API: 保存猫咪图片到收藏"""
    data = request.get_json()
    image_url = data.get('image_url')
    
    if not image_url:
        return jsonify({'success': False, 'error': 'Missing image_url'}), 400
    
    # 从URL中提取文件路径
    if image_url.startswith('/cats/'):
        relative_path = image_url[6:]  # 移除 '/cats/' 前缀
        file_path = f"cats/{relative_path}"
    else:
        file_path = image_url
    
    # 标准化路径分隔符为正斜杠（用于数据库存储）
    file_path = file_path.replace('\\', '/')
    
    try:
        conn = get_db_connection()
        # 检查是否已经收藏
        existing = conn.execute('SELECT id FROM cats WHERE file_path = ?', (file_path,)).fetchone()
        
        if existing:
            conn.close()
            return jsonify({'success': False, 'error': 'Already saved'})
        
        # 保存到数据库
        conn.execute('INSERT INTO cats (file_path) VALUES (?)', (file_path,))
        conn.commit()
        conn.close()
        
        logger.info(f"Saved cat image: {file_path}")
        return jsonify({'success': True, 'message': 'Cat saved to favorites'})
    
    except sqlite3.Error as e:
        logger.error(f"FAVRITE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'FAVRITE_DATABASE error'}), 500

@app.route('/api/favorites')
def api_get_favorites():
    """API: 获取收藏的猫咪图片"""
    try:
        conn = get_db_connection()
        cats = conn.execute(
            'SELECT id, file_path, created_at FROM cats ORDER BY id DESC LIMIT 50'
        ).fetchall()
        conn.close()
        
        favorites = []
        for cat in cats:
            file_path = cat['file_path']
            # 标准化路径分隔符
            file_path = file_path.replace('\\', '/')
            
            # 处理新的目录结构
            if file_path.startswith('cats/'):
                relative_path = file_path[5:]  # 移除 'cats/' 前缀
            else:
                relative_path = file_path
            
            favorites.append({
                'id': cat['id'],
                'url': f"/cats/{relative_path}",
                'created_at': cat['created_at']
            })
        
        return jsonify({
            'success': True,
            'favorites': favorites,
            'count': len(favorites)
        })
    
    except sqlite3.Error as e:
        logger.error(f"FAVRITE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'FAVRITE_DATABASE error'}), 500

@app.route('/api/remove_favorite', methods=['POST'])
def api_remove_favorite():
    """API: 从收藏中移除猫咪图片"""
    data = request.get_json()
    cat_id = data.get('id')
    
    if not cat_id:
        return jsonify({'success': False, 'error': 'Missing cat id'}), 400
    
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM cats WHERE id = ?', (cat_id,))
        conn.commit()
        
        if result.rowcount > 0:
            conn.close()
            return jsonify({'success': True, 'message': 'Cat removed from favorites'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Cat not found'}), 404
    
    except sqlite3.Error as e:
        logger.error(f"FAVRITE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'FAVRITE_DATABASE error'}), 500

@app.route('/api/remove_favorite_by_url', methods=['POST'])
def api_remove_favorite_by_url():
    """API: 通过URL从收藏中移除猫咪图片"""
    data = request.get_json()
    image_url = data.get('image_url')
    
    if not image_url:
        return jsonify({'success': False, 'error': 'Missing image_url'}), 400
    
    # 从URL中提取文件路径
    if image_url.startswith('/cats/'):
        relative_path = image_url[6:]  # 移除 '/cats/' 前缀
        file_path = f"cats/{relative_path}"
    else:
        file_path = image_url
    
    # 标准化路径分隔符为正斜杠（用于数据库存储）
    file_path = file_path.replace('\\', '/')
    
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM cats WHERE file_path = ?', (file_path,))
        conn.commit()
        
        if result.rowcount > 0:
            conn.close()
            logger.info(f"Removed cat image from favorites: {file_path}")
            return jsonify({'success': True, 'message': 'Cat removed from favorites'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Cat not found in favorites'})
    
    except sqlite3.Error as e:
        logger.error(f"FAVRITE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'FAVRITE_DATABASE error'}), 500

@app.route('/api/import_cats_from_api', methods=['POST'])
def api_import_cats_from_api():
    """API: 从Cat API导入猫咪图片到本地并保存到源数据库"""
    data = request.get_json()
    count = data.get('count', 10)
    count = min(count, 50)  # 限制最大数量
    
    try:
        # 从Cat API获取猫咪图片
        url = f"https://api.thecatapi.com/v1/images/search?limit={count}&api_key=live_ylX4blBYT9FaoVd6OhvR"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        cat_data = response.json()
        
        # 创建cats目录（如果不存在）
        os.makedirs('cats', exist_ok=True)
        
        # 下载图片并保存到源数据库
        conn = get_source_db_connection()
        imported_count = 0
        
        for cat in cat_data:
            cat_url = cat['url']
            cat_id = cat.get('id', f"cat_{imported_count + 1}")
            cat_name = f"Cat_{cat_id}"
            
            # 获取文件扩展名
            file_ext = cat_url.split('.')[-1] if '.' in cat_url else 'jpg'
            file_name = f"{cat_id}.{file_ext}"
            file_path = f"cats/{file_name}"
            
            # 检查文件路径是否已经存在
            existing = conn.execute('SELECT id FROM cats WHERE file_path = ?', (file_path,)).fetchone()
            
            if not existing:
                # 下载图片
                try:
                    img_response = requests.get(cat_url, timeout=10)
                    img_response.raise_for_status()
                    
                    # 保存图片文件 - 使用OS路径
                    os_file_path = file_path.replace('/', os.sep)
                    with open(os_file_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # 添加到数据库 - 使用标准化路径
                    conn.execute('INSERT INTO cats (name, file_path) VALUES (?, ?)', (cat_name, file_path))
                    imported_count += 1
                    
                    logger.info(f"Downloaded and saved: {file_path}")
                    
                except requests.RequestException as e:
                    logger.error(f"Failed to download image {cat_url}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Imported {imported_count} cats from API to source database")
        return jsonify({
            'success': True,
            'message': f'Imported {imported_count} cats',
            'imported_count': imported_count
        })
    
    except requests.RequestException as e:
        logger.error(f"Failed to import cats from API: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch from API'}), 500
    except sqlite3.Error as e:
        logger.error(f"SOURCE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'SOURCE_DATABASE error'}), 500

@app.route('/api/source_cats')
def api_get_source_cats():
    """API: 获取源数据库中的所有猫咪信息（按时间倒序）"""
    try:
        conn = get_source_db_connection()
        cats = conn.execute(
            'SELECT id, name, file_path, time FROM cats ORDER BY time DESC'
        ).fetchall()
        conn.close()
        
        source_cats = []
        for cat in cats:
            file_path = normalize_path(cat['file_path'])
            
            if file_path.startswith('cats/'):
                relative_path = file_path[5:]
            else:
                relative_path = file_path
            
            source_cats.append({
                'id': cat['id'],
                'name': cat['name'],
                'url': f"/cats/{relative_path}",
                'file_path': cat['file_path'],
                'time': cat['time']
            })
        
        return jsonify({
            'success': True,
            'cats': source_cats,
            'count': len(source_cats)
        })
    
    except sqlite3.Error as e:
        logger.error(f"SOURCE_DATABASE error: {e}")
        return jsonify({'success': False, 'error': 'SOURCE_DATABASE error'}), 500

@app.route('/api/search_cats')
def api_search_cats():
    """API: 根据名字搜索猫咪"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'success': True, 'cats': [], 'count': 0})
        
    try:
        conn = get_source_db_connection()
        # 使用 LIKE 进行模糊查询
        cats = conn.execute(
            "SELECT id, name, file_path, time FROM cats WHERE name LIKE ? ORDER BY time DESC",
            (f'%{query}%',)
        ).fetchall()
        conn.close()
        
        searched_cats = []
        for cat in cats:
            file_path = normalize_path(cat['file_path'])
            
            if file_path.startswith('cats/'):
                relative_path = file_path[5:]
            else:
                relative_path = file_path
            
            searched_cats.append({
                'id': cat['id'],
                'name': cat['name'],
                'url': f"/cats/{relative_path}",
                'time': cat['time']
            })
            
        return jsonify({
            'success': True,
            'cats': searched_cats,
            'count': len(searched_cats)
        })
        
    except sqlite3.Error as e:
        logger.error(f"Search error: {e}")
        return jsonify({'success': False, 'error': 'Database search error'}), 500

@app.route('/api/upload_cats', methods=['POST'])
def api_upload_cats():
    """API: 上传多张猫咪图片"""
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        cat_name = request.form.get('cat_name', '').strip()
        
        if not cat_name:
            return jsonify({'success': False, 'error': 'Cat name is required'}), 400
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # 创建猫咪专用目录
        cat_dir = create_cat_directory(cat_name)
        
        # 连接数据库
        conn = get_source_db_connection()
        uploaded_files = []
        
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                # 生成唯一的文件ID
                file_id = str(uuid.uuid4())
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{file_id}.{file_ext}"
                
                # 创建标准化的存储路径（用于数据库）
                normalized_path = f"cats/{sanitize_name(cat_name)}/{filename}"
                
                # 创建OS路径（用于文件系统）
                os_file_path = normalized_path.replace('/', os.sep)
                
                try:
                    # 保存文件
                    file.save(os_file_path)
                    
                    # 添加到数据库
                    conn.execute(
                        'INSERT INTO cats (name, file_path) VALUES (?, ?)',
                        (cat_name, normalized_path)
                    )
                    
                    uploaded_files.append({
                        'filename': filename,
                        'path': normalized_path,
                        'id': file_id
                    })
                    
                    logger.info(f"Uploaded file: {normalized_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to save file {file.filename}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        if uploaded_files:
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(uploaded_files)} images for {cat_name}',
                'uploaded_count': len(uploaded_files),
                'cat_name': cat_name,
                'files': uploaded_files
            })
        else:
            return jsonify({'success': False, 'error': 'No valid files were uploaded'}), 400
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': 'Upload failed'}), 500

# 添加识别功能的路由
# --- 1. 修改调用AI服务器的函数 ---

def recognize_cat(image_path):
    """
    调用AI识别服务器来识别猫咪。
    返回一个包含详细识别结果的字典，如果失败则返回None。
    """
    # AI识别服务器的地址
    RECOGNITION_SERVER_URL = "http://localhost:2255/recognize"

    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}

            # 发送请求到AI服务器，设置一个合理的超时
            response = requests.post(
                RECOGNITION_SERVER_URL,
                files=files,
                timeout=30  # 设置30秒超时，防止无限等待
            )

            response.raise_for_status()  # 如果状态码不是2xx，则抛出异常

            result = response.json()
            if result.get('success'):
                # 成功时，返回整个 'data' 对象
                return result.get('data')
            else:
                # AI服务器返回了 'success': False
                logger.warning(f"AI服务器识别失败: {result.get('error')}")
                return {'error': result.get('error', 'unknown_ai_error')}

    except requests.exceptions.Timeout:
        logger.error("连接AI识别服务超时。")
        return {'error': 'ai_server_timeout'}
    except requests.exceptions.RequestException as e:
        logger.error(f"连接AI识别服务时发生错误: {e}")
        return {'error': 'ai_server_connection_error'}
    except Exception as e:
        logger.error(f"处理AI服务响应时发生未知错误: {e}")
        return {'error': 'unknown_processing_error'}


# --- 2. 修改主API端点以处理新的返回结构 ---

@app.route('/api/recognize_cats', methods=['POST'])
def api_recognize_cats():
    """识别多张猫咪图片（仅返回识别结果，不写入数据库）"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': 'No files selected'}), 400

    tmp_dir = os.path.join(UPLOAD_FOLDER, 'tmp', str(uuid.uuid4()))
    os.makedirs(tmp_dir, exist_ok=True)

    recognition_results = []
    failed_files = []

    for file in files:
        if not (file and file.filename and allowed_file(file.filename)):
            failed_files.append({'filename': file.filename, 'error': 'Invalid file or file type'})
            continue

        filename = secure_filename(file.filename)
        temp_path = os.path.join(tmp_dir, f"{uuid.uuid4()}{os.path.splitext(filename)[1].lower()}")

        try:
            file.save(temp_path)

            # 调用更新后的识别函数
            ai_result = recognize_cat(temp_path)

            if ai_result and not ai_result.get('error'):
                # AI服务器成功返回了识别数据
                recognition_results.append({
                    'filename': filename,
                    'status': ai_result.get('status'),  # 'matched' or 'unmatched'
                    'cat_name': ai_result.get('cat_name'),  # "Garfield" or "待定 (Unknown)"
                    'similarity': ai_result.get('similarity'),  # 相似度得分
                    'message': ai_result.get('message')  # AI服务器给出的提示信息
                })
                logger.info(
                    f"AI识别成功: {filename} -> {ai_result.get('cat_name')} (Sim: {ai_result.get('similarity')})")
            else:
                # 识别失败 (连接失败、AI服务器出错或未检测到猫脸等)
                error_message = ai_result.get('error', 'Recognition failed') if ai_result else 'Recognition failed'
                failed_files.append({
                    'filename': filename,
                    'error': error_message
                })
                logger.warning(f"AI识别失败: {filename}, 原因: {error_message}")

        except Exception as e:
            failed_files.append({'filename': filename, 'error': f'Processing error: {str(e)}'})
            logger.error(f"处理文件 {filename} 时发生错误: {e}", exc_info=True)
        finally:
            # 确保临时文件被删除
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 清理临时目录
    try:
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)
    except OSError:
        pass  # 如果目录非空（说明有其他并行进程），则不删除

    if not recognition_results and not failed_files:
        return jsonify({'success': False, 'error': 'No valid files processed'}), 400

    # --- 汇总结果 ---
    # 新的汇总逻辑：只对成功匹配的猫进行统计
    # 我们只认为 status == 'matched' 的是确认的猫
    matched_cat_names = [
        res['cat_name'] for res in recognition_results if res.get('status') == 'matched'
    ]

    suggested_name = None
    if matched_cat_names:
        # 统计最常见的已匹配猫咪名字
        most_common = Counter(matched_cat_names).most_common(1)
        if most_common:
            suggested_name = most_common[0][0]

    return jsonify({
        'success': True,
        'message': f'Processed {len(files)} files.',
        'recognized_count': len(recognition_results),
        'failed_count': len(failed_files),
        'suggested_name': suggested_name,  # 建议的猫咪名字 (可能为 None)
        'recognition_results': recognition_results,
        'failed_files': failed_files
    })

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5200)
