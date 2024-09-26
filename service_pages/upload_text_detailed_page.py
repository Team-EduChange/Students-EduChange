import os
import errno
import asyncio
import streamlit as st
from PIL import Image
from io import BytesIO
from datetime import datetime
import pillow_heif
from utilities.ui_components import button_style_2
from pdf2image import convert_from_bytes
from utilities.process_utils import extract_text_from_pdf, convert_image_to_pdf_bytes
from utilities.common_utils import go_back, request_chat_completion, deduct_credit
from utilities.github_utils import save_student_text_data_to_github, get_submission_count, update_submission_count, load_user_database
from utilities.logger import log_credit_transaction

LOCK_FILE = 'submission_lock.lock'
PREVIEW_COUNT_FILE = 'preview_count.txt'
PREVIEW_LOCK_FILE = 'preview_lock.lock'
MAX_PREVIEW_USERS = 10  # Maximum number of simultaneous users

# Initialize preview slots to avoid issues when starting the server
def initialize_preview_slots():
    if os.path.exists(PREVIEW_COUNT_FILE):
        with open(PREVIEW_COUNT_FILE, 'w') as f:
            f.write('0')  # Reset preview count to 0
    if os.path.exists(PREVIEW_LOCK_FILE):
        os.remove(PREVIEW_LOCK_FILE)  # Remove lock file if exists

# Initialize the preview slots when starting the application
initialize_preview_slots()

# Acquire lock for critical sections
async def acquire_lock(lock_file):
    while True:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except OSError as e:
            if e.errno == errno.EEXIST:
                await asyncio.sleep(0.1)  # Wait before retrying
            else:
                raise

# Release lock after finishing critical sections
async def release_lock(lock_file):
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)  # Ensure the lock is removed after use
    except OSError as e:
        print(f"Error releasing lock: {e}")  # Add error handling if lock removal fails

