import logging
import json # For handling JSON data
from flask import render_template, redirect, url_for, flash, request, jsonify # Added jsonify
from flask_login import login_required, current_user
from backend.models import Resume, Credit
from backend.extensions import db
from . import bp
from .forms import ResumeForm

# Configure logger for this blueprint
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def index():
    """Displays a list of the user's resumes."""
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Resume.updated_at.desc()).all()
    return render_template('resume_builder/my_resumes.html', resumes=resumes)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """DEPRECATED: Handles creation of a new resume via the old form.
    New resumes should be created via the formatter UI and /create_new_formatter route."""
    form = ResumeForm()
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()

    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to create a new resume. Please purchase more credits.', 'warning')
        return redirect(url_for('resume_builder.index'))

    if form.validate_on_submit():
        if not user_credit or user_credit.amount <= 0: # Re-check credits
             flash('Credit check failed upon submission. Please ensure you have enough credits.', 'warning')
             return redirect(url_for('resume_builder.index'))

        # For old form, content might not be JSON. Default to basic JSON structure if empty.
        content_data = form.content.data
        try:
            # Attempt to load it as JSON, if it's already JSON, fine.
            # If it's plain text, wrap it in a simple structure.
            json.loads(content_data)
        except json.JSONDecodeError:
            # If it's not valid JSON (e.g., plain text from old form), wrap it.
            # This is a basic adaptation. The new formatter will save proper JSON.
            content_data = json.dumps({"raw_text": content_data, "sections": []})


        new_resume = Resume(
            user_id=current_user.id,
            title=form.title.data,
            content=content_data # Save as JSON string
        )
        user_credit.amount -= 1
        db.session.add(new_resume)
        db.session.add(user_credit)
        try:
            db.session.commit()
            flash('Resume created successfully using the old form! Consider using the new editor for more features.', 'success')
            return redirect(url_for('resume_builder.index'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating resume with old form: {str(e)}", exc_info=True)
            flash(f'Error creating resume: {str(e)}', 'danger')
    
    flash('You are using the old resume creation form. For a better experience, try the new AI Resume Formatter.', 'info')
    return render_template('resume_builder/create_resume.html', form=form)


# --- New Formatter Routes ---

@bp.route('/formatter/create_new', methods=['GET'])
@login_required
def create_new_formatter():
    """Renders the new AI resume formatter for creating a new resume."""
    # Check credits before even rendering the form
    user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()
    if not user_credit or user_credit.amount <= 0:
        flash('You do not have enough credits to create a new resume. Please purchase more credits.', 'warning')
        return redirect(url_for('resume_builder.index'))

    default_resume_data = {
        "title": "Untitled Resume",
        "content": { # Basic structure for the new formatter
            "personal": {"full_name": "", "email": "", "phone": "", "location": "", "linkedin": "", "portfolio": ""},
            "summary": "",
            "experiences": [],
            "education": [],
            "skills": {"technical_skills": "", "soft_skills": "", "certifications": ""},
            "additional": {"projects": "", "languages": "", "volunteer": ""}
        }
    }
    # Content needs to be a JSON string when passed to template if template expects string
    # Or template JS handles it if passed as dict. For consistency with loading, pass as string.
    return render_template('resume_builder/formatter.html',
                           resume_title=default_resume_data["title"],
                           resume_content_json=json.dumps(default_resume_data["content"]),
                           resume_id=None)

@bp.route('/formatter/edit/<int:resume_id>', methods=['GET'])
@login_required
def edit_formatter(resume_id):
    """Renders the new AI resume formatter for editing an existing resume."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id, is_archived=False).first()
    if not resume:
        flash('Resume not found or you do not have permission to edit it.', 'danger')
        return redirect(url_for('resume_builder.index'))

    # resume.content is already a JSON string
    return render_template('resume_builder/formatter.html',
                           resume_title=resume.title,
                           resume_content_json=resume.content, # Pass as JSON string
                           resume_id=resume.id)

@bp.route('/formatter/save_resume_data', methods=['POST'])
@login_required
def save_resume_data():
    """API endpoint to save resume data from the new formatter."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid data format."}), 400

    title = data.get('title')
    content_json_str = data.get('content') # This should be a JSON string from the frontend
    resume_id = data.get('resume_id') # Could be None or missing for new resumes

    if not title or not content_json_str:
        return jsonify({"success": False, "error": "Title and content are required."}), 400

    # Validate if content_json_str is valid JSON (optional, but good practice)
    try:
        json.loads(content_json_str)
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "Content is not valid JSON."}), 400

    if resume_id: # Editing an existing resume
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({"success": False, "error": "Resume not found or permission denied."}), 404

        resume.title = title
        resume.content = content_json_str # Store as JSON string
        message = "Resume updated successfully!"
    else: # Creating a new resume
        user_credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()
        if not user_credit or user_credit.amount <= 0:
            return jsonify({"success": False, "error": "Insufficient credits to create a new resume."}), 403

        resume = Resume(
            user_id=current_user.id,
            title=title,
            content=content_json_str # Store as JSON string
        )
        db.session.add(resume)
        user_credit.amount -= 1
        db.session.add(user_credit)
        message = "Resume created successfully!"

    try:
        db.session.commit()
        return jsonify({"success": True, "resume_id": resume.id, "message": message}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving resume data: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500

# Note on old routes like preview_resume, delete_resume, etc.
# These were not in the provided simplified routes.py.
# If they exist in the actual project, they might need adjustments
# or could be replaced by functionality within the new formatter.
# For instance, `preview.html` logic is now largely superseded by `formatter.html`'s live preview.
# Deletion could be a separate API endpoint called from `my_resumes.html` or the formatter.
