import os
import re
import time
import random
import datetime
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from trello import TrelloClient

# Constants
CHANNEL_ID = "-1001921875703"  # os.getenv('TELEGRAM_CHANNEL_ID')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
READ_ME_PATH = 'README.md'
HISTORY_PATH = 'table.csv'
TABLE_START = '<!-- TABLE_START -->\n'
TABLE_END = '\n<!-- TABLE_END -->'

# Initialize Trello client
def init_trello_client():
    return TrelloClient(
        api_key=os.getenv('TRELLO_API_KEY'),
        api_secret=os.getenv('TRELLO_API_SECRET'),
        token=os.getenv('TRELLO_TOKEN')
    )

# Send and pin Telegram message
def send_message_and_pin(text):
    send_message_url = f"{BASE_URL}/sendMessage"
    message_data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    
    response = requests.post(send_message_url, data=message_data)
    # print(response.json())
    message_id = response.json()['result']['message_id']
    
    pin_message_url = f"{BASE_URL}/pinChatMessage"
    pin_data = {"chat_id": CHANNEL_ID, "message_id": message_id}
    return requests.post(pin_message_url, data=pin_data)

# Map Trello card to dictionary
def map_to(card):
    tags = " ".join([f"#{label.name.replace(' ', '_')}" for label in card.labels])
    weight = 30 if "#high_priority" in tags else 10
    return {
        "title": card.name, 
        "tags": tags,
        "weight": weight, 
        "short_url": card.shortUrl,
        "uuid": card.id
    }

def get_random_task(tasks_df):
    return random.choices(
        population=list(tasks_df.index),
        weights=list(tasks_df.weight),
        k=1
    )[0]

# Update task history
def update_history(history_df, task):
    now = datetime.datetime.now()
    if history_df.empty:
        current_date = now.strftime('%Y-%m')
    else:
        previous_date = datetime.datetime.strptime(history_df.iloc[-1]['Date'], '%Y-%m')
        current_date = (previous_date + relativedelta(months=1)).strftime('%Y-%m')
    
    new_row = {'Date': current_date, 'Title': task['title'].replace("|", "-"), 'Tags': task['tags']}
    history_df = pd.concat([history_df, pd.DataFrame(new_row, index=[0])], ignore_index=True)
    history_df.to_csv(HISTORY_PATH, index=False)
    return history_df

# Update README.md with new history table
def update_readme(history_df):
    with open(READ_ME_PATH, 'r') as file:
        readme_content = file.read()
    
    markdown_table = history_df.to_markdown(index=False)
    regex = f"{re.escape(TABLE_START)}(.*?){re.escape(TABLE_END)}"
    updated_readme_content = re.sub(regex, f"{TABLE_START}\n{markdown_table}\n{TABLE_END}", readme_content, flags=re.DOTALL)
    
    with open(READ_ME_PATH, 'w') as file:
        file.write(updated_readme_content)

def main():
    trello_client = init_trello_client()
    all_boards = trello_client.list_boards()
    last_board = all_boards[0]
    todo_list = last_board.get_list("631058bee13e0d048d72c450")
    tasks_df = pd.DataFrame(list(map(map_to, todo_list.list_cards())))
    
    history_df = pd.read_csv(HISTORY_PATH)
    
    for i in range(10):
        time.sleep(3)  # Delay for 3 seconds
        random_id = get_random_task(tasks_df)
        if i < 9:
            print("不是: " + tasks_df.loc[random_id]['title'])
    
    selected_task = tasks_df.loc[random_id]
    msg = f"{(datetime.datetime.today().month) % 12}月决定就是: <b>{selected_task['title']}</b> \n\n🌟🎉 恭喜恭喜!!! ({datetime.datetime.now().strftime('%Y-%m-%d')} <a href=\"{selected_task['short_url']}\">传送门</a>)\n{selected_task['tags']} #random_todolist"
    
    print("\n\n", msg)
    send_message_and_pin(msg)
    
    for card in todo_list.list_cards():
        if card.id == selected_task['uuid']:
            card.change_list("6024cd248ecb43309b5eb2d0")
    
    history_df = update_history(history_df, selected_task)
    update_readme(history_df)

if __name__ == "__main__":
    main()