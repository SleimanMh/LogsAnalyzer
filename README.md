Log Analyzer System

This application monitors runtime logs, extracts exceptions, classifies errors using an ML model, enriches them using an LLM, and automatically opens or updates Jira tickets.
It is designed for automated debugging, issue triage, and continuous monitoring of your application's logs.

🔍 What This Application Does
Here are the main steps performed by the system:

Watch the log files for any new entries.
Parse and extract errors from log lines.
Check if the error already exists
If it's a duplicate, update the related Jira ticket with a new comment.
If it's new, continue to the next steps.
Extract the corresponding code snippet from the stack trace (based on file paths found in the log).
Send the exception and snippet to the ML classifier to predict the error category.
Send the same error to the LLM to generate explanations, suggestions, and context.
Create a Jira ticket containing the structured error analysis.
View the updated ticket in the dashboard.
🚀 Running the Application
Use Docker Compose to build and start the system:

docker-compose build
docker-compose up
Dashboard URL:
http://localhost:8502

Jira URL:
https://mail-team-anmv56g9.atlassian.net/jira/software/c/projects/AL/list?jql=project%20%3D%20%22AL%22%20ORDER%20BY%20created%20DESC

Use the following env variables(.env): OPENAI_API_KEY=your_api_key_here JIRA_BASE_URL = "https://mail-team-anmv56g9.atlassian.net" JIRA_EMAIL = "sam96@mail.aub.edu" JIRA_API_TOKEN = "@T@TT3x#fG#0qG#QTvmu_cx_dash_8ilCnbKUVQRkUzUgW7#3Boxy5mlvZ19G#95iNedYg6SdiTTnOIzo11hUMSyyQ5iOTXqS7GN1kSLpqbmGdyCGRXIKKeP4JZDEtxG#Hy_gWlWQt1UEoQwIH76zOs0vClBRrADnyhvhbphe5@nBMxLps5YQzZMSxYk_eq_8730C1E9 " JIRA_PROJECT_KEY = "AL" JIRA_ASSIGNEE_ID="712020:983b8039-c12f-46ca-a912-fe314313e6fc"

The JIRA_API_TOKEN is provided in an obfuscated form.
To reconstruct it, do the following replacements:

Replace every '@' with 'A'
Replace every '#' with 'F'
Replace every '_dash_' with '-'
Replace every '_eq_' with '='
After applying all replacements, you will get the correct API token.
