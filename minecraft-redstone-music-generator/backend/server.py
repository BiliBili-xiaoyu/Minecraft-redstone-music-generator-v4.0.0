#!/usr/bin/env python3
"""
Minecraft红石音乐投影生成器 - 完整增强版后端服务器
包含所有修复和新功能
"""

import os
import sys
import json
import uuid
import time
import traceback
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS

# 打印Python版本和路径信息
print(f"Python版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path}")

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
try:
    print("正在导入自定义模块...")
    from audio_processor import AudioProcessor
    from redstone_mapper import RedstoneMapper
    from litematic_generator import LitematicGenerator
    print("✓ 所有自定义模块导入成功")
except ImportError as e:
    print(f"✗ 模块导入失败: {e}")
    print("请确保以下模块已安装:")
    print("  - audio_processor.py")
    print("  - redstone_mapper.py")
    print("  - litematic_generator.py")
    sys.exit(1)

# 检查关键库
try:
    import numpy as np
    print(f"✓ NumPy版本: {np.__version__}")
except ImportError:
    print("✗ NumPy未安装，请运行: pip install numpy")
    sys.exit(1)

try:
    import librosa
    print(f"✓ Librosa版本: {librosa.__version__}")
except ImportError:
    print("✗ Librosa未安装，请运行: pip install librosa")
    sys.exit(1)

# 尝试导入ConfigLoader（可选）
try:
    from config_loader import ConfigLoader
    CONFIG_LOADER_AVAILABLE = True
    print("✓ ConfigLoader可用")
except ImportError:
    CONFIG_LOADER_AVAILABLE = False
    print("⚠ ConfigLoader不可用，将使用默认配置")

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = 'uploads'
PROJECTIONS_FOLDER = 'projections'
LOGS_FOLDER = 'logs'
CONFIG_FOLDER = 'configs'
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROJECTIONS_FOLDER'] = PROJECTIONS_FOLDER
app.config['LOGS_FOLDER'] = LOGS_FOLDER
app.config['CONFIG_FOLDER'] = CONFIG_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'minecraft-redstone-music-secret-2024')
app.config['DEBUG'] = True

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROJECTIONS_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

print(f"上传文件夹: {os.path.abspath(UPLOAD_FOLDER)}")
print(f"投影文件夹: {os.path.abspath(PROJECTIONS_FOLDER)}")
print(f"日志文件夹: {os.path.abspath(LOGS_FOLDER)}")
print(f"配置文件夹: {os.path.abspath(CONFIG_FOLDER)}")

# 初始化配置加载器
if CONFIG_LOADER_AVAILABLE:
    try:
        config_loader = ConfigLoader(os.path.join(CONFIG_FOLDER, 'default.json'))
        print("✓ 配置加载器初始化成功")
    except Exception as e:
        print(f"⚠ 配置加载器初始化失败: {e}")
        CONFIG_LOADER_AVAILABLE = False

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def get_file_info(filepath):
    """获取文件信息"""
    try:
        stats = os.stat(filepath)
        return {
            'size': stats.st_size,
            'created': datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'size_mb': stats.st_size / (1024 * 1024)
        }
    except:
        return {}

