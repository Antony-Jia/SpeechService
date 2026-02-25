# SpeechService

本地语音服务，将 IndexTTS（TTS 文字转语音）与 OpenAI Whisper（STT 语音转文字）整合为一个统一的 REST API 服务，配套一个纯 HTML 测试页面。

## 项目结构

```
SpeechService/
├── backend/                  # Python 后端（FastAPI + uvicorn）
│   ├── speech_service/       # 服务代码
│   │   ├── main.py           # FastAPI 应用入口
│   │   ├── config.py         # 配置（环境变量/默认值）
│   │   └── tts_engine.py     # TTS 引擎封装
│   ├── pyproject.toml        # uv 依赖管理
│   └── .env.example          # 配置文件模板
├── frontend/
│   └── index.html            # 单页测试工具（无需构建）
├── checkpoints/              # ← 粘贴 index-tts/checkpoints/ 内容到这里
├── voices/                   # ← 存放参考音色 .wav 文件
└── base.pt                   # ← 粘贴 whisper-stt/base.pt 到这里
```

## 快速开始

### 1. 准备模型文件

```
# 将 index-tts 的模型文件夹整个复制过来
xcopy /E /I D:\Code\IndexTTSService\index-tts\checkpoints D:\Code\SpeechService\checkpoints

# 将 whisper base 模型复制过来
copy D:\Code\IndexTTSService\whisper-stt\base.pt D:\Code\SpeechService\base.pt

# 将至少一个参考音色 .wav 文件放入 voices 目录
copy 你的音色文件.wav D:\Code\SpeechService\voices\
```

### 2. 安装依赖（首次或迁移后）

```powershell
cd D:\Code\SpeechService\backend
uv sync
```

> 首次运行会从 GitHub 拉取 `indextts` 包并安装所有 ML 依赖，耗时较长，请耐心等待。
> 需要 CUDA 12.8 对应的 NVIDIA 驱动。

### 3. 启动服务

```powershell
# 方式一：直接运行
cd D:\Code\SpeechService\backend
uv run uvicorn speech_service.main:app --host 0.0.0.0 --port 8080

# 方式二：使用启动脚本
D:\Code\SpeechService\start.bat
```

### 4. 打开测试页面

直接用浏览器打开 `frontend/index.html`，确认"后端地址"为 `http://localhost:8080` 即可。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/speech/tts` | 文字转语音，返回 WAV 音频 |
| POST | `/stt` | 语音转文字，返回识别文本 |
| GET  | `/api/voices` | 列出可用音色 |
| GET  | `/health` | 健康检查 |

### TTS 请求示例

```json
POST /api/speech/tts
{"text": "你好，世界", "voice": "my_voice"}
```

响应：`audio/wav` 二进制流

### STT 请求示例

```json
POST /stt
{"audioBase64": "<base64>", "mimeType": "audio/webm", "language": "zh"}
```

响应：`{"text": "识别出的文字"}`

---

## 配置

复制 `backend/.env.example` 为 `backend/.env` 并按需修改：

```
SPEECH_SERVICE_PORT=8080
SPEECH_SERVICE_DEVICE=cuda
SPEECH_SERVICE_WHISPER_MODEL_NAME=base
```

## 使用本地 index-tts（可选）

如果不想每次从 GitHub 拉取 `indextts`，可改用本地路径依赖：

1. 打开 `backend/pyproject.toml`
2. 将 `dependencies` 中 `indextts @ git+...` 那行注释掉
3. 取消 `[tool.uv.sources]` 下 `indextts` 那行的注释，修改路径
4. 重新执行 `uv sync`

## 迁移到其他机器

需要：
1. 安装 uv（`pip install uv` 或参考 https://docs.astral.sh/uv/）
2. 安装 CUDA 12.x 驱动
3. 复制整个 `SpeechService/` 文件夹
4. 在 `backend/` 下执行 `uv sync`
