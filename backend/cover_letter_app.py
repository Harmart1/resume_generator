from flask import Flask, request, render_template, redirect, url_for, flash
from cov_let import CoverLetterForm
from file_utils import extract_text_from_file
from prompt_engine import build_cover_letter_prompt
from security import rate_limited, validate_input_length
import os
import tempfile
import requests
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB file limit

# Mistral API Configuration
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', 'Om9YIaeWFVHtKqvMTt7jc9DGn47dF1Go')
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def generate_with_mistral(prompt):
    """Send prompt to Mistral AI API with enhanced error handling"""
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
        app.logger.error(f"Mistral API request failed: {str(e)}")
        return None
    except (KeyError, ValueError) as e:
        app.logger.error(f"Error parsing Mistral response: {str(e)}")
        return None

@app.route('/', methods=['GET'])
def index():
    form = CoverLetterForm()
    return render_template('cover_letter_form.html', form=form)

@app.route('/generate', methods=['POST'])
@rate_limited
def generate():
    form = CoverLetterForm()
    if not form.validate_on_submit():
        return render_template('cover_letter_form.html', form=form)
    
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
    app.logger.info(f"Generated cover letter - Tracking ID: {tracking_id}")
    
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

@app.errorhandler(413)
def request_entity_too_large(error):
    return 'File too large (max 5MB)', 413

@app.errorhandler(429)
def ratelimit_handler(error):
    return 'Too many requests. Please try again in a minute.', 429

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
