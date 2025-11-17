import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:5000/exceptions"

st.set_page_config(
    page_title="Exception Dashboard",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Exception Monitoring Dashboard")
st.markdown("A live overview of detected exceptions with AI-generated insights.")

# ---------------------------
# Fetch Data From Flask API
# ---------------------------
@st.cache_data(ttl=5)
def load_exceptions():
    try:
        res = requests.get(API_URL)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Failed to load exceptions: {e}")
        return []

data = load_exceptions()

if not data:
    st.warning("No exception data found.")
    st.stop()

# ---------------------------
# Sidebar Filters
# ---------------------------
st.sidebar.header("Filters")

priority_filter = st.sidebar.multiselect(
    "Filter by priority",
    ["High", "Medium", "Low"],
    default=["High", "Medium", "Low"]
)

exception_class_filter = st.sidebar.multiselect(
    "Filter by exception class",
    ["PythonError", "MLError", "AIPipelineError", "DataError"],
    default=["PythonError", "MLError", "AIPipelineError", "DataError"]
)

search_query = st.sidebar.text_input("Search in summary / cause")

# ---------------------------
# Filtering Logic
# ---------------------------
filtered = []
for ex in data:

    # Filter by priority
    if ex.get("priority") not in priority_filter:
        continue

    # Filter by exception_class
    if ex.get("exception_class") not in exception_class_filter:
        continue

    # Search text
    if search_query:
        q = search_query.lower()
        if q not in ex["summary"].lower() and q not in ex["cause"].lower():
            continue

    filtered.append(ex)

st.subheader(f"Showing **{len(filtered)}** matching exceptions")

# ---------------------------
# Exception Cards
# ---------------------------
for ex in filtered:
    with st.expander(
        f"{ex['priority']} | {ex['exception_class']} | {ex['summary']} — {ex['created_at']}"
    ):

        # Summary
        st.write("### 📝 Summary")
        st.write(ex["summary"])

        # Cause
        st.write("### ❗ Cause")
        st.write(ex["cause"])

        # Suggestions
        st.write("### 💡 Suggestions")
        try:
            suggestions = json.loads(ex["suggestions"])
            for s in suggestions:
                st.markdown(f"- {s}")
        except Exception:
            st.text(ex["suggestions"])

        # Documentation links
        st.write("### 📚 Documentation Links")
        try:
            links = json.loads(ex.get("documentation_links", "[]"))
            for url in links:
                st.markdown(f"- [{url}]({url})")
        except:
            st.write("No documentation links")

        # Jira key (optional)
        st.write("### 🔗 Jira Ticket")
        jira_key = ex.get("jira_key")
        if jira_key:
            st.markdown(
                f"[Open Jira Ticket](https://your-jira-instance/browse/{jira_key})"
            )
        else:
            st.write("No Jira key")

        # Timestamp
        st.write("### 🕑 Timestamp")
        st.code(ex["created_at"])
