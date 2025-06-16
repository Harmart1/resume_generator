from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from backend.models import MockInterview, Credit # Ensure Credit model is correctly named
from backend.extensions import db
from . import mock_interview_bp # Import the blueprint defined in __init__.py
import json # For storing sample questions as JSON

# Helper function for CSRF token placeholder
def csrf_token_field():
    # This is a placeholder. Actual CSRF implementation might vary.
    return ""

@mock_interview_bp.route('/')
@login_required
def index():
    """Displays a list of the user's mock interviews."""
    interviews = MockInterview.query.filter_by(user_id=current_user.id, is_archived=False).order_by(MockInterview.created_at.desc()).all()
    return render_template('mock_interview/index.html', interviews=interviews)

@mock_interview_bp.route('/start', methods=['GET', 'POST'])
@login_required
def start():
    """Handles starting a new mock interview, with credit checking."""

    # Credit Checking for 'legacy' credits
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to start a new mock interview. Please purchase more credits.', 'warning')
        return redirect(url_for('mock_interview.index'))

    if request.method == 'POST':
        job_description = request.form.get('job_description', '') # Optional field

        # Placeholder for sample questions. In a real app, these might be generated
        # or selected based on the job description.
        sample_questions = [
            "Tell me about yourself.",
            "Why are you interested in this role?",
            "What are your strengths?",
            "What are your weaknesses?",
            "Describe a challenging situation you faced and how you handled it."
        ]

        new_interview = MockInterview(
            user_id=current_user.id,
            job_description=job_description,
            questions=json.dumps(sample_questions), # Store questions as JSON string
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
            flash(f'Error starting mock interview: {str(e)}', 'danger')
            # Consider logging the error e

    return render_template('mock_interview/start.html', csrf_token_field=csrf_token_field)

# Note: This simplified version replaces the previous complex logic.
# Assumes MockInterview model has fields like: user_id, job_description, questions (TEXT/JSON),
# created_at, updated_at, is_archived.
# And potentially: answers, scores, feedback, overall_score.
# `is_archived` default should be False.
# `created_at` and `updated_at` are assumed to be handled by the model.
# The template names `mock_interview/index.html` and `mock_interview/start.html` match the blueprint's template_folder.
