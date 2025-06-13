from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Optional

class IndustryForm(FlaskForm):
    industry = SelectField(
        'Industry Focus',
        choices=[
            ('technology', 'Technology'),
            ('marketing', 'Marketing & Sales'),
            ('academic', 'Academic & Teaching'),
            ('legal', 'Legal'),
            ('healthcare', 'Healthcare'),
            ('finance', 'Finance'),
            ('other', 'Other')
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    submit = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class PersonalForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()], render_kw={"class": "form-control"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"class": "form-control"})
    phone = StringField('Phone', validators=[DataRequired()], render_kw={"class": "form-control"})
    location = StringField('Location', render_kw={"class": "form-control"})
    linkedin = StringField('LinkedIn URL', render_kw={"class": "form-control"})
    portfolio = StringField('Portfolio URL', render_kw={"class": "form-control"})
    summary = TextAreaField('Professional Summary', render_kw={"class": "form-control", "rows": 4})
    submit = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class ExperienceForm(FlaskForm):
    job_title = StringField('Job Title', validators=[DataRequired()], render_kw={"class": "form-control"})
    company = StringField('Company', validators=[DataRequired()], render_kw={"class": "form-control"})
    location = StringField('Location', render_kw={"class": "form-control"})
    start_date = StringField('Start Date', validators=[DataRequired()], render_kw={"class": "form-control"})
    end_date = StringField('End Date', render_kw={"class": "form-control"})
    achievements = TextAreaField(
        'Key Achievements', 
        render_kw={
            "class": "form-control", 
            "rows": 4,
            "placeholder": "Describe your responsibilities and achievements. The AI will help refine this."
        }
    )
    submit = SubmitField('Add Experience', render_kw={"class": "btn btn-secondary"})
    continue_btn = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class SkillsForm(FlaskForm):
    technical_skills = TextAreaField(
        'Technical Skills', 
        render_kw={
            "class": "form-control", 
            "rows": 3,
            "placeholder": "List technical skills (e.g., Python, Photoshop, Salesforce)"
        }
    )
    soft_skills = TextAreaField(
        'Soft Skills', 
        render_kw={
            "class": "form-control", 
            "rows": 3,
            "placeholder": "List soft skills (e.g., Leadership, Communication)"
        }
    )
    certifications = TextAreaField(
        'Certifications', 
        render_kw={
            "class": "form-control", 
            "rows": 2,
            "placeholder": "List relevant certifications"
        }
    )
    submit = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class EducationForm(FlaskForm):
    institution = StringField('Institution', render_kw={"class": "form-control"})
    degree = StringField('Degree', render_kw={"class": "form-control"})
    field_of_study = StringField('Field of Study', render_kw={"class": "form-control"})
    graduation_year = StringField('Graduation Year', render_kw={"class": "form-control"})
    submit = SubmitField('Add Education', render_kw={"class": "btn btn-secondary"})
    continue_btn = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class AdditionalForm(FlaskForm):
    projects = TextAreaField('Projects', render_kw={"class": "form-control", "rows": 3})
    languages = TextAreaField('Languages', render_kw={"class": "form-control", "rows": 2})
    volunteer = TextAreaField('Volunteer Experience', render_kw={"class": "form-control", "rows": 2})
    submit = SubmitField('Generate Resume', render_kw={"class": "btn btn-primary"})
