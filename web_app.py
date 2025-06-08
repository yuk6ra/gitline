from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import datetime
import json
import uuid
from src.note import NoteRegistry, SocraticAI, DeepDiveSession

# FastAPIアプリケーション初期化
app = FastAPI(title="Oracle AI API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],  # Next.js開発サーバーとVercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエスト/レスポンスモデル
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    session_state: str
    questions: Optional[list] = None
    error: Optional[str] = None

class SessionStatusResponse(BaseModel):
    session_id: str
    session_state: str
    questions: Optional[list] = None
    qa_pairs: Optional[list] = None
    last_activity: Optional[str] = None

# グローバルインスタンス（遅延初期化）
note = None
ai = None
deep_dive = None

def init_services():
    """サービスの初期化（遅延初期化）"""
    global note, ai, deep_dive
    if note is None:
        note = NoteRegistry()
        ai = SocraticAI()
        deep_dive = DeepDiveSession()

# アクティブセッション管理
active_sessions: Dict[str, Dict[str, Any]] = {}

def create_session(session_id: str) -> str:
    """新しいセッションを作成"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    active_sessions[session_id] = {
        "session_id": None,  # deep_dive session id
        "questions": [],
        "current_question": None,
        "waiting_for": None,  # "choice", "answer", "continue", "analysis_context", "analysis_followup"
        "last_activity": datetime.datetime.now(),
        "timeout_minutes": 30,  # Web版は30分に延長
        "current_analysis": None
    }
    return session_id

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """セッションを取得"""
    return active_sessions.get(session_id)

def update_session_activity(session_id: str):
    """セッションの最終活動時刻を更新"""
    if session_id in active_sessions:
        active_sessions[session_id]["last_activity"] = datetime.datetime.now()

def check_session_timeout(session_id: str) -> bool:
    """セッションタイムアウトをチェック"""
    session = get_session(session_id)
    if session and session["last_activity"]:
        elapsed = datetime.datetime.now() - session["last_activity"]
        if elapsed.total_seconds() > session["timeout_minutes"] * 60:
            # セッションをリセット
            if session["session_id"]:
                deep_dive.end_session(session["session_id"])
            del active_sessions[session_id]
            return True
    return False

def reset_session(session_id: str):
    """セッションをリセット"""
    session = get_session(session_id)
    if session:
        if session["session_id"]:
            deep_dive.end_session(session["session_id"])
        session.update({
            "session_id": None,
            "questions": [],
            "current_question": None,
            "waiting_for": None,
            "current_analysis": None
        })

@app.get("/")
async def root():
    return {"message": "Oracle AI API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/api/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    try:
        # サービス初期化
        init_services()
        
        # 環境変数チェック
        required_vars = ["GITHUB_ACCESS_TOKEN", "GITHUB_USERNAME", "GITHUB_REPOSITORY", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise HTTPException(
                status_code=500, 
                detail=f"Missing environment variables: {missing_vars}"
            )

        # セッション管理
        session_id = request.session_id or str(uuid.uuid4())
        
        # セッション存在確認・作成
        if session_id not in active_sessions:
            create_session(session_id)
        
        # タイムアウトチェック
        if check_session_timeout(session_id):
            create_session(session_id)
            return MessageResponse(
                success=True,
                message="セッションがタイムアウトしました（30分経過）。新しいメモを送信してください。",
                session_id=session_id,
                session_state="timeout"
            )
        
        # 活動時刻更新
        update_session_activity(session_id)
        
        current_session = active_sessions[session_id]
        content = request.message.strip()

        print(f"[Debug] Processing message: '{content}' for session: {session_id}")
        print(f"[Debug] Current session state: {current_session}")
        print(f"[Debug] waiting_for: {current_session['waiting_for']}")
        print(f"[Debug] session_id exists: {current_session['session_id'] is not None}")
        print(f"[Debug] content == 'はい': {content == 'はい'}")

        # 「終了」コマンドの処理（どの状態でも優先）
        if content in ["終了", "エンド", "exit", "quit", "終わり", "やめる"]:
            if current_session["session_id"]:
                reset_session(session_id)
                return MessageResponse(
                    success=True,
                    message="深堀りセッションを終了しました。",
                    session_id=session_id,
                    session_state="ended"
                )
            else:
                return MessageResponse(
                    success=True,
                    message="現在アクティブなセッションはありません。",
                    session_id=session_id,
                    session_state="idle"
                )

        # 現在の状態に応じて処理を分岐
        if current_session["waiting_for"] == "choice":
            return handle_question_choice(session_id, content)
        elif current_session["waiting_for"] == "answer":
            return handle_answer(session_id, content)
        elif current_session["waiting_for"] == "continue":
            return handle_continue_choice(session_id, content)
        elif current_session["waiting_for"] == "analysis_context":
            return handle_analysis_context(session_id, content)
        elif current_session["waiting_for"] == "analysis_followup":
            return handle_analysis_followup(session_id, content)
        elif current_session["waiting_for"] == "deep_dive_confirm":
            # 深堀り確認待ち状態
            print(f"[Debug] In deep_dive_confirm state, content: '{content}'")
            if content == "はい":
                print(f"[Debug] Starting deep dive")
                return start_deep_dive(session_id)
            else:
                print(f"[Debug] Not 'はい', saving as new memo")
                # 「はい」以外は新しいメモとして保存
                return handle_new_memo(session_id, content)
        else:
            # 通常のメモ保存（初回）
            return handle_new_memo(session_id, content)

    except Exception as e:
        print(f"[Error] Exception in send_message: {e}")
        return MessageResponse(
            success=False,
            message="処理中にエラーが発生しました",
            session_id=session_id or str(uuid.uuid4()),
            session_state="error",
            error=str(e)
        )

def handle_new_memo(session_id: str, content: str) -> MessageResponse:
    """新しいメモの処理"""
    try:
        print(f"[Debug] Saving memo: {content}")
        note.write(content=content)
        print(f"[Debug] Memo saved successfully")
        
        # セッション開始
        dive_session_id = deep_dive.start_session("web_user", content)
        active_sessions[session_id]["session_id"] = dive_session_id
        active_sessions[session_id]["waiting_for"] = "deep_dive_confirm"  # 深堀り確認待ち状態
        update_session_activity(session_id)
        
        return MessageResponse(
            success=True,
            message="深堀りしますか？「はい」と答えるとAIが質問を生成します。\n「はい」以外の回答はそのまま次のメモとして保存します。",
            session_id=session_id,
            session_state="waiting_deep_dive"
        )
        
    except Exception as e:
        print(f"[Error] Failed to save memo: {e}")
        raise HTTPException(status_code=500, detail="メモの保存に失敗しました")

def start_deep_dive(session_id: str) -> MessageResponse:
    """深堀りセッション開始"""
    current_session = active_sessions[session_id]
    session = deep_dive.get_session(current_session["session_id"])
    
    if session:
        qa_history = session.get("qa_pairs", [])
        questions = ai.generate_questions(session["original_memo"], qa_history)
        
        if questions:
            current_session["questions"] = questions
            
            question_text = "以下から質問を選んでください：\n\n"
            for i, q in enumerate(questions):
                question_text += f"{i+1}. [{q['type']}] {q['q']}\n"
            question_text += f"\n{len(questions)+1}. [Analysis] AIによる客観的な分析・意見を聞く\n"
            question_text += f"\n番号（1-{len(questions)+1}）で回答してください。\n「再考」と入力すると別の質問を生成します。\n「終了」でセッションを終了できます。"
            
            current_session["waiting_for"] = "choice"
            
            return MessageResponse(
                success=True,
                message=question_text,
                session_id=session_id,
                session_state="waiting_choice",
                questions=questions
            )
        else:
            return MessageResponse(
                success=False,
                message="質問の生成に失敗しました。",
                session_id=session_id,
                session_state="error"
            )
    else:
        return MessageResponse(
            success=False,
            message="セッションが見つかりません。",
            session_id=session_id,
            session_state="error"
        )

def handle_question_choice(session_id: str, content: str) -> MessageResponse:
    """質問選択の処理"""
    current_session = active_sessions[session_id]
    
    # 再考の処理
    if content in ["再考", "再生成", "やり直し", "別の質問"]:
        return regenerate_questions(session_id)
    
    try:
        choice = int(content)
        total_options = len(current_session["questions"]) + 1
        
        if 1 <= choice <= len(current_session["questions"]):
            selected_question = current_session["questions"][choice - 1]
            current_session["current_question"] = selected_question
            current_session["waiting_for"] = "answer"
            
            return MessageResponse(
                success=True,
                message=f"質問: {selected_question['q']}\n\n回答を入力してください。\n（「終了」でセッション終了）",
                session_id=session_id,
                session_state="waiting_answer"
            )
        elif choice == total_options:  # AI分析オプション
            current_session["waiting_for"] = "analysis_context"
            
            return MessageResponse(
                success=True,
                message="AIによる客観的な分析を生成しています...\n\n追加で伝えたい仮説や考えがあれば入力してください。\n何もなければ「なし」と入力してください。\n（「終了」でセッション終了）",
                session_id=session_id,
                session_state="waiting_analysis_context"
            )
        else:
            return MessageResponse(
                success=False,
                message=f"1-{total_options}の番号で選択してください。",
                session_id=session_id,
                session_state="waiting_choice"
            )
    except ValueError:
        return MessageResponse(
            success=False,
            message="数字で回答するか、「再考」と入力してください。",
            session_id=session_id,
            session_state="waiting_choice"
        )

def handle_answer(session_id: str, content: str) -> MessageResponse:
    """回答の処理"""
    current_session = active_sessions[session_id]
    question_text = current_session["current_question"]["q"]
    session = deep_dive.get_session(current_session["session_id"])
    
    if session:
        # GitHubに保存
        note.write_qa_pair(question_text, content)
        
        # セッションに記録
        deep_dive.add_qa_pair(current_session["session_id"], question_text, content)
    
    # 続行するかを確認
    if not deep_dive.is_session_complete(current_session["session_id"]):
        current_session["waiting_for"] = "continue"
        
        return MessageResponse(
            success=True,
            message="回答を保存しました。\n\n続けて深堀りしますか？「はい」で継続、「いいえ」で終了",
            session_id=session_id,
            session_state="waiting_continue"
        )
    else:
        reset_session(session_id)
        return MessageResponse(
            success=True,
            message="深堀りセッション完了！（最大10回に達しました）",
            session_id=session_id,
            session_state="completed"
        )

def handle_continue_choice(session_id: str, content: str) -> MessageResponse:
    """継続選択の処理"""
    if content.lower() in ["はい", "yes", "y"]:
        return start_deep_dive(session_id)
    else:
        reset_session(session_id)
        return MessageResponse(
            success=True,
            message="深堀りセッションを終了しました。",
            session_id=session_id,
            session_state="ended"
        )

def regenerate_questions(session_id: str) -> MessageResponse:
    """質問の再生成"""
    current_session = active_sessions[session_id]
    session = deep_dive.get_session(current_session["session_id"])
    
    if session:
        qa_history = session.get("qa_pairs", [])
        questions = ai.generate_questions(session["original_memo"], qa_history, regenerate=True)
        
        if questions:
            current_session["questions"] = questions
            
            question_text = "【再生成された質問】以下から質問を選んでください：\n\n"
            for i, q in enumerate(questions):
                question_text += f"{i+1}. [{q['type']}] {q['q']}\n"
            question_text += f"\n{len(questions)+1}. [Analysis] AIによる客観的な分析・意見を聞く\n"
            question_text += f"\n番号（1-{len(questions)+1}）で回答してください。\n「再考」でさらに別の質問を生成します。\n「終了」でセッションを終了できます。"
            
            return MessageResponse(
                success=True,
                message=question_text,
                session_id=session_id,
                session_state="waiting_choice",
                questions=questions
            )
        else:
            return MessageResponse(
                success=False,
                message="質問の再生成に失敗しました。",
                session_id=session_id,
                session_state="error"
            )
    else:
        return MessageResponse(
            success=False,
            message="セッションが見つかりません。",
            session_id=session_id,
            session_state="error"
        )

def handle_analysis_context(session_id: str, content: str) -> MessageResponse:
    """AI分析のためのユーザーコンテキストを処理"""
    current_session = active_sessions[session_id]
    session = deep_dive.get_session(current_session["session_id"])
    
    if session:
        qa_history = session.get("qa_pairs", [])
        user_context = None if content.lower() in ["なし", ""] else content
        
        # AI分析を生成
        analysis = ai.generate_analysis(session["original_memo"], qa_history, user_context)
        
        if analysis:
            # 分析をGitHubに保存
            note.write_qa_pair("AIによる客観的分析", analysis)
            
            # セッションに記録
            deep_dive.add_qa_pair(current_session["session_id"], "AIによる客観的分析", analysis)
            
            current_session["current_analysis"] = analysis
            current_session["waiting_for"] = "analysis_followup"
            
            follow_up_message = f"【AI分析】\n{analysis}\n\n"
            follow_up_message += "この分析についてどう思いますか？感想や意見を自由に入力してください。\n特にない場合は「ない」と入力してください。\n（「終了」でセッション終了）"
            
            return MessageResponse(
                success=True,
                message=follow_up_message,
                session_id=session_id,
                session_state="waiting_analysis_followup"
            )
        else:
            current_session["waiting_for"] = "choice"
            return MessageResponse(
                success=False,
                message="分析の生成に失敗しました。",
                session_id=session_id,
                session_state="error"
            )
    else:
        return MessageResponse(
            success=False,
            message="セッションが見つかりません。",
            session_id=session_id,
            session_state="error"
        )

def handle_analysis_followup(session_id: str, content: str) -> MessageResponse:
    """AI分析に対するユーザーの意見を処理"""
    current_session = active_sessions[session_id]
    
    message = "承知しました。"
    
    if current_session.get("current_analysis"):
        # 「ない」以外の場合のみGitHubに保存
        if content.lower() not in ["ない", "なし", "特にない", "特になし"]:
            note.write_qa_pair("この分析についてどう思いますか？", content)
            deep_dive.add_qa_pair(current_session["session_id"], "この分析についてどう思いますか？", content)
            message = "回答を保存しました。"
        
        # 現在の分析情報をクリア
        current_session["current_analysis"] = None
        
        # 続行するかを確認
        if not deep_dive.is_session_complete(current_session["session_id"]):
            current_session["waiting_for"] = "continue"
            return MessageResponse(
                success=True,
                message=f"{message}\n\n続けて深堀りしますか？「はい」で継続、「いいえ」で終了",
                session_id=session_id,
                session_state="waiting_continue"
            )
        else:
            reset_session(session_id)
            return MessageResponse(
                success=True,
                message="深堀りセッション完了！（最大10回に達しました）",
                session_id=session_id,
                session_state="completed"
            )
    else:
        return MessageResponse(
            success=False,
            message="分析データが見つかりません。",
            session_id=session_id,
            session_state="error"
        )

@app.get("/api/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """セッション状態を取得"""
    init_services()
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    dive_session = None
    if session["session_id"]:
        dive_session = deep_dive.get_session(session["session_id"])
    
    return SessionStatusResponse(
        session_id=session_id,
        session_state=session["waiting_for"] or "idle",
        questions=session.get("questions"),
        qa_pairs=dive_session.get("qa_pairs", []) if dive_session else [],
        last_activity=session["last_activity"].isoformat() if session["last_activity"] else None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")