
import os
import trello
import pandas

trello_client = trello.TrelloClient(
    api_key=os.getenv('TRELLO_API_KEY'),
    api_secret=os.getenv('TRELLO_API_SECRET'),
    token=os.getenv('TRELLO_TOKEN')
)

all_boards = trello_client.list_boards()
last_board = all_boards[0]
print(last_board.name)
print(all_boards[0].list_lists()[3].id)

import requests

# channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
channel_id = "-1001921875703"
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
base_url = f"https://api.telegram.org/bot{bot_token}"

def send_message_and_pin(text):
    send_message_url = f"{base_url}/sendMessage"
    message_data = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML"
    }

    # 发送消息
    response = requests.post(send_message_url, data=message_data)
    print(response.json())
    message_id = response.json()['result']['message_id']

    # 置顶消息
    pin_message_url = f"{base_url}/pinChatMessage"
    pin_data = {
        "chat_id": channel_id,
        "message_id": message_id
    }
    return requests.post(pin_message_url, data=pin_data)

print(send_message_and_pin("稍微测试测试"))