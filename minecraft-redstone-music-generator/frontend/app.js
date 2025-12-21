// 前端应用程序逻辑
class RedstoneMusicGenerator {
    constructor() {
        this.audioContext = null;
        this.audioBuffer = null;
        this.isAudioLoaded = false;
        this.currentAudioSource = null;
        this.isPlaying = false;
        this.currentFile = null;
        
        // 后端API地址
        this.apiBaseUrl = 'http://localhost:5000/api';
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initAudioContext();
        this.updateSliderValues();
    }
    
    bindEvents() {
        // 文件上传相关
        document.getElementById('dropZone').addEventListener('click', () => document.getElementById('fileInput').click());
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));
        
        // 拖放功能
        const dropZone = document.getElementById('dropZone');
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) this.handleFileSelect(e.dataTransfer.files[0]);
        });
        
        // 滑块事件
        document.getElementById('pitchSlider').addEventListener('input', () => this.updateSliderValues());
        document.getElementById('octaveSlider').addEventListener('input', () => this.updateSliderValues());
        document.getElementById('speedSlider').addEventListener('input', () => this.updateSliderValues());
        document.getElementById('densitySlider').addEventListener('input', () => this.updateSliderValues());
        document.getElementById('maxNotesSlider').addEventListener('input', () => this.updateSliderValues());
        
        // 按钮事件
        document.getElementById('resetBtn').addEventListener('click', () => this.resetAudio());
        document.getElementById('previewBtn').addEventListener('click', () => this.previewAudio());
        document.getElementById('generateBtn').addEventListener('click', () => this.generateProjection());
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadProjection('litematic'));
        document.getElementById('schematicBtn').addEventListener('click', () => this.downloadProjection('schematic'));
        
        // 音频控制
        document.getElementById('playBtn').addEventListener('click', () => this.playAudio());
        document.getElementById('pauseBtn').addEventListener('click', () => this.pauseAudio());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopAudio());
        document.getElementById('volumeSlider').addEventListener('input', (e) => this.setVolume(e.target.value / 100));
        
        // 循环播放
        document.getElementById('loopCheckbox').addEventListener('change', (e) => {
            if (this.audioBuffer) {
                this.audioBuffer.loop = e.target.checked;
            }
        });
    }
    
    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            this.showStatus('浏览器不支持Web Audio API', 'error');
        }
    }
    
    async handleFileSelect(file) {
        // 检查文件类型
        const validTypes = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3', 'audio/x-m4a', 'audio/aac'];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|ogg|m4a|aac)$/i)) {
            this.showStatus('请选择有效的音频文件 (MP3, WAV, OGG, M4A, AAC)', 'error');
            return;
        }
        
        this.currentFile = file;
        
        // 显示文件信息
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = this.formatFileSize(file.size);
        document.getElementById('fileDuration').textContent = '计算中...';
        document.getElementById('fileInfo').classList.add('active');
        
        // 创建音频URL用于播放
        const audioURL = URL.createObjectURL(file);
        const audioElement = new Audio(audioURL);
        
        audioElement.addEventListener('loadedmetadata', () => {
            document.getElementById('fileDuration').textContent = this.formatDuration(audioElement.duration);
            document.getElementById('totalTime').textContent = this.formatDuration(audioElement.duration);
        });
        
        // 设置音频源
        audioElement.addEventListener('canplay', () => {
            this.audioElement = audioElement;
            this.isAudioLoaded = true;
            this.drawWaveform(file);
            this.showStatus('音频文件加载成功！', 'success');
        });
        
        // 监听时间更新
        audioElement.addEventListener('timeupdate', () => {
            document.getElementById('currentTime').textContent = this.formatDuration(audioElement.currentTime);
        });
        
        // 监听播放结束
        audioElement.addEventListener('ended', () => {
            this.isPlaying = false;
            document.getElementById('playBtn').innerHTML = '<i class="fas fa-play"></i>';
        });
    }
    
    playAudio() {
        if (!this.isAudioLoaded) {
            this.showStatus('请先加载音频文件', 'error');
            return;
        }
        
        if (this.isPlaying) {
            this.audioElement.pause();
            this.isPlaying = false;
            document.getElementById('playBtn').innerHTML = '<i class="fas fa-play"></i>';
        } else {
            this.audioElement.play();
            this.isPlaying = true;
            document.getElementById('playBtn').innerHTML = '<i class="fas fa-pause"></i>';
        }
    }
    
    pauseAudio() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.isPlaying = false;
            document.getElementById('playBtn').innerHTML = '<i class="fas fa-play"></i>';
        }
    }
    
    stopAudio() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
            this.isPlaying = false;
            document.getElementById('playBtn').innerHTML = '<i class="fas fa-play"></i>';
            document.getElementById('currentTime').textContent = '0:00';
        }
    }
    
    setVolume(volume) {
        if (this.audioElement) {
            this.audioElement.volume = volume;
        }
    }
    
    async drawWaveform(file) {
        // 这里简化波形绘制，实际项目中可以使用Web Audio API分析音频数据
        const canvas = document.getElementById('waveformCanvas');
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height;
        
        // 清除画布
        ctx.clearRect(0, 0, width, height);
        
        // 绘制简单的波形背景
        ctx.fillStyle = 'rgba(42, 54, 71, 0.5)';
        ctx.fillRect(0, 0, width, height);
        
        // 绘制波形线
        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#4dabf7';
        ctx.moveTo(0, height / 2);
        
        // 生成简单的模拟波形
        for (let i = 0; i < width; i++) {
            const x = i;
            const y = height / 2 + Math.sin(i * 0.05 + Date.now() * 0.001) * 30;
            ctx.lineTo(x, y);
        }
        
        ctx.stroke();
        
        // 绘制中心线
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 1;
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
    }
    
    updateSliderValues() {
        document.getElementById('pitchValue').textContent = document.getElementById('pitchSlider').value;
        document.getElementById('octaveValue').textContent = document.getElementById('octaveSlider').value;
        document.getElementById('speedValue').textContent = parseFloat(document.getElementById('speedSlider').value).toFixed(1) + 'x';
        
        const densityValue = parseInt(document.getElementById('densitySlider').value);
        const densityText = ['低', '中', '高'];
        document.getElementById('densityValue').textContent = densityText[densityValue - 1];
        
        document.getElementById('maxNotesValue').textContent = document.getElementById('maxNotesSlider').value;
    }
    
    resetAudio() {
        if (!this.isAudioLoaded) {
            this.showStatus('请先加载音频文件', 'error');
            return;
        }
        
        document.getElementById('pitchSlider').value = 0;
        document.getElementById('octaveSlider').value = 0;
        document.getElementById('speedSlider').value = 1;
        document.getElementById('densitySlider').value = 2;
        
        this.updateSliderValues();
        this.showStatus('音频参数已重置', 'success');
    }
    
    async previewAudio() {
        if (!this.isAudioLoaded) {
            this.showStatus('请先加载音频文件', 'error');
            return;
        }
        
        this.showStatus('音频处理中...', 'info');
        
        // 创建FormData对象
        const formData = new FormData();
        formData.append('audio', this.currentFile);
        formData.append('pitch', document.getElementById('pitchSlider').value);
        formData.append('octave', document.getElementById('octaveSlider').value);
        formData.append('speed', document.getElementById('speedSlider').value);
        formData.append('density', document.getElementById('densitySlider').value);
        formData.append('preview', 'true');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/preview`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // 创建音频播放
                const audio = new Audio(data.audio_url);
                audio.play();
                this.showStatus('正在播放处理后的音频...', 'success');
                
                audio.addEventListener('ended', () => {
                    this.showStatus('试听完成', 'success');
                });
            } else {
                this.showStatus(`处理失败: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showStatus(`试听失败: ${error.message}`, 'error');
        }
    }
    
    async generateProjection() {
        if (!this.isAudioLoaded) {
            this.showStatus('请先加载音频文件', 'error');
            return;
        }
        
        // 显示进度条
        document.getElementById('progressContainer').classList.add('active');
        this.updateProgress(0, '准备上传文件...');
        
        // 创建FormData对象
        const formData = new FormData();
        formData.append('audio', this.currentFile);
        formData.append('pitch', document.getElementById('pitchSlider').value);
        formData.append('octave', document.getElementById('octaveSlider').value);
        formData.append('speed', document.getElementById('speedSlider').value);
        formData.append('density', document.getElementById('densitySlider').value);
        formData.append('max_notes', document.getElementById('maxNotesSlider').value);
        formData.append('auto_tune', document.getElementById('autoTuneCheckbox').checked);
        
        try {
            this.updateProgress(10, '上传文件中...');
            
            // 使用Fetch API发送请求
            const response = await fetch(`${this.apiBaseUrl}/generate`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }
            
            // 处理流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let result = '';
            
            while (true) {
                this.updateProgress(30, '处理音频数据...');
                
                const { done, value } = await reader.read();
                if (done) break;
                
                result += decoder.decode(value);
                
                // 尝试解析进度信息
                try {
                    const lines = result.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.substring(6));
                            if (data.progress) {
                                this.updateProgress(30 + data.progress * 0.6, data.message || '生成红石投影...');
                            }
                        }
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
            
            // 解析最终响应
            const lines = result.split('\n');
            let finalData = null;
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.complete) {
                            finalData = data;
                        }
                    } catch (e) {
                        // 忽略错误
                    }
                }
            }
            
            if (finalData && finalData.success) {
                this.updateProgress(100, '生成完成！');
                
                // 更新预览面板
                document.getElementById('statNotes').textContent = finalData.stats.notes;
                document.getElementById('statLength').textContent = `${finalData.stats.redstone_length} 格`;
                document.getElementById('statTime').textContent = `${finalData.stats.duration.toFixed(1)} 秒`;
                document.getElementById('statSize').textContent = `${finalData.stats.file_size} KB`;
                
                // 更新投影详情
                const detailsHtml = `
                    <p><strong>投影名称:</strong> ${finalData.projection.name}</p>
                    <p><strong>尺寸:</strong> ${finalData.projection.dimensions.width}×${finalData.projection.dimensions.height}×${finalData.projection.dimensions.length}</p>
                    <p><strong>音符盒数量:</strong> ${finalData.projection.note_blocks}</p>
                    <p><strong>红石粉数量:</strong> ${finalData.projection.redstone_dust}</p>
                    <p><strong>中继器数量:</strong> ${finalData.projection.repeaters}</p>
                    <p><strong>文件ID:</strong> ${finalData.file_id}</p>
                `;
                document.getElementById('projectionDetails').innerHTML = detailsHtml;
                
                // 显示预览和下载按钮
                document.getElementById('projectionPreview').classList.add('active');
                document.getElementById('downloadBtn').style.display = 'block';
                document.getElementById('schematicBtn').style.display = 'block';
                document.getElementById('downloadBtn').dataset.fileId = finalData.file_id;
                document.getElementById('schematicBtn').dataset.fileId = finalData.file_id;
                
                this.showStatus('红石音乐投影生成成功！', 'success');
                
                // 3秒后隐藏进度条
                setTimeout(() => {
                    document.getElementById('progressContainer').classList.remove('active');
                }, 3000);
            } else {
                throw new Error(finalData?.error || '生成失败');
            }
        } catch (error) {
            this.updateProgress(0, '');
            document.getElementById('progressContainer').classList.remove('active');
            this.showStatus(`生成失败: ${error.message}`, 'error');
        }
    }
    
    async downloadProjection(format) {
        const fileId = document.getElementById('downloadBtn').dataset.fileId;
        
        if (!fileId) {
            this.showStatus('请先生成投影文件', 'error');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/download/${fileId}?format=${format}`);
            
            if (!response.ok) {
                throw new Error(`下载失败: ${response.status}`);
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `redstone_music.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showStatus(`投影文件下载开始 (${format})`, 'success');
        } catch (error) {
            this.showStatus(`下载失败: ${error.message}`, 'error');
        }
    }
    
    updateProgress(percent, message) {
        document.getElementById('progressFill').style.width = `${percent}%`;
        document.getElementById('progressText').textContent = message;
    }
    
    showStatus(message, type) {
        const statusElement = document.getElementById('statusMessage');
        statusElement.textContent = message;
        statusElement.className = `status-message ${type}`;
        
        // 3秒后自动隐藏成功/信息消息
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                statusElement.className = 'status-message';
            }, 3000);
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RedstoneMusicGenerator();
});