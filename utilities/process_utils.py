import re
import io
import streamlit as st
import fitz  # For handling PDFs
from google.cloud import vision
from google.oauth2 import service_account

# ===============================*** Setup Configuration ***===============================

# Set up Google Cloud Vision API
credentials = service_account.Credentials.from_service_account_info(st.secrets["Google"])
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# ===============================*** Document Processing Functions ***===============================

def extract_subject_ranges(text, start_grade, end_grade=None):
    if end_grade:
        pattern = rf'\[{start_grade}\](.*?)\[{end_grade}\]'
    else:
        pattern = rf'\[{start_grade}\](.*)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    return ""

def create_subject_dict(range_text):
    subjects_matches = re.findall(r'\n(.*?):', range_text)
    subjects = [match.strip() for match in subjects_matches]
    subjects = [subject for subject in subjects if len(subject) < 12]
    subject_dict = {subject: '' for subject in subjects}

    for i, subject in enumerate(subjects):
        if i + 1 < len(subjects):
            content = re.search(f'{re.escape(subject)}:(.*?){re.escape(subjects[i+1])}:', range_text, re.S)
        else:
            content = re.search(f'{re.escape(subject)}:(.*)', range_text, re.S)
        if content:
            subject_dict[subject] = content.group(1).strip()

    return subject_dict

def process_detailed_skills(detailed_skills):
    career_elective_subjects = "<진로 선택 과목>"
    individual_specific_abilities = '개인별 세부능력 특기사항'

    key_with_career_elective = None
    for key, value in detailed_skills.items():
        if career_elective_subjects in value:
            key_with_career_elective = key
            break

    if key_with_career_elective:
        value = detailed_skills[key_with_career_elective]
        parts = value.split("\n\n", 1)
        front_text = parts[0]
        back_text = parts[1]

        back_text = back_text.replace(career_elective_subjects, "")
        detailed_skills[key_with_career_elective] = front_text
        detailed_skills[individual_specific_abilities] = back_text

    return detailed_skills

def extract_text_from_pdf(file):
    pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    extracted_text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        extracted_text += text
        if not text.strip():
            image = page.get_pixmap()
            image_bytes = image.tobytes("png")
            image = vision.Image(content=image_bytes)
            response = vision_client.text_detection(image=image)

            if response.text_annotations:
                extracted_text += response.text_annotations[0].description
    return extracted_text


def convert_image_to_pdf_bytes(image):
    pdf_buffer = io.BytesIO()
    image.convert('RGB').save(pdf_buffer, format="PDF")
    pdf_buffer.seek(0) 
    return pdf_buffer.getvalue()
