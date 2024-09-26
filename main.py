import streamlit as st
import asyncio  # Import asyncio to run async functions in sync context
from service_pages.verify_pin_page import verify_pin_page
from service_pages.select_service_page import select_service_page
from service_pages.upload_text_detailed_page import upload_text_detailed_page
from service_pages.upload_text_evaluation_page import upload_text_evaluation_page
from service_pages.enter_interview_info_page import enter_interview_info_page


#====================*** Page Configuration ***====================
st.set_page_config(
    page_title="EduChange",
    layout="wide"
)

#====================*** Initialize session state ***====================
if 'page' not in st.session_state:
    st.session_state['page'] = 'pin'  

if 'page_history' not in st.session_state:
    st.session_state['page_history'] = []


#====================*** session state ***====================
if st.session_state['page'] == 'pin':
    verify_pin_page()
elif st.session_state['page'] == 'select_service':
    select_service_page()
elif st.session_state['page'] == 'upload_text_detailed':
    asyncio.run(upload_text_detailed_page()) 
elif st.session_state['page'] == 'upload_text_evaluation':
    asyncio.run(upload_text_evaluation_page()) 
elif st.session_state['page'] == 'enter_interview':
    enter_interview_info_page()
