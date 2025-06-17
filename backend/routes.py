from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from backend.models import User, Resume, CoverLetter, MockInterview, Credit, FeatureUsageLog
from backend.extensions import db, bcrypt
from datetime import datetime

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
        print(f"Error logging feature usage: {e}") # Replace with actual logging
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
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # Ensure User model has check_password method
        user = User.query.filter_by(email=email).first()
        if user and hasattr(user, 'check_password') and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html')

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
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        # Ensure User model has set_password method
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
        elif not (username and email and password):
            flash('All fields are required.', 'danger')
        else:
            new_user = User(username=username, email=email, tier='free')
            if hasattr(new_user, 'set_password'):
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('main.login'))
            else:
                flash('Error setting up user. Please contact support.', 'danger')
                # Log this server-side, User model is missing set_password
    return render_template('auth/register.html')
