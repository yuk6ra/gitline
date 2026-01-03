#!/usr/bin/env python3
"""
ローカルテスト用スクリプト
LINEからのWebhookをシミュレートしてapp.pyをテストする
"""
import json
from app import save_note

def simulate_line_message(text: str):
    """LINEメッセージをシミュレート"""
    event = {
        "body": json.dumps({
            "events": [{
                "type": "message",
                "message": {
                    "type": "text",
                    "text": text
                }
            }]
        })
    }
    print(f"\n{'='*50}")
    print(f"送信メッセージ: {text}")
    print(f"{'='*50}")
    result = save_note(event, None)
    print(f"結果: {result}")
    return result

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # コマンドライン引数からメッセージを取得
        message = " ".join(sys.argv[1:])
        simulate_line_message(message)
    else:
        # インタラクティブモード
        print("ローカルテストモード（終了: Ctrl+C または 'exit'）")
        print("日付形式（2026/01/03）で始まると日記、それ以外はメモ")
        print()

        while True:
            try:
                text = input("メッセージ> ").strip()
                if text.lower() in ["exit", "quit", "q"]:
                    break
                if text:
                    simulate_line_message(text)
            except KeyboardInterrupt:
                print("\n終了")
                break
