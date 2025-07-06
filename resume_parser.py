import re
import spacy
import json
import os
from spacy.cli import download

# Try loading the model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Download it if missing (first-time Render run)
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


# Path to skill storage
SKILL_FILE = os.path.join(os.path.dirname(__file__),'skills.json')

EMAIL_REGEX = r'[\w\.-]+@[\w\.-]+\.\w+'
PHONE_REGEX = r'\+?\d[\d\s-]{8,15}'

def load_skills():
    with open(SKILL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_skills(skills):
    with open(SKILL_FILE, 'w') as f:
        json.dump(sorted(list(set(skills))), f, indent=2)

def update_skills(new_text):
    skills = load_skills()
    doc = nlp(new_text.lower())
    tokens = set(token.text for token in doc if not token.is_stop and not token.is_punct)

    new_skills_found = {token for token in tokens if token not in skills and len(token) > 2}
    if new_skills_found:
        skills.extend(new_skills_found)
        save_skills(skills)

def parse_resume(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ''
    elif file_path.endswith(".docx"):
        import docx
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif file_path.endswith(".txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    return text

def extract_fields(text):
    update_skills(text)  # <--- this updates skills.json if new ones are found
    skills = load_skills()

    doc = nlp(text.lower())
    tokens = [token.text for token in doc if not token.is_stop and not token.is_punct]

    found_skills = list({skill for skill in skills if skill in ' '.join(tokens)})

    email = re.findall(EMAIL_REGEX, text)
    phone = re.findall(PHONE_REGEX, text)

    return {
        "email": email[0] if email else "",
        "phone": phone[0] if phone else "",
        "skills": found_skills
    }
