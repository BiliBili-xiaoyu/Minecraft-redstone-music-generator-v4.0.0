"""
红石映射模块 - 增强版
改进音符映射算法，支持智能和声、多乐器配置
"""

import numpy as np
from collections import defaultdict
import random

class RedstoneMapper:
    def __init__(self):
        """初始化红石映射器"""
        # Minecraft音符盒音高映射（0-24）
        self.note_pitches = list(range(25))
        
        # Minecraft音符频率表（半音阶）- 扩展更多音符
        self.minecraft_notes = {
            0: 185.00,   # F#3
            1: 196.00,   # G3
            2: 207.65,   # G#3
            3: 220.00,   # A3
            4: 233.08,   # A#3
            5: 246.94,   # B3
            6: 261.63,   # C4
            7: 277.18,   # C#4
            8: 293.66,   # D4
            9: 311.13,   # D#4
            10: 329.63,  # E4
            11: 349.23,  # F4
            12: 369.99,  # F#4
            13: 392.00,  # G4
            14: 415.30,  # G#4
            15: 440.00,  # A4
            16: 466.16,  # A#4
            17: 493.88,  # B4
            18: 523.25,  # C5
            19: 554.37,  # C#5
            20: 587.33,  # D5
            21: 622.25,  # D#5
            22: 659.25,  # E5
            23: 698.46,  # F5
            24: 739.99   # F#5
        }
        
        # 扩展乐器列表
        self.instruments = {
            'harp': {'range': (0, 24), 'color': 0, 'weight': 1.0},
            'bass': {'range': (0, 12), 'color': 1, 'weight': 0.8},
            'snare': {'range': (8, 20), 'color': 2, 'weight': 0.3},
            'hat': {'range': (12, 24), 'color': 3, 'weight': 0.2},
            'bassdrum': {'range': (0, 8), 'color': 4, 'weight': 0.5},
            'bell': {'range': (12, 24), 'color': 5, 'weight': 0.7},
            'flute': {'range': (8, 20), 'color': 6, 'weight': 0.6},
            'chime': {'range': (8, 24), 'color': 7, 'weight': 0.4},
            'guitar': {'range': (4, 20), 'color': 8, 'weight': 0.9},
            'xylophone': {'range': (8, 24), 'color': 9, 'weight': 0.5},
            'iron_xylophone': {'range': (8, 20), 'color': 10, 'weight': 0.4},
            'cow_bell': {'range': (8, 16), 'color': 11, 'weight': 0.3},
            'didgeridoo': {'range': (0, 12), 'color': 12, 'weight': 0.6},
            'bit': {'range': (4, 24), 'color': 13, 'weight': 0.8},
            'banjo': {'range': (4, 20), 'color': 14, 'weight': 0.7},
            'pling': {'range': (8, 24), 'color': 15, 'weight': 0.9}
        }
        
        # 和弦库
        self.chords = {
            'major': [0, 4, 7],        # 大三和弦
            'minor': [0, 3, 7],        # 小三和弦
            'diminished': [0, 3, 6],   # 减三和弦
            'augmented': [0, 4, 8],    # 增三和弦
            'sus2': [0, 2, 7],         # Sus2和弦
            'sus4': [0, 5, 7],         # Sus4和弦
            'major7': [0, 4, 7, 11],   # 大七和弦
            'minor7': [0, 3, 7, 10],   # 小七和弦
            'dominant7': [0, 4, 7, 10] # 属七和弦
        }
        
        # 音阶库
        self.scales = {
            'major': [0, 2, 4, 5, 7, 9, 11],      # 大调音阶
            'minor': [0, 2, 3, 5, 7, 8, 10],      # 小调音阶
            'pentatonic': [0, 2, 4, 7, 9],        # 五声音阶
            'blues': [0, 3, 5, 6, 7, 10],         # 蓝调音阶
            'harmonic_minor': [0, 2, 3, 5, 7, 8, 11], # 和声小调
            'dorian': [0, 2, 3, 5, 7, 9, 10],     # 多利亚调式
            'mixolydian': [0, 2, 4, 5, 7, 9, 10], # 混合利底亚调式
        }
        
        # 红石刻与秒的转换
        self.ticks_per_second = 10
        
        print("[红石映射器] 增强版初始化完成，支持智能和声和多乐器配置")
    
    def map_to_minecraft_enhanced(self, notes, config=None):
        """
        增强版映射算法
        
        参数:
            notes: 音频音符列表
            config: 配置字典，包含：
                - auto_tune: 自动调音
                - harmony_enabled: 启用和声
                - harmony_type: 和声类型（'chords', 'scale', 'parallel'）
                - instrument_strategy: 乐器策略（'frequency', 'random', 'pattern'）
                - rhythm_complexity: 节奏复杂度（1-5）
                - dynamics: 动态范围（1-5）
                
        返回:
            minecraft_notes: Minecraft音符列表
        """
        if config is None:
            config = {}
        
        auto_tune = config.get('auto_tune', True)
        harmony_enabled = config.get('harmony_enabled', False)
        harmony_type = config.get('harmony_type', 'chords')
        instrument_strategy = config.get('instrument_strategy', 'frequency')
        rhythm_complexity = config.get('rhythm_complexity', 3)
        dynamics = config.get('dynamics', 3)
        
        print(f"[增强映射] 配置: 和声={harmony_enabled}, 类型={harmony_type}, 乐器策略={instrument_strategy}")
        
        minecraft_notes = []
        
        if not notes:
            print("[增强映射] 警告: 输入音符列表为空")
            return minecraft_notes
        
        # 分析音频特征
        audio_features = self.analyze_audio_features(notes)
        
        # 根据节奏复杂度调整最小间隔
        min_interval = max(1, 6 - rhythm_complexity)  # 复杂度越高，间隔越小
        
        last_tick = -min_interval
        
        for idx, (time_sec, freq, volume) in enumerate(notes):
            # 时间映射
            target_tick = int(time_sec * self.ticks_per_second)
            
            # 节奏处理
            if idx > 0:
                time_diff = target_tick - last_tick
                if time_diff < min_interval:
                    target_tick = last_tick + min_interval
                elif rhythm_complexity > 3:
                    # 添加节奏变化
                    if idx % rhythm_complexity == 0:
                        target_tick += random.randint(-2, 2)
            
            # 频率映射
            if auto_tune:
                main_pitch = self._find_closest_pitch(freq)
            else:
                main_pitch = self._linear_map_pitch(freq)
            
            # 音量映射（考虑动态范围）
            base_power = self._map_volume_to_power(volume)
            if dynamics > 1:
                power_variation = random.randint(-dynamics, dynamics)
                redstone_power = max(1, min(15, base_power + power_variation))
            else:
                redstone_power = base_power
            
            # 主音符
            main_instrument = self._select_instrument_enhanced(freq, instrument_strategy, audio_features)
            
            main_note = {
                'time_ticks': target_tick,
                'pitch': main_pitch,
                'instrument': main_instrument,
                'power': redstone_power,
                'original_freq': freq,
                'original_volume': volume,
                'note_type': 'main'
            }
            minecraft_notes.append(main_note)
            
            # 和声处理
            if harmony_enabled and volume > 0.2:  # 只有音量足够的音才添加和声
                harmony_notes = self._generate_harmony(
                    main_pitch, freq, volume, harmony_type, audio_features
                )
                
                for harmony_note in harmony_notes:
                    # 和声音符稍微延迟（模仿真实和声）
                    harmony_tick = target_tick + random.randint(0, 2)
                    harmony_note['time_ticks'] = harmony_tick
                    harmony_note['power'] = max(1, redstone_power - random.randint(1, 3))
                    harmony_note['note_type'] = 'harmony'
                    minecraft_notes.append(harmony_note)
            
            last_tick = target_tick
        
        # 按时间排序
        minecraft_notes.sort(key=lambda x: x['time_ticks'])
        
        print(f"[增强映射] 生成完成: {len(minecraft_notes)} 个音符")
        return minecraft_notes
    
    def analyze_audio_features(self, notes):
        """分析音频特征"""
        if not notes:
            return {}
        
        times = [t for t, _, _ in notes]
        freqs = [f for _, f, _ in notes]
        volumes = [v for _, _, v in notes]
        
        features = {
            'avg_freq': np.mean(freqs) if freqs else 440,
            'avg_volume': np.mean(volumes) if volumes else 0.5,
            'freq_range': (min(freqs), max(freqs)) if freqs else (220, 880),
            'duration': max(times) - min(times) if len(times) > 1 else 0,
            'tempo': self._estimate_tempo(times),
            'key': self._estimate_key(freqs)
        }
        
        return features
    
    def _estimate_tempo(self, times):
        """估计节奏"""
        if len(times) < 3:
            return 120  # 默认120BPM
        
        intervals = []
        for i in range(1, len(times)):
            intervals.append(times[i] - times[i-1])
        
        if intervals:
            avg_interval = np.mean(intervals)
            if avg_interval > 0:
                return 60 / avg_interval
        
        return 120
    
    def _estimate_key(self, freqs):
        """估计调性"""
        if not freqs:
            return 'C'
        
        # 将频率转换为音符
        pitches = []
        for freq in freqs:
            pitch = self._find_closest_pitch(freq)
            pitch_class = pitch % 12
            pitches.append(pitch_class)
        
        # 统计最常见的音级
        if pitches:
            pitch_counts = np.bincount(pitches, minlength=12)
            main_pitch = np.argmax(pitch_counts)
            
            # 转换为调名
            pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            return pitch_names[main_pitch]
        
        return 'C'
    
    def _generate_harmony(self, main_pitch, freq, volume, harmony_type, audio_features):
        """生成和声音符"""
        harmony_notes = []
        
        if harmony_type == 'chords':
            # 和弦和声
            chord_type = random.choice(list(self.chords.keys()))
            chord_offsets = self.chords[chord_type]
            
            for offset in chord_offsets[1:]:  # 跳过根音
                harmony_pitch = (main_pitch + offset) % 25
                harmony_instrument = self._select_harmony_instrument(freq)
                
                harmony_note = {
                    'pitch': harmony_pitch,
                    'instrument': harmony_instrument,
                    'original_freq': freq * (2 ** (offset/12))
                }
                harmony_notes.append(harmony_note)
        
        elif harmony_type == 'scale':
            # 音阶和声
            scale_name = random.choice(list(self.scales.keys()))
            scale_offsets = self.scales[scale_name]
            
            # 选择音阶中的音符（避免太多和声）
            num_harmony = random.randint(1, 2)
            selected_offsets = random.sample(scale_offsets[1:], min(num_harmony, len(scale_offsets)-1))
            
            for offset in selected_offsets:
                harmony_pitch = (main_pitch + offset) % 25
                harmony_instrument = self._select_harmony_instrument(freq)
                
                harmony_note = {
                    'pitch': harmony_pitch,
                    'instrument': harmony_instrument,
                    'original_freq': freq * (2 ** (offset/12))
                }
                harmony_notes.append(harmony_note)
        
        elif harmony_type == 'parallel':
            # 平行和声（三度或六度）
            interval = random.choice([3, 4, 5, 7])  # 小三度、大三度、纯四度、纯五度
            harmony_pitch = (main_pitch + interval) % 25
            harmony_instrument = self._select_harmony_instrument(freq)
            
            harmony_notes.append({
                'pitch': harmony_pitch,
                'instrument': harmony_instrument,
                'original_freq': freq * (2 ** (interval/12))
            })
        
        return harmony_notes
    
    def _select_instrument_enhanced(self, freq, strategy, audio_features):
        """增强版乐器选择"""
        if strategy == 'frequency':
            # 基于频率选择
            if freq < 150:
                return 'bass'
            elif freq < 250:
                return 'bassdrum'
            elif freq < 350:
                return 'snare'
            elif freq < 450:
                return 'harp'
            elif freq < 550:
                return 'bell'
            elif freq < 650:
                return 'flute'
            else:
                return 'pling'
        
        elif strategy == 'random':
            # 随机选择，但考虑频率范围
            valid_instruments = []
            for inst_name, inst_info in self.instruments.items():
                min_range, max_range = inst_info['range']
                if min_range <= (freq / 30) <= max_range:  # 粗略估计
                    valid_instruments.append(inst_name)
            
            if valid_instruments:
                return random.choice(valid_instruments)
            return 'harp'
        
        elif strategy == 'pattern':
            # 模式选择（根据时间位置）
            avg_freq = audio_features.get('avg_freq', 440)
            
            if freq < avg_freq * 0.7:
                return random.choice(['bass', 'didgeridoo'])
            elif freq > avg_freq * 1.3:
                return random.choice(['bell', 'pling', 'chime'])
            else:
                return random.choice(['harp', 'guitar', 'banjo'])
        
        # 默认策略
        return 'harp'
    
    def _select_harmony_instrument(self, freq):
        """选择和声乐器"""
        if freq < 300:
            return random.choice(['bass', 'didgeridoo'])
        else:
            return random.choice(['harp', 'guitar', 'banjo', 'flute'])
    
    def _find_closest_pitch(self, frequency):
        """找到最接近的Minecraft音高"""
        closest_pitch = 0
        min_diff = float('inf')
        
        for pitch, note_freq in self.minecraft_notes.items():
            diff = abs(note_freq - frequency)
            if diff < min_diff:
                min_diff = diff
                closest_pitch = pitch
        
        return closest_pitch
    
    def _linear_map_pitch(self, frequency):
        """线性映射频率到音高"""
        min_freq = 100.0
        max_freq = 800.0
        
        if frequency < min_freq:
            frequency = min_freq
        elif frequency > max_freq:
            frequency = max_freq
        
        pitch = int(((frequency - min_freq) / (max_freq - min_freq)) * 24)
        
        return max(0, min(24, pitch))
    
    def _map_volume_to_power(self, volume):
        """映射音量到红石信号强度"""
        power = int(volume * 14) + 1
        return max(1, min(15, power))
    
    # 保持原有方法兼容性
    def map_to_minecraft(self, notes, auto_tune=True, audio_duration=None):
        """保持原有接口兼容"""
        result = self.map_to_minecraft_enhanced(notes, {
            'auto_tune': auto_tune,
            'harmony_enabled': False,
            'instrument_strategy': 'frequency'
        })
        return result if result is not None else []
    
    def optimize_circuit(self, minecraft_notes, max_ticks=1000):
        """电路优化（原有方法）"""
        # 安全检查：确保输入不为None
        if minecraft_notes is None:
            print("[电路优化] 警告: 输入音符列表为None，返回空列表")
            return []
        
        # 安全检查：确保是列表
        if not isinstance(minecraft_notes, list):
            print(f"[电路优化] 警告: 输入类型不是列表，而是{type(minecraft_notes)}，返回空列表")
            return []
        
        # 如果没有音符，直接返回
        if len(minecraft_notes) == 0:
            return minecraft_notes
        
        print(f"[电路优化] 开始优化 {len(minecraft_notes)} 个音符")
        
        try:
            # 简单的优化逻辑：合并时间上非常接近的音符
            optimized_notes = []
            last_note = None
            
            for note in sorted(minecraft_notes, key=lambda x: x.get('time_ticks', 0)):
                # 确保note是字典且有time_ticks
                if not isinstance(note, dict) or 'time_ticks' not in note:
                    print(f"[电路优化] 警告: 跳过无效音符: {note}")
                    continue
                
                current_tick = note['time_ticks']
                
                if last_note is None:
                    optimized_notes.append(note)
                    last_note = note
                else:
                    last_tick = last_note['time_ticks']
                    
                    # 如果两个音符的时间太近（小于2刻），合并它们
                    if current_tick - last_tick < 2:
                        # 选择音量较大的音符
                        current_power = note.get('power', 1)
                        last_power = last_note.get('power', 1)
                        
                        if current_power > last_power:
                            # 用当前音符替换上一个音符
                            optimized_notes[-1] = note
                            last_note = note
                        # 否则保持上一个音符
                    else:
                        optimized_notes.append(note)
                        last_note = note
            
            # 限制最大刻数
            if max_ticks > 0:
                optimized_notes = [note for note in optimized_notes if note['time_ticks'] <= max_ticks]
            
            original_count = len(minecraft_notes)
            optimized_count = len(optimized_notes)
            
            if optimized_count < original_count:
                print(f"[电路优化] {original_count} -> {optimized_count} 个音符 (减少 {original_count - optimized_count})")
            else:
                print(f"[电路优化] 未减少音符数量，保持 {optimized_count} 个音符")
            
            return optimized_notes
            
        except Exception as e:
            print(f"[电路优化] 优化过程中出错: {e}")
            # 出错时返回原始列表
            return minecraft_notes