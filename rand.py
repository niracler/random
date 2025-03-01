import os
import re
import time
import random
import datetime
import requests
import pandas as pd
import json
from dateutil.relativedelta import relativedelta

# Constants
GH_TOKEN = os.getenv('GH_TOKEN')
USERNAME = "niracler"
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '-1001921875703')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
READ_ME_PATH = 'README.md'
HISTORY_PATH = 'table.csv'
TABLE_START = '<!-- TABLE_START -->\n'
TABLE_END = '\n<!-- TABLE_END -->'
PROJECT_ID = "PVT_kwHOAXsRh84Ak2d1"


def send_message_and_pin(text):
    send_message_url = f"{BASE_URL}/sendMessage"
    message_data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}

    response = requests.post(send_message_url, data=message_data)
    message_id = response.json()['result']['message_id']

    pin_message_url = f"{BASE_URL}/pinChatMessage"
    pin_data = {"chat_id": CHANNEL_ID, "message_id": message_id}
    return requests.post(pin_message_url, data=pin_data)


def map_to(card):
    priority = card.get('priority', None)
    weight = {None: 10, 'P2': 15, 'P1': 20, 'P0': 30}.get(priority, 10)

    return {
        "title": card["title"] + " | " + card["body"],
        "tags": card["labels"],
        "weight": weight,
        "short_url": card["url"],
        "uuid": card['id']
    }


def get_random_task(tasks_df):
    return random.choices(
        population=list(tasks_df.index),
        weights=list(tasks_df.weight),
        k=1
    )[0]


def update_history(history_df, task):
    now = datetime.datetime.now()
    current_date = now.strftime('%Y-%m')
    title = "[%s](%s)" % (
        task['title'].split("|")[0].strip(),
        task['short_url']
    )
    new_row = {'Date': current_date, 'Title': title, 'Tags': task['tags']}
    history_df = pd.concat([history_df, pd.DataFrame(
        new_row)], ignore_index=True)
    history_df.to_csv(HISTORY_PATH, index=False)
    return history_df


def update_readme(history_df):
    with open(READ_ME_PATH, 'r') as file:
        readme_content = file.read()

    markdown_table = history_df.to_markdown(index=False)
    regex = f"{re.escape(TABLE_START)}(.*?){re.escape(TABLE_END)}"
    updated_readme_content = re.sub(
        regex, f"{TABLE_START}\n{markdown_table}\n{TABLE_END}", readme_content, flags=re.DOTALL)

    with open(READ_ME_PATH, 'w') as file:
        file.write(updated_readme_content)


def fetch_github_project_items():
    query = """
    query {
        node(id: "%s") {
            ... on ProjectV2 {
                items(first: 100) {
                    nodes {
                        id
                        fieldValues(first: 8) {
                            nodes {
                                ... on ProjectV2ItemFieldTextValue {
                                    text
                                    field {
                                        ... on ProjectV2FieldCommon {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldDateValue {
                                    date
                                    field {
                                        ... on ProjectV2FieldCommon {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                    field {
                                        ... on ProjectV2FieldCommon {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                        content {
                            ... on Issue {
                                title
                                body
                                labels(first: 10) { 
                                    nodes {
                                        name
                                    }
                                }
                                url
                            }
                        }
                    }
                }
            }
        }
    }
    """ % PROJECT_ID

    headers = {
        'Authorization': f'Bearer {GH_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.post('https://api.github.com/graphql',
                             headers=headers, data=json.dumps({"query": query}))
    return response.json()


def parse_project_items(data):
    todo_list = []
    items = data.get('data', {}).get(
        'node', {}).get('items', {}).get('nodes', [])

    if items:
        for item in items:
            random_item = {}
            field_values = item.get('fieldValues', {}).get('nodes', [])
            for field_value in field_values:
                field = field_value.get('field', {}).get(
                    'name', 'Unknown field')
                if field == 'Status':
                    random_item['status'] = field_value.get('name', "")
                if field == 'Priority':
                    random_item['priority'] = field_value.get('name', "")

            if random_item.get('status') != 'Ready':
                continue

            content = item.get('content', {})
            random_item['id'] = item['id']
            random_item['title'] = content.get('title', "")
            text = content.get('body', "")
            random_item['body'] = re.search(
                r'\|\s*(.*?)\n\n', text, re.S).group(1).strip() if text else ""
            labels = content.get('labels', {}).get('nodes', [])
            random_item['labels'] = [label['name'] for label in labels]
            random_item['url'] = content.get('url', "")

            todo_list.append(random_item)
    return todo_list


def select_task_and_notify(tasks_df):
    print()
    for i in range(10):
        time.sleep(0.3)  # Delay for 3 seconds
        random_id = get_random_task(tasks_df)
        if i < 9:
            print("不是: " + tasks_df.loc[random_id]['title'])

    selected_task = tasks_df.loc[get_random_task(tasks_df)]
    tags = " ".join(
        [f"#{label.replace(' ', '_')}" for label in selected_task['tags']])
    msg = f"{(datetime.datetime.today().month) % 12}月决定就是: <b>{selected_task['title']}</b> \n\n🌟🎉 恭喜恭喜!!! ({datetime.datetime.now().strftime('%Y-%m-%d')} <a href=\"{selected_task['short_url']}\">传送门</a>)\n{tags} #random_todolist"
    
    print("\n" + msg)
    send_message_and_pin(msg)

    return selected_task


def update_task_status(selected_task):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": """
        mutation {
            updateProjectV2ItemFieldValue(
                input: {
                    projectId: "%s",
                    itemId: "%s",
                    fieldId: "PVTSSF_lAHOAXsRh84Ak2d1zgc_r_o",
                    value: { singleSelectOptionId: "47fc9ee4" }
                }
            ) {
                projectV2Item {
                    id
                }
            }
        }
        """ % (PROJECT_ID, selected_task['uuid'])
    }
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("请求失败:", response.status_code)
        print("错误信息:", response.text)


def main():
    data = fetch_github_project_items()

    todo_list = parse_project_items(data)
    tasks_df = pd.DataFrame(map(map_to, todo_list))
    history_df = pd.read_csv(HISTORY_PATH)

    selected_task = select_task_and_notify(tasks_df)
    update_task_status(selected_task)

    history_df = update_history(history_df, selected_task)
    update_readme(history_df)

if __name__ == "__main__":
    main()
