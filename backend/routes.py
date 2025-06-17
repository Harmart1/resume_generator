import logging # Added for logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from backend.models import User, Resume, CoverLetter, MockInterview, Credit, FeatureUsageLog
from backend.extensions import db, bcrypt
from datetime import datetime
from backend.forms import LoginForm, RegistrationForm # Added for auth forms

# Configure logger for this blueprint
logger = logging.getLogger(__name__) # Added for logging

main_bp = Blueprint('main', __name__, template_folder='../../frontend/templates')

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Tier limits
    tier_limits = {
        'free': {'resumes': 1, 'cover_letters': 1, 'interviews': 0},
        'starter': {'resumes': 5, 'cover_letters': 3, 'interviews': 3},
        'pro': {'resumes': float('inf'), 'cover_letters': float('inf'), 'interviews': float('inf')}
    }

    user_tier = current_user.tier if hasattr(current_user, 'tier') else 'free'
    limits = tier_limits.get(user_tier, tier_limits['free'])

    resumes = Resume.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Resume.updated_at.desc()).all()
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id, is_archived=False).order_by(CoverLetter.updated_at.desc()).all()
    interviews = MockInterview.query.filter_by(user_id=current_user.id, is_archived=False).order_by(MockInterview.updated_at.desc()).all()

    resumes_limited = resumes[:int(limits['resumes'])]
    cover_letters_limited = cover_letters[:int(limits['cover_letters'])]
    interviews_limited = interviews[:int(limits['interviews'])]

    credit = Credit.query.filter_by(user_id=current_user.id, credit_type='legacy').first()
    credit_amount = credit.amount if credit else 0

    # Feature usage logging
    try:
        log = FeatureUsageLog(
            user_id=current_user.id,
            feature_name='dashboard_view',
            usage_timestamp=datetime.utcnow()
            # credits_used defaults to 0 as per model definition if not specified
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Log or handle the exception if the database commit fails
        # For now, let's assume it's important to still render the dashboard
        logger.error(f"Error logging feature usage: {e}", exc_info=True)
        db.session.rollback()


    return render_template('dashboard.html',
                         resumes=resumes_limited,
                         cover_letters=cover_letters_limited,
                         interviews=interviews_limited,
                         credit_amount=credit_amount)

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.route('/analyzer')
def analyzer():
    return render_template('index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and hasattr(user, 'check_password') and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data, tier='free')
        if hasattr(new_user, 'set_password'):
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in.', 'success')
            return redirect(url_for('main.login'))
        else:
            # This case should ideally not happen if User model is correctly defined
            logger.error("Critical: User model is missing set_password method during registration.", exc_info=False)
            flash('Error setting up user. Please contact support.', 'danger')
    return render_template('auth/register.html', title='Register', form=form)
