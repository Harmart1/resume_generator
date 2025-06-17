import random
import spacy
import logging # Added

logger = logging.getLogger(__name__) # Added

# Ensure model is loaded.
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    logger.error("Spacy model 'en_core_web_sm' not found. This model should be downloaded at application startup. Question generation will be impaired.")
    # Fallback or raise exception: For question generation, a dummy might be less useful.
    # For now, let it proceed (Spacy might raise error later or work with blank nlp object if it allows)
    # or define a simple dummy if Spacy calls will fail hard.
    # To be safe, let's use a similar dummy as in analyzer to avoid crashes.
    class DummySpacyNLP:
        def __call__(self, text):
            class Doc:
                def __init__(self, text): self.text = text; self.ents = []; self.noun_chunks = []
            return Doc(text)
    nlp = DummySpacyNLP()

def generate_questions(job_desc, resume_text="", num_skill_questions=3, num_behavioral_questions=2):
    doc = nlp(job_desc)

    # Extract potential skills (noun chunks)
    skills = list(set([chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3 and chunk.root.pos_ == 'NOUN']))
    # Filter out very common words or non-skill like terms if possible (simple example)
    common_non_skills = ['experience', 'responsibilities', 'requirements', 'description', 'job', 'role', 'company', 'team', 'project']
    skills = [s for s in skills if s not in common_non_skills]

    selected_skills = random.sample(skills, min(len(skills), num_skill_questions))

    skill_question_templates = [
        "Tell me about your experience with {}.",
        "Describe a project where you utilized {}.",
        "How would you rate your proficiency in {}, and can you give an example?",
        "Walk me through a situation where you applied {} to solve a problem."
    ]
    skill_questions = [random.choice(skill_question_templates).format(skill) for skill in selected_skills]

    if resume_text:
        resume_doc = nlp(resume_text)
        # Extract entities that might be skills or technologies from resume
        resume_keywords = [ent.text for ent in resume_doc.ents if ent.label_ in ['SKILL', 'PRODUCT', 'TECH', 'ORG', 'WORK_OF_ART']]
        resume_keywords = list(set([k.lower() for k in resume_keywords]))

        # Add one question based on a resume keyword if not already covered
        if len(skill_questions) < num_skill_questions and resume_keywords:
            additional_skill = random.choice(resume_keywords)
            if not any(additional_skill in q for q in skill_questions):
                 skill_questions.append(f"Your resume mentions {additional_skill}. Can you elaborate on your experience with it?")

    behavioral_questions_pool = [
        "Describe a challenging situation you faced at work and how you handled it.",
        "Tell me about a time you had to collaborate with a difficult colleague.",
        "How do you prioritize your tasks when faced with multiple deadlines?",
        "Give an example of a goal you set for yourself and how you achieved it.",
        "Describe a time you made a mistake at work. How did you rectify it?",
        "Tell me about a time you had to learn a new skill quickly for a project.",
        "How do you handle feedback or criticism?"
    ]
    selected_behavioral = random.sample(behavioral_questions_pool, min(len(behavioral_questions_pool), num_behavioral_questions))

    # Ensure we have a fallback if no skill questions were generated
    if not skill_questions and (num_skill_questions > 0):
        skill_questions.append("Can you describe your technical skills relevant to this job description?")

    return skill_questions + selected_behavioral
