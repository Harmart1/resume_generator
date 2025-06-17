import logging # Added for logging
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from backend.models import CoverLetter, Credit # Ensure Credit model is correctly named
from backend.extensions import db
from . import cover_letter_bp # Import the blueprint defined in __init__.py
from .forms import CoverLetterForm # Added for Flask-WTF form

# Configure logger for this blueprint
logger = logging.getLogger(__name__) # Added for logging

@cover_letter_bp.route('/')
@login_required
def index():
    """Displays a list of the user's cover letters."""
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id, is_archived=False).order_by(CoverLetter.updated_at.desc()).all()
    return render_template('cover_letter/index.html', cover_letters=cover_letters)

@cover_letter_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Handles creation of a new cover letter, with credit checking and Flask-WTF form."""
    form = CoverLetterForm()

    # Credit Checking for 'legacy' credits
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to create a new cover letter. Please purchase more credits.', 'warning')
        return redirect(url_for('cover_letter.index')) # Redirect if no credits

    if form.validate_on_submit():
        # Re-check credits on submission, though it might be redundant if only decremented here
        if not user_credit or user_credit.amount <= 0: # Should be checked before form processing
            flash('Credit check failed upon submission. Please ensure you have enough credits.', 'warning')
            return redirect(url_for('cover_letter.index'))

        new_cover_letter = CoverLetter(
            user_id=current_user.id,
            title=form.title.data,
            content=form.content.data
        )

        user_credit.amount -= 1

        db.session.add(new_cover_letter)
        db.session.add(user_credit)

        try:
            db.session.commit()
            flash('Cover Letter created successfully!', 'success')
            return redirect(url_for('cover_letter.index'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating cover letter: {str(e)}", exc_info=True)
            flash(f'Error creating cover letter: {str(e)}', 'danger')
            # Error already logged
    
    return render_template('cover_letter/create.html', form=form)

# Note: This simplified version replaces the previous complex logic involving AI generation,
# file processing, and specific forms. It focuses on basic CRUD and credit checking.
# Assumes CoverLetter model has fields: user_id, title, content, created_at, updated_at, is_archived.
# Assumes Credit model has fields: user_id, credit_type, amount.
# `is_archived` default should be False for new CoverLetters.
# `created_at` and `updated_at` are assumed to be handled by the model (e.g., default=datetime.utcnow).
# The template names `cover_letter/index.html` and `cover_letter/create.html` match the blueprint's template_folder.
