import logging # Added for logging
from flask import render_template, redirect, url_for, flash, request, current_app # Added current_app
from flask_login import login_required, current_user
import spacy # Added spacy
from backend.models import MockInterview, Credit # Ensure Credit model is correctly named
from backend.extensions import db
from . import mock_interview_bp # Import the blueprint defined in __init__.py
from .forms import MockInterviewStartForm # Added for Flask-WTF form
from .utils.question_generator import QuestionGenerator # Import QuestionGenerator
from .utils.interview_analyzer import InterviewAnalyzer # Import InterviewAnalyzer
import json # For storing sample questions as JSON

# Configure logger for this blueprint
logger = logging.getLogger(__name__) # Added for logging

# Global cache for NLP models
NLP_MODELS = {}

def load_spacy_model_for_language(lang='en'):
    if lang in NLP_MODELS:
        return NLP_MODELS[lang]

    model_name = None
    if lang == 'en':
        model_name = 'en_core_web_sm'
    elif lang == 'es':
        model_name = 'es_core_news_sm'
    # Add more languages and their models here
    # else:
    #     current_app.logger.warning(f"Unsupported language '{lang}', defaulting to English model.")
    #     model_name = 'en_core_web_sm'
    #     lang = 'en' # ensure lang reflects the model being loaded

    if not model_name: # Default if lang not 'en' or 'es'
        print(f"Unsupported language '{lang}', defaulting to English model.")
        # current_app.logger.warning(f"Unsupported language '{lang}', defaulting to English model.")
        model_name = 'en_core_web_sm'
        lang = 'en'


    try:
        nlp = spacy.load(model_name)
        NLP_MODELS[lang] = nlp
        print(f"Successfully loaded spaCy model '{model_name}' for language '{lang}'.")
        # current_app.logger.info(f"Successfully loaded spaCy model '{model_name}' for language '{lang}'.")
        return nlp
    except OSError:
        print(f"spaCy model '{model_name}' not found. Attempting to download...")
        # current_app.logger.info(f"spaCy model '{model_name}' not found. Attempting to download...")
        try:
            spacy.cli.download(model_name)
            nlp = spacy.load(model_name)
            NLP_MODELS[lang] = nlp
            print(f"Successfully downloaded and loaded spaCy model '{model_name}' for language '{lang}'.")
            # current_app.logger.info(f"Successfully downloaded and loaded spaCy model '{model_name}' for language '{lang}'.")
            return nlp
        except Exception as e:
            print(f"Failed to download/load spaCy model '{model_name}': {e}. Defaulting to English.")
            # current_app.logger.error(f"Failed to download/load spaCy model '{model_name}': {e}", exc_info=True)
            if 'en' not in NLP_MODELS: # Ensure English is loaded as a last resort
                # This assumes 'en_core_web_sm' is either already downloaded or will be by this call
                # Potentially add a specific download for 'en_core_web_sm' here if truly critical and might be missing
                try:
                    NLP_MODELS['en'] = spacy.load('en_core_web_sm')
                except OSError: # Fallback if even english model download fails during fallback.
                    print("CRITICAL: English spaCy model 'en_core_web_sm' also failed to load. NLP features will be impaired.")
                    # current_app.logger.critical("CRITICAL: English spaCy model 'en_core_web_sm' also failed to load. NLP features will be impaired.")
                    return None # Or raise an error
            return NLP_MODELS.get('en')

@mock_interview_bp.route('/')
@login_required
def index():
    """Displays a list of the user's mock interviews."""
    interviews = MockInterview.query.filter_by(user_id=current_user.id, is_archived=False).order_by(MockInterview.created_at.desc()).all()
    return render_template('mock_interview/index.html', interviews=interviews)

