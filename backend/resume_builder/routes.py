# ... existing imports ...
from .utils import translation  # NEW
from .utils.translation import detect_language, translate_text  # NEW
from flask_login import login_required, current_user
from backend.app import db, Resume, tier_required, CREDIT_TYPE_RESUME_AI, consume_credit, FeatureUsageLog, logger # Added Credit constants and functions
from . import bp # Import bp from the local __init__.py
from flask import render_template, session, redirect, url_for, flash, jsonify, request # Added request
import json
from datetime import datetime, date
from sqlalchemy import func
from .forms import LanguageForm, IndustryForm, ExperienceForm # Ensure all forms are imported

# Helper function to count monthly saves
def get_monthly_save_count(user_id, model_class):
    today = date.today()
    start_of_month = today.replace(day=1)
    count = db.session.query(func.count(model_class.id)).filter(
        model_class.user_id == user_id,
        model_class.created_at >= start_of_month
    ).scalar()
    return count

@bp.route('/resume-builder', methods=['GET'])
@login_required
@tier_required('free')
def start():
    session.clear()
    return redirect(url_for('resume_builder.step0_language'))  # NEW first step

# NEW Language selection step
@bp.route('/step0', methods=['GET', 'POST'])
@login_required
@tier_required('free')
def step0_language():
    form = LanguageForm()
    if form.validate_on_submit():
        session['input_lang'] = form.input_language.data
        session['output_lang'] = form.output_language.data
        return redirect(url_for('resume_builder.step1_industry'))
    return render_template('resume_builder/step0_language.html', form=form)

# Updated industry step
@bp.route('/step1', methods=['GET', 'POST'])
@login_required
@tier_required('free')
def step1_industry():
    form = IndustryForm()
    if form.validate_on_submit():
        session['industry'] = form.industry.data
        return redirect(url_for('resume_builder.step2_personal'))
    return render_template('resume_builder/step1_industry.html', form=form)

# Updated experience handler with translation
@bp.route('/step3', methods=['GET', 'POST'])
def step3_experience():
    form = ExperienceForm()
    experiences = session.get('experiences', [])
    
    if form.validate_on_submit():
        if form.submit.data:  # Add button clicked
            # Get languages
            input_lang = session.get('input_lang', 'auto')
            output_lang = session.get('output_lang', 'en')
            
            # Detect language if needed
            if input_lang == 'auto':
                input_lang = translation.detect_language(form.achievements.data)
            
            # Translate if needed
            achievements = form.achievements.data
            if input_lang != output_lang:
                achievements = translation.translate_text(
                    form.achievements.data, 
                    target_lang=output_lang,
                    source_lang=input_lang
                )
            
            # Generate refined achievements with AI
            
            refined_achievements = achievements # Default to original
            can_use_ai_enhancement = False

            if current_user.tier == 'pro':
                can_use_ai_enhancement = True
                db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=f"{CREDIT_TYPE_RESUME_AI}_step3_pro", credits_used=0))
            elif current_user.tier == 'starter':
                if consume_credit(current_user.id, CREDIT_TYPE_RESUME_AI):
                    can_use_ai_enhancement = True
                    db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=CREDIT_TYPE_RESUME_AI + "_step3", credits_used=1))
                else:
                    flash("No 'Resume AI' credits left for refining achievements. Entry saved without AI enhancement.", "warning")
            # Free tier users skip AI enhancement by default

            if can_use_ai_enhancement:
                prompt = generate_resume_section_prompt(
                    'experience',
                    {
                        'achievements': achievements, # Use potentially translated achievements
                        'job_title': form.job_title.data,
                        'industry': session.get('industry', 'technology')
                    },
                    session.get('industry', 'technology')
                )
                ai_generated_text = generate_with_mistral(prompt)
                if ai_generated_text: # Check if AI generation was successful
                    refined_achievements = ai_generated_text
                else:
                    logger.warning(f"AI achievement refinement failed for user {current_user.id}. Using original achievements.")
                    # Optionally flash a message, but could be noisy

            # Commit any credit changes or feature logs
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error committing session in step3_experience: {e}")
                flash("An error occurred while saving progress. Please try again.", "error")
                # Potentially redirect or handle error more gracefully
            
            experiences.append({
                'job_title': form.job_title.data,
                'company': form.company.data,
                'location': form.location.data,
                'start_date': form.start_date.data,
                'end_date': form.end_date.data,
                'achievements': refined_achievements
            })
            session['experiences'] = experiences
            return redirect(url_for('resume_builder.step3_experience'))
        
        elif form.continue_btn.data:  # Continue button clicked
            return redirect(url_for('resume_builder.step4_skills'))
    
    return render_template('resume_builder/step3_experience.html', 
                          form=form, 
                          experiences=experiences)

