from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import Length, Optional

class MockInterviewStartForm(FlaskForm):
    job_description = TextAreaField(
        'Job Description (Optional)',
        validators=[
            Optional(), # Make this field optional
            Length(max=5000, message="Job description cannot exceed 5000 characters.")
        ]
    )
    submit = SubmitField('Start Mock Interview')
