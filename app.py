import os
import re
import json
from linebot.v3.messaging.models.push_message_request import PushMessageRequest
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, MessagingApiBlob, TextMessage
from src.note import NoteRegistry
from src.daily import DailyRegistry

configuration = Configuration(access_token=os.environ["LINEBOT_CHANNEL_ACCESS_TOKEN"])
LINEBOT_USER_ID = os.environ["LINEBOT_USER_ID"]
note = NoteRegistry()
daily = DailyRegistry()

# 日付パターン: YYYY/MM/DD または YYYY-MM-DD
DATE_PATTERN = re.compile(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})')

def send_line_message(message):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        push_message_request = PushMessageRequest(
            to=LINEBOT_USER_ID,
            messages=[TextMessage(text=message)]
        )
        line_bot_api.push_message(push_message_request)

def save_note(event, context):
    try:
        print(f"[Debug] Raw event received: {json.dumps(event, ensure_ascii=False)}")

        # 環境変数チェック
        required_vars = ["GITHUB_ACCESS_TOKEN", "GITHUB_USERNAME", "GITHUB_REPOSITORY"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            print(f"[Error] Missing environment variables: {missing_vars}")
            return {
                'statusCode': 500,
                'body': f'Missing environment variables: {missing_vars}'
            }

        # API Gateway経由の場合、bodyをパース
        if 'body' in event:
            try:
                body = json.loads(event['body'])
                print(f"[Debug] Parsed body: {json.dumps(body, ensure_ascii=False)}")
                event = body
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[Debug] Failed to parse body: {e}")
                return {
                    'statusCode': 400,
                    'body': 'Invalid JSON in request body'
                }

        # Handle empty events array (health check from LINE Platform)
        if not event.get('events'):
            print(f"[Debug] Empty events array - health check")
            return {
                'statusCode': 200,
                'body': 'OK'
            }

        message_event = event['events'][0]
        if message_event['type'] != 'message':
            return {
                'statusCode': 200,
                'body': 'Not a message event'
            }

        message_type = message_event['message']['type']

        # テキストメッセージの処理
        if message_type == 'text':
            content = message_event['message']['text']

            # 日付パターンで始まる場合は日記として保存
            date_match = DATE_PATTERN.match(content)
            if date_match:
                print(f"[Debug] Saving daily: {content}")
                try:
                    daily.save(content=content)
                    print(f"[Debug] Daily saved successfully")
                except Exception as e:
                    print(f"[Error] Failed to save daily: {e}")
                    send_line_message("日記の保存に失敗しました。")
                    return {
                        'statusCode': 200,
                        'body': 'Failed to save daily'
                    }
            else:
                # メモを保存
                print(f"[Debug] Saving memo: {content}")
                try:
                    note.append(content=content)
                    print(f"[Debug] Memo saved successfully")
                except Exception as e:
                    print(f"[Error] Failed to save memo: {e}")
                    send_line_message("メモの保存に失敗しました。")
                    return {
                        'statusCode': 200,
                        'body': 'Failed to save memo'
                    }

        # 画像メッセージの処理
        elif message_type == 'image':
            message_id = message_event['message']['id']
            print(f"[Debug] Saving image: {message_id}")

            try:
                # LINE APIから画像を取得
                with ApiClient(configuration) as api_client:
                    blob_api = MessagingApiBlob(api_client)
                    image_content = blob_api.get_message_content(message_id)

                # GitHubに保存
                note.append_image(image_content, extension="jpg")
                print(f"[Debug] Image saved successfully")
            except Exception as e:
                print(f"[Error] Failed to save image: {e}")
                send_line_message("画像の保存に失敗しました。")
                return {
                    'statusCode': 200,
                    'body': 'Failed to save image'
                }

        return {
            'statusCode': 200,
            'body': 'Success'
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 200,
            'body': 'Failed'
        }
