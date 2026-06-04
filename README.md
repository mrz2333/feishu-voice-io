# Feishu Voice I/O

飞书原生语音消息收发工具，支持 STT + TTS + 飞书语音气泡。

适配 OpenClaw、Hermes、QwenPaw 等 AI Agent 框架。

## ✨ 特性

- 🎤 STT 语音识别（sherpa-onnx，离线）
- 🗣️ TTS 语音合成（Edge / Piper / MIMO）
- 📡 飞书原生语音气泡
- 🧹 自动清理临时文件
- 🔧 环境变量配置，通用适配

## 🚀 快速开始

```bash
# 安装依赖
pip install requests edge-tts sherpa-onnx

# 配置环境变量
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_secret"
export SHERPA_ONNX_MODEL_DIR="/path/to/model"

# 运行
python3 scripts/feishu_voice_reply.py \
    --input voice.opus \
    --reply-text "收到！"
```

## 📖 文档

详见 [SKILL.md](SKILL.md)

## 📁 结构

```
feishu-voice-io/
├── scripts/
│   ├── feishu_voice_reply.py   # 主入口
│   ├── voice_to_text.py        # STT
│   ├── tts_wrapper.py          # TTS
│   └── feishu/
│       └── feishu_audio_send.py # 飞书发送
├── models/                     # 模型目录
└── docs/                       # 扩展文档
```

## 📝 License

MIT
