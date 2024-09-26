import streamlit as st
import random
import fitz
import re
import tempfile
from google.cloud import vision
import openai
from datetime import datetime
from google.oauth2 import service_account
from google.cloud import vision
from data.example_sentences import example_sentences_interview
from utilities.ui_components import button_style_2
from data.university_department import university_department
from utilities.process_utils import extract_subject_ranges, create_subject_dict, process_detailed_skills
from utilities.common_utils import go_back, request_chat_completion, deduct_credit
from utilities.github_utils import save_student_interview_data_to_github, get_submission_count, update_submission_count, load_user_database
from utilities.logger import log_credit_transaction
import gc  # Import garbage collector

# Set up OpenAI API
openai.api_key = st.secrets["OpenAI"]["openai_api_key"]
openai_client = openai.OpenAI(api_key=openai.api_key)

# Set up Google Cloud Vision API
credentials = service_account.Credentials.from_service_account_info(st.secrets["Google"]) 
vision_client = vision.ImageAnnotatorClient(credentials=credentials)


def enter_interview_info_page():
    st.subheader("대학 면접정보 입력하기")
    st.write('   ')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        grade = st.selectbox("학년", [" ", "1학년", "2학년", "3학년"])
    with col2:
        class_num = st.selectbox("반", [" ", '1반', '2반', '3반', '4반', '5반', '6반', '7반', '8반', '9반', '10반', '11반', '12반'])
    with col3:
        number = st.selectbox("번호", list(range(1, 41)))
    with col4:
        name = st.text_input("이름")
        
    col1, col2 = st.columns(2)
    with col1:
        university = st.selectbox("대학", list(university_department.keys()), key="university")
    with col2:
        if university:
            department = st.selectbox("학과", university_department[university], key="department")
    st.write("   ")
    
    st.write("학생의 생활기록부를 업로드")
    uploaded_files = st.file_uploader("생기부를 업로드하세요", label_visibility="collapsed", accept_multiple_files=True, type=["pdf"])

    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Step 1: Save the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
                temp_pdf_file.write(uploaded_file.read())
                temp_pdf_path = temp_pdf_file.name

            # Step 2: Open and read the PDF file
            doc = fitz.open(temp_pdf_path)

            # Step 3: Define Keywords and Initialize Variables
            keywords = [
                "자율활동", "동아리활동", "진로활동", "창 의 적 체 험 활 동 상 황", "봉 사 활 동 실 적",
                "[1학년]", "[2학년]", "[3학년]", "행 동 특 성 및 종 합 의 견", "<진로 선택 과목>"
            ]

            text = ""
            self_directed_activities = {"1학년": "", "2학년": "", "3학년": ""}
            club_activities = {"1학년": "", "2학년": "", "3학년": ""}
            career_activities = {"1학년": "", "2학년": "", "3학년": ""}
            first_detailed_skills = {}
            second_detailed_skills = {}
            third_detailed_skills = {}
            behavioral_characteristics = []

            # Step 4: Extract and Clean Text from PDF
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text("blocks")
                for block in blocks:
                    page_block_text = block[4]

                    # Define the patterns to remove
                    date_time_pattern = re.compile(r'^.*?\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}/.*?\n', re.DOTALL)
                    specific_pattern = re.compile(r'과목\s+세 부 능 력 및 특 기 사 항\n', re.DOTALL)

                    # Remove the matched patterns
                    page_block_text = re.sub(date_time_pattern, '', page_block_text)
                    page_block_text = re.sub(specific_pattern, '', page_block_text)

                    # Process the text
                    lines = page_block_text.split('\n')
                    filtered_lines = []
                    previous_line_saved = False

                    for i, line in enumerate(lines):
                        # Check if the current line meets the conditions
                        meets_condition = any(keyword in line for keyword in keywords) or len(line) > 30
                        
                        # Check if the next line is '\n'
                        next_line_is_newline = (i < len(lines) - 1) and (lines[i + 1] == '')
                        
                        # Save the current line if it meets the conditions or the previous line was saved and the next line is '\n'
                        if meets_condition or (previous_line_saved and next_line_is_newline):
                            filtered_lines.append(line)
                            previous_line_saved = True
                        else:
                            previous_line_saved = False

                    filtered_text = '\n'.join(filtered_lines)

                    # Concatenate the filtered text
                    if text:
                        text += "\n\n"
                    text += filtered_text
            
            merged_text = text.replace("\n", "")

            # Step 5: Extract Subject Ranges for Each Grade
            range_text_1 = extract_subject_ranges(text, '1학년', '2학년')
            range_text_2 = extract_subject_ranges(text, '2학년', '3학년')
            range_text_3 = extract_subject_ranges(text, '3학년')

            # Step 6: Extract Detailed Subject Contents
            first_detailed_skills = create_subject_dict(range_text_1)
            second_detailed_skills = create_subject_dict(range_text_2)
            third_detailed_skills = create_subject_dict(range_text_3)

            # Step 7: Process Detailed Skills for Each Grade
            first_detailed_skills = process_detailed_skills(first_detailed_skills)
            second_detailed_skills = process_detailed_skills(second_detailed_skills)
            third_detailed_skills = process_detailed_skills(third_detailed_skills)

            first_detailed_skills = {key: value.replace('\n', ' ') for key, value in first_detailed_skills.items()}
            second_detailed_skills = {key: value.replace('\n', ' ') for key, value in second_detailed_skills.items()}
            third_detailed_skills = {key: value.replace('\n', ' ') for key, value in third_detailed_skills.items()}

            # Step 8: Extract Activity Texts
            self_pattern = r"자율활동(.*?)동아리활동"
            club_pattern = r"동아리활동(.*?)진로활동"
            first_career_pattern = r"진로활동(.*?)자율활동"
            second_career_pattern = r"진로활동((?:.(?!진로활동))*?)봉 사 활 동 실 적"

            self_matches = re.findall(self_pattern, merged_text)
            club_matches = re.findall(club_pattern, merged_text)
            career_matches = re.findall(first_career_pattern, merged_text) + re.findall(second_career_pattern, merged_text)

            for i in range(3):
                self_directed_activities[f"{i+1}학년"] = self_matches[i] if i < len(self_matches) else "0"
                club_activities[f"{i+1}학년"] = club_matches[i] if i < len(club_matches) else "0"
                career_activities[f"{i+1}학년"] = career_matches[i] if i < len(career_matches) else "0"

            # Step 9: Extract Behavioral Characteristics
            start = re.search("행 동 특 성 및 종 합 의 견", merged_text)
            if start:
                start_idx = start.end()
                behavioral_characteristics = merged_text[start_idx:]
            else:
                behavioral_characteristics = ""

            # Free up memory by closing the PDF document and deleting variables
            doc.close()
            del text, merged_text, filtered_text, doc
            gc.collect()

    ### Submit and Request API ###
    button_style_2()
    col1, col2 = st.columns(2)
    submission_message = None
    error_message = None
    with col1:
        if st.button("뒤로가기"):
            go_back()
    with col2:
        if st.button("생성하기"):
            if not university:
                st.error("지원하고자하는 대학을 입력해주세요.")
            elif not department:
                st.error("지원하고자 하는 학과를 입력해주세요.")
            elif not uploaded_files:
                st.error("생활기록부를 업로드해주세요.")
            elif grade.strip() and class_num.strip() and number and name.strip() and uploaded_files is not None:
                selected_project = st.session_state.get('selected_project')
                user_id = st.session_state.get('teacher_user_id')

                if selected_project:
                    project_name = selected_project.get('project_name', '대학면접 예상질문 생성')
                    submission_count = get_submission_count(user_id, grade, class_num, number, name, project_name)
                    if submission_count >= 3:
                        error_message = "제출 횟수가 최대 3회를 초과했습니다. 더 이상 제출할 수 없습니다."
                    else:
                        if deduct_credit(user_id, 10):
                            user_database = load_user_database()
                            user_credits_after_transaction = user_database['credentials']['user_ids'][user_id]['credit']
                            log_credit_transaction(user_id, "decrease", 10, user_credits_after_transaction, "service_10")

                            uploaded_files_bytes = b''.join([file.read() for file in uploaded_files])
                            st.session_state['grade'] = grade.strip()
                            st.session_state['class_num'] = class_num.strip()
                            st.session_state['number'] = number
                            st.session_state['name'] = name.strip()

                            # Avoid saving large files in session state
                            del st.session_state['upload_file']
                            gc.collect()

                            prompt_template_interview = selected_project.get('prompt_template', '')
                            if prompt_template_interview:
                                prompt = prompt_template_interview.format(
                                    university=university,
                                    department=department,
                                    self_directed_activities=self_directed_activities,
                                    club_activities=club_activities,
                                    career_activities=career_activities,
                                    first_detailed_skills=first_detailed_skills,
                                    second_detailed_skills=second_detailed_skills,
                                    third_detailed_skills=third_detailed_skills,
                                    behavioral_characteristics=behavioral_characteristics
                                )
                                final_prompt = prompt
                                if university == university and department == department:
                                    field = university_department.get(university, {}).get(department, None)
                                    example_questions = example_sentences_interview[field]
                                    if len(example_questions) > 10:
                                        example_questions = random.sample(example_questions, 10)
                                    for example_question in example_questions:
                                        final_prompt += f"\n- {example_question}"

                                response = request_chat_completion(
                                    final_prompt,
                                    model="gpt-4o-2024-08-06",
                                    stream=True,
                                    temperature=0.0
                                )
                                response_text = ''.join([chunk.choices[0].delta.content if chunk.choices[0].delta.content else '' for chunk in response])

                                st.session_state['gpt_response'] = response_text  
                                submission_message = "결과물 제출이 성공적으로 완료되었습니다."

                                filename = f"{user_id}_{grade}_{class_num}_{number}_{name}_{project_name}"
                                save_student_interview_data_to_github({
                                    "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "grade": grade,
                                    "class_num": class_num,
                                    "student_number": number,
                                    "student_name": name,
                                    "project_name": project_name,
                                    "gpt_response": response_text  
                                }, filename)

                                update_submission_count(user_id, grade, class_num, number, name, project_name)
                            else:
                                error_message = "선택된 프로젝트에 템플릿 정보가 없습니다."
                        else:
                            error_message = "제출이 불가합니다. 선생님께 문의하시길 바랍니다."
                else:
                    error_message = "선택된 프로젝트 정보가 없습니다."
            else:
                error_message = "학년, 반, 번호, 이름을 모두 입력하고 결과물 이미지를 업로드해주세요."

    if submission_message:
        st.success(submission_message)
    if error_message:
        st.error(error_message)
