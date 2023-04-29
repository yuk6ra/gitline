from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler # pip install line-bot-sdk
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import datetime
import dotenv
from GithubMemo import MemoRegistry

dotenv.load_dotenv()

app = FastAPI()
memo = MemoRegistry()

line_bot_api = LineBotApi(os.environ["LINEBOT_CHANNEL_ACCESS_TOKEN"])
line = WebhookHandler(os.environ['LINEBOT_CHANNEL_SECRET'])
LINE_USER_ID = os.environ["LINEBOT_USER_ID"]
REMINDER_MESSAGE = os.environ["REMINDER_MESSAGE"]

@app.post("/callback")
async def webhook(request: Request):
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body_bytes = await request.body()
    body = body_bytes.decode('utf-8')

    # handle webhook body
    try:
        line.handle(body, signature)
    except InvalidSignatureError:
        return HTTPException(status_code=400, detail="Invalid signature")

    return 'OK'

@line.add(MessageEvent, message=TextMessage)
def handle_text_message(event):

    path = memo.write_memo(event.message.text)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"Saved!\n{path}")
    )

# id: reminder
@app.post('/__space/v0/actions')
async def actions(request: Request):
    data = await request.json()
    event = data['event']
    if event['id'] == 'reminder':
        sendReminder()
        return {"message": "cleanup started successfully"}
    if event['id'] == 'review':
        sendReview()
        return {"message": "cleanup started successfully"}
    else:
        return {"message": "no action found for this event"}
    
def sendReminder():
    line_bot_api.push_message(
        LINE_USER_ID,
        TextSendMessage(text=f"{REMINDER_MESSAGE}")
    )

def sendReview():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
    content, year, month, day = memo.read_random_file()

    memo_date = datetime.datetime(year=year, month=month, day=day, tzinfo=datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
    
    days_diff = (now.date() - memo_date.date()).days

    message = f"{year}.{month}.{day} ({days_diff} days ago)\n\n{content}"
    line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=message))