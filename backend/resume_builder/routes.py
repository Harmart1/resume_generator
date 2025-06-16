from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from backend.models import Resume, Credit # Make sure Credit model is correctly named and imported
from backend.extensions import db
from . import bp # Import bp from the local __init__.py

# Helper function to get CSRF token if not using Flask-WTF forms explicitly
# This is a placeholder; actual CSRF protection might be handled globally
# or via a more specific Flask-WTF integration if forms are used.
def csrf_token_field():
    # In a real app, you might generate a CSRF token and pass it to the template
    # For Flask-WTF, it's often {{ form.csrf_token }}
    # If CSRFProtect is enabled globally, it might inject it or expect it in headers
    # For simplicity, if not using Flask-WTF forms here, this might be an empty string
    # or a custom solution. The template calls csrf_token_field().
    # Let's assume it's available in template context via an extension or app.context_processor
    return ""

@bp.route('/')
@login_required
def index():
    """Displays a list of the user's resumes."""
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Resume.updated_at.desc()).all()
    return render_template('resume_builder/my_resumes.html', resumes=resumes)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Handles creation of a new resume, with credit checking."""
    
    # Credit Checking
    # Using 'legacy' as specified, adjust if a different credit_type is used for resumes
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to create a new resume. Please purchase more credits.', 'warning')
        return redirect(url_for('resume_builder.index'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content') # This would be raw text or JSON depending on design

        if not title or not content:
            flash('Title and content are required.', 'danger')
            return render_template('resume_builder/create_resume.html', csrf_token_field=csrf_token_field)

        # Proceed with creation if credit check passed and form is valid
        new_resume = Resume(
            user_id=current_user.id,
            title=title,
            content=content # Store as is; could be structured JSON if form supports it
        )

        # Decrement credit
        user_credit.amount -= 1

        db.session.add(new_resume)
        db.session.add(user_credit) # Add updated credit object to session

        try:
            db.session.commit()
            flash('Resume created successfully!', 'success')
            return redirect(url_for('resume_builder.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating resume: {str(e)}', 'danger')
            # Log the error e for debugging
    
    return render_template('resume_builder/create_resume.html', csrf_token_field=csrf_token_field)

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
