# Minecraft红石音乐投影生成器 
 
一个可以将音频文件转换为Minecraft红石音乐投影文件的工具 
 
## 项目结构 
 
``` 
minecraft-redstone-music-generator/ 
├── frontend/                    # 前端界面 
│   ├── index.html 
│   ├── styles.css 
│   └── app.js 
├── backend/                    # 后端处理 
│   ├── server.py 
│   ├── audio_processor.py 
│   ├── redstone_mapper.py 
│   ├── litematic_generator.py 
│   ├── requirements.txt 
│   └── uploads/ 
└── README.md 
``` 
 
## 安装说明 
 
1. 安装Python依赖: 
   ```bash 
   cd backend 
   pip install -r requirements.txt 
   ``` 
 
2. 运行后端服务器: 
   ```bash 
   python server.py 
   ``` 
 
3. 打开前端界面: 
   ```bash 
   cd frontend 
   python -m http.server 8080 
   ``` 
 
4. 访问 http://localhost:8080 
