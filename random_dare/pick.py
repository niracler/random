import datetime
import json
import os
import random
import re
import time
from typing import Any

import pandas as pd
import requests

from .constants import PROJECT_ID, STATUS_FIELD_ID, STATUS_IN_PROGRESS_OPTION_ID

GH_TOKEN = os.getenv("GH_TOKEN")
USERNAME = "niracler"
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "-1001921875703")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
README_PATH = "README.md"
HISTORY_PATH = "data/table.csv"
TABLE_START = "<!-- TABLE_START -->\n"
TABLE_END = "\n<!-- TABLE_END -->"


def send_message_and_pin(text: str) -> requests.Response:
    send_message_url = f"{BASE_URL}/sendMessage"
    message_data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}

    response = requests.post(send_message_url, data=message_data)
    message_id = response.json()["result"]["message_id"]

    pin_message_url = f"{BASE_URL}/pinChatMessage"
    pin_data = {"chat_id": CHANNEL_ID, "message_id": message_id}
    return requests.post(pin_message_url, data=pin_data)


def map_to(card: dict[str, Any]) -> dict[str, Any]:
    priority = card.get("priority")
    weight = {None: 10, "P2": 15, "P1": 20, "P0": 30}.get(priority, 10)

    return {
        "title": card["title"] + " | " + card["body"],
        "tags": card["labels"],
        "weight": weight,
        "short_url": card["url"],
        "uuid": card["id"],
    }


def get_random_task(tasks_df: pd.DataFrame) -> int:
    return random.choices(
        population=list(tasks_df.index),
        weights=list(tasks_df.weight),
        k=1,
    )[0]


def update_history(history_df: pd.DataFrame, task: pd.Series) -> pd.DataFrame:
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m")
    english_title = task["title"].split("|")[0].strip()
    title = f"[{english_title}]({task['short_url']})"
    new_row = {"Date": current_date, "Title": title, "Tags": task["tags"]}
    history_df = pd.concat([history_df, pd.DataFrame(new_row)], ignore_index=True)
    history_df.to_csv(HISTORY_PATH, index=False)
    return history_df


def update_readme(history_df: pd.DataFrame) -> None:
    with open(README_PATH) as file:
        readme_content = file.read()

    markdown_table = history_df.to_markdown(index=False)
    regex = f"{re.escape(TABLE_START)}(.*?){re.escape(TABLE_END)}"
    updated_readme_content = re.sub(
        regex,
        f"{TABLE_START}\n{markdown_table}\n{TABLE_END}",
        readme_content,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w") as file:
        file.write(updated_readme_content)


def fetch_github_project_items() -> dict[str, Any]:
    query = """
    query($projectId: ID!) {
        node(id: $projectId) {
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
    """

    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {"query": query, "variables": {"projectId": PROJECT_ID}}
    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        data=json.dumps(payload),
    )
    return response.json()


def parse_project_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    todo_list: list[dict[str, Any]] = []
    items = data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])

    if items:
        for item in items:
            random_item: dict[str, Any] = {}
            field_values = item.get("fieldValues", {}).get("nodes", [])
            for field_value in field_values:
                field = field_value.get("field", {}).get("name", "Unknown field")
                if field == "Status":
                    random_item["status"] = field_value.get("name", "")
                if field == "Priority":
                    random_item["priority"] = field_value.get("name", "")

            if random_item.get("status") != "Ready":
                continue

            content = item.get("content", {})
            random_item["id"] = item["id"]
            random_item["title"] = content.get("title", "")
            text = content.get("body", "")
            match = re.search(r"\|\s*(.*?)\n\n", text, re.S) if text else None
            random_item["body"] = match.group(1).strip() if match else ""
            labels = content.get("labels", {}).get("nodes", [])
            random_item["labels"] = [label["name"] for label in labels]
            random_item["url"] = content.get("url", "")

            todo_list.append(random_item)
    return todo_list


def select_task_and_notify(tasks_df: pd.DataFrame) -> pd.Series:
    print()
    for i in range(10):
        time.sleep(0.3)  # Delay for 3 seconds
        random_id = get_random_task(tasks_df)
        if i < 9:
            print("不是: " + tasks_df.loc[random_id]["title"])

    selected_task = tasks_df.loc[get_random_task(tasks_df)]
    tags = " ".join([f"#{label.replace(' ', '_')}" for label in selected_task["tags"]])
    msg = (
        f"{datetime.datetime.today().month % 12}月决定就是: "
        f"<b>{selected_task['title']}</b> \n\n🌟🎉 恭喜恭喜!!! "
        f"({datetime.datetime.now().strftime('%Y-%m-%d')} "
        f'<a href="{selected_task["short_url"]}">传送门</a>)\n'
        f"{tags} #random_todolist"
    )

    print("\n" + msg)
    send_message_and_pin(msg)

    return selected_task


def update_task_status(selected_task: pd.Series) -> None:
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Content-Type": "application/json",
    }
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
        updateProjectV2ItemFieldValue(
            input: {
                projectId: $projectId,
                itemId: $itemId,
                fieldId: $fieldId,
                value: { singleSelectOptionId: $optionId }
            }
        ) {
            projectV2Item {
                id
            }
        }
    }
    """
    payload = {
        "query": mutation,
        "variables": {
            "projectId": PROJECT_ID,
            "itemId": selected_task["uuid"],
            "fieldId": STATUS_FIELD_ID,
            "optionId": STATUS_IN_PROGRESS_OPTION_ID,
        },
    }
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("请求失败:", response.status_code)
        print("错误信息:", response.text)


def main() -> None:
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
