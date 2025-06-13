from flask import Blueprint, render_template, request, session, redirect, url_for
from .forms import IndustryForm, PersonalForm, ExperienceForm, SkillsForm, EducationForm, AdditionalForm
from .utils.prompt_engine import generate_resume_section_prompt
from .utils.industry_templates import get_industry_template
from config.resume_builder_config import ResumeBuilderConfig
import requests
import json

bp = Blueprint('resume_builder', __name__, 
               template_folder='../../../frontend/templates/resume_builder',
               static_folder='../../../frontend/static')

config = ResumeBuilderConfig()

@bp.route('/resume-builder', methods=['GET'])
def start():
    session.clear()
    return redirect(url_for('resume_builder.step1_industry'))

@bp.route('/step1', methods=['GET', 'POST'])
def step1_industry():
    form = IndustryForm()
    if form.validate_on_submit():
        session['industry'] = form.industry.data
        return redirect(url_for('resume_builder.step2_personal'))
    return render_template('resume_builder/step1_industry.html', form=form)

@bp.route('/step2', methods=['GET', 'POST'])
def step2_personal():
    form = PersonalForm()
    if form.validate_on_submit():
        session['personal'] = {
            'full_name': form.full_name.data,
            'email': form.email.data,
            'phone': form.phone.data,
            'location': form.location.data,
            'linkedin': form.linkedin.data,
            'portfolio': form.portfolio.data,
            'summary': form.summary.data
        }
        return redirect(url_for('resume_builder.step3_experience'))
    return render_template('resume_builder/step2_personal.html', form=form)

@bp.route('/step3', methods=['GET', 'POST'])
def step3_experience():
    form = ExperienceForm()
    experiences = session.get('experiences', [])
    
    if form.validate_on_submit():
        if form.submit.data:  # Add button clicked
            # Generate refined achievements with AI
            prompt = generate_resume_section_prompt(
                'experience',
                {'achievements': form.achievements.data},
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

@bp.route('/step4', methods=['GET', 'POST'])
def step4_skills():
    form = SkillsForm()
    if form.validate_on_submit():
        session['skills'] = {
            'technical_skills': form.technical_skills.data,
            'soft_skills': form.soft_skills.data,
            'certifications': form.certifications.data
        }
        return redirect(url_for('resume_builder.step5_education'))
    return render_template('resume_builder/step4_skills.html', form=form)

@bp.route('/step5', methods=['GET', 'POST'])
def step5_education():
    form = EducationForm()
    education = session.get('education', [])
    
    if form.validate_on_submit():
        if form.submit.data:  # Add button clicked
            education.append({
                'institution': form.institution.data,
                'degree': form.degree.data,
                'field_of_study': form.field_of_study.data,
                'graduation_year': form.graduation_year.data
            })
            session['education'] = education
            return redirect(url_for('resume_builder.step5_education'))
        
        elif form.continue_btn.data:  # Continue button clicked
            return redirect(url_for('resume_builder.step6_additional'))
    
    return render_template('resume_builder/step5_education.html', 
                          form=form, 
                          education=education)

@bp.route('/step6', methods=['GET', 'POST'])
def step6_additional():
    form = AdditionalForm()
    if form.validate_on_submit():
        session['additional'] = {
            'projects': form.projects.data,
            'languages': form.languages.data,
            'volunteer': form.volunteer.data
        }
        
        # Generate professional summary if not provided
        if not session['personal'].get('summary'):
            prompt = generate_resume_section_prompt(
                'summary',
                {
                    'technical_skills': session['skills']['technical_skills'],
                    'experience_years': len(session['experiences']),
                    'career_focus': session['industry']
                },
                session['industry']
            )
            session['personal']['summary'] = generate_with_mistral(prompt)
        
        return redirect(url_for('resume_builder.preview'))
    
    return render_template('resume_builder/step6_additional.html', form=form)

@bp.route('/preview', methods=['GET'])
def preview():
    industry = session.get('industry', 'technology')
    industry_css = get_industry_template(industry)
    
    return render_template('resume_builder/preview.html',
                           personal=session.get('personal', {}),
                           experiences=session.get('experiences', []),
                           skills=session.get('skills', {}),
                           education=session.get('education', []),
                           additional=session.get('additional', {}),
                           industry_css=industry_css)

def generate_with_mistral(prompt):
    """Generate content using Mistral API"""
    headers = {
        "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(config.MISTRAL_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error generating content: {e}")
        return ""
