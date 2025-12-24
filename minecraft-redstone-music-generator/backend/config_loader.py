"""
配置管理模块 - 用于管理所有配置选项
"""

import json
import yaml
import os

class ConfigLoader:
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config = self.load_default_config()
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
    
    def load_default_config(self):
        """加载默认配置"""
        return {
            'audio_processing': {
                'echo_enabled': False,
                'echo_delay': 0.3,
                'echo_decay': 0.5,
                'reverb_enabled': False,
                'reverb_size': 0.5,
                'reverb_damping': 0.5,
                'eq_enabled': False,
                'eq_bass': 1.0,
                'eq_mid': 1.0,
                'eq_treble': 1.0,
                'compressor_enabled': False,
                'compressor_threshold': 0.5,
                'compressor_ratio': 4.0,
                'compressor_attack': 0.01,
                'compressor_release': 0.1,
                'chorus_enabled': False,
                'chorus_depth': 0.5,
                'chorus_rate': 0.5,
                'chorus_mix': 0.5
            },
            'redstone_mapping': {
                'auto_tune': True,
                'harmony_enabled': False,
                'harmony_type': 'chords',
                'instrument_strategy': 'frequency',
                'rhythm_complexity': 3,
                'dynamics': 3,
                'min_note_interval': 2
            },
            'projection_generation': {
                'format': 'schematic',
                'height': 6,
                'base_block': 'stone',
                'decorate': True,
                'include_entities': False,
                'include_tile_entities': True,
                'schematic_version': 2,
                'author': 'RedstoneMusicGenerator'
            },
            'performance': {
                'max_notes': 500,
                'max_file_size_mb': 50,
                'enable_caching': True,
                'cleanup_temp_files': True
            }
        }
    
    def load_config(self, config_file):
        """从文件加载配置"""
        try:
            ext = os.path.splitext(config_file)[1].lower()
            
            if ext == '.json':
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
            elif ext in ['.yaml', '.yml']:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
            else:
                print(f"[配置] 不支持的文件格式: {ext}")
                return
            
            # 深度合并配置
            self._deep_merge(self.config, loaded_config)
            print(f"[配置] 已从 {config_file} 加载配置")
            
        except Exception as e:
            print(f"[配置] 加载配置文件失败: {e}")
    
    def save_config(self, config_file=None):
        """保存配置到文件"""
        if config_file is None:
            config_file = self.config_file
        
        if not config_file:
            print("[配置] 未指定配置文件路径")
            return
        
        try:
            ext = os.path.splitext(config_file)[1].lower()
            
            if ext == '.json':
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
            elif ext in ['.yaml', '.yml']:
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(self.config, f, allow_unicode=True)
            else:
                print(f"[配置] 不支持的文件格式: {ext}")
                return
            
            print(f"[配置] 已保存配置到 {config_file}")
            
        except Exception as e:
            print(f"[配置] 保存配置文件失败: {e}")
    
    def _deep_merge(self, base, update):
        """深度合并两个字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def validate(self):
        """验证配置有效性"""
        errors = []
        
        # 验证音频处理配置
        audio_config = self.config.get('audio_processing', {})
        if audio_config.get('echo_decay', 0) < 0 or audio_config.get('echo_decay', 0) > 1:
            errors.append("回声衰减系数应在0-1之间")
        
        # 验证红石映射配置
        mapping_config = self.config.get('redstone_mapping', {})
        if mapping_config.get('rhythm_complexity', 1) < 1 or mapping_config.get('rhythm_complexity', 1) > 5:
            errors.append("节奏复杂度应在1-5之间")
        
        # 验证性能配置
        perf_config = self.config.get('performance', {})
        if perf_config.get('max_notes', 100) < 10 or perf_config.get('max_notes', 100) > 5000:
            errors.append("最大音符数应在10-5000之间")
        
        return errors
    
    def get_preset(self, preset_name):
        """获取预设配置"""
        presets = {
            'basic': {
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
        
        return presets.get(preset_name, {})
    
    def apply_preset(self, preset_name):
        """应用预设配置"""
        preset = self.get_preset(preset_name)
        if preset:
            self._deep_merge(self.config, preset)
            print(f"[配置] 已应用预设: {preset_name}")
            return True
        else:
            print(f"[配置] 预设不存在: {preset_name}")
            return False