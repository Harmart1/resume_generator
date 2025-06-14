from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, StringField
from wtforms.validators import DataRequired
# Assuming Resume model is accessible for choices, e.g. from ..models import Resume or from ..app import Resume
# from ..app import Resume  # Example if Resume is in app.py and User is too
from flask_login import current_user # Required for get_resume_choices

# Temporary Resume class for defining choices if actual import fails in this isolated context
# Replace with actual import like: from ..app import Resume
class TempResumeForForm:
    @staticmethod
    def query_filter_by_user_id_is_archived(user_id, is_archived):
        # This should query the actual database
        # For now, returns an empty list to allow form definition
        print(f"TempResumeForForm: Simulating query for user {user_id}")
        return []

def get_resume_choices():
    from ..app import Resume # Late import to use actual Resume model
    if current_user.is_authenticated:
        resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).all()
        choices = [(0, 'None (or paste resume below)')] + [(resume.id, resume.title if resume.title else f"Resume {resume.id}") for resume in resumes]
        return choices
    return [(0, 'None (or paste resume below)')]

class MockInterviewForm(FlaskForm):
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    # resume_id = SelectField('Select Saved Resume', coerce=int, choices=get_resume_choices) # Dynamic choices
    resume_id = SelectField('Select Saved Resume', coerce=int) # Choices loaded in route
    resume_text = TextAreaField('Or Paste Resume Text (Optional if a saved resume is selected)')
    submit = SubmitField('Start Interview')
