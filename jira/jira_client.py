import requests
import json
from config.settings import (
    JIRA_BASE_URL,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
    JIRA_ASSIGNEE_ID,
    DEFAULT_LABELS,
    JIRA_ISSUE_TYPE
)

class JiraClient:

    def __init__(self):
        self.base = JIRA_BASE_URL
        self.auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    def create_ticket(self, summary, description, priority, suggestions):
        url = f"{self.base}/rest/api/3/issue"

        # 🧩 Build bullet list for suggestions
        suggestion_items = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": f"- {s}"}]
            }
            for s in suggestions or []
        ]

        payload = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description}
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "\nSuggestions:"}
                            ]
                        },
                        *suggestion_items
                    ]
                },
                "issuetype": {"name": JIRA_ISSUE_TYPE},
                "priority": {"name": priority},
                "labels": DEFAULT_LABELS,
            }
        }

        if JIRA_ASSIGNEE_ID:
            payload["fields"]["assignee"] = {"id": JIRA_ASSIGNEE_ID}

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            auth=self.auth,
            data=json.dumps(payload)
        )

        if response.status_code >= 300:
            raise Exception(f"Jira error: {response.text}")

        return response.json()["key"]

    def add_comment(self, issue_key, comment):
        """Add a comment to an existing Jira issue."""
        url = f"{self.base}/rest/api/3/issue/{issue_key}/comment"

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": comment}
                        ]
                    }
                ]
            }
        }

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            auth=self.auth,
            data=json.dumps(payload)
        )

        if response.status_code >= 300:
            raise Exception(
                f"Failed to add comment to {issue_key}: {response.status_code} {response.text}"
            )

        return response.json()
