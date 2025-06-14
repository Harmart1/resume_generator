from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app
from cov_let import CoverLetterForm
from file_utils import extract_text_from_file
from prompt_engine import build_cover_letter_prompt
from security import rate_limited, validate_input_length
from flask_login import login_required, current_user
from backend.app import db, CoverLetter, tier_required, MISTRAL_API_KEY, MISTRAL_API_URL, CREDIT_TYPE_COVER_LETTER_AI, consume_credit, FeatureUsageLog, logger # Import Credit items
import os
import tempfile
import requests
from datetime import datetime, date # Added date
from sqlalchemy import func # Added func
import json # Added json
import uuid

bp = Blueprint('cover_letter', __name__, template_folder='../../frontend/templates')

# Helper function to count monthly cover letter saves
def get_monthly_cover_letter_save_count(user_id):
    today = date.today()
    start_of_month = today.replace(day=1)
    count = db.session.query(func.count(CoverLetter.id)).filter(
        CoverLetter.user_id == user_id,
        CoverLetter.created_at >= start_of_month,
        CoverLetter.is_archived == False # Count only non-archived saves against the limit
    ).scalar()
    return count

# Mistral API Configuration removed from here, will use imported ones.

def generate_with_mistral(prompt):
    """Send prompt to Mistral AI API with enhanced error handling"""
    if not MISTRAL_API_KEY:
        current_app.logger.warning("MISTRAL_API_KEY not found. Cover letter generation via Mistral is disabled.")
        return None

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
            timeout=30  # 30 seconds timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Mistral API request failed: {str(e)}")
        return None
    except (KeyError, ValueError) as e:
        current_app.logger.error(f"Error parsing Mistral response: {str(e)}")
        return None

@bp.route('/', methods=['GET'])
@login_required
@tier_required('pro')
def index():
    form = CoverLetterForm()
    return render_template('cover_letter_form.html', form=form)

@bp.route('/generate', methods=['POST'])
@login_required
@tier_required(['starter', 'pro']) # Allow starter tier
@rate_limited
def generate():
    form = CoverLetterForm()
    if not form.validate_on_submit():
        return render_template('cover_letter_form.html', form=form)

    # Credit consumption logic
    if current_user.tier == 'starter':
        if not consume_credit(current_user.id, CREDIT_TYPE_COVER_LETTER_AI):
            flash(f"You have no '{CREDIT_TYPE_COVER_LETTER_AI}' credits remaining. Please upgrade to Pro for unlimited cover letters or wait for your monthly refresh.", "warning")
            return redirect(url_for('cover_letter.index'))
        db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=CREDIT_TYPE_COVER_LETTER_AI, credits_used=1))
        logger.info(f"Starter user {current_user.email} consumed 1 credit for {CREDIT_TYPE_COVER_LETTER_AI}.")
    elif current_user.tier == 'pro':
        db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=f"{CREDIT_TYPE_COVER_LETTER_AI}_pro_usage", credits_used=0))
        logger.info(f"Pro user {current_user.email} used {CREDIT_TYPE_COVER_LETTER_AI} (unlimited).")
    
    # Commit credit changes and logs immediately
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error committing credit consumption/log for cover letter: {e}")
        flash("An error occurred while processing credits. Please try again.", "error")
        return redirect(url_for('cover_letter.index'))

    # Process uploaded cover letter file
    cover_letter_text = ""
    if form.cover_letter_file.data:
        file = form.cover_letter_file.data
        _, ext = os.path.splitext(file.filename)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            file.save(tmp.name)
            cover_letter_text = extract_text_from_file(tmp.name)
        os.unlink(tmp.name)
    elif form.previous_cover_letter.data:
        cover_letter_text = form.previous_cover_letter.data

    # Validate input sizes
    validation_error = validate_input_length(
        form.job_description.data,
        form.resume_text.data,
        cover_letter_text
    )
    
    if validation_error:
        flash(validation_error, 'danger')
        return redirect(url_for('index'))
    
    # Prepare form data
    form_data = {
        'job_title': form.job_title.data,
        'company_name': form.company_name.data,
        'your_name': form.your_name.data,
        'your_email': form.your_email.data,
        'job_description': form.job_description.data,
        'resume_text': form.resume_text.data,
        'tone': form.tone.data,
        'key_points': form.key_points.data,
        'refinement_type': form.refinement_type.data
    }
    
    # Build optimized prompt
    prompt = build_cover_letter_prompt(form_data, cover_letter_text)
    
    # Generate cover letter with Mistral AI
    generated_content = generate_with_mistral(prompt)
    
    if not generated_content:
        flash('Failed to generate cover letter. Please try again.', 'danger')
        return redirect(url_for('index'))
    
    # Add tracking ID for analytics
    tracking_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"Generated cover letter - Tracking ID: {tracking_id}")
    
    # Render with consistent styling
    return render_template(
        'cover_letter_template.html',
        content=generated_content,
        company=form.company_name.data,
        job_title=form.job_title.data,
        your_name=form.your_name.data,
        your_email=form.your_email.data,
        current_date=datetime.now().strftime("%B %d, %Y"),
        tracking_id=tracking_id
    )

