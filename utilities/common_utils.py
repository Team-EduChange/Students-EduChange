import streamlit as st
import openai
from utilities.github_utils import load_yaml_from_github, save_yaml_to_github

# ===============================*** Setup Configuration ***===============================

# Set up OpenAI API
openai.api_key = st.secrets["OpenAI"]["openai_api_key"]
openai_client = openai.OpenAI(api_key=openai.api_key)


# ===============================*** Page Navigation Functions ***===============================

def set_page(page_name):
    st.session_state['page_history'].append(st.session_state['page'])
    st.session_state['page'] = page_name
    st.rerun()  

def go_back():
    if st.session_state['page_history']:
        st.session_state['page'] = st.session_state['page_history'].pop()
        st.rerun()  

# ===============================*** OpenAI Integration Functions ***===============================

def request_chat_completion(prompt, 
                            system_role="You are a helpful assistant.", 
                            model="gpt-3.5-turbo",
                            temperature=0.0,
                            stream=False):
    messages = [
        {"role": "user", "content": prompt}
    ]
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream
    )
    return response

# ===============================*** User Management Functions ***===============================

def deduct_credit(user_id, amount):
    user_database = load_yaml_from_github('user_database.yaml') 
    if not user_database:
        st.error("Failed to load user database.")
        return False

    user_info = user_database.get('credentials', {}).get('user_ids', {}).get(user_id, None)
    
    if not user_info:
        st.error("User information not found.")
        return False

    current_credit = user_info.get('credit', 0)
    
    if current_credit < amount:
        st.error("Insufficient credits.")
        return False
    user_info['credit'] = current_credit - amount
    user_database['credentials']['user_ids'][user_id] = user_info
    save_yaml_to_github('user_database.yaml', user_database)
    
    return True
