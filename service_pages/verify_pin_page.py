import streamlit as st
from utilities.ui_components import button_style_2
from utilities.common_utils import set_page
from utilities.github_utils import load_yaml_from_github

def verify_pin_page():
    if 'pin_verified' not in st.session_state:
        st.session_state['pin_verified'] = False
    button_style_2()
    if not st.session_state['pin_verified']:
        st.image('data/칼제출 로고.png')
        st.write('   ')
        pin_input = st.text_input("선생님의 PIN 번호 6자리를 입력하세요.", type="password", max_chars=6)

        if st.button("확인"):
            user_database = load_yaml_from_github('user_database.yaml')
            project_database = load_yaml_from_github('project_database.yaml')
            if user_database:
                found_user_id = None
                for teacher_user_id, user_info in user_database.get('credentials', {}).get('user_ids', {}).items():
                    if user_info['pin'] == pin_input:
                        teacher_name = user_info.get('name')
                        found_user_id = teacher_user_id
                        st.session_state['teacher_user_id'] = teacher_user_id
                        st.session_state['pin_verified'] = True
                        st.session_state['teacher_name'] = teacher_name
                        if project_database:
                            user_projects = []
                            projects = project_database.get('projects', [])

                            # Handling both list and dict structures
                            if isinstance(projects, dict):
                                projects = projects.items()
                            elif isinstance(projects, list):
                                projects = [(project.get('project_name', 'Unknown Project'), project) for project in projects]

                            for project_name, project_info in projects:
                                if project_info.get('created_by') == teacher_user_id:
                                    user_projects.append({
                                        'project_name': project_name,
                                        'project_info': project_info
                                    })
                            st.session_state['user_projects'] = user_projects
                        break
                if found_user_id:
                    set_page('select_service')
                else:
                    st.error("일치하는 선생님을 찾을 수 없습니다. 다시 시도해 주세요.")