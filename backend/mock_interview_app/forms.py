from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import TextAreaField, SubmitField, SelectField # Added SelectField
from wtforms.validators import Length, Optional, DataRequired

# Define allowed file extensions and size for uploads
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
MAX_FILE_SIZE_MB = 2  # Max file size in megabytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class MockInterviewStartForm(FlaskForm):
    job_description = TextAreaField(
        'Job Description (Optional, but recommended for tailored questions)',
        validators=[
            Optional(),
            Length(max=7000, message="Job description cannot exceed 7000 characters.")
        ],
        render_kw={"rows": 10, "placeholder": "Paste the full job description here..."}
    )
    resume_text = TextAreaField(
        'Paste Your Resume Text (Optional if uploading file)',
        validators=[Optional(), Length(max=7000)],
        render_kw={"rows": 15, "placeholder": "Paste your resume content here, or upload a file below. This helps in generating more relevant questions."}
    )
    resume_file = FileField(
        'Upload Resume (Optional, formats: .txt, .pdf, .doc, .docx)',
        validators=[
            Optional(),
            FileAllowed(ALLOWED_EXTENSIONS, f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed!"),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message=f"File size must be less than {MAX_FILE_SIZE_MB}MB.")
        ]
    )
    language = SelectField(
        'Interview Language',
        choices=[
            ('English', 'English'),
            ('Spanish', 'Spanish'),
            ('Mandarin', 'Mandarin')
            # TODO: Add more languages as supported by backend/NLP tools
        ],
        validators=[DataRequired()],
        default='English'
    )
    submit = SubmitField('Start Mock Interview')
