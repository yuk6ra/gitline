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

def send_review():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        text = ""

        # Note: 1 day, 3 days, 1 week, 2 weeks, 1 month, 2 months, 3 months, 6 months, 9 months, 1 year
        day_list = [1, 3, 7, 14, 30, 60, 90, 180, 270, 365]
        for day in day_list:
            d = now - datetime.timedelta(days=day)
            content = note.read_file(d.year, d.month, d.day)
            year, month, day = d.year, d.month, d.day        

            days_diff = (now.date() - d.date()).days
            if text:
                text += "\n\n"

            if not content:
                content = "No content found."

            text += f"👉{year}.{month}.{day} ({days_diff} days ago)\n\n{content}"

        line_bot_api.push_message_with_http_info(
            PushMessageRequest(
                to=LINEBOT_USER_ID,
                messages=[TextMessage(
                    type="text",
                    text=text
                )]
            )
        )

def send_review_random():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        content, year, month, day = note.read_random_file()

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        days_diff = (now.date() - datetime.date(year, month, day)).days
        text = f"👉{year}.{month}.{day} ({days_diff} days ago)\n\n{content}"

        line_bot_api.push_message_with_http_info(
            PushMessageRequest(
                to=LINEBOT_USER_ID,
                messages=[TextMessage(
                    type="text",
                    text=text
                )]
            )
        )

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
