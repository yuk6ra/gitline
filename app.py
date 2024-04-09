import os
import datetime
from linebot.v3.messaging.models.push_message_request import PushMessageRequest
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage
from src.note import NoteRegistry

configuration = Configuration(access_token=os.environ["LINEBOT_CHANNEL_ACCESS_TOKEN"])
LINEBOT_USER_ID = os.environ["LINEBOT_USER_ID"]
note = NoteRegistry()

def save_note(event, context):
    try:
        if event['events'][0]['type'] == 'message' and event['events'][0]['message']['type'] == 'text':
            
            content = event['events'][0]['message']['text']
            note.write(content=content)

    except Exception as e:
        print(e)
        return "Failed"

# if __name__ == "__main__":
#     sample_event = {
#         "events": [
#             {
#                 "type": "message",
#                 "message": {
#                     "type": "text",
#                     "text": "1000\n食費\n現金"
#                 }
#             }
#         ]
#     }

#     send_review()
#     send_review_random()
#     save_note(sample_event, None)
