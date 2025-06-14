from ..extensions import db # UPDATED to import from extensions
from ..models import User, Resume # Added to ensure User and Resume are in scope for relationships if uncommented
from datetime import datetime
# Need to ensure Resume model is accessible, e.g. from ..models import Resume or from ..app import Resume
# For now, assuming Resume would be imported if this file was part of a larger models.py
# If Resume is in app.py, it might be: from ..app import Resume

class MockInterview(db.Model):
    __tablename__ = 'mock_interview' # Added as per convention from migration script
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)
    job_description = db.Column(db.Text, nullable=False)
    questions = db.Column(db.JSON, nullable=False)
    answers = db.Column(db.JSON, nullable=True)
    scores = db.Column(db.JSON, nullable=True)
    feedback = db.Column(db.JSON, nullable=True)
    overall_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False) # nullable=False as per user script

    # Relationships can be defined here if User and Resume models are imported.
    # user = db.relationship('User', backref=db.backref('mock_interviews', lazy=True))
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
