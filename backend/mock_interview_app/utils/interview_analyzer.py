import logging
import random
from textblob import TextBlob
import spacy # Keep spacy import for type hinting if desired, but model loaded by instance

logger = logging.getLogger(__name__)

# Helper function (can be static method or outside class if preferred)
def _extract_skill_from_question(question_text, nlp_model):
    if not nlp_model: return None
    question_doc = nlp_model(question_text.lower())
    keywords = ["with", "using", "used", "proficiency in", "experience in", "knowledge of", "about"]
    skill = None
    for token in question_doc:
        if token.text in keywords:
            for child in token.rights:
                if child.pos_ in ["NOUN", "PROPN"] and not child.is_stop:
                    skill = child.text
                    break
            if skill: break
    if not skill and len(question_doc.noun_chunks) > 0:
        skill = question_doc.noun_chunks[-1].text
    return skill

class InterviewAnalyzer:
    def __init__(self, user_answer, question, language_nlp, language_code='en', resume_text=""):
        self.user_answer = user_answer
        self.question = question
        self.nlp = language_nlp # This is the language-specific model
        self.language_code = language_code
        self.resume_text = resume_text

        if not self.nlp:
            logger.error(f"NLP model not provided for language {self.language_code}. Analysis will be limited.")
            # Create a dummy nlp if one wasn't provided to avoid crashes, though functionality will be basic
            class DummySpacyNLP:
                def __call__(self, text):
                    class Doc:
                        def __init__(self, text): self.text = text; self.ents = []; self.noun_chunks = []
                        def similarity(self, other_doc): return 0.0
                    return Doc(text)
            self.nlp = DummySpacyNLP()

    def _score_answer_component(self):
        answer_doc = self.nlp(self.user_answer)
        answer_blob = TextBlob(self.user_answer) # TextBlob will attempt to detect language

        skill_in_question = _extract_skill_from_question(self.question, self.nlp)

        relevance_score = 1
        if skill_in_question:
            if skill_in_question.lower() in self.user_answer.lower():
                relevance_score = 5
            else:
                skill_doc = self.nlp(skill_in_question)
                # Check for vector similarity only if tokens have vectors
                # and both skill_doc and answer_doc have them
                if skill_doc.has_vector and any(token.has_vector for token in answer_doc):
                     similarities = [token.similarity(skill_doc) for token in answer_doc if token.has_vector and token.vector_norm]
                     if similarities and any(s > 0.6 for s in similarities):
                        relevance_score = 3
                elif len(self.user_answer.split()) > 10 : # Fallback if no vectors
                    relevance_score = 2

        elif len(self.user_answer.split()) > 10:
            relevance_score = 3
            if len(self.user_answer.split()) > 50: relevance_score = 4

        specificity_score = 1
        if any(ent.label_ in ['CARDINAL', 'DATE', 'QUANTITY', 'PERCENT'] for ent in answer_doc.ents):
            specificity_score = 5
        elif len(answer_doc.ents) > 1:
            specificity_score = 3

        if specificity_score < 5 and self.resume_text:
            resume_doc = self.nlp(self.resume_text)
            resume_keywords = [ent.text.lower() for ent in resume_doc.ents if ent.label_ in ['ORG', 'PRODUCT', 'GPE']]
            if any(keyword in self.user_answer.lower() for keyword in resume_keywords):
                specificity_score = max(specificity_score, 4)

        clarity_score = 3
        word_count = len(self.user_answer.split())
        if 30 <= word_count <= 250: clarity_score = 5
        elif 10 <= word_count < 30 or (word_count > 250 and word_count < 400): clarity_score = 3
        else: clarity_score = 1

        confidence_score = 3
        # TextBlob sentiment polarity is between -1 and 1
        if answer_blob.sentiment.polarity > 0.2: confidence_score = 5
        elif answer_blob.sentiment.polarity < -0.1: confidence_score = 1

        overall = round((relevance_score + specificity_score + clarity_score + confidence_score) / 4.0, 1)
        return {
            'relevance': relevance_score, 'specificity': specificity_score,
            'clarity': clarity_score, 'confidence': confidence_score, 'overall': overall
        }

    def _generate_feedback_points(self, scores):
        feedback_points = []
        skill_in_question = _extract_skill_from_question(self.question, self.nlp)

        if scores['relevance'] < 3:
            feedback_points.append(f"Consider directly addressing your experience with '{skill_in_question}'." if skill_in_question else "Try to more directly answer the question.")
        if scores['specificity'] < 3:
            feedback_points.append("Make your answer more specific. Include concrete examples, numbers, or outcomes.")
        # elif scores['specificity'] < 5 and self.resume_text:
        #     # This logic could be refined or made optional
        #     pass
        if scores['clarity'] < 3:
            feedback_points.append("Aim for clear and concise answers. A typical good length is between 30 to 250 words.")
        if scores['confidence'] < 3:
            feedback_points.append("Try using more assertive and positive language.")

        if not feedback_points:
            feedback_points.append("Good answer overall." if scores['overall'] >= 4.0 else "This is a decent start. Consider adding more detail.")

        # Language-specific feedback example
        if self.language_code == 'es':
            if "excelente" in self.user_answer.lower(): # Simple keyword example
                feedback_points.append("(Detectada palabra clave en Español: excelente)")

        # Add TextBlob sentiment to feedback for context
        answer_blob = TextBlob(self.user_answer)
        feedback_points.append(f"Sentiment (TextBlob): polarity={answer_blob.sentiment.polarity:.2f}, subjectivity={answer_blob.sentiment.subjectivity:.2f}")

        return feedback_points

    def analyze(self):
        scores = self._score_answer_component()
        feedback_texts = self._generate_feedback_points(scores)

        return {
            "scores": scores,
            "feedback_summary": " ".join(feedback_texts), # Combine points into a single string
            "feedback_points": feedback_texts # Or return as a list
        }
