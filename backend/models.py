from datetime import datetime
from flask_login import UserMixin
from .extensions import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False) # Re-added
    password_hash = db.Column(db.String(128), nullable=False)
    tier = db.Column(db.String(50), nullable=False, default='free')
    stripe_customer_id = db.Column(db.String(120), nullable=True, unique=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True, unique=True)
    industry_preference = db.Column(db.String(50), nullable=True) # Re-added
    contact_phone = db.Column(db.String(30), nullable=True) # Re-added
    profile_updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow) # Re-added

    # Relationships will be defined here or through backrefs in other models
    # resumes = db.relationship('Resume', backref='user', lazy=True) # Example if Resume is defined here
    # cover_letters = db.relationship('CoverLetter', backref='user', lazy=True)
    # usage_logs = db.relationship('FeatureUsageLog', backref='user', lazy=True)
    # credits = db.relationship('Credit', backref='user', lazy=True) # If Credit model is restored

    def set_password(self, password):
        # Assuming bcrypt is available via db.app.bcrypt or similar if app context is configured
        # For simplicity, if bcrypt is globally available or passed differently, adjust
        # This might require app context or moving bcrypt to extensions too.
        # For now, assuming bcrypt might be an issue here.
        # Let's assume bcrypt is available on the app instance from app.py
        # This will be handled when app.py imports bcrypt.
        # A better way is to pass bcrypt object or make it available via extensions.
        from .extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')


    def check_password(self, password):
        from .extensions import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)


    def __repr__(self):
        return f'<User {self.email} (Tier: {self.tier})>'

class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, default='Untitled Resume')
    content = db.Column(db.Text, nullable=False) # Should store JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('resumes', lazy=True))

class CoverLetter(db.Model):
    __tablename__ = 'cover_letters'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, default='Untitled Cover Letter')
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('cover_letters', lazy=True))

class MockInterview(db.Model):
    __tablename__ = 'mock_interview' # Changed from 'mock_interviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    questions = db.Column(db.Text, nullable=False)
    answers = db.Column(db.Text, nullable=True)
    scores = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    overall_score = db.Column(db.Float, nullable=True)
    language = db.Column(db.String(50), nullable=False, default='English', server_default='English')
    pronunciation_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User', backref=db.backref('mock_interviews', lazy=True))

# class Credit(db.Model):
#     __tablename__ = 'credits'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
#     credit_type = db.Column(db.String(50), nullable=False)
#     amount = db.Column(db.Integer, default=0, nullable=False)
#     last_reset = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
#     user = db.relationship('User', backref=db.backref('credits', lazy=True))
#     __table_args__ = (db.UniqueConstraint('user_id', 'credit_type', name='uq_user_credit_type'),)

class FeatureUsageLog(db.Model):
    __tablename__ = 'feature_usage_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False) # e.g., 'resume_ai_step3', 'cover_letter_generate'
    credits_used = db.Column(db.Integer, nullable=False, default=0) # 0 for pro, 1 for starter if consumed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('feature_usage_logs', lazy=True))

    def __repr__(self):
        return f'<FeatureUsageLog user_id={self.user_id} feature={self.feature_name} time={self.timestamp}>'

class Credit(db.Model):
    __tablename__ = 'credits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credit_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, default=0, nullable=False)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    user = db.relationship('User', backref=db.backref('credits', lazy=True))
    __table_args__ = (db.UniqueConstraint('user_id', 'credit_type', name='uq_user_credit_type'),)

# UserCredit model deleted as per instruction for baseline migration, will be defined by user-provided script

# New Feature Models Start

class EQFeedback(db.Model):
    __tablename__ = 'eq_feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    interview_id = db.Column(db.Integer, db.ForeignKey('mock_interview.id'), nullable=True) # Changed from mock_interview.id
    empathy_score = db.Column(db.Float, nullable=False)
    self_awareness_score = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('eq_feedbacks', lazy=True))
    interview = db.relationship('MockInterview', backref=db.backref('eq_feedbacks', lazy=True))

class BrandingKit(db.Model):
    __tablename__ = 'branding_kit'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    linkedin_banner = db.Column(db.Text, nullable=True)  # Stores SVG or link
    portfolio_template = db.Column(db.Text, nullable=True) # Stores HTML/CSS or link
    elevator_pitch = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('branding_kits', lazy=True))

class Negotiation(db.Model):
    __tablename__ = 'negotiation'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False) # Increased length from 100 to 150
    script = db.Column(db.Text, nullable=False)
    scenario = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('negotiations', lazy=True))

class SkillGap(db.Model):
    __tablename__ = 'skill_gap'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    # For missing_skills and resources, Text will be used by default for SQLite.
    # setup_migrations.py will handle using sa.JSON() for PostgreSQL if that's configured.
    # So, defining as db.Text here is fine as a base.
    missing_skills = db.Column(db.Text, nullable=False)  # JSON stored as Text
    resources = db.Column(db.Text, nullable=False)     # JSON stored as Text
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('skill_gaps', lazy=True))

# New Feature Models End
