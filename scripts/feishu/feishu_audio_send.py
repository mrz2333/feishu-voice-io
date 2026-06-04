#!/usr/bin/env python3
"""飞书语音消息发送。

用法：
  python3 feishu_audio_send.py --receive-id-type open_id --receive-id ou_xxx --wav audio.opus

环境变量：
  FEISHU_APP_ID       飞书应用 ID（必填）
  FEISHU_APP_SECRET   飞书应用 Secret（必填）

输出 JSON：
  {"ok": true, "send": {...}}
  {"ok": false, "error": "错误信息"}
"""

import argparse
import json
import os
import sys
import requests


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token。"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": app_id,
        "app_secret": app_secret
    }, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取 token 失败: {data.get('msg')}")
    return data["tenant_access_token"]


def upload_audio(token: str, audio_path: str) -> str:
    """上传音频文件，返回 file_key。"""
    url = "https://open.feishu.cn/open-apis/im/v1/files"
    headers = {"Authorization": f"Bearer {token}"}
    with open(audio_path, "rb") as f:
        resp = requests.post(
            url,
            headers=headers,
            data={"file_type": "opus"},
            files={"file": (os.path.basename(audio_path), f, "audio/ogg")},
            timeout=30
        )
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"上传音频失败: {data.get('msg')}")
    return data["data"]["file_key"]


def send_audio_message(token: str, receive_id_type: str, receive_id: str, file_key: str) -> dict:
    """发送语音消息。"""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "receive_id": receive_id,
        "msg_type": "audio",
        "content": json.dumps({"file_key": file_key})
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="飞书语音消息发送")
    parser.add_argument("--receive-id-type", default="open_id",
                        choices=["open_id", "user_id", "union_id", "email", "chat_id"],
                        help="接收者 ID 类型")
    parser.add_argument("--receive-id", required=True, help="接收者 ID")
    parser.add_argument("--wav", required=True, help="音频文件路径（opus 格式）")
    args = parser.parse_args()

    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        print(json.dumps({"ok": False, "error": "FEISHU_APP_ID 或 FEISHU_APP_SECRET 未设置"}))
        sys.exit(1)

    if not os.path.exists(args.wav):
        print(json.dumps({"ok": False, "error": f"文件不存在: {args.wav}"}))
        sys.exit(1)

    try:
        # 获取 token
        token = get_tenant_token(app_id, app_secret)

        # 上传音频
        file_key = upload_audio(token, args.wav)

        # 发送消息
        result = send_audio_message(token, args.receive_id_type, args.receive_id, file_key)

        if result.get("code") == 0:
            print(json.dumps({"ok": True, "send": result}, ensure_ascii=False))
        else:
            print(json.dumps({"ok": False, "error": result.get("msg", "未知错误")}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
