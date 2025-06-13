from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    SubmitField
)
from wtforms.validators import DataRequired, Optional, Email

class CoverLetterForm(FlaskForm):
    job_description = TextAreaField(
        'Job Description',
        validators=[DataRequired()],
        render_kw={
            "rows": 7, 
            "placeholder": "Paste the job description...", 
            "aria-label": "Job Description Textarea",
            "class": "form-control"
        }
    )
    resume_text = TextAreaField(
        'Your Resume Content',
        validators=[Optional()],
        render_kw={
            "rows": 10, 
            "placeholder": "Paste your resume text (optional but recommended)...", 
            "aria-label": "Resume Content Textarea",
            "class": "form-control"
        }
    )
    previous_cover_letter = TextAreaField(
        'Existing Cover Letter (Optional)',
        validators=[Optional()],
        render_kw={
            "rows": 10, 
            "placeholder": "Paste your existing cover letter to refine...", 
            "aria-label": "Cover Letter Textarea",
            "class": "form-control"
        }
    )
    cover_letter_file = FileField(
        'Upload Cover Letter (Optional)',
        validators=[
            Optional(),
            FileAllowed(['pdf', 'docx', 'txt'], 'PDF, DOCX, or TXT files only')
        ],
        render_kw={
            "aria-label": "Cover Letter File Upload",
            "class": "form-control"
        }
    )
    company_name = StringField(
        'Company Name',
        validators=[Optional()],
        render_kw={
            "placeholder": "Company name (optional)", 
            "aria-label": "Company Name",
            "class": "form-control"
        }
    )
    job_title = StringField(
        'Job Title',
        validators=[DataRequired()],
        render_kw={
            "placeholder": "e.g., Senior Software Engineer", 
            "aria-label": "Job Title",
            "class": "form-control"
        }
    )
    your_name = StringField(
        'Your Full Name',
        validators=[DataRequired()],
        render_kw={
            "placeholder": "Your full name", 
            "aria-label": "Your Full Name",
            "class": "form-control"
        }
    )
    your_email = StringField(
        'Your Email',
        validators=[DataRequired(), Email()],
        render_kw={
            "placeholder": "your.email@example.com", 
            "aria-label": "Your Email",
            "class": "form-control"
        }
    )
    tone = SelectField(
        'Writing Tone',
        choices=[
            ('professional', 'Professional'),
            ('enthusiastic', 'Enthusiastic'),
            ('concise', 'Concise'),
            ('storytelling', 'Storytelling')
        ],
        default='professional',
        render_kw={
            "aria-label": "Writing Tone",
            "class": "form-select"
        }
    )
    key_points = TextAreaField(
        'Key Points to Highlight',
        validators=[Optional()],
        render_kw={
            "rows": 4, 
            "placeholder": "Specific achievements or skills to emphasize (optional)...", 
            "aria-label": "Key Points",
            "class": "form-control"
        }
    )
    refinement_type = SelectField(
        'Refinement Type',
        choices=[
            ('generate', 'Generate New'),
            ('refine', 'Refine Existing'),
            ('enhance', 'Enhance with Resume')
        ],
        default='generate',
        render_kw={
            "aria-label": "Refinement Type",
            "class": "form-select"
        }
    )
    submit = SubmitField(
        'Generate Cover Letter', 
        render_kw={
            "aria-label": "Generate Cover Letter Button",
            "class": "btn btn-primary"
        }
    )
