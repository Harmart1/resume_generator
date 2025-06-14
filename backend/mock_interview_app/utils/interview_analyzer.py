from textblob import TextBlob
import spacy

try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    # This should ideally be handled at app startup or installation
    print("Spacy model 'en_core_web_sm' not found. Please download it by running: python -m spacy download en_core_web_sm")
    # Fallback to a dummy nlp if model is not found, to prevent crash, though analysis will be poor.
    class DummySpacyNLP:
        def __call__(self, text):
            class Doc:
                def __init__(self, text): self.text = text; self.ents = []; self.noun_chunks = []
                def similarity(self, other_doc): return 0.0
            return Doc(text)
    nlp = DummySpacyNLP()


def extract_skill_from_question(question_text):
    # Simple keyword extraction, can be improved with NLP
    # Looks for phrases like "experience with X", "used X", "proficiency in X"
    question_doc = nlp(question_text.lower())
    keywords = ["with", "using", "used", "proficiency in", "experience in", "knowledge of", "about"]
    skill = None
    for token in question_doc:
        if token.text in keywords:
            # Next non-stopword noun/propn could be the skill
            for child in token.rights:
                if child.pos_ in ["NOUN", "PROPN"] and not child.is_stop:
                    skill = child.text
                    break
            if skill: break
    if not skill and len(question_doc.noun_chunks) > 0: # Fallback to last noun chunk
        skill = question_doc.noun_chunks[-1].text
    return skill

def score_answer(question, answer_text, resume_text=""):
    answer_doc = nlp(answer_text)
    answer_blob = TextBlob(answer_text)

    skill_in_question = extract_skill_from_question(question)

    # Relevance: Check if skill from question is in answer, or general relevance.
    relevance_score = 1
    if skill_in_question:
        if skill_in_question.lower() in answer_text.lower():
            relevance_score = 5
        else: # Check similarity
            skill_doc = nlp(skill_in_question)
            if any(token.similarity(skill_doc) > 0.6 for token in answer_doc if token.has_vector and skill_doc.has_vector):
                relevance_score = 3
    elif len(answer_text.split()) > 10: # General check if no specific skill
        relevance_score = 3 # Default for a reasonable answer
        if len(answer_text.split()) > 50: relevance_score = 4

    # Specificity: Presence of numbers, named entities (examples, projects, results)
    specificity_score = 1
    if any(ent.label_ in ['CARDINAL', 'DATE', 'QUANTITY', 'PERCENT'] for ent in answer_doc.ents):
        specificity_score = 5
    elif len(answer_doc.ents) > 1: # Any other entities like ORG, PERSON, PRODUCT
        specificity_score = 3
    if specificity_score < 5 and resume_text: # Check if resume keywords are mentioned
        resume_doc = nlp(resume_text)
        resume_keywords = [ent.text.lower() for ent in resume_doc.ents if ent.label_ in ['ORG', 'PRODUCT', 'GPE']]
        if any(keyword in answer_text.lower() for keyword in resume_keywords):
            specificity_score = max(specificity_score, 4)


    # Clarity: Based on sentence structure, length. Penalize very short/long.
    clarity_score = 3 # Default
    word_count = len(answer_text.split())
    if 30 <= word_count <= 250: # Good range
        clarity_score = 5
    elif 10 <= word_count < 30 or (word_count > 250 and word_count < 400):
        clarity_score = 3
    else: # Too short or too long
        clarity_score = 1

    # Confidence: Based on sentiment polarity.
    confidence_score = 3 # Neutral default
    if answer_blob.sentiment.polarity > 0.2:
        confidence_score = 5
    elif answer_blob.sentiment.polarity < -0.1: # Negative sentiment
        confidence_score = 1

    overall = round((relevance_score + specificity_score + clarity_score + confidence_score) / 4.0, 1)

    return {
        'relevance': relevance_score,
        'specificity': specificity_score,
        'clarity': clarity_score,
        'confidence': confidence_score,
        'overall': overall
    }

def generate_feedback(scores, question, answer_text, resume_text=""):
    feedback_points = []
    skill_in_question = extract_skill_from_question(question)

    if scores['relevance'] < 3:
        if skill_in_question:
            feedback_points.append(f"Consider directly addressing your experience with '{skill_in_question}'.")
        else:
            feedback_points.append("Try to more directly answer the question. Providing specific examples can help.")

    if scores['specificity'] < 3:
        feedback_points.append("Make your answer more specific. Include concrete examples, numbers, or outcomes if possible.")
    elif scores['specificity'] < 5 and resume_text:
        resume_doc = nlp(resume_text)
        resume_entities = {ent.text.lower(): ent.label_ for ent in resume_doc.ents if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'EVENT']}
        mentioned_entities = {ent.text.lower() for ent in nlp(answer_text).ents}
        unmentioned_resume_entities = [k for k,v in resume_entities.items() if k not in mentioned_entities]
        if unmentioned_resume_entities:
             feedback_points.append(f"You could strengthen your answer by mentioning relevant experiences from your resume, such as your work with {random.choice(unmentioned_resume_entities)}.")

    if scores['clarity'] < 3:
        feedback_points.append("Aim for clear and concise answers. A typical good length is between 30 to 250 words.")

    if scores['confidence'] < 3:
        feedback_points.append("Try using more assertive and positive language to convey confidence.")

    if not feedback_points:
        if scores['overall'] >= 4.0:
            feedback_points.append("Great job on this answer! It was clear, specific, and relevant.")
        else:
            feedback_points.append("This is a decent answer. Consider if you can add more detail or examples to make it stronger.")

    return feedback_points
