#!/usr/bin/env python3
"""飞书语音回复 - 通用版，支持 OpenClaw / Hermes / QwenPaw 等 Agent。

用法：
  python3 feishu_voice_reply.py --input /path/to/audio.opus --reply-text "回复文字"

环境变量：
  FEISHU_APP_ID       飞书应用 ID（必填）
  FEISHU_APP_SECRET   飞书应用 Secret（必填）
  FEISHU_RECEIVE_ID   默认接收者 ID（可选，命令行可覆盖）
  SHERPA_ONNX_MODEL_DIR  STT 模型路径（必填，除非 --skip-stt）
  TTS_ENGINE          默认 TTS 引擎（可选，默认 edge）

流程：
  1. STT 识别输入语音（自动清理临时文件）
  2. TTS 生成回复语音
  3. 转换为 opus 格式
  4. 发送飞书语音气泡
  5. 自动清理所有临时文件
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

# 默认路径（可通过环境变量覆盖）
VOICE_IO_DIR = Path(os.getenv("VOICE_IO_DIR", Path(__file__).parent.parent))
STT_MODEL = os.getenv("SHERPA_ONNX_MODEL_DIR", "")


def check_env():
    """检查必要的环境变量。"""
    errors = []
    if not os.getenv("FEISHU_APP_ID"):
        errors.append("FEISHU_APP_ID 未设置")
    if not os.getenv("FEISHU_APP_SECRET"):
        errors.append("FEISHU_APP_SECRET 未设置")
    return errors


def run_stt(audio_path: str) -> dict:
    """运行 STT 识别语音。"""
    if not STT_MODEL:
        return {"ok": False, "error": "SHERPA_ONNX_MODEL_DIR 未设置"}

    cmd = [
        "python3", str(VOICE_IO_DIR / "scripts" / "voice_to_text.py"),
        audio_path
    ]
    env = os.environ.copy()
    env["SHERPA_ONNX_MODEL_DIR"] = STT_MODEL

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "STT 超时"}
    except json.JSONDecodeError:
        return {"ok": False, "error": f"STT 输出解析失败: {result.stdout[:200]}"}


def run_tts(text: str, engine: str, output: str) -> bool:
    """运行 TTS 生成语音。"""
    cmd = [
        "python3", str(VOICE_IO_DIR / "scripts" / "tts_wrapper.py"),
        "--text", text,
        "--engine", engine,
        "--output", output
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ TTS 超时", file=sys.stderr)
        return False


def convert_to_opus(input_path: str, output_path: str) -> bool:
    """转换音频为 opus 格式。"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000",
        "-c:a", "libopus", "-b:a", "32k",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ ffmpeg 转换超时", file=sys.stderr)
        return False


def send_feishu_voice(opus_path: str, receive_id: str) -> dict:
    """发送飞书语音消息。"""
    cmd = [
        "python3", str(VOICE_IO_DIR / "scripts" / "feishu" / "feishu_audio_send.py"),
        "--receive-id-type", "open_id",
        "--receive-id", receive_id,
        "--wav", opus_path
    ]
    env = os.environ.copy()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "飞书发送超时"}
    except json.JSONDecodeError:
        return {"ok": False, "error": f"飞书输出解析失败: {result.stdout[:200]}"}


