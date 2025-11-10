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

    def create_ticket(self, summary, description, priority):
        url = f"{self.base}/rest/api/3/issue"

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
                        }
                    ]
                },
                "issuetype": {"name": JIRA_ISSUE_TYPE},
                "priority": {"name": "High"},
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

        data = response.json()
        return data["key"]

    def add_comment(self, issue_key, comment):
        url = f"{self.base}/rest/api/3/issue/{issue_key}/comment"

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}]
                    }
                ]
            }
        }

        requests.post(
            url,
            headers={"Content-Type": "application/json"},
            auth=self.auth,
            data=json.dumps(payload)
        )
