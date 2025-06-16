from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from backend.models import User, Resume, CoverLetter, MockInterview, Credit
from backend.extensions import db, bcrypt

main_bp = Blueprint('main', __name__, template_folder='../../frontend/templates')

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('home.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id).all()
    interviews = MockInterview.query.filter_by(user_id=current_user.id).all()
    credits_list = Credit.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', resumes=resumes, cover_letters=cover_letters, interviews=interviews, credits=credits_list, user=current_user)

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