def cleanup_old_files(hours=1):
    """清理旧的临时文件"""
    try:
        current_time = time.time()
        cleaned_count = 0
        expiry_time = hours * 3600
        
        # 清理上传文件夹
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.startswith('preview_') or filename.startswith('temp_'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if current_time - file_time > expiry_time:
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                            print(f"清理旧文件: {filename}")
                        except:
                            pass
        
        # 清理旧日志
        for filename in os.listdir(app.config['LOGS_FOLDER']):
            if filename.endswith('.log'):
                filepath = os.path.join(app.config['LOGS_FOLDER'], filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if current_time - file_time > 24 * 3600:  # 24小时
                        try:
                            os.remove(filepath)
                        except:
                            pass
        
        print(f"清理了 {cleaned_count} 个旧文件")
        return cleaned_count
    except Exception as e:
        print(f"清理文件时出错: {e}")
        return 0

def log_error(error_msg, exc_info=None):
    """记录错误日志"""
    try:
        log_file = os.path.join(app.config['LOGS_FOLDER'], f"error_{datetime.now().strftime('%Y%m%d')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] {error_msg}\n")
            if exc_info:
                f.write(f"异常信息: {exc_info}\n")
            f.write("-" * 80 + "\n")
    except:
        pass

def parse_boolean_param(param_value, default=False):
    """解析布尔参数"""
    if isinstance(param_value, str):
        return param_value.lower() in ('true', 'yes', '1', 'on')
    return bool(param_value)

def parse_float_param(param_value, default=0.0):
    """解析浮点数参数"""
    try:
        return float(param_value)
    except (ValueError, TypeError):
        return default

def parse_int_param(param_value, default=0):
    """解析整数参数"""
    try:
        return int(param_value)
    except (ValueError, TypeError):
        return default

def generate_progress_stream(file_id, audio_path, params):
    """生成进度流式响应 - 增强版"""
    try:
        total_steps = 7
        current_step = 0
        
        # 步骤1: 音频处理开始
        current_step += 1
        progress_data = {
            'progress': 5,
            'message': '开始处理音频文件...',
            'step': f'步骤 {current_step}/{total_steps}'
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        # 处理音频
        print(f"\n{'='*60}")
        print(f"开始处理音频文件: {os.path.basename(audio_path)}")
        print(f"文件ID: {file_id}")
        print(f"处理参数: {params}")
        print(f"{'='*60}")
        
        processor = AudioProcessor(audio_path)
        audio_data = processor.load_audio()
        
        # 获取音频时长
        audio_duration = processor.duration
        sample_rate = processor.sample_rate
        print(f"[音频信息] 时长: {audio_duration:.2f}秒, 采样率: {sample_rate}Hz, 样本数: {len(audio_data)}")
        
        # 步骤2: 音频参数调整
        current_step += 1
        progress_data = {
            'progress': 15,
            'message': '调整音频参数...',
            'step': f'步骤 {current_step}/{total_steps}',
            'audio_info': {
                'duration': audio_duration,
                'sample_rate': sample_rate,
                'samples': len(audio_data)
            }
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        # 基本参数调整
        pitch = parse_int_param(params.get('pitch', 0))
        octave = parse_int_param(params.get('octave', 0))
        speed = parse_float_param(params.get('speed', 1.0))
        
        print(f"[基本调整] 半音: {pitch}, 八度: {octave}, 速度: {speed}")
        
        if pitch != 0 or octave != 0:
            print(f"[音调调整] 开始...")
            audio_data = processor.adjust_pitch(audio_data, semitones=pitch, octaves=octave)
            print(f"[音调调整] 完成")
        
        if speed != 1.0:
            print(f"[速度调整] 开始 (速度: {speed}x)...")
            audio_data = processor.adjust_speed(audio_data, speed=speed)
            audio_duration = len(audio_data) / processor.sample_rate
            print(f"[速度调整] 完成: {audio_duration:.2f}秒")
        
        # 音频效果处理（新增功能）
        effects_config = {
            'echo_enabled': parse_boolean_param(params.get('echo_enabled', False)),
            'echo_delay': parse_float_param(params.get('echo_delay', 0.3)),
            'echo_decay': parse_float_param(params.get('echo_decay', 0.5)),
            'reverb_enabled': parse_boolean_param(params.get('reverb_enabled', False)),
            'reverb_size': parse_float_param(params.get('reverb_size', 0.5)),
            'reverb_damping': parse_float_param(params.get('reverb_damping', 0.5)),
            'eq_enabled': parse_boolean_param(params.get('eq_enabled', False)),
            'eq_bass': parse_float_param(params.get('eq_bass', 1.0)),
            'eq_mid': parse_float_param(params.get('eq_mid', 1.0)),
            'eq_treble': parse_float_param(params.get('eq_treble', 1.0)),
            'compressor_enabled': parse_boolean_param(params.get('compressor_enabled', False)),
            'compressor_threshold': parse_float_param(params.get('compressor_threshold', 0.5)),
            'compressor_ratio': parse_float_param(params.get('compressor_ratio', 4.0)),
            'compressor_attack': parse_float_param(params.get('compressor_attack', 0.01)),
            'compressor_release': parse_float_param(params.get('compressor_release', 0.1)),
            'chorus_enabled': parse_boolean_param(params.get('chorus_enabled', False)),
            'chorus_depth': parse_float_param(params.get('chorus_depth', 0.5)),
            'chorus_rate': parse_float_param(params.get('chorus_rate', 0.5)),
            'chorus_mix': parse_float_param(params.get('chorus_mix', 0.5))
        }
        
        # 应用音频效果
        if any(effects_config.values()):
            print(f"[音频效果] 开始应用效果...")
            enabled_effects = [k for k, v in effects_config.items() if v and k.endswith('_enabled')]
            print(f"[音频效果] 启用的效果: {enabled_effects}")
            audio_data = processor.apply_effects(audio_data, effects_config)
            print(f"[音频效果] 效果应用完成")
        
        # 步骤3: 提取音符
        current_step += 1
        progress_data = {
            'progress': 30,
            'message': '分析音频特征...',
            'step': f'步骤 {current_step}/{total_steps}',
            'audio_info': {
                'original_duration': audio_duration,
                'speed_adjusted': speed
            }
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        max_notes = parse_int_param(params.get('max_notes', 500))
        density = parse_int_param(params.get('density', 2))
        
        print(f"[音符提取] 开始...")
        print(f"[参数] 最大音符数: {max_notes}, 密度: {density}, 音频时长: {audio_duration:.2f}秒")
        
        notes = processor.extract_notes(
            max_notes=max_notes,
            density=density,
            audio_duration=audio_duration
        )
        
        print(f"[音符提取] 完成: 提取到 {len(notes)} 个音符")
        if notes:
            first_time = notes[0][0]
            last_time = notes[-1][0]
            time_span = last_time - first_time
            time_coverage = (time_span / audio_duration * 100) if audio_duration > 0 else 0
            print(f"[时间范围] {first_time:.2f} - {last_time:.2f}秒 (跨度: {time_span:.2f}秒)")
            print(f"[时长覆盖] {time_coverage:.1f}%")
        
        # 步骤4: 映射到Minecraft音符
        current_step += 1
        progress_data = {
            'progress': 50,
            'message': f'映射到红石音符盒 ({len(notes)}个音符)...',
            'step': f'步骤 {current_step}/{total_steps}',
            'notes_extracted': len(notes),
            'time_coverage': f"{time_coverage:.1f}%" if notes else "0%"
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        mapper = RedstoneMapper()
        
        # 红石映射配置（新增功能）
        mapping_config = {
            'auto_tune': parse_boolean_param(params.get('auto_tune', True)),
            'harmony_enabled': parse_boolean_param(params.get('harmony_enabled', False)),
            'harmony_type': params.get('harmony_type', 'chords'),
            'instrument_strategy': params.get('instrument_strategy', 'frequency'),
            'rhythm_complexity': parse_int_param(params.get('rhythm_complexity', 3)),
            'dynamics': parse_int_param(params.get('dynamics', 3))
        }
        
        print(f"[红石映射] 开始...")
        print(f"[配置] {mapping_config}")
        
        # 使用增强版映射（如果可用）
        if hasattr(mapper, 'map_to_minecraft_enhanced'):
            redstone_notes = mapper.map_to_minecraft_enhanced(notes, mapping_config)
            print(f"[增强映射] 完成: 映射到 {len(redstone_notes)} 个红石音符")
        else:
            # 回退到原有映射
            redstone_notes = mapper.map_to_minecraft(
                notes,
                auto_tune=mapping_config['auto_tune'],
                audio_duration=audio_duration
            )
            print(f"[基本映射] 完成: 映射到 {len(redstone_notes)} 个红石音符")
        
        # 优化电路
        if len(redstone_notes) > 50:
            original_count = len(redstone_notes)
            redstone_notes = mapper.optimize_circuit(redstone_notes, max_ticks=2000)
            print(f"[电路优化] {original_count} -> {len(redstone_notes)} 个音符 (减少 {original_count - len(redstone_notes)})")
        
        if redstone_notes:
            first_tick = redstone_notes[0]['time_ticks']
            last_tick = redstone_notes[-1]['time_ticks']
            generated_duration = (last_tick - first_tick) / 10.0
            duration_ratio = (generated_duration / audio_duration * 100) if audio_duration > 0 else 0
            
            print(f"[时长统计] 原音频: {audio_duration:.2f}秒")
            print(f"[时长统计] 红石音乐: {generated_duration:.2f}秒 ({last_tick - first_tick}刻)")
            print(f"[时长比例] {duration_ratio:.1f}%")
            
            if duration_ratio < 70:
                print(f"[警告] 时长比例不足70%，尝试优化...")
                if hasattr(mapper, '_add_fill_notes'):
                    redstone_notes = mapper._add_fill_notes(redstone_notes, audio_duration)
                    last_tick = redstone_notes[-1]['time_ticks']
                    generated_duration = (last_tick - first_tick) / 10.0
                    duration_ratio = (generated_duration / audio_duration * 100) if audio_duration > 0 else 0
                    print(f"[重新调整] 新时长: {generated_duration:.2f}秒 ({duration_ratio:.1f}%)")
        
        # 步骤5: 生成投影文件
        current_step += 1
        progress_data = {
            'progress': 70,
            'message': '生成投影文件...',
            'step': f'步骤 {current_step}/{total_steps}',
            'redstone_notes': len(redstone_notes),
            'generated_duration': f"{generated_duration:.2f}秒" if redstone_notes else "0秒",
            'duration_ratio': f"{duration_ratio:.1f}%" if redstone_notes and audio_duration > 0 else "0%"
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        generator = LitematicGenerator()
        
        # 投影生成配置（新增功能）
        projection_config = {
            'format': params.get('format', 'schematic'),
            'height': parse_int_param(params.get('height', 6)),
            'base_block': params.get('base_block', 'stone'),
            'decorate': parse_boolean_param(params.get('decorate', True)),
            'include_entities': parse_boolean_param(params.get('include_entities', False)),
            'include_tile_entities': parse_boolean_param(params.get('include_tile_entities', True)),
            'schematic_version': parse_int_param(params.get('schematic_version', 2)),
            'author': params.get('author', 'RedstoneMusicGenerator'),
            'name': params.get('name', f"RedstoneMusic_{file_id[:8]}")
        }
        
        # 生成主文件
        main_format = projection_config['format']
        main_path = os.path.join(app.config['PROJECTIONS_FOLDER'], f"{file_id}.{main_format}")
        
        print(f"[投影生成] 开始...")
        print(f"[配置] {projection_config}")
        print(f"[文件] {main_path}")
        
        # 使用增强版投影生成（如果可用）
        if hasattr(generator, 'generate_projection'):
            stats = generator.generate_projection(
                redstone_notes,
                main_path,
                format_type=main_format,
                config=projection_config
            )
            print(f"[增强投影] 完成: {main_path}")
        else:
            # 回退到原有生成
            if main_format == 'litematic':
                stats = generator.generate_litematic(redstone_notes, main_path, projection_config['name'])
            else:
                stats = generator.generate_schematic(redstone_notes, main_path)
            print(f"[基本投影] 完成: {main_path}")
        
        # 同时生成Schematic文件以确保兼容性
        if main_format != 'schematic':
            schematic_path = os.path.join(app.config['PROJECTIONS_FOLDER'], f"{file_id}.schematic")
            print(f"[Schematic生成] 开始...")
            if hasattr(generator, 'generate_schematic'):
                generator.generate_schematic(redstone_notes, schematic_path)
                print(f"[Schematic生成] 完成: {schematic_path}")
        
        # 步骤6: 生成完成
        current_step += 1
        progress_data = {
            'progress': 95,
            'message': '生成完成，准备下载...',
            'step': f'步骤 {current_step}/{total_steps}',
            'complete': True,
            'success': True,
            'file_id': file_id,
            'stats': {
                'notes': len(redstone_notes),
                'redstone_length': stats.get('redstone_length', 0),
                'duration': stats.get('duration', 0),
                'duration_seconds': stats.get('duration', 0),
                'file_size': stats.get('file_size', 0)
            },
            'projection': {
                'name': stats.get('name', f"RedstoneMusic_{file_id[:8]}"),
                'dimensions': stats.get('dimensions', {'width': 10, 'height': 5, 'length': 10}),
                'note_blocks': stats.get('note_blocks', len(redstone_notes)),
                'redstone_dust': stats.get('redstone_dust', len(redstone_notes)),
                'repeaters': stats.get('repeaters', max(len(redstone_notes) // 10, 1)),
                'audio_duration': audio_duration,
                'generated_duration': stats.get('duration', 0),
                'duration_ratio': f"{stats.get('duration', 0)/audio_duration*100:.1f}%" if audio_duration > 0 else "N/A",
                'format': stats.get('format', main_format)
            }
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        # 清理上传的音频文件
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"[清理] 临时文件: {os.path.basename(audio_path)}")
        except Exception as e:
            print(f"[清理失败] 临时文件: {e}")
        
        # 最终完成
        current_step += 1
        progress_data = {
            'progress': 100,
            'message': '所有处理完成！',
            'step': f'步骤 {current_step}/{total_steps}',
            'complete': True,
            'success': True
        }
        yield f"data: {json.dumps(progress_data)}\n\n"
        
        print(f"\n{'='*60}")
        print(f"项目 {file_id} 生成完成")
        print(f"总结: 原曲 {audio_duration:.1f}秒 -> 红石音乐 {stats.get('duration', 0):.1f}秒")
        print(f"比例: {stats.get('duration', 0)/audio_duration*100:.1f}%" if audio_duration > 0 else "N/A")
        print(f"文件: {main_path}")
        print(f"{'='*60}")
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"生成过程中出错: {e}")
        print(f"{'='*60}")
        print(f"错误详情: {error_trace}")
        print(f"{'='*60}")
        
        log_error(f"生成过程出错: {str(e)}", error_trace)
        
        try:
            if 'audio_path' in locals() and os.path.exists(audio_path):
                os.remove(audio_path)
        except:
            pass
        
        error_data = {
            'complete': True,
            'success': False,
            'error': str(e),
            'error_trace': error_trace if app.config['DEBUG'] else None
        }
        yield f"data: {json.dumps(error_data)}\n\n"

@app.route('/')
def index():
    """主页"""
    return jsonify({
        'name': 'Minecraft红石音乐投影生成器',
        'version': '2.3.0',  # 增强版本号
        'status': '运行中',
        'enhancements': {
            'audio_effects': '回声、混响、均衡器、压缩器、合唱效果',
            'redstone_mapping': '智能和声、多乐器策略、节奏控制',
            'projection_formats': 'Schematic、Litematic、Structure NBT、Blueprint',
            'configuration': '配置管理和预设系统'
        },
        'endpoints': {
            'health': '/api/health',
            'upload': '/api/upload',
            'preview': '/api/preview',
            'generate': '/api/generate',
            'download': '/api/download/<file_id>',
            'cleanup': '/api/cleanup',
            'list': '/api/list',
            'config': '/api/config',
            'presets': '/api/presets',
            'test': '/api/test'
        },
        'supported_formats': {
            'input': list(ALLOWED_EXTENSIONS),
            'output': ['schematic', 'litematic', 'structure', 'blueprint']
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 检查目录权限
        upload_writable = os.access(app.config['UPLOAD_FOLDER'], os.W_OK)
        projections_writable = os.access(app.config['PROJECTIONS_FOLDER'], os.W_OK)
        
        # 检查文件数量
        upload_files = os.listdir(app.config['UPLOAD_FOLDER'])
        projection_files = os.listdir(app.config['PROJECTIONS_FOLDER'])
        
        upload_count = len(upload_files)
        projections_count = len(projection_files)
        
        # 检查Python包
        import importlib
        modules_status = {}
        required_modules = ['flask', 'numpy', 'librosa', 'scipy', 'soundfile']
        optional_modules = ['nbtlib', 'yaml']
        
        for module_name in required_modules + optional_modules:
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, '__version__'):
                    modules_status[module_name] = mod.__version__
                else:
                    modules_status[module_name] = '已加载'
            except ImportError:
                modules_status[module_name] = '未安装' if module_name in required_modules else '可选未安装'
        
        return jsonify({
            'status': 'healthy',
            'version': '2.3.0',
            'timestamp': datetime.now().isoformat(),
            'enhancements_available': {
                'audio_effects': hasattr(AudioProcessor, 'apply_effects') if 'AudioProcessor' in globals() else False,
                'enhanced_mapping': hasattr(RedstoneMapper, 'map_to_minecraft_enhanced') if 'RedstoneMapper' in globals() else False,
                'multi_format': hasattr(LitematicGenerator, 'generate_projection') if 'LitematicGenerator' in globals() else False,
                'config_loader': CONFIG_LOADER_AVAILABLE
            },
            'directories': {
                'uploads': {
                    'path': app.config['UPLOAD_FOLDER'],
                    'writable': upload_writable,
                    'file_count': upload_count
                },
                'projections': {
                    'path': app.config['PROJECTIONS_FOLDER'],
                    'writable': projections_writable,
                    'file_count': projections_count
                },
                'logs': {
                    'path': app.config['LOGS_FOLDER'],
                    'writable': os.access(app.config['LOGS_FOLDER'], os.W_OK),
                    'file_count': len(os.listdir(app.config['LOGS_FOLDER']))
                },
                'configs': {
                    'path': app.config['CONFIG_FOLDER'],
                    'writable': os.access(app.config['CONFIG_FOLDER'], os.W_OK),
                    'file_count': len(os.listdir(app.config['CONFIG_FOLDER']))
                }
            },
            'modules': modules_status,
            'system': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cwd': os.getcwd()
            }
        })
    except Exception as e:
        log_error(f"健康检查出错: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """文件上传端点"""
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            allowed_str = ', '.join(ALLOWED_EXTENSIONS)
            return jsonify({'success': False, 'error': f'不支持的文件格式。支持格式: {allowed_str}'}), 400
        
        # 生成文件ID
        file_id = str(uuid.uuid4())
        
        # 保存上传的文件
        filename = f"{file_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 获取文件信息
        file_size = os.path.getsize(filepath)
        
        # 获取音频时长信息
        audio_info = None
        try:
            processor = AudioProcessor(filepath)
            processor.load_audio()
            duration = processor.duration
            sample_rate = processor.sample_rate
            audio_info = {
                'duration': duration,
                'sample_rate': sample_rate,
                'format': file.filename.rsplit('.', 1)[1].upper(),
                'size_mb': file_size / (1024 * 1024),
                'duration_formatted': f"{int(duration//60)}分{int(duration%60)}秒"
            }
            print(f"[文件上传] 音频信息: {duration:.2f}秒, {sample_rate}Hz, {file_size/1024/1024:.2f}MB")
        except Exception as e:
            print(f"[文件上传] 获取音频信息失败: {e}")
            audio_info = None
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'file_size': file_size,
            'audio_info': audio_info,
            'message': '文件上传成功'
        })
        
    except Exception as e:
        error_msg = f"文件上传失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def preview_audio():
    """音频预览端点 - 增强版"""
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '不支持的文件格式'}), 400
        
        # 保存上传的文件
        file_id = str(uuid.uuid4())
        filename = f"preview_{file_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 处理音频参数
        pitch = parse_int_param(request.form.get('pitch', 0))
        octave = parse_int_param(request.form.get('octave', 0))
        speed = parse_float_param(request.form.get('speed', 1.0))
        
        # 音频效果参数
        effects_config = {
            'echo_enabled': parse_boolean_param(request.form.get('echo_enabled', False)),
            'echo_delay': parse_float_param(request.form.get('echo_delay', 0.3)),
            'echo_decay': parse_float_param(request.form.get('echo_decay', 0.5)),
            'reverb_enabled': parse_boolean_param(request.form.get('reverb_enabled', False)),
            'reverb_size': parse_float_param(request.form.get('reverb_size', 0.5)),
            'reverb_damping': parse_float_param(request.form.get('reverb_damping', 0.5)),
            'eq_enabled': parse_boolean_param(request.form.get('eq_enabled', False)),
            'eq_bass': parse_float_param(request.form.get('eq_bass', 1.0)),
            'eq_mid': parse_float_param(request.form.get('eq_mid', 1.0)),
            'eq_treble': parse_float_param(request.form.get('eq_treble', 1.0))
        }
        
        print(f"[音频预览] 开始处理: {file.filename}")
        print(f"[基本参数] 半音: {pitch}, 八度: {octave}, 速度: {speed}")
        print(f"[效果参数] {effects_config}")
        
        try:
            # 处理音频
            processor = AudioProcessor(filepath)
            audio_data = processor.load_audio()
            
            # 获取原始时长
            original_duration = processor.duration
            original_samples = len(audio_data)
            print(f"[原始音频] 时长: {original_duration:.2f}秒, 样本数: {original_samples}")
            
            # 调整音调
            if pitch != 0 or octave != 0:
                print(f"[音调调整] 开始...")
                audio_data = processor.adjust_pitch(audio_data, semitones=pitch, octaves=octave)
                print(f"[音调调整] 完成: {len(audio_data)} 样本")
            
            # 调整速度
            if speed != 1.0:
                print(f"[速度调整] 开始 (速度: {speed}x)...")
                audio_data = processor.adjust_speed(audio_data, speed=speed)
                print(f"[速度调整] 完成: {len(audio_data)} 样本")
            
            # 应用音频效果
            if any(effects_config.values()):
                print(f"[音频效果] 开始应用效果...")
                enabled_effects = [k for k, v in effects_config.items() if v and k.endswith('_enabled')]
                print(f"[音频效果] 启用的效果: {enabled_effects}")
                
                if hasattr(processor, 'apply_effects'):
                    audio_data = processor.apply_effects(audio_data, effects_config)
                    print(f"[音频效果] 效果应用完成")
                else:
                    print(f"[音频效果] apply_effects方法不可用")
            
            # 保存处理后的音频
            preview_filename = f"preview_{file_id}.wav"  # 使用WAV确保兼容性
            preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_filename)
            processor.save_audio(audio_data, preview_path)
            
            # 计算处理后的时长
            processed_duration = len(audio_data) / processor.sample_rate
            print(f"[处理后音频] 时长: {processed_duration:.2f}秒, 样本数: {len(audio_data)}")
            
            # 清理原始上传文件
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"[清理] 原始文件: {filename}")
            except Exception as e:
                print(f"[清理失败] 原始文件: {e}")
            
            # 返回预览URL
            preview_url = f"/api/preview_audio/{preview_filename}"
            
            return jsonify({
                'success': True,
                'audio_url': preview_url,
                'duration': processed_duration,
                'original_duration': original_duration,
                'speed_adjusted': speed,
                'sample_rate': processor.sample_rate,
                'effects_applied': enabled_effects,
                'message': '音频处理完成，可以试听'
            })
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[音频处理失败] {e}")
            print(error_trace)
            
            # 如果处理失败，返回原始文件
            preview_filename = f"preview_{file_id}_original.wav"
            preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_filename)
            
            # 尝试转换原始文件为WAV
            try:
                from pydub import AudioSegment
                sound = AudioSegment.from_file(filepath)
                sound.export(preview_path, format="wav")
                print(f"[备用方案] 使用原始音频: {preview_filename}")
            except:
                # 如果转换失败，直接复制
                shutil.copy2(filepath, preview_path)
                print(f"[备用方案] 直接复制原始音频: {preview_filename}")
            
            preview_url = f"/api/preview_audio/{preview_filename}"
            
            return jsonify({
                'success': True,
                'audio_url': preview_url,
                'duration': original_duration,
                'original_duration': original_duration,
                'speed_adjusted': 1.0,
                'message': '使用原始音频进行预览',
                'warning': f'音频处理失败: {str(e)}'
            })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        error_msg = f"音频预览出错: {str(e)}"
        print(error_msg)
        print(error_trace)
        log_error(error_msg, error_trace)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/preview_audio/<filename>', methods=['GET'])
def serve_preview_audio(filename):
    """提供预览音频文件"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            # 根据文件扩展名设置MIME类型
            if filename.endswith('.mp3'):
                mimetype = 'audio/mpeg'
            elif filename.endswith('.wav'):
                mimetype = 'audio/wav'
            elif filename.endswith('.ogg'):
                mimetype = 'audio/ogg'
            elif filename.endswith('.m4a'):
                mimetype = 'audio/mp4'
            else:
                mimetype = 'audio/mpeg'
            
            print(f"[提供预览] {filename} ({os.path.getsize(filepath)} 字节)")
            return send_file(filepath, mimetype=mimetype)
        
        print(f"[预览文件不存在] {filename}")
        return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        error_msg = f"提供预览音频失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_projection():
    """生成投影文件端点 - 增强版"""
    try:
        start_time = time.time()
        
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '不支持的文件格式'}), 400
        
        # 生成文件ID
        file_id = str(uuid.uuid4())
        
        # 保存上传的文件
        filename = f"{file_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"\n{'='*60}")
        print(f"开始生成投影: {file_id}")
        print(f"原始文件: {file.filename}")
        print(f"保存路径: {filepath}")
        print(f"{'='*60}")
        
        # 获取所有参数
        params = {
            'pitch': request.form.get('pitch', 0),
            'octave': request.form.get('octave', 0),
            'speed': request.form.get('speed', 1.0),
            'density': request.form.get('density', 2),
            'max_notes': request.form.get('max_notes', 500),
            'auto_tune': request.form.get('auto_tune', 'true'),
            'original_filename': file.filename,
            'name': request.form.get('name', f"RedstoneMusic_{file_id[:8]}"),
            
            # 音频效果参数
            'echo_enabled': request.form.get('echo_enabled', 'false'),
            'echo_delay': request.form.get('echo_delay', 0.3),
            'echo_decay': request.form.get('echo_decay', 0.5),
            'reverb_enabled': request.form.get('reverb_enabled', 'false'),
            'reverb_size': request.form.get('reverb_size', 0.5),
            'reverb_damping': request.form.get('reverb_damping', 0.5),
            'eq_enabled': request.form.get('eq_enabled', 'false'),
            'eq_bass': request.form.get('eq_bass', 1.0),
            'eq_mid': request.form.get('eq_mid', 1.0),
            'eq_treble': request.form.get('eq_treble', 1.0),
            'compressor_enabled': request.form.get('compressor_enabled', 'false'),
            'compressor_threshold': request.form.get('compressor_threshold', 0.5),
            'compressor_ratio': request.form.get('compressor_ratio', 4.0),
            'compressor_attack': request.form.get('compressor_attack', 0.01),
            'compressor_release': request.form.get('compressor_release', 0.1),
            'chorus_enabled': request.form.get('chorus_enabled', 'false'),
            'chorus_depth': request.form.get('chorus_depth', 0.5),
            'chorus_rate': request.form.get('chorus_rate', 0.5),
            'chorus_mix': request.form.get('chorus_mix', 0.5),
            
            # 红石映射参数
            'harmony_enabled': request.form.get('harmony_enabled', 'false'),
            'harmony_type': request.form.get('harmony_type', 'chords'),
            'instrument_strategy': request.form.get('instrument_strategy', 'frequency'),
            'rhythm_complexity': request.form.get('rhythm_complexity', 3),
            'dynamics': request.form.get('dynamics', 3),
            
            # 投影生成参数
            'format': request.form.get('format', 'schematic'),
            'height': request.form.get('height', 6),
            'base_block': request.form.get('base_block', 'stone'),
            'decorate': request.form.get('decorate', 'true'),
            'include_entities': request.form.get('include_entities', 'false'),
            'include_tile_entities': request.form.get('include_tile_entities', 'true'),
            'schematic_version': request.form.get('schematic_version', 2),
            'author': request.form.get('author', 'RedstoneMusicGenerator')
        }
        
        print(f"生成参数:")
        for key, value in params.items():
            print(f"  {key}: {value}")
        print(f"{'='*60}\n")
        
        # 返回流式响应
        response = Response(
            stream_with_context(generate_progress_stream(file_id, filepath, params)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
        end_time = time.time()
        print(f"[响应生成] 投影 {file_id} 处理开始，初始化用时: {end_time - start_time:.2f}秒")
        
        return response
        
    except Exception as e:
        error_trace = traceback.format_exc()
        error_msg = f"生成投影出错: {str(e)}"
        print(f"\n{'='*60}")
        print(error_msg)
        print(error_trace)
        print(f"{'='*60}")
        log_error(error_msg, error_trace)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_projection(file_id):
    """下载投影文件"""
    try:
        format_type = request.args.get('format', 'litematic').lower()
        
        if format_type not in ['litematic', 'schematic', 'structure', 'blueprint']:
            return jsonify({'error': '不支持的格式，支持: litematic, schematic, structure, blueprint'}), 400
        
        filename = f"{file_id}.{format_type}"
        filepath = os.path.join(app.config['PROJECTIONS_FOLDER'], filename)
        
        # 如果请求的格式不存在，尝试其他格式
        if not os.path.exists(filepath):
            # 尝试其他扩展名
            for ext in [format_type, 'schematic', 'litematic']:
                alt_filepath = os.path.join(app.config['PROJECTIONS_FOLDER'], f"{file_id}.{ext}")
                if os.path.exists(alt_filepath):
                    filepath = alt_filepath
                    filename = f"{file_id}.{ext}"
                    format_type = ext
                    print(f"[文件下载] 使用备用格式: {ext}")
                    break
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"[文件下载] {filename} ({file_size} 字节)")
            
            # 设置下载文件名
            if format_type == 'structure':
                download_name = f"redstone_music_{file_id[:8]}.nbt"
                mimetype = 'application/octet-stream'
            elif format_type == 'blueprint':
                download_name = f"redstone_music_{file_id[:8]}.json"
                mimetype = 'application/json'
            else:
                download_name = f"redstone_music_{file_id[:8]}.{format_type}"
                mimetype = 'application/octet-stream'
            
            return send_file(
                filepath,
                mimetype=mimetype,
                as_attachment=True,
                download_name=download_name
            )
        
        print(f"[文件不存在] {filename}")
        return jsonify({'error': '文件不存在或已过期'}), 404
    
    except Exception as e:
        error_msg = f"下载文件失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/list', methods=['GET'])
def list_projects():
    """列出所有项目"""
    try:
        projects = []
        
        # 支持的文件格式
        supported_extensions = ['.litematic', '.schematic', '.nbt', '.json']
        
        for filename in os.listdir(app.config['PROJECTIONS_FOLDER']):
            file_ext = None
            for ext in supported_extensions:
                if filename.endswith(ext):
                    file_ext = ext
                    break
            
            if file_ext:
                file_id = filename.replace(file_ext, '')
                filepath = os.path.join(app.config['PROJECTIONS_FOLDER'], filename)
                
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    modified_time = os.path.getmtime(filepath)
                    
                    # 确定格式类型
                    if file_ext == '.nbt':
                        file_format = 'structure'
                    elif file_ext == '.json':
                        file_format = 'blueprint'
                    else:
                        file_format = file_ext[1:]  # 去掉点号
                    
                    projects.append({
                        'file_id': file_id,
                        'name': f"RedstoneMusic_{file_id[:8]}",
                        'format': file_format,
                        'size': file_size,
                        'size_mb': f"{file_size / (1024 * 1024):.2f}",
                        'modified': datetime.fromtimestamp(modified_time).isoformat(),
                        'download_url': f"/api/download/{file_id}?format={file_format}"
                    })
        
        # 按修改时间排序
        projects.sort(key=lambda x: x['modified'], reverse=True)
        
        print(f"[项目列表] 找到 {len(projects)} 个项目")
        return jsonify({
            'success': True,
            'count': len(projects),
            'projects': projects
        })
        
    except Exception as e:
        error_msg = f"列出项目失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_files():
    """清理临时文件"""
    try:
        cleaned_count = cleanup_old_files(1)  # 清理1小时前的文件
        
        current_time = time.time()
        projection_cleaned = 0
        
        # 清理24小时前的投影文件
        for filename in os.listdir(app.config['PROJECTIONS_FOLDER']):
            filepath = os.path.join(app.config['PROJECTIONS_FOLDER'], filename)
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                if current_time - file_time > 86400:  # 24小时
                    try:
                        os.remove(filepath)
                        projection_cleaned += 1
                        print(f"[清理投影] {filename}")
                    except Exception as e:
                        print(f"[清理投影失败] {filename}: {e}")
        
        total_cleaned = cleaned_count + projection_cleaned
        
        print(f"[清理完成] 共删除 {total_cleaned} 个文件")
        return jsonify({
            'success': True, 
            'message': f'清理完成，共删除 {total_cleaned} 个文件',
            'details': {
                'uploads_cleaned': cleaned_count,
                'projections_cleaned': projection_cleaned
            }
        })
    except Exception as e:
        error_msg = f"清理文件失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST', 'PUT'])
def manage_config():
    """管理配置文件"""
    if not CONFIG_LOADER_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'ConfigLoader不可用'
        }), 501
    
    try:
        if request.method == 'GET':
            # 获取配置
            config_name = request.args.get('name', 'default')
            config_file = os.path.join(CONFIG_FOLDER, f"{config_name}.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                return jsonify({
                    'success': True,
                    'name': config_name,
                    'config': config_data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'配置文件不存在: {config_name}'
                }), 404
        
        elif request.method == 'POST':
            # 保存配置
            config_name = request.form.get('name', 'default')
            config_data = request.get_json() or {}
            
            config_file = os.path.join(CONFIG_FOLDER, f"{config_name}.json")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"[配置管理] 保存配置: {config_name}")
            return jsonify({
                'success': True,
                'message': f'配置已保存: {config_name}'
            })
        
        elif request.method == 'PUT':
            # 更新配置
            config_name = request.args.get('name', 'default')
            updates = request.get_json() or {}
            
            config_file = os.path.join(CONFIG_FOLDER, f"{config_name}.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {}
            
            # 深度合并
            def deep_merge(base, update):
                for key, value in update.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
            
            deep_merge(config_data, updates)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"[配置管理] 更新配置: {config_name}")
            return jsonify({
                'success': True,
                'message': f'配置已更新: {config_name}'
            })
    
    except Exception as e:
        error_msg = f"配置管理失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/presets', methods=['GET'])
def get_presets():
    """获取预设配置"""
    if not CONFIG_LOADER_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'ConfigLoader不可用'
        }), 501
    
    try:
        presets = {
            'basic': {
                'name': '基础配置',
                'description': '适合大多数音频的基本配置',
                'audio_processing': {
                    'eq_enabled': True,
                    'eq_bass': 1.2,
                    'eq_treble': 1.1
                },
                'redstone_mapping': {
                    'harmony_enabled': False,
                    'rhythm_complexity': 2
                }
            },
            'advanced': {
                'name': '高级配置',
                'description': '启用所有音频效果和智能和声',
                'audio_processing': {
                    'echo_enabled': True,
                    'reverb_enabled': True,
                    'eq_enabled': True,
                    'compressor_enabled': True
                },
                'redstone_mapping': {
                    'harmony_enabled': True,
                    'harmony_type': 'chords',
                    'rhythm_complexity': 4,
                    'dynamics': 4
                },
                'projection_generation': {
                    'decorate': True,
                    'include_tile_entities': True
                }
            },
            'performance': {
                'name': '性能配置',
                'description': '优化处理速度，适合长音频',
                'performance': {
                    'max_notes': 1000,
                    'enable_caching': True
                },
                'redstone_mapping': {
                    'harmony_enabled': False,
                    'rhythm_complexity': 1
                }
            }
        }
        
        return jsonify({
            'success': True,
            'presets': presets
        })
    
    except Exception as e:
        error_msg = f"获取预设失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoints():
    """测试端点功能"""
    try:
        test_results = []
        
        # 测试1: 健康检查
        try:
            import requests
            response = requests.get('http://localhost:5000/api/health', timeout=5)
            test_results.append({
                'endpoint': '/api/health',
                'status': 'passed' if response.status_code == 200 else 'failed',
                'details': f"HTTP {response.status_code}"
            })
        except Exception as e:
            test_results.append({
                'endpoint': '/api/health',
                'status': 'failed',
                'details': str(e)
            })
        
        # 测试2: 列出项目
        try:
            response = requests.get('http://localhost:5000/api/list', timeout=5)
            test_results.append({
                'endpoint': '/api/list',
                'status': 'passed' if response.status_code == 200 else 'failed',
                'details': f"HTTP {response.status_code}"
            })
        except Exception as e:
            test_results.append({
                'endpoint': '/api/list',
                'status': 'failed',
                'details': str(e)
            })
        
        # 测试3: 清理文件
        try:
            response = requests.post('http://localhost:5000/api/cleanup', timeout=5)
            test_results.append({
                'endpoint': '/api/cleanup',
                'status': 'passed' if response.status_code == 200 else 'failed',
                'details': f"HTTP {response.status_code}"
            })
        except Exception as e:
            test_results.append({
                'endpoint': '/api/cleanup',
                'status': 'failed',
                'details': str(e)
            })
        
        # 总结
        passed_tests = sum(1 for test in test_results if test['status'] == 'passed')
        total_tests = len(test_results)
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'summary': {
                'passed': passed_tests,
                'total': total_tests,
                'percentage': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        })
    
    except Exception as e:
        error_msg = f"测试失败: {str(e)}"
        print(error_msg)
        log_error(error_msg, traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug_info', methods=['GET'])
def debug_info():
    """调试信息端点"""
    try:
        import platform
        
        return jsonify({
            'system': {
                'platform': platform.platform(),
                'python_version': sys.version,
                'python_executable': sys.executable,
                'current_directory': os.getcwd(),
                'cpu_count': os.cpu_count(),
                'memory_info': dict(os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else {})
            },
            'flask': {
                'debug': app.debug,
                'testing': app.testing,
                'secret_key_set': bool(app.secret_key)
            },
            'directories': {
                'uploads': {
                    'path': app.config['UPLOAD_FOLDER'],
                    'exists': os.path.exists(app.config['UPLOAD_FOLDER']),
                    'writable': os.access(app.config['UPLOAD_FOLDER'], os.W_OK),
                    'files': len(os.listdir(app.config['UPLOAD_FOLDER']))
                },
                'projections': {
                    'path': app.config['PROJECTIONS_FOLDER'],
                    'exists': os.path.exists(app.config['PROJECTIONS_FOLDER']),
                    'writable': os.access(app.config['PROJECTIONS_FOLDER'], os.W_OK),
                    'files': len(os.listdir(app.config['PROJECTIONS_FOLDER']))
                }
            },
            'process': {
                'pid': os.getpid(),
                'uid': os.getuid() if hasattr(os, 'getuid') else None,
                'gid': os.getgid() if hasattr(os, 'getgid') else None
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'success': False,
        'error': f'文件太大。最大允许大小: {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB'
    }), 413

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': '端点不存在'}), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_trace = traceback.format_exc() if app.debug else None
    error_msg = f"服务器内部错误: {str(error)}"
    log_error(error_msg, error_trace)
    
    return jsonify({
        'success': False,
        'error': '服务器内部错误',
        'trace': error_trace
    }), 500

# 启动时清理旧文件
print("\n" + "="*80)
print("Minecraft红石音乐投影生成器 - 增强版后端服务器")
print("="*80)
print(f"版本: 2.3.0")
print(f"启动时间: {datetime.now().isoformat()}")
print(f"服务器地址: http://localhost:5000")
print(f"前端地址: http://localhost:8080")
print(f"健康检查: http://localhost:5000/api/health")
print(f"调试信息: http://localhost:5000/api/debug_info")
print("="*80)

print("\n新增功能:")
print("1. ✓ 音频效果处理 (回声、混响、均衡器、压缩器、合唱)")
print("2. ✓ 智能红石映射 (和声、多乐器策略、节奏控制)")
print("3. ✓ 多格式支持 (Schematic、Litematic、Structure、Blueprint)")
print("4. ✓ 配置管理系统 (预设、保存、加载)")
print("5. ✓ 向后兼容 (原有API完全支持)")
print("\n按 Ctrl+C 停止服务器\n")
print("="*80)

print("\n启动时清理旧文件...")
cleaned = cleanup_old_files(1)
print(f"清理了 {cleaned} 个旧文件")

if __name__ == '__main__':
    try:
        # 设置调试模式
        debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
        
        app.run(
            debug=debug_mode,
            host='0.0.0.0',
            port=5000,
            threaded=True,
            use_reloader=False  # 避免重复启动
        )
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
        # 清理临时文件
        try:
            cleanup_old_files(0)  # 清理所有临时文件
        except:
            pass
        print("服务器已关闭")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)