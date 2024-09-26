import streamlit as st
from utilities.ui_components import button_style_2
from utilities.common_utils import set_page
from utilities.github_utils import load_yaml_from_github


def select_service_page():
    if st.session_state['pin_verified']:
        teacher_name = st.session_state.get('teacher_name')
        teacher_user_id = st.session_state.get('teacher_user_id')
        user_database = load_yaml_from_github('user_database.yaml')
        project_database = load_yaml_from_github('project_database.yaml')

        st.markdown(f"""
            <div style='font-size:35px; font-weight:bold;'>
                <span style='color:gold;'>{teacher_name}</span> 선생님의 프로젝트
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

        if user_database and project_database:
            user_info = user_database.get('credentials', {}).get('user_ids', {}).get(teacher_user_id, None)
            if user_info:
                projects = project_database.get('projects', [])
                filtered_projects = [
                    project for project in projects
                    if project.get('creator') == teacher_user_id
                ]

                if filtered_projects:
                    project_names_with_grade = [ 
                        f"( {project.get('grade', '전학년')} {project.get('subject', '과목 없음')} ) {project.get('service_name', '서비스 이름 없음')} // {project.get('project_name', '대학면접 예상질문 생성')} "
                        for project in filtered_projects
                    ]
                    project_name_map = {
                        f"( {project.get('grade', '전학년')} {project.get('subject', '과목 없음')} ) {project.get('service_name', '서비스 이름 없음')} // {project.get('project_name', '대학면접 예상질문 생성')} ": {
                            'service_name': project.get('service_name', '서비스 이름 없음'),
                            'project_name': project.get('project_name', '대학면접 예상질문 생성')
                        }
                        for project in filtered_projects
                    }
                    selected_display_name = st.selectbox("제출하고자 하는 프로젝트를 선택하세요.", project_names_with_grade)

                    if selected_display_name:
                        # Extract service_name and project_name from the selected project
                        selected_project_info = project_name_map.get(selected_display_name)
                        service_name = selected_project_info['service_name']
                        st.session_state['service_name'] = service_name
                        project_name = selected_project_info['project_name']

                        # Now search for the project based on both service_name and project_name
                        selected_project = next(
                            (project for project in filtered_projects 
                            if project.get('service_name', '서비스 이름 없음') == service_name and 
                                project.get('project_name', '대학면접 예상질문 생성') == project_name), 
                            None
                        )
                        button_style_2()
                        
                        if st.button("다음"):
                            if "생활기록부 생성" in selected_project["service_name"]:
                                st.session_state['selected_project'] = selected_project
                                st.session_state.pop('user_projects', None)
                                set_page("upload_text_detailed")
                            elif "수행평가 채점" in selected_project["service_name"]:
                                st.session_state['selected_project'] = selected_project
                                st.session_state.pop('user_projects', None)
                                set_page("upload_text_evaluation")
                            elif "면접질문 생성" in selected_project["service_name"]:
                                st.session_state['selected_project'] = selected_project
                                st.session_state.pop('user_projects', None)
                                set_page("enter_interview")
                    else:
                        st.error("프로젝트를 선택해주세요.")
                else:
                    st.warning("해당 선생님이 생성한 수행평가가 없습니다.")
            else:
                st.error("사용자 정보를 찾을 수 없습니다.")