# Acquire preview slot (manage concurrent users)
async def acquire_preview_slot():
    while True:
        try:
            fd = os.open(PREVIEW_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # Lock file to prevent race conditions
            try:
                if os.path.exists(PREVIEW_COUNT_FILE):
                    with open(PREVIEW_COUNT_FILE, 'r') as f:
                        count = int(f.read().strip() or 0)  # Ensure valid integer value is read
                else:
                    count = 0

                if count < MAX_PREVIEW_USERS:
                    count += 1
                    with open(PREVIEW_COUNT_FILE, 'w') as f:
                        f.write(str(count))
                    return True, count  # Slot acquired successfully
                else:
                    return False, count  # All preview slots are full
            finally:
                os.close(fd)
                os.remove(PREVIEW_LOCK_FILE)
        except OSError as e:
            if e.errno == errno.EEXIST:
                await asyncio.sleep(0.1)  # Wait before retrying to acquire the lock
            else:
                raise

# Release preview slot when the user is done
async def release_preview_slot():
    try:
        fd = os.open(PREVIEW_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            if os.path.exists(PREVIEW_COUNT_FILE):
                with open(PREVIEW_COUNT_FILE, 'r') as f:
                    count = int(f.read())
                count -= 1
                if count < 0:
                    count = 0  # Ensure count doesn't go negative
                with open(PREVIEW_COUNT_FILE, 'w') as f:
                    f.write(str(count))
            else:
                with open(PREVIEW_COUNT_FILE, 'w') as f:
                    f.write('0')
        finally:
            os.close(fd)
            os.remove(PREVIEW_LOCK_FILE)  # Always remove lock file
    except OSError as e:
        if e.errno == errno.EEXIST:
            await asyncio.sleep(0.1)  # Retry if lock is held by another process
        else:
            raise

# Process uploaded files (image/PDF preview)
async def process_upload(uploaded_file):
    file_type = uploaded_file.type
    if file_type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1)
        for i, image in enumerate(images):
            image.thumbnail((800, 800))
            rotated_image = image.rotate(-90, expand=True)
            st.image(rotated_image, caption=f"PDF 페이지 {i+1} 미리보기 - {uploaded_file.name}", use_column_width=True)
    elif file_type in ["image/jpeg", "image/png", "image/jpg", "image/heic"]:
        if file_type == "image/heic":
            heif_file = pillow_heif.open_heif(uploaded_file)
            image = heif_file.convert("RGB")
        else:
            image = Image.open(uploaded_file)
        image.thumbnail((800, 800))
        rotated_image = image.rotate(-90, expand=True)
        st.image(rotated_image, caption=f"이미지 파일 미리보기 - {uploaded_file.name}", use_column_width=True)
    return uploaded_file

# Upload text page with async functionality
async def upload_text_detailed_page():
    # Acquire preview slot before proceeding
    if not st.session_state.get('preview_slot_acquired', False):
        slot_acquired, queue_position = await acquire_preview_slot()
        if not slot_acquired:
            # Provide clear feedback with queue position and expected wait time
            st.error(f"현재 제출자가 많아 잠시후 다시 시도해주세요. 현재 대기 인원: {queue_position}/{MAX_PREVIEW_USERS}")
            estimated_wait_time = (queue_position + 1) * 10  # Assuming 10 seconds wait per user
            st.info(f"예상 대기 시간: {estimated_wait_time} 초")
            button_style_2()
            if st.button("다시 시도하기"):
                st.rerun()
            return
        else:
            st.session_state['preview_slot_acquired'] = True

    st.header("결과물 제출하기")
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        grade = st.selectbox("학년", [" ", "1학년", "2학년", "3학년"])
    with col2:
        class_num = st.selectbox("반", [" ", '1반', '2반', '3반', '4반', '5반', '6반', '7반', '8반', '9반', '10반', '11반', '12반', '13반', '14반', '15반'])
    with col3:
        number = st.selectbox("번호", list(range(1, 46)))
    with col4:
        name = st.text_input("이름")

    uploaded_files = st.file_uploader("작성한 결과물 이미지를 업로드해주세요.",
                                      label_visibility="collapsed", 
                                      type=["pdf", "jpg", "jpeg", "png", "heic"],
                                      accept_multiple_files=True)

    extracted_texts = []

    if uploaded_files:
        tasks = [process_upload(file) for file in uploaded_files]
        await asyncio.gather(*tasks)  # Process uploaded files concurrently

    submission_message = None 
    error_message = None

    button_style_2()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("뒤로가기"):
            if st.session_state.get('preview_slot_acquired', False):
                await release_preview_slot()
                st.session_state['preview_slot_acquired'] = False
            go_back()
    with col2:
        if st.button("제출하기"):
            if not await acquire_lock(LOCK_FILE):
                error_message = "현재 제출자가 많아 잠시후 다시 제출하길 바랍니다."
            else:
                try:
                    content = ""
                    for uploaded_file in uploaded_files:
                        file_type = uploaded_file.type
                        if file_type == "application/pdf":
                            processed_pdf_bytes = uploaded_file.read()
                            content += extract_text_from_pdf(BytesIO(processed_pdf_bytes))
                        else:
                            if file_type == "image/heic":
                                heif_file = pillow_heif.open_heif(uploaded_file)
                                image = heif_file.convert("RGB")
                            else:
                                image = Image.open(uploaded_file)
                            processed_pdf_bytes = convert_image_to_pdf_bytes(image)
                            content += extract_text_from_pdf(BytesIO(processed_pdf_bytes))

                    if grade.strip() and class_num.strip() and number and name.strip() and content:
                        selected_project = st.session_state.get('selected_project')
                        if selected_project:
                            service_name = st.session_state.get('service_name')
                            project_name = selected_project.get('project_name')
                            user_id = st.session_state.get('teacher_user_id')

                            submission_count = get_submission_count(user_id, grade, class_num, number, name, service_name, project_name) 
                            if submission_count >= 3:
                                error_message = "제출 횟수가 최대 3회를 초과했습니다. 더 이상 제출할 수 없습니다."
                            else:
                                if deduct_credit(user_id, 4):  
                                    user_database = load_user_database()
                                    user_credits_after_transaction = user_database['credentials']['user_ids'][user_id]['credit']
                                    log_credit_transaction(user_id, "decrease", 4, user_credits_after_transaction, "upload_text_detailed_page")

                                    submission_message = "결과물 제출이 성공적으로 완료되었습니다."

                                    st.session_state['grade'] = grade.strip()
                                    st.session_state['class_num'] = class_num.strip()
                                    st.session_state['number'] = number
                                    st.session_state['name'] = name.strip()
                                    st.session_state['extracted_text'] = content 

                                    prompt_template_text = selected_project.get('prompt_template', '')
                                    if prompt_template_text:
                                        prompt = prompt_template_text.format(content=content)
                                        
                                        response = request_chat_completion(
                                            prompt, 
                                            model="gpt-4o-2024-08-06",  
                                            stream=True, 
                                            temperature=0.0
                                        )
                                        response_text = ''.join([chunk.choices[0].delta.content if chunk.choices[0].delta.content else '' for chunk in response])

                                        st.session_state['gpt_response'] = response_text  

                                        filename = f"{user_id}_{grade}_{class_num}_{number}_{name}_{service_name}_{project_name}"
                                        save_student_text_data_to_github({
                                            "teacher": user_id,
                                            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "grade": grade,  
                                            "class_num": class_num,
                                            "student_number": number,
                                            "student_name": name,
                                            "service_name": service_name,
                                            "project_name": project_name, 
                                            "extracted_text": content,
                                            "gpt_response": response_text,  
                                        }, filename) 
                                        
                                        update_submission_count(user_id, grade, class_num, number, name, service_name, project_name)
                                    else:
                                        error_message = "선택된 프로젝트에 템플릿 정보가 없습니다."
                                else:
                                    error_message = "제출이 불가합니다. 선생님께 문의하시길 바랍니다."
                        else:
                            error_message = "선택된 프로젝트 정보가 없습니다."
                    else:
                        error_message = "학년, 반, 번호, 이름을 모두 입력하고 결과물 이미지를 업로드해주세요."
                finally:
                    await release_lock(LOCK_FILE)
                    if st.session_state.get('preview_slot_acquired', False):
                        await release_preview_slot()
                        st.session_state['preview_slot_acquired'] = False

    if submission_message:
        st.success(submission_message)
    if error_message:
        st.error(error_message)
    st.write('   ')
    st.markdown('<p style="color:red; font-weight:bold;">⚠️같은 결과는 최대 3번 제출이 가능합니다.</p>', unsafe_allow_html=True)