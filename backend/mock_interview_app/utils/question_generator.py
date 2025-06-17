import random
import logging

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self, job_description, language_nlp, language_code='en', resume_text=""):
        self.job_description = job_description
        self.nlp = language_nlp
        self.language_code = language_code
        self.resume_text = resume_text
        # self.questions_db = self.load_questions_for_language(language_code) # If using a DB of questions

    def generate_questions(self, num_skill_questions=3, num_behavioral_questions=2):
        if not self.nlp:
            logger.error("NLP model not available for QuestionGenerator. Returning generic questions.")
            return ["Tell me about yourself.", "Why are you interested in this role?"]

        # Language-specific question generation
        if self.language_code == 'es':
            # Placeholder for Spanish-specific skill extraction and question generation
            # For now, returning translated examples or generic Spanish questions
            # Ideally, skill extraction and templating would also be language-aware
            jd_skills_es = ["trabajo en equipo", "resolución de problemas"] # Dummy extraction

            skill_questions_es = [f"Háblame de tu experiencia con {skill}." for skill in jd_skills_es[:num_skill_questions]]

            behavioral_questions_es = [
                "Describe una situación desafiante que enfrentaste en el trabajo y cómo la manejaste.",
                "Cuéntame sobre una vez que tuviste que colaborar con un colega difícil."
            ]
            selected_behavioral_es = random.sample(behavioral_questions_es, min(len(behavioral_questions_es), num_behavioral_questions))

            if not skill_questions_es and num_skill_questions > 0:
                 skill_questions_es.append("¿Puedes describir tus habilidades técnicas relevantes para esta descripción de trabajo?")

            return skill_questions_es + selected_behavioral_es

        # Default to English if not 'es' or if specific English logic is needed
        doc = self.nlp(self.job_description)
        skills = list(set([chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3 and chunk.root.pos_ == 'NOUN']))
        common_non_skills = ['experience', 'responsibilities', 'requirements', 'description', 'job', 'role', 'company', 'team', 'project']
        skills = [s for s in skills if s not in common_non_skills and s in self.job_description.lower()] # Ensure skill is in JD

        selected_skills = []
        if skills:
            selected_skills = random.sample(skills, min(len(skills), num_skill_questions))

        skill_question_templates = [
            "Tell me about your experience with {}.",
            "Describe a project where you utilized {}.",
            "How would you rate your proficiency in {}, and can you give an example?",
            "Walk me through a situation where you applied {} to solve a problem."
        ]
        skill_questions = [random.choice(skill_question_templates).format(skill) for skill in selected_skills]

        if self.resume_text:
            resume_doc = self.nlp(self.resume_text)
            # Using noun_chunks as a simple proxy if specific skill entities aren't available
            resume_keywords = [chunk.text.lower() for chunk in resume_doc.noun_chunks if len(chunk.text.split()) <= 2]
            resume_keywords = list(set(resume_keywords))

            # Add one question based on a resume keyword if not already covered by JD skills
            # and we still need more skill questions.
            if len(skill_questions) < num_skill_questions and resume_keywords:
                potential_resume_skills = [rk for rk in resume_keywords if not any(rk in q_text for q_text in skill_questions)]
                if potential_resume_skills:
                    additional_skill = random.choice(potential_resume_skills)
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
        selected_behavioral = []
        if behavioral_questions_pool:
            selected_behavioral = random.sample(behavioral_questions_pool, min(len(behavioral_questions_pool), num_behavioral_questions))

        if not skill_questions and (num_skill_questions > 0):
            skill_questions.append("Can you describe your technical skills relevant to this job description?")

        return skill_questions + selected_behavioral
