from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize # For file uploads
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

# Define allowed file extensions and size for uploads
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
MAX_FILE_SIZE_MB = 2  # Max file size in megabytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class AICoverLetterForm(FlaskForm):
    # Basic Info
    title = StringField(
        'Cover Letter Title (Optional)',
        validators=[Optional(), Length(min=3, max=100, message="Title must be between 3 and 100 characters if provided.")]
    )
    your_name = StringField(
        'Your Name',
        validators=[DataRequired(message="Your name is required."), Length(max=100)]
    )
    your_email = StringField(
        'Your Email',
        validators=[DataRequired(message="Your email is required."), Length(max=120)] # Not an Email validator, assuming basic string
    )

    # Job Details
    job_title = StringField(
        'Job Title You Are Applying For',
        validators=[DataRequired(message="Job title is required."), Length(max=150)]
    )
    company_name = StringField(
        'Company Name (Optional)',
        validators=[Optional(), Length(max=150)]
    )
    job_description = TextAreaField(
        'Job Description',
        validators=[DataRequired(message="Job description is required."), Length(min=50, max=5000)],
        render_kw={"rows": 10, "placeholder": "Paste the full job description here..."}
    )

    # Applicant's Content
    resume_text = TextAreaField(
        'Paste Your Resume Text (Optional if uploading file)',
        validators=[Optional(), Length(max=7000)], # Increased max length
        render_kw={"rows": 15, "placeholder": "Paste your resume content here, or upload a file below."}
    )
    resume_file = FileField(
        'Upload Resume (Optional)',
        validators=[
            Optional(),
            FileAllowed(ALLOWED_EXTENSIONS, f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed!"),
            FileSize(max_size=MAX_FILE_SIZE_BYTES, message=f"File size must be less than {MAX_FILE_SIZE_MB}MB")
        ]
    )

    # Refinement and Customization
    refinement_type = SelectField(
        'Generation Mode',
        choices=[
            ('create_new', 'Create New Cover Letter'),
            ('refine_existing', 'Refine an Existing Cover Letter'),
            ('enhance_with_resume', 'Enhance Existing Cover Letter with Resume Details')
        ],
        validators=[DataRequired()]
    )
    existing_cover_letter_text = TextAreaField(
        'Paste Existing Cover Letter (if refining/enhancing)',
        validators=[Optional(), Length(max=5000)],
        render_kw={"rows": 10, "placeholder": "If you selected 'refine' or 'enhance', paste your existing cover letter text here."}
    )
    # existing_cover_letter_file = FileField( # Decided against file upload for existing cover letter for simplicity now
    #     'Upload Existing Cover Letter (Optional, if refining/enhancing)',
    #     validators=[
    #         Optional(),
    #         FileAllowed(ALLOWED_EXTENSIONS, f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed!"),
    #         FileSize(max_size=MAX_FILE_SIZE_BYTES, message=f"File size must be less than {MAX_FILE_SIZE_MB}MB")
    #     ]
    # )
    key_points = TextAreaField(
        'Key Points to Emphasize or Areas for Improvement (Optional)',
        validators=[Optional(), Length(max=1000)],
        render_kw={"rows": 5, "placeholder": "e.g., Highlight my Python skills, focus on leadership examples, make it more concise..."}
    )
    tone = SelectField(
        'Desired Tone',
        choices=[
            ('professional', 'Professional'),
            ('enthusiastic', 'Enthusiastic'),
            ('concise', 'Concise'),
            ('storytelling', 'Storytelling')
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Generate Cover Letter')

# Keep the old simple form if needed for basic CRUD, or remove if AI is the only path
class SimpleCoverLetterForm(FlaskForm):
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
