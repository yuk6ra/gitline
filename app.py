import os
import datetime
import json
from linebot.v3.messaging.models.push_message_request import PushMessageRequest
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage
from src.note import NoteRegistry, SocraticAI, DeepDiveSession

configuration = Configuration(access_token=os.environ["LINEBOT_CHANNEL_ACCESS_TOKEN"])
LINEBOT_USER_ID = os.environ["LINEBOT_USER_ID"]
note = NoteRegistry()
ai = SocraticAI()
deep_dive = DeepDiveSession()

# 現在のセッション状態を保持（個人用なのでグローバル変数で管理）
current_session = {
    "session_id": None,
    "questions": [],
    "current_question": None,
    "waiting_for": None,  # "choice", "answer", "continue"
    "last_activity": None,
    "timeout_minutes": 5
}

def send_line_message(message):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        push_message_request = PushMessageRequest(
            to=LINEBOT_USER_ID,
            messages=[TextMessage(text=message)]
        )
        line_bot_api.push_message(push_message_request)

def check_session_timeout():
    """セッションタイムアウトをチェックし、必要に応じてリセット"""
    if current_session["last_activity"] and current_session["session_id"]:
        elapsed = datetime.datetime.now() - current_session["last_activity"]
        if elapsed.total_seconds() > current_session["timeout_minutes"] * 60:
            send_line_message("セッションがタイムアウトしました。新しいメモを送信してください。")
            reset_session()
            return True
    return False

def update_session_activity():
    """セッションの最終活動時刻を更新"""
    current_session["last_activity"] = datetime.datetime.now()

def save_note(event, context):
    try:
        if event['events'][0]['type'] == 'message' and event['events'][0]['message']['type'] == 'text':
            content = event['events'][0]['message']['text']
            
            # セッションタイムアウトをチェック
            if check_session_timeout():
                return "Session timeout"
            
            # 活動時刻を更新
            update_session_activity()
            
            # 現在の状態に応じて処理を分岐
            if current_session["waiting_for"] == "choice":
                handle_question_choice(content)
            elif current_session["waiting_for"] == "answer":
                handle_answer(content)
            elif current_session["waiting_for"] == "continue":
                handle_continue_choice(content)
            elif content == "はい" and current_session["session_id"]:
                start_deep_dive()
            else:
                # 通常のメモ保存
                print(f"[Debug] Saving memo: {content}")
                try:
                    note.write(content=content)
                    print(f"[Debug] Memo saved successfully")
                except Exception as e:
                    print(f"[Error] Failed to save memo: {e}")
                    return "Failed to save memo"
                
                # 深堀するかを聞く
                send_line_message("深堀りしますか？「はい」と答えるとAIが質問を生成します。")
                
                # セッション開始
                session_id = deep_dive.start_session("user", content)
                current_session["session_id"] = session_id
                update_session_activity()
                print(f"[Debug] Session started: {session_id}")
                
        return "Success"
    except Exception as e:
        print(e)
        return "Failed"

def start_deep_dive():
    session = deep_dive.get_session(current_session["session_id"])
    if session:
        # これまでのQ&A履歴を取得
        qa_history = session.get("qa_pairs", [])
        questions = ai.generate_questions(session["original_memo"], qa_history)
        if questions:
            current_session["questions"] = questions
            
            # 質問リストを作成
            question_text = "以下から質問を選んでください：\n\n"
            for i, q in enumerate(questions):
                question_text += f"{i+1}. [{q['type']}] {q['q']}\n"
            question_text += "\n番号（1-5）で回答してください。\n「再考」と入力すると別の質問を生成します。"
            
            send_line_message(question_text)
            current_session["waiting_for"] = "choice"
        else:
            send_line_message("質問の生成に失敗しました。")

