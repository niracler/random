"""Close GitHub issues that have 'Reject' status on the project board as 'not planned'."""

import os
import json
import requests

GH_TOKEN = os.getenv("GH_TOKEN")
PROJECT_ID = "PVT_kwHOAXsRh84Ak2d1"
GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Content-Type": "application/json",
}


def fetch_project_items() -> list[dict]:
    """Fetch all items from the project board with their status and issue info."""
    query = """
    query {
        node(id: "%s") {
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
    """ % PROJECT_ID

    response = requests.post(
        GRAPHQL_URL, headers=HEADERS, data=json.dumps({"query": query})
    )
    data = response.json()
    return data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])


def get_rejected_issues(items: list[dict]) -> list[dict]:
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
    mutation {
        closeIssue(input: {issueId: "%s", stateReason: NOT_PLANNED}) {
            issue {
                number
                state
            }
        }
    }
    """ % issue_id

    response = requests.post(
        GRAPHQL_URL, headers=HEADERS, data=json.dumps({"query": mutation})
    )
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
