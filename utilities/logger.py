import streamlit as st
import datetime
import json
from github import Github

# GitHub Repository Info
github_token = st.secrets["Github"]["github_token"]
github_user = "Team-EduChange"
github_repo = "Data_Base"
github_branch = "main"

# Initialize GitHub object
g = Github(github_token)
repo = g.get_repo(f"{github_user}/{github_repo}")

def log_event(event_type, details):
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "details": details
    }

    if 'logs' not in st.session_state:
        st.session_state['logs'] = []
    
    st.session_state['logs'].append(log_entry)
    
    save_log_to_github(log_entry)


def save_log_to_github(log_entry):
    file_path = "logs/log_data.json" 
    
    try:
        try:
            file_content = repo.get_contents(file_path, ref=github_branch)
            existing_logs = json.loads(file_content.decoded_content.decode('utf-8'))
            sha = file_content.sha 
        except Exception:
            existing_logs = []
            sha = None

        existing_logs.append(log_entry)

        if sha:
            repo.update_file(
                path=file_path,
                message="Appending new log entry",
                content=json.dumps(existing_logs, ensure_ascii=False, indent=4),
                sha=sha,  
                branch=github_branch
            )
        else:
            repo.create_file(
                path=file_path,
                message="Creating log file with the first log entry",
                content=json.dumps(existing_logs, ensure_ascii=False, indent=4),
                branch=github_branch
            )
    except Exception as e:
        st.error(f"Error saving log to GitHub: {e}")

# Function to log login with timestamp
def log_login(user_id):
    details = {
        "user_id": user_id,
        "login_time": datetime.datetime.now().isoformat()  # Log the login time
    }
    log_event("login", details)

# Function to log credit transactions and track service usage count
def log_credit_transaction(user_id, transaction_type, amount, user_credits_after_transaction, service_id):
    if 'service_usage_count' not in st.session_state:
        st.session_state['service_usage_count'] = {}
    
    if service_id not in st.session_state['service_usage_count']:
        st.session_state['service_usage_count'][service_id] = 0

    st.session_state['service_usage_count'][service_id] += 1
    
    details = {
        "user_id": user_id,
        "transaction_type": transaction_type,
        "amount": amount,
        "transaction_time": datetime.datetime.now().isoformat(),  
        "user_credits_after_transaction": user_credits_after_transaction,  
        "service_id": service_id,
        "service_usage_count": st.session_state['service_usage_count'][service_id] 
    }
    log_event("credit_transaction", details)