@bp.errorhandler(413)
def request_entity_too_large(error):
    return 'File too large (max 5MB)', 413

@bp.errorhandler(429)
def ratelimit_handler(error):
    return 'Too many requests. Please try again in a minute.', 429

@bp.route('/save-cover-letter', methods=['POST'])
@login_required
def save_cover_letter():
    title = request.form.get('cover_letter_title', f"Cover Letter - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    content = request.form.get('cover_letter_content')

    if not content:
        flash("No content to save.", "error")
        return redirect(request.referrer or url_for('cover_letter.index'))

    if current_user.tier == 'free':
        flash("Please upgrade to a Starter or Pro plan to save your cover letters.", "warning")
        return redirect(request.referrer or url_for('cover_letter.index'))

    if current_user.tier == 'starter':
        save_count = get_monthly_cover_letter_save_count(current_user.id)
        if save_count >= 3: # Starter tier limit
            flash("You have reached your monthly save limit (3) for cover letters on the Starter tier. Please upgrade to Pro for unlimited saves or wait until next month.", "warning")
            return redirect(request.referrer or url_for('cover_letter.index'))

    # Pro tier has unlimited saves (or Starter tier within limit)
    new_cover_letter = CoverLetter(
        user_id=current_user.id,
        title=title,
        content=content # Assuming content is the full letter text
    )
    db.session.add(new_cover_letter)
    db.session.commit()
    flash(f"Cover letter '{title}' saved successfully!", "success")
    return redirect(url_for('cover_letter.my_cover_letters'))

@bp.route('/my-cover-letters', methods=['GET'])
@login_required
def my_cover_letters():
    letters = CoverLetter.query.filter_by(user_id=current_user.id, is_archived=False).order_by(CoverLetter.updated_at.desc()).all()
    return render_template('my_cover_letters.html', letters=letters)

@bp.route('/load-cover-letter/<int:letter_id>')
@login_required
def load_cover_letter(letter_id):
    letter = CoverLetter.query.filter_by(id=letter_id, user_id=current_user.id, is_archived=False).first_or_404()
    # For "loading", we are re-displaying it on the template used for generated letters.
    # The template needs to be able to distinguish between newly generated content vs loaded.
    # Or, more simply, just pass the necessary parts.
    # The cover_letter_template.html expects 'content', 'company', 'job_title', 'your_name', 'your_email', 'current_date'.
    # We only have 'title' and 'content' stored directly. Others would need to be parsed or omitted.

    # Simplification: Pass what we have. The template will need to be robust.
    # Or, we can try to parse details from the content if it follows a strict format, which is complex.
    # For now, just pass title and content. Other details might be missing on "view" unless stored.

    # To make it more useful, we can pass some context to the template to indicate it's a loaded letter
    # and potentially not try to extract all original form fields if they weren't saved.
    # The `generate` route passes: content, company, job_title, your_name, your_email, current_date, tracking_id
    # We have: letter.title, letter.content, letter.user.name (if we add that to User), letter.user.email

    # For simplicity in this step, we'll just pass the core content.
    # The `cover_letter_template.html` will need to be robust to missing context variables
    # or we adjust what we pass / how it's rendered.
    return render_template(
        'cover_letter_template.html',
        content=letter.content,
        title=letter.title, # Pass the title
        your_name=current_user.username or current_user.email, # Best effort
        your_email=current_user.email,
        current_date=letter.updated_at.strftime("%B %d, %Y"), # Use updated_at as a relevant date
        is_loaded=True, # Flag to template that this is a loaded letter
        letter_id=letter.id # For potential re-save or other actions
    )
