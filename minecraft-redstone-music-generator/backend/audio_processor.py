"""
音频处理模块 - 修复音频试听问题
"""

import numpy as np
import librosa
import soundfile as sf
import tempfile
import os
import shutil
from scipy import signal

class AudioProcessor:
    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.sample_rate = None
        self.audio_data = None
        self.duration = None
        
    def load_audio(self):
        """加载音频文件"""
        try:
            # 使用librosa加载音频
            self.audio_data, self.sample_rate = librosa.load(
                self.audio_path, 
                sr=None,
                mono=True,
                duration=None
            )
            
            if len(self.audio_data) == 0:
                raise ValueError("音频文件为空或损坏")
            
            self.duration = len(self.audio_data) / self.sample_rate
            print(f"[音频加载] 时长: {self.duration:.2f}秒, 采样率: {self.sample_rate}Hz")
            return self.audio_data
            
        except Exception as e:
            print(f"音频加载失败: {str(e)}")
            raise Exception(f"加载音频失败: {str(e)}")
    
    def adjust_pitch(self, audio_data, semitones=0, octaves=0):
        """调整音频音调"""
        try:
            total_semitones = semitones + (octaves * 12)
            if total_semitones == 0:
                return audio_data
            
            print(f"[音调调整] {total_semitones} 半音")
            pitched_audio = librosa.effects.pitch_shift(
                y=audio_data,
                sr=self.sample_rate,
                n_steps=total_semitones
            )
            return pitched_audio
        except Exception as e:
            print(f"音调调整失败: {e}")
            return audio_data
    
    def adjust_speed(self, audio_data, speed=1.0):
        """调整音频播放速度"""
        try:
            if speed == 1.0:
                return audio_data
            
            print(f"[速度调整] {speed}倍")
            time_stretched_audio = librosa.effects.time_stretch(
                y=audio_data,
                rate=speed
            )
            
            new_duration = len(time_stretched_audio) / self.sample_rate
            print(f"[速度调整] 新时长: {new_duration:.2f}秒")
            return time_stretched_audio
        except Exception as e:
            print(f"速度调整失败: {e}")
            return audio_data
    
    def apply_effects(self, audio_data, effects_config):
        """
        应用音频效果 - 简化版，确保稳定
        
        参数:
            audio_data: 音频数据
            effects_config: 效果配置字典
            
        返回:
            应用效果后的音频数据
        """
        print(f"[音频效果] 开始应用效果...")
        print(f"[音频效果] 启用的效果: {[k for k, v in effects_config.items() if v and 'enabled' in k]}")
        
        result = audio_data.copy()
        
        try:
            # 回声效果
            if effects_config.get('echo_enabled', False):
                delay = effects_config.get('echo_delay', 0.3)
                decay = effects_config.get('echo_decay', 0.5)
                print(f"[回声效果] 延迟: {delay}秒, 衰减: {decay}")
                
                # 创建回声
                delay_samples = int(delay * self.sample_rate)
                if delay_samples < len(result):
                    echo = np.zeros_like(result)
                    echo[delay_samples:] = result[:-delay_samples] * decay
                    result = result + echo
            
            # 混响效果（简化版）
            if effects_config.get('reverb_enabled', False):
                print(f"[混响效果] 应用简化的混响")
                # 使用简单的延迟线模拟混响
                for i in range(3):
                    delay = int(0.03 * self.sample_rate * (1 + i * 0.5))
                    if delay < len(result):
                        delayed = np.zeros_like(result)
                        delayed[delay:] = result[:-delay] * (0.5 / (i + 1))
                        result = result + delayed
            
            # 均衡器效果
            if effects_config.get('eq_enabled', False):
                bass = effects_config.get('eq_bass', 1.0)
                mid = effects_config.get('eq_mid', 1.0)
                treble = effects_config.get('eq_treble', 1.0)
                print(f"[均衡器] 低音: {bass}, 中音: {mid}, 高音: {treble}")
                
                # 简单的均衡器实现
                if bass != 1.0 or mid != 1.0 or treble != 1.0:
                    # 这里简化处理，实际可以使用滤波器
                    result = self._simple_eq(result, bass, mid, treble)
            
            # 压缩器效果（简化版）
            if effects_config.get('compressor_enabled', False):
                threshold = effects_config.get('compressor_threshold', 0.5)
                print(f"[压缩器] 阈值: {threshold}")
                # 简单的压缩
                result = np.where(np.abs(result) > threshold, 
                                np.sign(result) * threshold + (result - np.sign(result) * threshold) * 0.5,
                                result)
            
            # 归一化防止爆音
            result = self.normalize_audio(result)
            
            print(f"[音频效果] 效果应用完成")
            return result
            
        except Exception as e:
            print(f"[音频效果] 应用效果失败: {e}")
            return audio_data
    
    def _simple_eq(self, audio_data, bass_gain, mid_gain, treble_gain):
        """简单的均衡器实现"""
        # 创建简单的滤波器
        # 低音增强（简单的低通滤波）
        if bass_gain != 1.0:
            b, a = signal.butter(2, 200 / (self.sample_rate / 2), 'low')
            bass = signal.filtfilt(b, a, audio_data)
            audio_data = audio_data + (bass * (bass_gain - 1.0))
        
        # 高音增强（简单的高通滤波）
        if treble_gain != 1.0:
            b, a = signal.butter(2, 2000 / (self.sample_rate / 2), 'high')
            treble = signal.filtfilt(b, a, audio_data)
            audio_data = audio_data + (treble * (treble_gain - 1.0))
        
        return self.normalize_audio(audio_data)
    
    def normalize_audio(self, audio_data):
        """归一化音频，防止爆音"""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0 and max_val < 0.95:  # 如果已经很小，不放大
            return audio_data
        elif max_val > 0:
            return audio_data / max_val * 0.95
        return audio_data
    
    def extract_notes(self, max_notes=500, density=2, audio_duration=None):
        """提取音符"""
        try:
            if self.audio_data is None:
                self.load_audio()
            
            if audio_duration is None:
                audio_duration = self.duration
            
            print(f"[音符提取] 从{audio_duration:.2f}秒音频中提取最多{max_notes}个音符")
            
            notes = []
            
            # 使用节拍检测
            try:
                tempo, beat_frames = librosa.beat.beat_track(
                    y=self.audio_data, 
                    sr=self.sample_rate,
                    units='time'
                )
                
                if len(beat_frames) > 0:
                    print(f"[节拍检测] 检测到节奏: {tempo:.1f} BPM, {len(beat_frames)}个节拍点")
                    
                    for beat_time in beat_frames:
                        if beat_time > audio_duration:
                            continue
                        
                        # 分析节拍点的频率
                        start_sample = int(beat_time * self.sample_rate)
                        end_sample = min(start_sample + 2048, len(self.audio_data))
                        
                        if end_sample - start_sample < 512:
                            continue
                        
                        segment = self.audio_data[start_sample:end_sample]
                        frequencies, magnitudes = self._analyze_segment(segment)
                        
                        if len(frequencies) > 0:
                            main_freq = frequencies[np.argmax(magnitudes)]
                            volume = np.max(magnitudes) / 100.0
                            
                            if 50 < main_freq < 2000:
                                notes.append((beat_time, main_freq, volume))
            except Exception as e:
                print(f"[节拍检测] 失败: {e}")
            
            # 如果节拍点不够，使用均匀采样
            if len(notes) < max_notes // 2:
                print(f"[均匀采样] 节拍点不足，使用均匀采样")
                time_points = np.linspace(0, audio_duration * 0.9, max_notes - len(notes))
                
                for time_sec in time_points:
                    # 随机生成合理的频率和音量
                    freq = 220 + np.random.randint(0, 12) * 50
                    volume = 0.3 + 0.4 * np.random.random()
                    notes.append((time_sec, freq, volume))
            
            # 限制最终数量
            if len(notes) > max_notes:
                indices = np.linspace(0, len(notes)-1, max_notes, dtype=int)
                notes = [notes[i] for i in indices]
            
            # 按时间排序
            notes.sort(key=lambda x: x[0])
            
            print(f"[音符提取完成] 共提取 {len(notes)} 个音符")
            return notes
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[音符提取失败] 使用默认音符: {e}")
            
            # 生成默认音符
            default_notes = []
            for i in range(min(20, max_notes)):
                time = (i / min(20, max_notes)) * (audio_duration or 30)
                freq = 220 + (i * 50) % 800
                volume = 0.5
                default_notes.append((time, freq, volume))
            
            return default_notes
    
    def _analyze_segment(self, segment):
        """分析音频片段"""
        if len(segment) < 256:
            return [], []
        
        # 计算FFT
        fft = np.fft.rfft(segment)
        frequencies = np.fft.rfftfreq(len(segment), 1.0/self.sample_rate)
        magnitudes = np.abs(fft)
        
        # 过滤无效频率
        valid_idx = (frequencies > 50) & (frequencies < 2000)
        return frequencies[valid_idx], magnitudes[valid_idx]
    
    def save_audio(self, audio_data, output_path):
        """保存音频文件 - 修复保存问题"""
        temp_wav_path = None
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 创建临时WAV文件
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            
            print(f"[音频保存] 保存到临时文件: {temp_wav_path}")
            
            # 保存为WAV
            sf.write(temp_wav_path, audio_data, self.sample_rate)
            print(f"[音频保存] WAV保存成功: {temp_wav_path} ({len(audio_data)} 样本)")
            
            # 检查文件是否存在且大小大于0
            if os.path.exists(temp_wav_path) and os.path.getsize(temp_wav_path) > 0:
                print(f"[音频保存] 临时文件有效，大小: {os.path.getsize(temp_wav_path)} 字节")
                
                # 直接复制WAV文件（确保格式兼容）
                shutil.copy2(temp_wav_path, output_path)
                print(f"[音频保存] 已保存到: {output_path}")
                
                # 验证保存的文件
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"[音频保存] 验证成功: {output_path} 大小: {os.path.getsize(output_path)} 字节")
                else:
                    print(f"[错误] 保存的文件无效: {output_path}")
                    return False
            else:
                print(f"[错误] 临时文件无效或为空")
                return False
                
            return True
            
        except Exception as e:
            print(f"[错误] 保存音频失败: {str(e)}")
            # 尝试简单保存
            try:
                # 直接保存为numpy格式，然后转换为WAV
                np.save(output_path.replace('.wav', '.npy'), audio_data)
                # 尝试再次保存为WAV
                sf.write(output_path, audio_data, self.sample_rate)
                print(f"[备用保存] 已保存为WAV: {output_path}")
                return True
            except Exception as e2:
                print(f"[严重错误] 所有保存方法都失败: {e2}")
                return False
        finally:
            # 清理临时文件
            try:
                if temp_wav_path and os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
                    print(f"[清理] 删除临时文件: {temp_wav_path}")
            except Exception as e:
                print(f"[警告] 清理临时文件失败: {e}")