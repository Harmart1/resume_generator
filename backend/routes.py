# backend/cover_letter/routes.py

import os
import tempfile
import uuid
import requests
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for, current_app
from .forms import CoverLetterForm
from .utils.file_processing import extract_text_from_file
from .utils.prompt_engine import build_cover_letter_prompt
from .utils.security import rate_limited, validate_input_length
from config.cover_letter_config import CoverLetterConfig

# Create config instance
config = CoverLetterConfig()

@current_app.route('/cover-letter', methods=['GET'])
def index():
    form = CoverLetterForm()
    return render_template('cover_letter/generate.html', form=form)

@current_app.route('/cover-letter/generate', methods=['POST'])
@rate_limited(max_requests=config.MAX_REQUESTS_PER_MINUTE)
def generate():
    form = CoverLetterForm()
    if not form.validate_on_submit():
        return render_template('cover_letter/generate.html', form=form), 400
    
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
        cover_letter_text,
        max_length=5000  # characters per field
    )
    if validation_error:
        flash(validation_error, 'danger')
        return redirect(url_for('cover_letter.index'))
    
    # Prepare form data
    form_data = {
        'job_title': form.job_title.data,
        'company_name': form.company_name.data or '[Company Name]',
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
    
    if generated_content is None:
        flash('Failed to generate cover letter. Please try again.', 'danger')
        return redirect(url_for('cover_letter.index'))
    
    # Add tracking ID for analytics
    tracking_id = str(uuid.uuid4())[:8]
    
    # Render with consistent styling
    return render_template(
        'cover_letter/result.html',
        content=generated_content,
        company=form_data['company_name'],
        job_title=form_data['job_title'],
        your_name=form_data['your_name'],
        your_email=form_data['your_email'],
        current_date=datetime.now().strftime("%B %d, %Y"),
        tracking_id=tracking_id
    )

def generate_with_mistral(prompt):
    """Send prompt to Mistral AI API with enhanced error handling"""
    headers = {
        "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
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
            config.MISTRAL_API_URL,
            headers=headers,
            json=payload,
            timeout=30  # 30 seconds timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        current_app.logger.error(f"Error generating cover letter: {str(e)}")
        return None

@bp.route('/save-progress', methods=['POST'])
def save_progress():
    """Save resume progress to database"""
    resume_data = {
        'personal': session.get('personal', {}),
        'experiences': session.get('experiences', []),
        'skills': session.get('skills', {}),
        'education': session.get('education', []),
        'additional': session.get('additional', {}),
        'industry': session.get('industry', 'technology'),
        'languages': {
            'input': session.get('input_lang', 'auto'),
            'output': session.get('output_lang', 'en')
        }
    }
    
    # Generate unique resume ID
    resume_id = str(uuid.uuid4())
    
    # Save to database (pseudo-code)
    db.save_resume(resume_id, resume_data)
    
    return jsonify({
        'resume_id': resume_id,
        'message': 'Progress saved successfully'
    })
