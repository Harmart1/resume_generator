from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class CoverLetterForm(FlaskForm):
    title = StringField(
        'Title',
        validators=[
            DataRequired(message="Title is required."),
            Length(min=3, max=100, message="Title must be between 3 and 100 characters.")
        ]
    )
    content = TextAreaField(
        'Content',
        validators=[
            DataRequired(message="Content is required."),
            Length(min=10, message="Content must be at least 10 characters long.")
        ]
    )
    submit = SubmitField('Save Cover Letter')
