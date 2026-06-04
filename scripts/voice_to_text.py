#!/usr/bin/env python3
"""STT 语音识别 - 使用 sherpa-onnx。

用法：
  python3 voice_to_text.py /path/to/audio.opus

环境变量：
  SHERPA_ONNX_MODEL_DIR  sherpa-onnx 模型目录（必填）

输出 JSON：
  {"ok": true, "text": "识别结果"}
  {"ok": false, "error": "错误信息"}
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def convert_to_wav(input_path: str, output_path: str) -> bool:
    """转换音频为 16kHz 单声道 WAV。"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-f", "wav",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def run_sherpa_onnx(wav_path: str, model_dir: str) -> dict:
    """运行 sherpa-onnx 识别。"""
    try:
        import sherpa_onnx
    except ImportError:
        return {"ok": False, "error": "sherpa-onnx 未安装，运行: pip install sherpa-onnx"}

    try:
        # 创建识别器
        recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=model_dir + "/model.onnx",
            tokens=model_dir + "/tokens.txt",
            num_threads=4,
            sample_rate=16000,
        )

        # 读取音频
        import wave
        with wave.open(wav_path, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            samples = wf.readframes(wf.getnframes())

        import numpy as np
        samples = np.frombuffer(samples, dtype=np.int16).astype(np.float32) / 32768.0

        # 识别
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        recognizer.decode_stream(stream)

        text = stream.result.text.strip()
        return {"ok": True, "text": text}

    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "缺少音频文件参数"}))
        sys.exit(1)

    audio_path = sys.argv[1]
    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR", "")

    if not os.path.exists(audio_path):
        print(json.dumps({"ok": False, "error": f"文件不存在: {audio_path}"}))
        sys.exit(1)

    if not model_dir or not os.path.exists(model_dir):
        print(json.dumps({"ok": False, "error": f"SHERPA_ONNX_MODEL_DIR 无效: {model_dir}"}))
        sys.exit(1)

    # 转换为 WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        if not convert_to_wav(audio_path, wav_path):
            print(json.dumps({"ok": False, "error": "音频转换失败"}))
            sys.exit(1)

        # 识别
        result = run_sherpa_onnx(wav_path, model_dir)
        print(json.dumps(result, ensure_ascii=False))

    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


if __name__ == "__main__":
    main()
