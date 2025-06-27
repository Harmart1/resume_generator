import os
import logging
import tempfile
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from backend.models import CoverLetter, Credit
from backend.extensions import db
from . import cover_letter_bp
from .forms import AICoverLetterForm, SimpleCoverLetterForm
from .utils.prompt_engine import build_cover_letter_prompt
from .utils.file_utils import extract_text_from_file
from .utils.security import rate_limited, validate_input_length

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_FOLDER = 'instance/uploads/cover_letter_files'

def get_upload_folder():
    return current_app.config.get('COVER_LETTER_UPLOAD_FOLDER', DEFAULT_UPLOAD_FOLDER)

@cover_letter_bp.route('/')
@login_required
def index():
    '''Displays a list of the user's cover letters.'''
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id, is_archived=False).order_by(CoverLetter.updated_at.desc()).all()
    return render_template('cover_letter/index.html', cover_letters=cover_letters)

@cover_letter_bp.route('/generate', methods=['GET', 'POST'])
@login_required
@rate_limited
def generate_ai_cover_letter():
    '''Handles AI-powered cover letter generation.'''
    form = AICoverLetterForm()
    upload_folder = get_upload_folder()
    os.makedirs(upload_folder, exist_ok=True)

    generation_credit_type = 'legacy'
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type=generation_credit_type).first()

    if request.method == 'GET' and (not user_credit or user_credit.amount <= 0):
        # Flash message for GET if no credits, but still show the form
        flash(f'Warning: You have no "{generation_credit_type}" credits. AI generation will not be possible until credits are available.', 'info')

    if request.method == 'POST':
        if not user_credit or user_credit.amount <= 0: # Check again on POST
            flash(f'You do not have enough "{generation_credit_type}" credits to generate a cover letter.', 'warning')
            return redirect(url_for('cover_letter.index')) # Or back to generate form with message

        if form.validate_on_submit():
            user_credit_on_submit = Credit.query.filter_by(user_id=current_user.id, credit_type=generation_credit_type).first()
            if not user_credit_on_submit or user_credit_on_submit.amount <= 0: # Final check
                flash('Credit check failed upon submission. Insufficient credits.', 'warning')
                return redirect(url_for('cover_letter.index'))

            resume_text_from_file = ""
            temp_file_path = None
            if form.resume_file.data:
                resume_file_storage = form.resume_file.data
                filename = secure_filename(resume_file_storage.filename)
                try:
                    with tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix="_" + filename, dir=upload_folder) as tmp_file:
                        resume_file_storage.save(tmp_file)
                        temp_file_path = tmp_file.name

                    logger.info(f"Resume file saved temporarily to {temp_file_path}")
                    resume_text_from_file = extract_text_from_file(temp_file_path)

                    if not resume_text_from_file and filename:
                        flash('Could not extract text from the uploaded resume. Check file or paste text.', 'warning')
                except Exception as e:
                    logger.error(f"Error processing resume file upload '{filename}': {e}", exc_info=True)
                    flash('An error occurred while processing your resume file.', 'danger')
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                            logger.info(f"Temporary file {temp_file_path} removed.")
                        except Exception as e_remove:
                            logger.error(f"Error removing temp file {temp_file_path}: {e_remove}", exc_info=True)

            final_resume_text = form.resume_text.data or resume_text_from_file

            form_data_dict = {
                'your_name': form.your_name.data, 'your_email': form.your_email.data,
                'job_title': form.job_title.data, 'company_name': form.company_name.data,
                'job_description': form.job_description.data, 'resume_text': final_resume_text,
                'refinement_type': form.refinement_type.data,
                'existing_cover_text': form.existing_cover_letter_text.data,
                'key_points': form.key_points.data, 'tone': form.tone.data,
            }

            validation_error = validate_input_length(
                form_data_dict['job_description'],
                form_data_dict['resume_text'],
                form_data_dict['existing_cover_text']
            )
            if validation_error:
                flash(validation_error, 'danger')
                return render_template('cover_letter/generate.html', form=form, title="Generate AI Cover Letter")

            try:
                ai_prompt = build_cover_letter_prompt(form_data_dict, form_data_dict['existing_cover_text'])
                logger.info(f"AI Prompt for user {current_user.id} (first 500 chars): {ai_prompt[:500]}...") # Ensuring clean f-string
                generated_content = f"--- PROMPT FOR AI ---\n{ai_prompt}\n\n--- END (Actual AI content here) ---" # Placeholder

                user_credit_on_submit.amount -= 1
                db.session.add(user_credit_on_submit)
                cover_letter_title = form.title.data or f"AI Gen: {form.job_title.data}"[:100]
                new_cover_letter = CoverLetter(user_id=current_user.id, title=cover_letter_title, content=generated_content)
                db.session.add(new_cover_letter)
                db.session.commit()
                flash('AI Cover Letter generation initiated (mock)!', 'success')
                return redirect(url_for('cover_letter.index'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in AI cover letter generation: {e}", exc_info=True)
                flash(f'An error during generation: {str(e)}', 'danger')
        # else: # Form validation failed
            # WTForms will add errors to form.errors, which can be displayed in the template
            # flash('Please correct the errors in the form.', 'warning')


    return render_template('cover_letter/generate.html', form=form, title="Generate AI Cover Letter")

@cover_letter_bp.route('/create_manual', methods=['GET', 'POST'])
@login_required
def create_manual_cover_letter():
    '''Handles manual creation of a cover letter.'''
    form = SimpleCoverLetterForm()
    manual_credit_type = 'legacy'
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type=manual_credit_type).first()

    if request.method == 'POST':
        if not user_credit or user_credit.amount <= 0:
            flash(f'You do not have enough "{manual_credit_type}" credits.', 'warning')
            return redirect(url_for('cover_letter.index'))

        if form.validate_on_submit():
            new_cl = CoverLetter(user_id=current_user.id, title=form.title.data, content=form.content.data)
            user_credit.amount -= 1
            db.session.add_all([new_cl, user_credit])
            try:
                db.session.commit()
                flash('Cover Letter created successfully!', 'success')
                return redirect(url_for('cover_letter.index'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating manual CL: {e}", exc_info=True)
                flash(f'Error creating CL: {str(e)}', 'danger')
    
    if request.method == 'GET' and (not user_credit or user_credit.amount <= 0):
         flash(f'Warning: No "{manual_credit_type}" credits for manual CL creation.', 'info')
    return render_template('cover_letter/create_manual.html', form=form, title="Create Manual Cover Letter")

# TODO: Add other CRUD routes like /view/<id>, /edit/<id>, /delete/<id>
