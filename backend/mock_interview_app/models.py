from ..extensions import db # UPDATED to import from extensions
from ..models import User, Resume # Added to ensure User and Resume are in scope for relationships if uncommented
from datetime import datetime
# Need to ensure Resume model is accessible, e.g. from ..models import Resume or from ..app import Resume
# For now, assuming Resume would be imported if this file was part of a larger models.py
# If Resume is in app.py, it might be: from ..app import Resume

class MockInterview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Corrected table name
    # resume_id might need to refer to a Resume table if it's separate
    # If Resume model is defined in app.py, user.id and resume.id are fine.
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True) # Corrected table name
    job_description = db.Column(db.Text, nullable=False)
    questions = db.Column(db.JSON, nullable=False) # Store questions as a list
    answers = db.Column(db.JSON, nullable=True)    # Store answers as a list
    scores = db.Column(db.JSON, nullable=True)     # Store scores for each answer
    feedback = db.Column(db.JSON, nullable=True)   # Store feedback for each answer
    overall_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to User (assuming User model is in app.py or a shared models.py)
    # user = db.relationship('User', backref=db.backref('mock_interviews', lazy=True))
    # Relationship to Resume (assuming Resume model is in app.py or a shared models.py)
    # resume = db.relationship('Resume', backref=db.backref('mock_interviews', lazy=True))

    def __repr__(self):
        return f'<MockInterview {self.id} for User {self.user_id}>'

# Placeholder for Resume model if it's not globally available via db.Model
# This is just for ORM reference, actual Resume model is likely in app.py or backend/models.py
# class Resume(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#    content = db.Column(db.Text, nullable=True)
#    title = db.Column(db.String(100))
#    is_archived = db.Column(db.Boolean, default=False)
