# 飞书语音 I/O

> 飞书（Lark）原生语音消息收发技能，支持 STT 语音识别 + TTS 语音合成 + 飞书语音气泡发送。

适配 OpenClaw、Hermes、QwenPaw 等 AI Agent 框架。

---

## 功能特性

- 🎤 **STT 语音识别**：使用 sherpa-onnx（离线）识别语音输入
- 🗣️ **TTS 语音合成**：支持 Edge TTS（在线免费）/ Piper TTS（离线）/ MIMO TTS（在线高质量）
- 📡 **飞书语音气泡**：发送 `msg_type=audio` 原生语音消息
- 🧹 **自动清理**：临时文件自动清理，不留垃圾
- 🔧 **通用适配**：通过环境变量配置，适配任意 Agent 框架

---

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install requests edge-tts

# STT 依赖（可选，如果只需要 TTS 可以跳过）
pip install sherpa-onnx numpy

# Piper TTS（可选，离线 TTS）
# 参考 https://github.com/rhasspy/piper 安装
```

### 2. 配置环境变量

```bash
# 必填：飞书应用凭据
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"

# 必填（如果使用 STT）：sherpa-onnx 模型路径
export SHERPA_ONNX_MODEL_DIR="/path/to/sherpa-onnx-paraformer-zh-small-2024-03-09"

# 可选：默认接收者
export FEISHU_RECEIVE_ID="ou_xxx"

# 可选：TTS 引擎选择
export TTS_ENGINE="edge"  # edge / piper / mimo / auto

# 可选：Edge TTS 语音
export TTS_EDGE_VOICE="zh-CN-XiaoxiaoNeural"

# 可选：Piper TTS 模型
export TTS_PIPER_MODEL="/path/to/piper/model.onnx"

# 可选：MIMO TTS API
export TTS_MIMO_URL="http://your-mimo-api/tts"
```

### 3. 运行

```bash
# 基本用法：STT + TTS + 发送
python3 scripts/feishu_voice_reply.py \
    --input /path/to/audio.opus \
    --reply-text "收到，我马上处理"

# 跳过 STT，直接 TTS 回复
python3 scripts/feishu_voice_reply.py \
    --input /path/to/audio.opus \
    --reply-text "好的" \
    --skip-stt

# 指定接收者和 TTS 引擎
python3 scripts/feishu_voice_reply.py \
    --input voice.opus \
    --reply-text "你好" \
    --receive-id ou_xxx \
    --tts-engine piper

# 保留临时文件（调试用）
python3 scripts/feishu_voice_reply.py \
    --input voice.opus \
    --reply-text "测试" \
    --keep-temp
```

---

## 项目结构

```
feishu-voice-io/
├── SKILL.md                    # 本文档
├── README.md                   # 项目说明
├── scripts/
│   ├── feishu_voice_reply.py   # 主入口：语音回复全流程
│   ├── voice_to_text.py        # STT：语音转文字
│   ├── tts_wrapper.py          # TTS：文字转语音（多引擎）
│   └── feishu/
│       └── feishu_audio_send.py # 飞书语音消息发送
├── models/                     # STT/TTS 模型（需自行下载）
└── docs/                       # 扩展文档
```

---

## Agent 框架适配

### OpenClaw

在 OpenClaw 的 `.env` 中添加：

```bash
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
SHERPA_ONNX_MODEL_DIR=/path/to/model
```

然后在 skill 脚本中调用：

```python
import subprocess
result = subprocess.run([
    "python3", "/opt/feishu-voice-io/scripts/feishu_voice_reply.py",
    "--input", audio_path,
    "--reply-text", reply_text,
    "--receive-id", user_open_id
], capture_output=True, text=True)
```

### Hermes

在 `~/.hermes/.env` 中添加环境变量，然后创建 skill：

```bash
# ~/.hermes/skills/feishu-voice-io/SKILL.md
# 参考本文档内容
```

### QwenPaw

```bash
# 在 QwenPaw 容器中挂载
-v /opt/feishu-voice-io:/app/working/skills/feishu-voice-io

# 环境变量
-e FEISHU_APP_ID=xxx
-e FEISHU_APP_SECRET=xxx
-e SHERPA_ONNX_MODEL_DIR=/app/working/models/sherpa/...
```

---

## 飞书应用配置

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

### 2. 配置权限

需要以下权限：

- `im:message:send_as_bot` — 以机器人身份发送消息
- `im:file` — 上传文件
- `im:resource` — 获取资源

### 3. 获取用户 open_id

通过飞书 API 或管理后台获取目标用户的 `open_id`。

---

## TTS 引擎对比

| 引擎 | 类型 | 质量 | 速度 | 依赖 |
|------|------|------|------|------|
| Edge TTS | 在线 | ⭐⭐⭐⭐ | 中 | `pip install edge-tts` |
| Piper TTS | 离线 | ⭐⭐⭐ | 快 | 需安装 piper |
| MIMO TTS | 在线 | ⭐⭐⭐⭐⭐ | 中 | 需部署 MIMO API |

---

## STT 模型下载

使用 sherpa-onnx 的 Paraformer 模型：

```bash
# 下载模型
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2
tar xvf sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2

# 设置环境变量
export SHERPA_ONNX_MODEL_DIR="$(pwd)/sherpa-onnx-paraformer-zh-small-2024-03-09"
```

---

## 常见问题

### Q: STT 识别不准确？

A: 确保音频是 16kHz 单声道 WAV 格式。脚本会自动用 ffmpeg 转换。

### Q: 飞书发送失败？

A: 检查：
1. App ID / Secret 是否正确
2. 应用权限是否配置
3. 接收者 open_id 是否有效

### Q: Edge TTS 超时？

A: Edge TTS 需要网络连接。如果网络不稳定，考虑使用 Piper TTS（离线）。

### Q: 如何调试？

A: 使用 `--keep-temp` 参数保留临时文件，检查生成的 WAV 和 opus 文件。

---

## 许可证

MIT License

---

## 致谢

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) — 语音识别引擎
- [edge-tts](https://github.com/rany2/edge-tts) — Edge TTS 封装
- [piper](https://github.com/rhasspy/piper) — 离线 TTS 引擎
- [飞书开放平台](https://open.feishu.cn) — 飞书 API
