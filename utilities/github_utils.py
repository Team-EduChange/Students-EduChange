import streamlit as st
import yaml
from github import Github
import openai
from io import BytesIO
import json

# ===============================*** Setup Configuration ***===============================

# GitHub Access Token and Repository Details
github_token = st.secrets["Github"]["github_token"]
github_user = "Team-EduChange"
github_repo = "Data_Base"
github_branch = "main"

# Initialize GitHub object
g = Github(github_token)
repo = g.get_repo(f"{github_user}/{github_repo}")

# Set up OpenAI API
openai.api_key = st.secrets["OpenAI"]["openai_api_key"]
openai_client = openai.OpenAI(api_key=openai.api_key)


# ===============================*** GitHub File Management Functions ***===============================

def load_yaml_from_github(file_path):
    try:
        content_file = repo.get_contents(file_path, ref=github_branch)
        content = content_file.decoded_content.decode("utf-8")
        return yaml.safe_load(content)
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return None

def save_student_text_data_to_github(data, filename):
    yaml_data = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    file_path = f"submissions/{filename}.yaml"

    try:
        existing_file = repo.get_contents(file_path, ref=github_branch)
        repo.update_file(
            path=existing_file.path,
            message="Update student submission data",
            content=yaml_data,
            sha=existing_file.sha,
            branch=github_branch
        )
    except:
        repo.create_file(
            path=file_path,
            message="Add new student submission data",
            content=yaml_data,
            branch=github_branch
        )


def save_student_interview_data_to_github(data, filename):
    yaml_data = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    yaml_file_path = f"submissions/{filename}.yaml"

    try:
        existing_file = repo.get_contents(yaml_file_path, ref=github_branch)
        repo.update_file(
            path=existing_file.path,
            message="Update student submission data",
            content=yaml_data,
            sha=existing_file.sha,
            branch=github_branch
        )
    except Exception:
        repo.create_file(
            path=yaml_file_path,
            message="Add new student submission data",
            content=yaml_data,
            branch=github_branch
        )

def save_yaml_to_github(file_path, data):
    yaml_data = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    try:
        existing_file = repo.get_contents(file_path, ref=github_branch)
        repo.update_file(
            path=existing_file.path,
            message="Update user database",
            content=yaml_data,
            sha=existing_file.sha,
            branch=github_branch
        )
    except Exception:
        repo.create_file(
            path=file_path,
            message="Create user database",
            content=yaml_data,
            branch=github_branch
        )

# ===============================*** Student Submission Tracking Functions ***===============================

def load_data_from_github():
    try:
        file_path = "submission_data.json"  
        file_content = repo.get_contents(file_path, ref=github_branch)
        data = json.loads(file_content.decoded_content.decode("utf-8"))
        return data
    except Exception as e:
        st.error(f"제출 기록을 불러오는 중 오류 발생: {str(e)}")
        return {}

def save_data_to_github(data):
    try:
        file_path = "submission_data.json"
        json_data = json.dumps(data, indent=4, ensure_ascii=False)  
        try:
            file_content = repo.get_contents(file_path, ref=github_branch)
            repo.update_file(
                file_path,
                "Update submission data",
                json_data,  
                file_content.sha,
                branch=github_branch
            )
        except Exception:
            repo.create_file(
                file_path,
                "Create submission data",
                json_data, 
                branch=github_branch
            )
    except Exception as e:
        st.error(f"제출 기록을 저장하는 중 오류 발생: {str(e)}")

def get_submission_count(user_id, grade, class_num, number, name, service_name, project_name):
    try:
        data = load_data_from_github()
        student_key = f"{user_id}_{grade}_{class_num}_{number}_{name}_{service_name}_{project_name}"
        return data.get(student_key, 0)
    except Exception as e:
        st.error(f"제출 기록을 불러오는 중 오류 발생: {str(e)}")
        return 0

def update_submission_count(user_id, grade, class_num, number, name, service_name, project_name):
    try:
        data = load_data_from_github()
        student_key = f"{user_id}_{grade}_{class_num}_{number}_{name}_{service_name}_{project_name}"
        if student_key in data:
            data[student_key] += 1
        else:
            data[student_key] = 1
        save_data_to_github(data)
    except Exception as e:
        st.error(f"제출 기록을 업데이트하는 중 오류 발생: {str(e)}")


def load_user_database():
    return load_yaml_from_github('user_database.yaml')

