
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

import pandas as pd
def map_to(x):
    tags = " ".join([ "#" + label.name.replace(" ", "_") for label in x.labels ])
    weight = 10
    if "#high_priority" in tags:
        weight = 30

    return { 
        "title": x.name, 
        "tags": tags,
        "weight": weight, 
        "short_url": x.shortUrl,
        "uuid":x.id
    }

todo_list = last_board.get_list("631058bee13e0d048d72c450")
l = pd.DataFrame(list(map(map_to, todo_list.list_cards())))

history = pd.read_csv('table.csv')
print(history)

import random, datetime, time

user_input = input("确定要继续运行吗？(Y/n): ")    

def rs():
    return random.choices(
        population=list(l.index),
        weights=list(l.weight),
        k=1
    )

e = datetime.datetime.now()
month = (datetime.datetime.today().month) % 12

for i in range(10):
    time.sleep(3) # Delay for 3 seconds.
    random_id = rs()[0]
    if i < 9:
        print("不是: " + str(l.loc[random_id]['title']))
        
msg = "{month}月决定就是: <b>{title}</b> \n\n🌟🎉 恭喜恭喜!!! ({time} <a href=\"{url}\">传送门</a>)\n{tags} #random_todolist".format(
    month=month,
    url=l.loc[random_id]['short_url'],
    title=l.loc[random_id]['title'],
    tags=l.loc[random_id]['tags'], 
    time=e.strftime("%Y-%m-%d")
)

print("\n" + msg)
print(send_message_and_pin(msg))

import json

for card in todo_list.list_cards():
    if(card.id == l.loc[random_id]['uuid']):
        card.change_list("6024cd248ecb43309b5eb2d0")

from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
history = pd.read_csv('table.csv')

if len(history) == 0:
    current_date = datetime.now().strftime('%Y-%m')
else:
    previous_date = history.iloc[-1]['Date']
    previous_date = datetime.strptime(previous_date, '%Y-%m')
    current_date = previous_date + relativedelta(months=1)
    current_date = current_date.strftime('%Y-%m')

new_row = {'Date': current_date, 'Title': l.loc[random_id]['title'].replace("|", "-"), 'Tags': l.loc[random_id]['tags']}
new_df = pd.DataFrame(new_row, index=[0])

history = pd.concat([history, new_df], ignore_index=True)
markdown_table = history.to_markdown(index=False)
history

# 更新 README 文档
readme_path = 'README.md'

with open(readme_path, 'r') as file:
    readme_content = file.read()

# 找到要替换的标记，例如 <!-- TABLE_START --> 和 <!-- TABLE_END -->
table_start = '<!-- TABLE_START -->\n'
table_end = '\n<!-- TABLE_END -->'

# 替换标记位置的内容为 Markdown 表格
regex = f"{re.escape(table_start)}(.*?)\n{re.escape(table_end)}"
updated_readme_content = re.sub(regex, f"{table_start}\n{markdown_table}\n{table_end}", readme_content, flags=re.DOTALL)
updated_readme_content

# 写入更新后的 README 文件
with open(readme_path, 'w') as file:
    file.write(updated_readme_content)

print("README 文件已更新！")
history.to_csv('table.csv', index=False)