# Updated preview handler
@bp.route('/preview', methods=['GET'])
@login_required
@tier_required('free')
def preview():
    industry = session.get('industry', 'technology')
    output_lang = session.get('output_lang', 'en')
    industry_css = get_industry_template(industry)
    
    # Get translated section titles
    from .utils.translation import SECTION_TITLES
    section_titles = SECTION_TITLES.get(output_lang, SECTION_TITLES['en'])
    
    return render_template('resume_builder/preview.html',
                           personal=session.get('personal', {}),
                           experiences=session.get('experiences', []),
                           skills=session.get('skills', {}),
                           education=session.get('education', []),
                           additional=session.get('additional', {}),
                           industry_css=industry_css,
                           section_titles=section_titles,  # NEW
                           lang=output_lang,  # NEW
                           resume_title=session.get('resume_title', f"Resume - {datetime.now().strftime('%Y-%m-%d %H:%M')}"))


@bp.route('/save-resume', methods=['POST'])
@login_required
def save_resume():
    resume_title = request.form.get('resume_title', f"Resume - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if current_user.tier == 'free':
        flash("Please upgrade to a Starter or Pro plan to save your resumes.", "warning")
        return redirect(url_for('resume_builder.preview'))

    if current_user.tier == 'starter':
        save_count = get_monthly_save_count(current_user.id, Resume)
        if save_count >= 3:
            flash("You have reached your monthly save limit (3) for the Starter tier. Please upgrade to Pro for unlimited saves or wait until next month.", "warning")
            return redirect(url_for('resume_builder.preview'))

    # Consolidate session data into a JSON string for the content field
    resume_content_data = {
        'personal': session.get('personal', {}),
        'experiences': session.get('experiences', []),
        'skills': session.get('skills', {}),
        'education': session.get('education', []),
        'additional': session.get('additional', {}),
        'industry': session.get('industry', 'technology'), # Save current industry
        'input_lang': session.get('input_lang', 'en'),   # Save languages
        'output_lang': session.get('output_lang', 'en')
    }
    content_json = json.dumps(resume_content_data)

    new_resume = Resume(
        user_id=current_user.id,
        title=resume_title,
        content=content_json
    )
    db.session.add(new_resume)
    db.session.commit()
    flash(f"Resume '{resume_title}' saved successfully!", "success")
    session['resume_title'] = resume_title # Keep title in session if they re-save
    return redirect(url_for('resume_builder.my_resumes'))


@bp.route('/my-resumes', methods=['GET'])
@login_required
def my_resumes():
    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Resume.updated_at.desc()).all()
    return render_template('resume_builder/my_resumes.html', resumes=resumes)


@bp.route('/load-resume/<int:resume_id>', methods=['GET'])
@login_required
def load_resume(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    try:
        content_data = json.loads(resume.content)
        session['personal'] = content_data.get('personal', {})
        session['experiences'] = content_data.get('experiences', [])
        session['skills'] = content_data.get('skills', {})
        session['education'] = content_data.get('education', [])
        session['additional'] = content_data.get('additional', {})
        session['industry'] = content_data.get('industry', 'technology')
        session['input_lang'] = content_data.get('input_lang', 'en')
        session['output_lang'] = content_data.get('output_lang', 'en')
        session['resume_title'] = resume.title # Load title into session
        flash(f"Resume '{resume.title}' loaded successfully.", "success")
        return redirect(url_for('resume_builder.preview'))
    except json.JSONDecodeError:
        flash("Error loading resume data. The resume content may be corrupted.", "error")
        return redirect(url_for('resume_builder.my_resumes'))


@bp.route('/get-recommendations', methods=['POST'])
@login_required
@tier_required(['starter', 'pro']) # Pro can also access, starter pays
def get_recommendations():
    """Get AI-powered resume suggestions"""
    if current_user.tier == 'starter':
        if not consume_credit(current_user.id, CREDIT_TYPE_RESUME_AI):
            return jsonify({"error": "No 'Resume AI' credits remaining. Upgrade to Pro for unlimited recommendations or wait for your next monthly refresh."}), 403
        db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=CREDIT_TYPE_RESUME_AI + "_get_recommendations", credits_used=1))
    elif current_user.tier == 'pro':
        db.session.add(FeatureUsageLog(user_id=current_user.id, feature_name=f"{CREDIT_TYPE_RESUME_AI}_get_recommendations_pro", credits_used=0))

    # Important: Commit session if credits were consumed or logs added
    db.session.commit()

    data = request.json
    industry = data.get('industry', 'technology')
    
    prompt = f"""
    As a professional career advisor specializing in {industry} resumes, provide 3 concrete suggestions 
    to improve this resume content: {data['content']}
    
    Guidelines:
    - Focus on ATS optimization
    - Suggest industry-specific keywords
    - Recommend quantifiable achievements
    - Keep suggestions actionable
    - Format as a bulleted list
    """
    
    recommendations = generate_with_mistral(prompt)
    return jsonify({'recommendations': recommendations})
