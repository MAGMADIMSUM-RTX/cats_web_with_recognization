# 猫咪相册 - Flask版本

这是一个使用Flask框架重写的猫咪图片查看器应用，原项目使用Dioxus框架开发。

## 功能特性

- 🐱 从Cat API获取随机猫咪图片
- 📱 响应式设计，支持桌面和移动端
- 💖 收藏功能，保存喜欢的猫咪图片
- 🔍 图片放大查看模态框
- 🎨 现代化UI设计，类似社交媒体风格
- 🔄 无限滚动加载更多图片
- 🗃️ SQLite数据库存储收藏

## 技术栈

- **后端**: Flask 3.0
- **前端**: 原生JavaScript + HTML5 + CSS3
- **数据库**: SQLite
- **API**: The Cat API
- **样式**: 自定义CSS，响应式设计

## 安装和运行

### 1. 克隆项目

```bash
cd cats_flask
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## API接口

### 获取随机猫咪图片
- **URL**: `/api/cats`
- **方法**: GET
- **参数**: `count` (可选，默认5，最大20)
- **返回**: JSON格式的猫咪图片URL列表

### 保存猫咪到收藏
- **URL**: `/api/save_cat`
- **方法**: POST
- **参数**: `{"image_url": "图片URL"}`
- **返回**: 保存结果

### 获取收藏列表
- **URL**: `/api/favorites`
- **方法**: GET
- **返回**: 收藏的猫咪图片列表

### 移除收藏
- **URL**: `/api/remove_favorite`
- **方法**: POST
- **参数**: `{"id": 收藏ID}`
- **返回**: 移除结果

## 项目结构

```
cats_flask/
├── app.py              # Flask应用主文件
├── requirements.txt    # Python依赖
├── hotcat.db          # SQLite数据库（自动创建）
├── templates/         # HTML模板
│   ├── index.html     # 主页模板
│   └── favorites.html # 收藏页模板
└── static/           # 静态资源
    ├── css/
    │   └── main.css  # 主样式文件
    └── js/
        ├── main.js   # 主页JavaScript
        └── favorites.js # 收藏页JavaScript
```

## 特性对比

| 功能 | 原Dioxus版本 | Flask版本 |
|------|-------------|-----------|
| 前端框架 | Dioxus (Rust) | 原生JavaScript |
| 后端框架 | Dioxus Fullstack | Flask (Python) |
| 数据库 | SQLite | SQLite |
| 响应式设计 | ✅ | ✅ |
| 图片收藏 | ✅ | ✅ |
| 模态框查看 | ✅ | ✅ |
| 无限滚动 | ✅ | ✅ |
| 热门照片侧栏 | ✅ | ✅ |

## 开发说明

- 使用The Cat API获取猫咪图片，需要API密钥
- 数据库会在首次运行时自动创建
- 支持CORS，可以从不同域名访问
- 生产环境建议使用WSGI服务器如Gunicorn

## 许可证

MIT License

## 🔍 猫咪识别功能

### 命令行识别服务器
项目包含一个纯命令行交互式识别服务器，运行在端口 2255。

#### 启动命令行识别服务器
```bash
# Windows
start_cli_recognition.bat

# Linux/Mac
chmod +x start_cli_recognition.sh
./start_cli_recognition.sh

# 或者直接运行
python recognition_server_cli.py
```

#### 测试命令行识别服务器
```bash
# 基本测试
python test_cli_recognition.py

# 使用图片测试（需要手动输入猫咪名字）
python test_cli_recognition.py path/to/your/cat_image.jpg
```

#### 命令行识别服务器 API

**识别端点**: `POST /recognize`
- 上传图片文件进行识别
- 需要在服务器终端中手动输入猫咪名字

**健康检查**: `GET /health`
- 检查服务器状态

**状态检查**: `GET /status`
- 查看队列状态和服务器信息

**示例请求**:
```bash
curl -X POST -F "image=@cat.jpg" http://localhost:2255/recognize
```

**响应格式**:
```json
{
  "success": true,
  "cat_name": "小白",
  "message": "Successfully recognized as 小白"
}
```

### 使用方法

1. **启动命令行识别服务器**:
   ```bash
   python recognition_server_cli.py
   ```

2. **启动主应用**:
   ```bash
   python app.py
   ```

3. **使用识别功能**:
   - 在主页点击"上传"按钮
   - 选择猫咪图片
   - 点击"🔍 识别猫咪"按钮
   - 在识别服务器的终端中输入猫咪名字
   - 系统会自动保存到对应的猫咪目录

### 命令行交互

识别服务器支持以下命令：

- **输入猫咪名字**: 完成识别并保存
- **输入 'skip'**: 跳过当前图片
- **输入 'quit'**: 退出识别服务

### 功能特点

- **纯命令行交互**: 无需图形界面，完全通过终端操作
- **实时显示**: 显示图片路径、文件大小等信息
- **容错处理**: 识别失败时会删除临时文件并提示用户
- **超时机制**: 60秒超时保护，防止长时间等待
- **状态监控**: 提供队列状态和服务器信息查询

---
