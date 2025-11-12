import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
# Logs directory
LOGS_DIR = r"C:\Users\sleim\IdeaProjects\LogGenerator\logs"

CODEBASE_DIRS = [
    r"C:\development\ML",              
    r"C:\Users\sleim\IdeaProjects\LogGenerator\src"
]

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "storage", "tickets.db")

MODEL_NAME = "gpt-4.1-mini"

EMBEDDING_MODEL = "text-embedding-3-small"

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

JIRA_ASSIGNEE_ID = os.getenv("JIRA_ASSIGNEE_ID")

# Ticket defaults
JIRA_ISSUE_TYPE = "Task"
DEFAULT_LABELS = ["automation", "log-bot"]

# Embedding similarity threshold (0–1)
SIMILARITY_THRESHOLD = 0.87
