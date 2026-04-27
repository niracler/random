"""Close GitHub issues that have 'Reject' status on the project board as 'not planned'."""

import json
import os
from typing import Any

import requests

from .constants import PROJECT_ID

GH_TOKEN = os.getenv("GH_TOKEN")
GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Content-Type": "application/json",
}


def fetch_project_items() -> list[dict[str, Any]]:
    """Fetch all items from the project board with their status and issue info."""
    query = """
    query($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                items(first: 100) {
                    nodes {
                        fieldValues(first: 8) {
                            nodes {
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
                                id
                                number
                                title
                                state
                                url
                            }
                        }
                    }
                }
            }
        }
    }
    """

    payload = {"query": query, "variables": {"projectId": PROJECT_ID}}
    response = requests.post(GRAPHQL_URL, headers=HEADERS, data=json.dumps(payload))
    data = response.json()
    return data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])


def get_rejected_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter items with 'Reject' status that are still open."""
    rejected = []
    for item in items:
        status = None
        for fv in item.get("fieldValues", {}).get("nodes", []):
            field = fv.get("field", {}).get("name", "")
            if field == "Status":
                status = fv.get("name", "")

        content = item.get("content", {})
        if not content or not content.get("id"):
            continue

        if status == "Reject" and content.get("state") == "OPEN":
            rejected.append(content)

    return rejected


def close_issue_as_not_planned(issue_id: str) -> bool:
    """Close an issue with state_reason NOT_PLANNED via GraphQL."""
    mutation = """
    mutation($issueId: ID!) {
        closeIssue(input: {issueId: $issueId, stateReason: NOT_PLANNED}) {
            issue {
                number
                state
            }
        }
    }
    """

    payload = {"query": mutation, "variables": {"issueId": issue_id}}
    response = requests.post(GRAPHQL_URL, headers=HEADERS, data=json.dumps(payload))
    result = response.json()
    return "errors" not in result


def main():
    items = fetch_project_items()
    rejected = get_rejected_issues(items)

    if not rejected:
        print("No rejected issues to close.")
        return

    print(f"Found {len(rejected)} rejected issue(s) to close:\n")
    for issue in rejected:
        print(f"  #{issue['number']} - {issue['title']}")
        success = close_issue_as_not_planned(issue["id"])
        status = "closed as not_planned" if success else "FAILED"
        print(f"    -> {status}")

    print("\nDone.")


if __name__ == "__main__":
    main()
