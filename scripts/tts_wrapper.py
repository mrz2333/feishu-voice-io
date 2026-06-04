#!/usr/bin/env python3
"""TTS 封装 - 支持 Edge TTS / Piper TTS / MIMO TTS。

用法：
  python3 tts_wrapper.py --text "你好" --engine edge --output output.wav

环境变量：
  TTS_EDGE_VOICE   Edge TTS 语音（可选，默认 zh-CN-XiaoxiaoNeural）
  TTS_PIPER_MODEL  Piper TTS 模型路径（可选）
  TTS_MIMO_URL     MIMO TTS API URL（可选）
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def tts_edge(text: str, output: str, voice: str = None) -> bool:
    """Edge TTS（在线，免费）。"""
    voice = voice or os.getenv("TTS_EDGE_VOICE", "zh-CN-XiaoxiaoNeural")
    try:
        import edge_tts
    except ImportError:
        print("❌ edge-tts 未安装，运行: pip install edge-tts", file=sys.stderr)
        return False

    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output)

    try:
        asyncio.run(_generate())
        return os.path.exists(output) and os.path.getsize(output) > 0
    except Exception as e:
        print(f"❌ Edge TTS 错误: {e}", file=sys.stderr)
        return False


def tts_piper(text: str, output: str, model: str = None) -> bool:
    """Piper TTS（离线，快速）。"""
    model = model or os.getenv("TTS_PIPER_MODEL", "")
    if not model:
        print("❌ TTS_PIPER_MODEL 未设置", file=sys.stderr)
        return False

    cmd = ["piper", "--model", model, "--output_file", output]
    try:
        result = subprocess.run(
            cmd, input=text, capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ piper 未安装", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("❌ Piper TTS 超时", file=sys.stderr)
        return False


def tts_mimo(text: str, output: str, url: str = None) -> bool:
    """MIMO TTS（在线，高质量）。"""
    url = url or os.getenv("TTS_MIMO_URL", "")
    if not url:
        print("❌ TTS_MIMO_URL 未设置", file=sys.stderr)
        return False

    try:
        import requests
    except ImportError:
        print("❌ requests 未安装，运行: pip install requests", file=sys.stderr)
        return False

    try:
        resp = requests.post(url, json={"text": text}, timeout=30)
        if resp.status_code == 200:
            with open(output, "wb") as f:
                f.write(resp.content)
            return os.path.getsize(output) > 0
        else:
            print(f"❌ MIMO TTS HTTP {resp.status_code}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"❌ MIMO TTS 错误: {e}", file=sys.stderr)
        return False


def tts_auto(text: str, output: str) -> bool:
    """自动选择可用的 TTS 引擎。"""
    engines = [
        ("edge", tts_edge),
        ("piper", lambda t, o: tts_piper(t, o)),
        ("mimo", lambda t, o: tts_mimo(t, o)),
    ]
    for name, func in engines:
        if func(text, output):
            print(f"✅ 使用 {name} TTS", file=sys.stderr)
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="TTS 封装")
    parser.add_argument("--text", required=True, help="要合成的文字")
    parser.add_argument("--engine", default="auto",
                        choices=["edge", "piper", "mimo", "auto"],
                        help="TTS 引擎（默认 auto）")
    parser.add_argument("--output", required=True, help="输出音频文件路径")
    parser.add_argument("--voice", default=None, help="Edge TTS 语音名称")
    parser.add_argument("--model", default=None, help="Piper TTS 模型路径")
    parser.add_argument("--url", default=None, help="MIMO TTS API URL")
    args = parser.parse_args()

    engine_map = {
        "edge": lambda: tts_edge(args.text, args.output, args.voice),
        "piper": lambda: tts_piper(args.text, args.output, args.model),
        "mimo": lambda: tts_mimo(args.text, args.output, args.url),
        "auto": lambda: tts_auto(args.text, args.output),
    }

    success = engine_map[args.engine]()
    if success:
        print(f"✅ TTS 生成成功: {args.output}", file=sys.stderr)
    else:
        print("❌ TTS 生成失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
