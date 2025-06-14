from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from . import mock_interview_bp
# Assuming db, User, Credit, Resume, MockInterview are accessible
# e.g. from .. import db (if db in backend/__init__.py)
# from ..app import db, User, Credit, Resume (if these are all in app.py)
from ..app import db, User, Credit, Resume # Using app.py as central model/db store
from .models import MockInterview
from .utils.question_generator import generate_questions
from .utils.interview_analyzer import score_answer, generate_feedback
from .forms import MockInterviewForm, get_resume_choices # Added get_resume_choices
from functools import wraps # For tier_required decorator
from datetime import datetime # For Credit model usage

# Tier check decorator (similar to one in the issue's app.py)
def tier_required(required_tier_list):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('auth.login')) # Assuming auth blueprint login route
            if current_user.tier not in required_tier_list:
                flash(f'This feature requires {", ".join(required_tier_list)} tier. Please upgrade your plan.', 'error')
                # Assuming a main.pricing route or similar
                return redirect(url_for('frontend_routes.pricing') if 'frontend_routes.pricing' else url_for('index_route')) # Fallback to index
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_and_use_credit(credit_type, amount_needed=1):
    if current_user.tier == 'pro': # Pro tier has unlimited
        return True, "Pro tier: unlimited credits."

    credit = Credit.query.filter_by(user_id=current_user.id, credit_type=credit_type).first()

    # Grant default credits if user has none of this type yet (e.g. for starter tier monthly allowance)
    # This logic might be better handled during user registration or monthly reset cron job
    if not credit and current_user.tier == 'starter':
        # Example: Starter gets 3 mock interview credits
        initial_amount = 0
        if credit_type == 'mock_interview': initial_amount = 3
        elif credit_type == 'resume_ai': initial_amount = 10 # from issue
        elif credit_type == 'cover_letter_ai': initial_amount = 5 # from issue

        if initial_amount > 0:
            credit = Credit(user_id=current_user.id, credit_type=credit_type, amount=initial_amount, last_reset=datetime.utcnow())
            db.session.add(credit)
            # db.session.commit() # Commit separately or after usage

    if not credit or credit.amount < amount_needed:
        return False, f'Insufficient {credit_type.replace("_", " ")} credits. Current: {credit.amount if credit else 0}. Needed: {amount_needed}. Consider upgrading your plan.'

    credit.amount -= amount_needed
    db.session.commit()
    return True, f'{credit_type.replace("_", " ")} credit used. Remaining: {credit.amount}.'

@mock_interview_bp.route('/', methods=['GET', 'POST'])
@login_required
@tier_required(['starter', 'pro']) # Mock interviews for starter and pro
def index():
    form = MockInterviewForm()
    form.resume_id.choices = get_resume_choices() # Populate choices dynamically

    if form.validate_on_submit():
        # Credit check for 'starter' tier
        if current_user.tier == 'starter':
            can_use, message = check_and_use_credit('mock_interview', 1)
            if not can_use:
                flash(message, 'error')
                return render_template('mock_interview/index.html', form=form, mock_interviews=MockInterview.query.filter_by(user_id=current_user.id).order_by(MockInterview.created_at.desc()).all())
            else:
                flash(message, 'info')

        job_desc = form.job_description.data
        resume_content = ""
        selected_resume_id = form.resume_id.data

        if selected_resume_id and selected_resume_id != 0:
            resume = Resume.query.filter_by(id=selected_resume_id, user_id=current_user.id).first()
            if resume:
                resume_content = resume.content # Assuming 'content' field stores resume text
            else:
                flash('Selected resume not found.', 'error')
                # Keep resume_text if user pasted something
                if not form.resume_text.data:
                    return render_template('mock_interview/index.html', form=form, mock_interviews=MockInterview.query.filter_by(user_id=current_user.id).order_by(MockInterview.created_at.desc()).all())
                resume_content = form.resume_text.data # Fallback to pasted text
        elif form.resume_text.data:
            resume_content = form.resume_text.data
        else:
            flash('Please select a resume or paste resume text.', 'warning')
            return render_template('mock_interview/index.html', form=form, mock_interviews=MockInterview.query.filter_by(user_id=current_user.id).order_by(MockInterview.created_at.desc()).all())

        questions_list = generate_questions(job_desc, resume_content)

        new_mock_interview = MockInterview(
            user_id=current_user.id,
            resume_id=selected_resume_id if selected_resume_id != 0 else None,
            job_description=job_desc,
            questions=questions_list, # Store as JSON
            answers=[],
            scores=[],
            feedback=[],
            overall_score=None
        )
        db.session.add(new_mock_interview)
        db.session.commit()
        flash('New mock interview session created! Answer the questions below.', 'success')
        return redirect(url_for('mock_interview.answer_questions', interview_id=new_mock_interview.id))

    past_interviews = MockInterview.query.filter_by(user_id=current_user.id).order_by(MockInterview.created_at.desc()).all()
    return render_template('mock_interview/index.html', form=form, mock_interviews=past_interviews)

@mock_interview_bp.route('/<int:interview_id>/answer', methods=['GET', 'POST'])
@login_required
def answer_questions(interview_id):
    interview_session = MockInterview.query.filter_by(id=interview_id, user_id=current_user.id).first_or_404()

    if interview_session.answers and len(interview_session.answers) > 0 : # Answers already submitted
         flash('Answers already submitted for this session. Viewing results.','info')
         return redirect(url_for('mock_interview.view_results', interview_id=interview_session.id))

    if request.method == 'POST':
        submitted_answers = request.form.getlist('answers') # Assumes textarea name="answers" for each

        if len(submitted_answers) != len(interview_session.questions):
            flash('Please answer all questions before submitting.', 'error')
            return render_template('mock_interview/answer.html', interview_session=interview_session)

        processed_scores = []
        processed_feedback = []
        total_overall_score = 0

        resume_used = Resume.query.get(interview_session.resume_id) if interview_session.resume_id else None
        resume_content_for_analysis = resume_used.content if resume_used else "" # TODO: what if resume_id was None but user pasted text? This info is lost currently.

        for i, q_text in enumerate(interview_session.questions):
            ans_text = submitted_answers[i]
            score_dict = score_answer(q_text, ans_text, resume_content_for_analysis)
            feedback_list = generate_feedback(score_dict, q_text, ans_text, resume_content_for_analysis)

            processed_scores.append(score_dict)
            processed_feedback.append(feedback_list)
            total_overall_score += score_dict['overall']

        interview_session.answers = submitted_answers
        interview_session.scores = processed_scores
        interview_session.feedback = processed_feedback
        interview_session.overall_score = round(total_overall_score / len(interview_session.questions), 1) if interview_session.questions else 0

        db.session.commit()
        flash('Your answers have been submitted and analyzed!', 'success')
        return redirect(url_for('mock_interview.view_results', interview_id=interview_session.id))

    return render_template('mock_interview/answer.html', interview_session=interview_session)

@mock_interview_bp.route('/<int:interview_id>/results')
@login_required
def view_results(interview_id):
    interview_session = MockInterview.query.filter_by(id=interview_id, user_id=current_user.id).first_or_404()
    if not interview_session.answers: # Not yet answered
        flash('This interview session has not been completed yet.','warning')
        return redirect(url_for('mock_interview.answer_questions', interview_id=interview_id))

    return render_template('mock_interview/results.html', interview_session=interview_session)

# Example of a route that might be in a 'main' or 'frontend' blueprint
@mock_interview_bp.route('/pricing') # TEMPORARY - this should be a global route
def pricing():
    return "Pricing Page Placeholder (to be implemented in a main blueprint)"
