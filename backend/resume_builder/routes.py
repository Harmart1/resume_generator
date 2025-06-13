# ... existing imports ...
from .utils import translation  # NEW
from .utils.translation import detect_language, translate_text  # NEW

@bp.route('/resume-builder', methods=['GET'])
def start():
    session.clear()
    return redirect(url_for('resume_builder.step0_language'))  # NEW first step

# NEW Language selection step
@bp.route('/step0', methods=['GET', 'POST'])
def step0_language():
    form = LanguageForm()
    if form.validate_on_submit():
        session['input_lang'] = form.input_language.data
        session['output_lang'] = form.output_language.data
        return redirect(url_for('resume_builder.step1_industry'))
    return render_template('resume_builder/step0_language.html', form=form)

# Updated industry step
@bp.route('/step1', methods=['GET', 'POST'])
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
            prompt = generate_resume_section_prompt(
                'experience',
                {
                    'achievements': achievements,
                    'job_title': form.job_title.data,
                    'industry': session.get('industry', 'technology')
                },
                session.get('industry', 'technology')
            )
            
            refined_achievements = generate_with_mistral(prompt)
            
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
                           lang=output_lang)  # NEW
    @bp.route('/get-recommendations', methods=['POST'])

    def get_recommendations():
    """Get AI-powered resume suggestions"""
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