@mock_interview_bp.route('/start', methods=['GET', 'POST'])
@login_required
def start():
    """Handles starting a new mock interview, with credit checking and Flask-WTF form."""
    form = MockInterviewStartForm()

    # Credit Checking for 'legacy' credits
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to start a new mock interview. Please purchase more credits.', 'warning')
        return redirect(url_for('mock_interview.index')) # Redirect if no credits

    if form.validate_on_submit():
        # Re-check credits on submission
        if not user_credit or user_credit.amount <= 0:
            flash('Credit check failed upon submission. Please ensure you have enough credits.', 'warning')
            return redirect(url_for('mock_interview.index'))

        job_description = form.job_description.data
        language = form.language.data
        nlp_model = load_spacy_model_for_language(language)

        # Placeholder for sample questions. In a real app, these might be generated
        # or selected based on the job description.
        if nlp_model:
            # Use resume_text=current_user.resume_text if available and relevant
            # For now, assuming resume_text is not readily available here or not used by default
            question_generator = QuestionGenerator(job_description=job_description, language_nlp=nlp_model, language_code=language)
            generated_questions = question_generator.generate_questions()
        else:
            # Fallback if NLP model failed to load critically
            logger.error(f"NLP model failed to load for language {language}. Using generic questions for interview.")
            generated_questions = ["Tell me about yourself.", "Why are you interested in this role?", "What are your strengths?"]


        new_interview = MockInterview(
            user_id=current_user.id,
            job_description=job_description,
            language=language, # Save the selected language
            questions=json.dumps(generated_questions), # Store questions as JSON string
            # Initialize other fields as needed by your MockInterview model
            # e.g., answers=json.dumps([]), scores=json.dumps([]), feedback=json.dumps([]), overall_score=None
        )

        user_credit.amount -= 1

        db.session.add(new_interview)
        db.session.add(user_credit)

        try:
            db.session.commit()
            flash('Mock interview session started successfully! You can find it in your list of interviews.', 'success')
            # For now, redirect to index. Later, this might redirect to an actual interview page.
            # e.g., return redirect(url_for('mock_interview.conduct_interview', interview_id=new_interview.id))
            return redirect(url_for('mock_interview.index'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting mock interview: {str(e)}", exc_info=True)
            flash(f'Error starting mock interview: {str(e)}', 'danger')
            # Error already logged

    return render_template('mock_interview/start.html', form=form)

# Note: This simplified version replaces the previous complex logic.
# Assumes MockInterview model has fields like: user_id, job_description, questions (TEXT/JSON),
# created_at, updated_at, is_archived.
# And potentially: answers, scores, feedback, overall_score.
# `is_archived` default should be False.
# `created_at` and `updated_at` are assumed to be handled by the model.
# The template names `mock_interview/index.html` and `mock_interview/start.html` match the blueprint's template_folder.

# Placeholder for answer processing route modifications:
@mock_interview_bp.route('/interview/<int:interview_id>/answer', methods=['POST']) # Example route
@login_required
def process_answer(interview_id):
    answer_data = request.form.get('answer') # Assuming answer comes from a form field
    current_question_index = int(request.form.get('question_index', 0)) # Assuming we track current question

    if not answer_data:
        return jsonify({'error': 'No answer provided'}), 400

    interview = MockInterview.query.get_or_404(interview_id)
    if interview.user_id != current_user.id:
        # flash('Unauthorized access.', 'danger') # flash won't work for jsonify response
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        questions = json.loads(interview.questions)
        if not (0 <= current_question_index < len(questions)):
            return jsonify({'error': 'Invalid question index'}), 400
        question_text = questions[current_question_index]
    except json.JSONDecodeError:
        logger.error(f"Could not parse questions for interview {interview_id}")
        return jsonify({'error': 'Could not retrieve questions for analysis'}), 500


    language = interview.language or 'en' # Default to 'en' if not set
    nlp_model = load_spacy_model_for_language(language)

    if not nlp_model:
        logger.error(f"NLP model for language '{language}' could not be loaded for interview {interview_id}.")
        return jsonify({'error': f"Could not load language model for '{language}'. Analysis aborted."}), 500

    # Assuming resume_text might be stored in user profile or passed differently
    # resume_text = current_user.profile.resume_text if hasattr(current_user, 'profile') else ""
    resume_text = "" # Placeholder

    analyzer = InterviewAnalyzer(user_answer=answer_data,
                                 question=question_text,
                                 language_nlp=nlp_model,
                                 language_code=language,
                                 resume_text=resume_text)
    feedback_result = analyzer.analyze()

    # Here you would typically save the feedback and scores to the database
    # For example, updating the 'answers' and 'feedback' fields in the MockInterview model
    # This part is highly dependent on your exact model structure for storing answers/feedback per question

    # Example: Storing feedback (simplified)
    # This assumes 'interview.feedback' is a JSON field that can store a list of feedback entries
    # Or you might have a separate AnswerFeedback model
    # current_feedback = json.loads(interview.feedback) if interview.feedback else []
    # current_feedback.append({
    #     'question': question_text,
    #     'answer': answer_data,
    #     'analysis': feedback_result
    # })
    # interview.feedback = json.dumps(current_feedback)
    # db.session.commit()

    logger.info(f"Answer processed for interview {interview_id}, question_index {current_question_index}, language {language}")
    return jsonify({
        'status': 'success',
        'feedback': feedback_result,
        'next_question_index': current_question_index + 1 if current_question_index + 1 < len(questions) else None
        # Add next question text if needed by frontend
    })
