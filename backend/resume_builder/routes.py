import logging # Added for logging
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from backend.models import Resume, Credit # Make sure Credit model is correctly named and imported
from backend.extensions import db
from . import bp # Import bp from the local __init__.py
from .forms import ResumeForm # Added for Flask-WTF form

# Configure logger for this blueprint
logger = logging.getLogger(__name__) # Added for logging

@bp.route('/')
@login_required
def index():
    """Displays a list of the user's resumes."""
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Resume.updated_at.desc()).all()
    return render_template('resume_builder/my_resumes.html', resumes=resumes)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Handles creation of a new resume, with credit checking and Flask-WTF form."""
    form = ResumeForm()
    
    # Credit Checking
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        # Flash message even if form is not submitted yet, or on GET request if no credits
        # This check should ideally happen before showing the form or on form submission
        flash('You do not have enough credits to create a new resume. Please purchase more credits.', 'warning')
        return redirect(url_for('resume_builder.index')) # Redirect if no credits

    if form.validate_on_submit():
        # Credit check again, in case state changed between page load and submission
        # Though for this simple flow, the above check might be sufficient if credits are only decremented here
        if not user_credit or user_credit.amount <= 0:
             flash('Credit check failed upon submission. Please ensure you have enough credits.', 'warning')
             return redirect(url_for('resume_builder.index'))

        new_resume = Resume(
            user_id=current_user.id,
            title=form.title.data,
            content=form.content.data
        )

        user_credit.amount -= 1

        db.session.add(new_resume)
        db.session.add(user_credit)

        try:
            db.session.commit()
            flash('Resume created successfully!', 'success')
            return redirect(url_for('resume_builder.index'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating resume: {str(e)}", exc_info=True)
            flash(f'Error creating resume: {str(e)}', 'danger')
            # Error already logged, no need for the comment "Log the error e for debugging"
    
    # For GET request or if form validation fails
    return render_template('resume_builder/create_resume.html', form=form)

# Note: The original routes.py had many other routes for a multi-step resume building process.
# This overwrite simplifies it to just an index and a direct create route as per the subtask.
# Features like loading resumes, AI enhancements, language selection from the old file are not included here.
# The 'is_archived' field was used in the old 'my_resumes' query, so I've kept it.
# The 'updated_at' field was used for ordering, kept that too.
# The Credit model interaction assumes 'amount' and 'credit_type' fields.
# The csrf_token_field is passed to the template for now.
# If Flask-WTF is intended for forms, a Form class should be defined,
# and form handling (validation, CSRF) would be more robust.
# The content field for Resume model is assumed to take string data.
# If it's JSON, the form and processing would need to reflect that.

# Ensure that the User model has a 'credits' relationship defined
# if you need to access credits via user.credits.
# Here, we are querying the Credit model directly.
# The prompt mentioned credit_type='legacy'.
# Ensure the Resume model has user_id, title, content, created_at, updated_at, is_archived fields.
# (created_at, updated_at are often handled by db.Column(DateTime, default=datetime.utcnow))
# is_archived default should be False.
# The prompt mentions {{ resume.created_at.strftime('%Y-%m-%d %H:%M') if resume.created_at else 'N/A' }}
# which implies created_at is a datetime object.
# The prompt mentions `resume_builder.index` and `resume_builder.create` for url_for, which matches these routes.
