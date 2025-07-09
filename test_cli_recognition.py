#!/usr/bin/env python3
"""
测试命令行识别服务器的脚本
"""

import requests
import sys
import os
import time
import threading

def test_cli_recognition_server():
    """测试命令行识别服务器"""
    server_url = "http://localhost:2255"
    
    print("🧪 测试命令行猫咪识别服务器...")
    print(f"服务器地址: {server_url}")
    print("-" * 50)
    
    # 1. 测试健康检查
    print("1. 测试健康检查...")
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ 健康检查通过")
            result = response.json()
            print(f"   服务: {result.get('service')}")
            print(f"   版本: {result.get('version')}")
            print(f"   模式: {result.get('mode')}")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ 无法连接到服务器。请确保服务器正在运行。")
        return False
    except Exception as e:
        print(f"   ❌ 健康检查错误: {e}")
        return False
    
    print()
    
    # 2. 测试状态检查
    print("2. 测试状态检查...")
    try:
        response = requests.get(f"{server_url}/status", timeout=5)
        if response.status_code == 200:
            print("   ✅ 状态检查通过")
            result = response.json()
            print(f"   队列大小: {result.get('queue_size')}")
            print(f"   待处理结果: {result.get('pending_results')}")
            print(f"   临时文件夹: {result.get('temp_folder')}")
        else:
            print(f"   ❌ 状态检查失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 状态检查错误: {e}")
    
    print()
    
    # 3. 测试识别端点（无图片）
    print("3. 测试识别端点（无图片）...")
    try:
        response = requests.post(f"{server_url}/recognize", timeout=5)
        if response.status_code == 400:
            print("   ✅ 正确拒绝了无图片的请求")
        else:
            print(f"   ⚠️  意外响应: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 识别测试错误: {e}")
    
    print()
    
    # 4. 如果提供了图片文件，测试识别
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if os.path.exists(image_path):
            print(f"4. 测试图片识别: {image_path}")
            print("   ⚠️  注意: 此测试需要在服务器终端中手动输入猫咪名字")
            print("   💡 建议: 在服务器终端中输入一个测试名字（如 'TestCat'）")
            
            def upload_image():
                """上传图片的线程函数"""
                try:
                    with open(image_path, 'rb') as f:
                        files = {'image': f}
                        response = requests.post(f"{server_url}/recognize", files=files, timeout=65)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('success'):
                                print(f"   ✅ 识别成功: {result.get('cat_name')}")
                            else:
                                print(f"   ❌ 识别失败: {result.get('error')}")
                        elif response.status_code == 404:
                            result = response.json()
                            print(f"   ⚠️  跳过或未检测到猫咪: {result.get('message')}")
                        elif response.status_code == 408:
                            print("   ⏰ 识别超时（60秒）")
                        else:
                            print(f"   ❌ 识别错误: {response.status_code}")
                            print(f"   响应: {response.text}")
                            
                except Exception as e:
                    print(f"   ❌ 图片识别测试错误: {e}")
            
            # 在单独的线程中上传图片
            upload_thread = threading.Thread(target=upload_image)
            upload_thread.start()
            
            # 等待用户输入或线程完成
            print("   🔄 正在上传图片并等待识别...")
            print("   ⏳ 请在服务器终端中输入猫咪名字...")
            
            upload_thread.join(70)  # 等待最多70秒
            
            if upload_thread.is_alive():
                print("   ⏰ 测试超时")
            
        else:
            print(f"4. 图片文件不存在: {image_path}")
    else:
        print("4. 未提供图片进行识别测试")
        print("   用法: python test_cli_recognition.py <图片路径>")
    
    print()
    print("🎉 测试完成!")
    print()
    print("📝 使用说明:")
    print("1. 启动服务器: python recognition_server_cli.py")
    print("2. 在Web界面上传图片或使用API")
    print("3. 在服务器终端中输入猫咪名字")
    print("4. 输入 'skip' 跳过图片")
    print("5. 输入 'quit' 退出服务")
    
    return True

if __name__ == '__main__':
    test_cli_recognition_server()
