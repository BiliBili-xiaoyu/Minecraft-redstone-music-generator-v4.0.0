#!/usr/bin/env python3
"""
完整功能测试脚本
测试音频处理、投影生成、文件下载等所有功能
"""

import os
import sys
import time
import json
import requests
import tempfile

def test_server_health():
    """测试服务器健康状态"""
    print("=" * 60)
    print("测试服务器健康状态")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务器状态: {data.get('status', '未知')}")
            print(f"✓ 版本: {data.get('version', '未知')}")
            print(f"✓ Python版本: {data.get('system', {}).get('python_version', '未知')}")
            return True
        else:
            print(f"✗ 服务器响应: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到服务器: {e}")
        return False

def test_audio_preview():
    """测试音频预览功能"""
    print("\n" + "=" * 60)
    print("测试音频预览功能")
    print("=" * 60)
    
    # 创建一个简单的测试音频文件
    import numpy as np
    from scipy.io import wavfile
    
    # 生成1秒的测试音频
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz正弦波
    
    # 保存为临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    wavfile.write(temp_path, sample_rate, audio_data)
    temp_file.close()
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'audio': f}
            data = {
                'pitch': '0',
                'octave': '0',
                'speed': '1.0'
            }
            
            response = requests.post(
                "http://localhost:5000/api/preview",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✓ 音频预览成功")
                print(f"  原始时长: {result.get('original_duration', 0):.2f}秒")
                print(f"  处理后时长: {result.get('duration', 0):.2f}秒")
                print(f"  预览URL: {result.get('audio_url', '未知')}")
                
                # 测试预览文件是否可以访问
                preview_url = result.get('audio_url')
                if preview_url:
                    preview_response = requests.get(f"http://localhost:5000{preview_url}", timeout=10)
                    if preview_response.status_code == 200:
                        print(f"✓ 预览文件可以访问")
                    else:
                        print(f"✗ 预览文件访问失败: {preview_response.status_code}")
                
                return True
            else:
                print(f"✗ 音频预览失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"✗ 服务器响应: {response.status_code}")
            print(f"  响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ 音频预览测试异常: {e}")
        return False
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass

def test_projection_generation():
    """测试投影生成功能"""
    print("\n" + "=" * 60)
    print("测试投影生成功能")
    print("=" * 60)
    
    # 创建一个简单的测试音频文件
    import numpy as np
    from scipy.io import wavfile
    
    # 生成3秒的测试音频
    sample_rate = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440Hz正弦波
    
    # 保存为临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    wavfile.write(temp_path, sample_rate, audio_data)
    temp_file.close()
    
    try:
        with open(temp_path, 'rb') as f:
            files = {'audio': f}
            data = {
                'pitch': '0',
                'octave': '0',
                'speed': '1.0',
                'density': '2',
                'max_notes': '50',
                'auto_tune': 'true'
            }
            
            print("正在生成投影文件...")
            response = requests.post(
                "http://localhost:5000/api/generate",
                files=files,
                data=data,
                timeout=60,  # 长时间等待
                stream=True
            )
        
        if response.status_code == 200:
            print("✓ 投影生成请求成功")
            
            # 解析流式响应
            file_id = None
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            event_data = json.loads(line_str[6:])
                            if event_data.get('progress'):
                                print(f"  进度: {event_data.get('progress')}% - {event_data.get('message')}")
                            if event_data.get('complete'):
                                if event_data.get('success'):
                                    file_id = event_data.get('file_id')
                                    stats = event_data.get('stats', {})
                                    print(f"✓ 投影生成成功")
                                    print(f"  文件ID: {file_id}")
                                    print(f"  音符数量: {stats.get('notes', 0)}")
                                    print(f"  音乐时长: {stats.get('duration', 0):.2f}秒")
                                    print(f"  文件大小: {stats.get('file_size', 0)}KB")
                                else:
                                    print(f"✗ 投影生成失败: {event_data.get('error', '未知错误')}")
                                break
                        except json.JSONDecodeError:
                            continue
            
            if file_id:
                # 测试文件下载
                print("\n测试文件下载...")
                for format_type in ['schematic', 'litematic']:
                    download_url = f"http://localhost:5000/api/download/{file_id}?format={format_type}"
                    download_response = requests.get(download_url, timeout=30)
                    
                    if download_response.status_code == 200:
                        file_size = len(download_response.content)
                        print(f"✓ {format_type.upper()}文件下载成功: {file_size}字节")
                        
                        # 保存文件以供检查
                        test_dir = "test_outputs"
                        os.makedirs(test_dir, exist_ok=True)
                        test_file = os.path.join(test_dir, f"test_{file_id}.{format_type}")
                        with open(test_file, 'wb') as f:
                            f.write(download_response.content)
                        print(f"  文件已保存到: {test_file}")
                    else:
                        print(f"✗ {format_type.upper()}文件下载失败: {download_response.status_code}")
                
                return True
            else:
                print("✗ 未收到完成事件或生成失败")
                return False
        else:
            print(f"✗ 服务器响应: {response.status_code}")
            print(f"  响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ 投影生成测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass

def test_schematic_validation():
    """验证Schematic文件格式"""
    print("\n" + "=" * 60)
    print("验证Schematic文件格式")
    print("=" * 60)
    
    try:
        import struct
        
        test_dir = "test_outputs"
        if not os.path.exists(test_dir):
            print("✗ 测试输出目录不存在")
            return False
        
        schematic_files = [f for f in os.listdir(test_dir) if f.endswith('.schematic')]
        if not schematic_files:
            print("✗ 未找到Schematic文件")
            return False
        
        for schematic_file in schematic_files[:2]:  # 检查前两个文件
            file_path = os.path.join(test_dir, schematic_file)
            file_size = os.path.getsize(file_path)
            
            print(f"\n检查文件: {schematic_file} ({file_size}字节)")
            
            with open(file_path, 'rb') as f:
                # 读取版本
                version = struct.unpack('>h', f.read(2))[0]
                print(f"  版本: {version}")
                
                # 读取尺寸
                width = struct.unpack('>h', f.read(2))[0]
                height = struct.unpack('>h', f.read(2))[0]
                length = struct.unpack('>h', f.read(2))[0]
                print(f"  尺寸: {width}x{height}x{length}")
                
                # 计算应有的方块数据大小
                expected_blocks = width * height * length
                
                # 读取方块数据
                blocks_data = f.read(expected_blocks)
                actual_blocks = len(blocks_data)
                
                if actual_blocks == expected_blocks:
                    print(f"  ✓ 方块数据正确: {actual_blocks}字节")
                    
                    # 检查是否有非空气方块
                    non_air_blocks = sum(1 for b in blocks_data if b != 0)
                    print(f"  非空气方块: {non_air_blocks}")
                    
                    # 检查是否有音符盒
                    note_blocks = sum(1 for b in blocks_data if b == 25)  # 25 = 音符盒ID
                    print(f"  音符盒数量: {note_blocks}")
                else:
                    print(f"  ✗ 方块数据错误: 应有{expected_blocks}字节，实际{actual_blocks}字节")
                
                # 读取方块附加数据
                data_data = f.read(expected_blocks)
                if len(data_data) == expected_blocks:
                    print(f"  ✓ 方块附加数据正确: {len(data_data)}字节")
                else:
                    print(f"  ✗ 方块附加数据错误")
            
            print(f"  ✓ 文件格式基本正确")
        
        return True
        
    except Exception as e:
        print(f"✗ Schematic验证失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Minecraft红石音乐投影生成器 - 完整功能测试")
    print("=" * 80)
    
    all_tests_passed = True
    
    # 测试1: 服务器健康
    if not test_server_health():
        all_tests_passed = False
        print("\n[警告] 服务器健康测试失败，但继续其他测试...")
    
    # 测试2: 音频预览
    if not test_audio_preview():
        all_tests_passed = False
    
    # 测试3: 投影生成
    if not test_projection_generation():
        all_tests_passed = False
    
    # 测试4: 文件验证
    if not test_schematic_validation():
        all_tests_passed = False
    
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("✓ 所有测试通过！系统可以正常工作")
        print("=" * 80)
        print("\n使用说明:")
        print("1. 运行 start_all.bat 启动前后端")
        print("2. 访问 http://localhost:8080")
        print("3. 上传音频文件并调整参数")
        print("4. 点击'试听'检查音频效果")
        print("5. 点击'生成红石音乐投影'")
        print("6. 下载生成的 .schematic 或 .litematic 文件")
        print("7. 在Minecraft中使用投影Mod导入文件")
    else:
        print("✗ 部分测试失败，请检查以上错误信息")
        print("=" * 80)
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)