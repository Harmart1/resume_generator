from flask import request, jsonify
from flask_login import login_required, current_user
import spacy
from backend.models import db, SkillGap
from . import skill_gap_bp

# Load spaCy model (consistent with EQ Coach approach)
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("Downloading en_core_web_sm for Skill Gap Analysis...")
    spacy.cli.download('en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

# Predefined common skills (can be expanded or use a more sophisticated extraction)
# This is a simplified list for demonstration.
# A more robust solution might use entity recognition for "SKILL" if available
# in the spaCy model or a custom NER model.
# For 'en_core_web_sm', direct skill entity recognition is limited.
# We'll rely on noun chunks and a predefined list for better results with a small model.
COMMON_SKILLS_KEYWORDS = {
    "python", "java", "c++", "javascript", "react", "angular", "vue", "node.js", "flask", "django",
    "sql", "nosql", "mongodb", "postgresql", "docker", "kubernetes", "aws", "azure", "gcp",
    "machine learning", "data analysis", "project management", "agile", "scrum", "communication",
    "problem solving", "leadership", "teamwork", "marketing", "sales", "seo", "content creation",
    "graphic design", "ui/ux"
}

def extract_skills_from_text(text):
    doc = nlp(text.lower())
    extracted_skills = set()
    # 1. Check for predefined keywords directly
    for keyword in COMMON_SKILLS_KEYWORDS:
        if keyword in text.lower():
            extracted_skills.add(keyword)

    # 2. Analyze noun chunks for potential skills (often multi-word)
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text
        # If a noun chunk is in our common skills, it's a good candidate
        if chunk_text in COMMON_SKILLS_KEYWORDS:
            extracted_skills.add(chunk_text)
        # Also, check parts of the chunk if it's a compound skill
        # (e.g., "machine learning" is a keyword, also a noun chunk)
        # This might be redundant if keyword check is thorough but can catch variations.
        # For simplicity, direct keyword match and noun chunk match to keywords is primary.

    # 3. (Optional) Entity recognition if model supports it well (e.g., ORG, PRODUCT can sometimes hint at tech skills)
    # for ent in doc.ents:
    #    if ent.label_ == "SKILL": # Ideal but 'en_core_web_sm' doesn't have SKILL entity
    #        extracted_skills.add(ent.text.lower())
    #    elif ent.label_ in ["ORG", "PRODUCT"] and ent.text.lower() in COMMON_SKILLS_KEYWORDS:
    #        extracted_skills.add(ent.text.lower()) # e.g. "AWS" might be ORG

    return list(extracted_skills)

# Simple resource mapping (can be expanded)
SKILL_RESOURCES = {
    "python": "Coursera (Python for Everybody), Udemy",
    "javascript": "freeCodeCamp, MDN Web Docs, Udemy",
    "aws": "AWS Training and Certification, A Cloud Guru",
    "project management": "PMI (Project Management Institute), Coursera (Google Project Management Certificate)",
    "data analysis": "Coursera (Google Data Analytics Certificate), Kaggle Learn"
}

@skill_gap_bp.route('/analyze', methods=['POST'])
@login_required
def analyze_skill_gap():
    data = request.form
    resume_text = data.get('resume_text')
    job_description_text = data.get('job_description_text')

    if not resume_text or not job_description_text:
        return jsonify({'error': 'Missing resume_text or job_description_text'}), 400

    resume_skills = extract_skills_from_text(resume_text)
    jd_skills = extract_skills_from_text(job_description_text)

    skill_gaps_found = [skill for skill in jd_skills if skill not in resume_skills]

    suggested_resources_dict = {}
    for skill in skill_gaps_found:
        if skill in SKILL_RESOURCES:
            suggested_resources_dict[skill] = SKILL_RESOURCES[skill]
        else:
            suggested_resources_dict[skill] = "General web search for learning resources (e.g., Udemy, Coursera, official documentation)."

    # Save to database
    skill_gap_entry = SkillGap(
        user_id=current_user.id,
        job_description_summary=job_description_text[:500], # Store a snippet
        identified_gaps=", ".join(skill_gaps_found) if skill_gaps_found else "No specific gaps identified based on keyword matching.",
        suggested_resources=jsonify(suggested_resources_dict).get_data(as_text=True) # Store as JSON string
    )
    db.session.add(skill_gap_entry)
    db.session.commit()

    return jsonify({
        'resume_skills': resume_skills,
        'job_description_skills': jd_skills,
        'skill_gaps': skill_gaps_found,
        'suggested_resources': suggested_resources_dict
    }), 200
