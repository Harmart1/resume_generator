from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Optional

class LanguageForm(FlaskForm):  # NEW
    input_language = SelectField(
        'Your Language',
        choices=[
            ('auto', 'Detect Automatically'),
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('zh', 'Chinese'),
            ('ja', 'Japanese'),
            ('ru', 'Russian'),
            ('pt', 'Portuguese'),
            ('ar', 'Arabic'),
            ('hi', 'Hindi')
        ],
        default='auto',
        render_kw={"class": "form-select"}
    )
    output_language = SelectField(
        'Resume Language',
        choices=[
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('zh', 'Chinese'),
            ('ja', 'Japanese'),
            ('pt', 'Portuguese')
        ],
        default='en',
        render_kw={"class": "form-select"}
    )
    submit = SubmitField('Continue', render_kw={"class": "btn btn-primary"})

class IndustryForm(FlaskForm):
    # ... (existing code) ...

# Add this to PersonalForm
class PersonalForm(FlaskForm):
    # ... (existing fields) ...
    desired_job_title = StringField(  # NEW
        'Desired Job Title',
        render_kw={"class": "form-control"}
    )
