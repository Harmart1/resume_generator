from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, SelectField # Added SelectField
from wtforms.validators import Length, Optional, DataRequired # Added DataRequired

class MockInterviewStartForm(FlaskForm):
    job_description = TextAreaField(
        'Job Description (Optional)',
        validators=[
            Optional(), # Make this field optional
            Length(max=5000, message="Job description cannot exceed 5000 characters.")
        ]
    )
    language = SelectField('Interview Language', choices=[('en', 'English'), ('es', 'Spanish')], default='en', validators=[DataRequired()])
    submit = SubmitField('Start Mock Interview')