def handle_question_choice(content):
    # 再考の処理
    if content.strip() in ["再考", "再生成", "やり直し", "別の質問"]:
        send_line_message("別の角度から質問を再生成しています...")
        regenerate_questions()  # 質問を再生成
        return
    
    try:
        choice = int(content.strip())
        if 1 <= choice <= len(current_session["questions"]):
            selected_question = current_session["questions"][choice - 1]
            current_session["current_question"] = selected_question
            
            send_line_message(f"質問: {selected_question['q']}\n\n回答を入力してください。")
            current_session["waiting_for"] = "answer"
        else:
            send_line_message("1-5の番号で選択してください。")
    except ValueError:
        send_line_message("数字で回答するか、「再考」と入力してください。")

def handle_answer(content):
    question_text = current_session["current_question"]["q"]
    session = deep_dive.get_session(current_session["session_id"])
    
    if session:
        # GitHubに固定階層で保存（質問は2階層、回答は3階層）
        note.write_qa_pair(question_text, content)
        
        # セッションに記録
        deep_dive.add_qa_pair(current_session["session_id"], question_text, content)
    
    # 続行するかを確認
    if not deep_dive.is_session_complete(current_session["session_id"]):
        send_line_message("回答を保存しました。\n\n続けて深堀りしますか？「はい」で継続、「いいえ」で終了")
        current_session["waiting_for"] = "continue"
    else:
        send_line_message("深堀りセッション完了！（最大5回に達しました）")
        reset_session()

def handle_continue_choice(content):
    if content.lower() in ["はい", "yes", "y"]:
        start_deep_dive()
    else:
        send_line_message("深堀りセッションを終了しました。")
        reset_session()

def regenerate_questions():
    """質問を再生成する"""
    session = deep_dive.get_session(current_session["session_id"])
    if session:
        # これまでのQ&A履歴を取得
        qa_history = session.get("qa_pairs", [])
        questions = ai.generate_questions(session["original_memo"], qa_history, regenerate=True)
        if questions:
            current_session["questions"] = questions
            
            # 質問リストを作成
            question_text = "【再生成された質問】以下から質問を選んでください：\n\n"
            for i, q in enumerate(questions):
                question_text += f"{i+1}. [{q['type']}] {q['q']}\n"
            question_text += "\n番号（1-5）で回答してください。\n「再考」でさらに別の質問を生成します。"
            
            send_line_message(question_text)
            current_session["waiting_for"] = "choice"
        else:
            send_line_message("質問の再生成に失敗しました。")

def reset_session():
    if current_session["session_id"]:
        deep_dive.end_session(current_session["session_id"])
    current_session.update({
        "session_id": None,
        "questions": [],
        "current_question": None,
        "waiting_for": None,
        "last_activity": None
    })

def create_mock_event(text):
    """ローカルテスト用のモックイベントを作成"""
    return {
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "text": text
                },
                "source": {
                    "userId": "local_test_user"
                }
            }
        ]
    }

def local_send_line_message(message):
    """ローカル用のメッセージ送信（コンソール出力）"""
    print(f"\n[LINE Bot] {message}\n")

def run_local_test():
    """ローカルテスト用の対話モード"""
    global send_line_message
    
    # ローカル環境では実際のLINE送信を無効化
    send_line_message = local_send_line_message
    
    print("=== ローカルテストモード ===")
    print("メモを入力してください（'quit'で終了）:")
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() == 'quit':
            print("テスト終了")
            break
            
        # モックイベントを作成して処理
        mock_event = create_mock_event(user_input)
        result = save_note(mock_event, None)
        print(f"[システム] {result}")

if __name__ == "__main__":
    # 環境変数チェック
    try:
        test_vars = [
            "GITHUB_ACCESS_TOKEN",
            "GITHUB_USERNAME", 
            "GITHUB_REPOSITORY",
            "OPENAI_API_KEY"
        ]
        
        missing_vars = [var for var in test_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"必要な環境変数が設定されていません: {missing_vars}")
            print("テストを続行しますが、一部機能が動作しない可能性があります。")
        
        run_local_test()
        
    except KeyboardInterrupt:
        print("\nテスト中断")