def check_dependencies():
    """检查必要的外部依赖。"""
    missing = []
    for cmd in ["ffmpeg"]:
        try:
            subprocess.run([cmd, "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            missing.append(cmd)
        except Exception:
            pass
    return missing


def main():
    parser = argparse.ArgumentParser(
        description="飞书语音回复（通用版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基本用法
  python3 feishu_voice_reply.py --input voice.opus --reply-text "收到"

  # 跳过 STT，直接 TTS 回复
  python3 feishu_voice_reply.py --input voice.opus --reply-text "好的" --skip-stt

  # 指定接收者和 TTS 引擎
  python3 feishu_voice_reply.py --input voice.opus --reply-text "你好" \\
      --receive-id ou_xxx --tts-engine piper
        """
    )
    parser.add_argument("--input", required=True, help="输入音频文件路径")
    parser.add_argument("--reply-text", required=True, help="回复文字")
    parser.add_argument("--tts-engine", default=os.getenv("TTS_ENGINE", "edge"),
                        choices=["mimo", "edge", "piper", "auto"],
                        help="TTS 引擎（默认 edge）")
    parser.add_argument("--receive-id", default=os.getenv("FEISHU_RECEIVE_ID"),
                        help="飞书接收者 open_id（默认从环境变量读取）")
    parser.add_argument("--skip-stt", action="store_true",
                        help="跳过 STT（输入仅作参考）")
    parser.add_argument("--keep-temp", action="store_true",
                        help="保留临时文件（调试用）")
    args = parser.parse_args()

    # 检查环境
    env_errors = check_env()
    if env_errors:
        for e in env_errors:
            print(f"❌ {e}", file=sys.stderr)
        return 1

    # 检查依赖
    dep_missing = check_dependencies()
    if dep_missing:
        for d in dep_missing:
            print(f"❌ 缺少依赖: {d}", file=sys.stderr)
        return 1

    if not args.receive_id:
        print("❌ 未指定接收者，请设置 FEISHU_RECEIVE_ID 或使用 --receive-id", file=sys.stderr)
        return 1

    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}", file=sys.stderr)
        return 1

    tmpdir = tempfile.mkdtemp(prefix="feishu_voice_")

    try:
        # Step 1: STT（可选）
        stt_text = None
        if not args.skip_stt:
            print(f"📝 Step 1: STT - {args.input}", file=sys.stderr)
            stt_result = run_stt(args.input)
            if stt_result.get("ok"):
                stt_text = stt_result["text"]
                print(f"   ✅ 识别结果: \"{stt_text}\"", file=sys.stderr)
            else:
                print(f"   ❌ STT 失败: {stt_result.get('error')}", file=sys.stderr)
                return 1

        # Step 2: TTS
        reply_text = args.reply_text
        wav_path = os.path.join(tmpdir, "reply.wav")
        print(f"\n🔊 Step 2: TTS ({args.tts_engine})", file=sys.stderr)
        if run_tts(reply_text, args.tts_engine, wav_path):
            print("   ✅ TTS 成功", file=sys.stderr)
        else:
            print("   ❌ TTS 失败", file=sys.stderr)
            return 1

        # Step 3: 转换为 opus
        opus_path = os.path.join(tmpdir, "reply.opus")
        print(f"\n🔄 Step 3: 转换格式", file=sys.stderr)
        if convert_to_opus(wav_path, opus_path):
            print("   ✅ 格式转换成功", file=sys.stderr)
        else:
            print("   ❌ 格式转换失败", file=sys.stderr)
            return 1

        # Step 4: 发送到飞书
        print(f"\n📤 Step 4: 发送飞书", file=sys.stderr)
        send_result = send_feishu_voice(opus_path, args.receive_id)
        if send_result.get("ok"):
            # 防御性解析 message_id
            send_data = send_result.get("send", {})
            msg_data = send_data.get("data", {})
            msg_id = msg_data.get("message_id", "unknown")
            print("   ✅ 发送成功!", file=sys.stderr)
            print(f"   📨 message_id: {msg_id}", file=sys.stderr)

            # 输出 JSON 结果到 stdout
            print(json.dumps({
                "ok": True,
                "stt_text": stt_text,
                "reply_text": reply_text,
                "message_id": msg_id
            }, ensure_ascii=False))
            return 0
        else:
            print(f"   ❌ 发送失败: {send_result.get('error')}", file=sys.stderr)
            return 1

    finally:
        if not args.keep_temp:
            shutil.rmtree(tmpdir, ignore_errors=True)
        else:
            print(f"📁 临时文件保留在: {tmpdir}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
