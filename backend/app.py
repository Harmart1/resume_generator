from flask import Flask, render_template, redirect, url_for, flash, session, g, request, jsonify, send_from_directory, abort # Added g, request, jsonify, send_from_directory, abort
# Removed: FlaskForm, CSRFProtect, wtforms, markupsafe, docx, spacy, collections, werkzeug, flask_bcrypt
# These seem to have been specific to the user's example app.py and not present in the original app.py I was working on.
# I will keep the imports that were in the *original* app.py and merge with user's structural changes.

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session # From original
from flask_wtf.csrf import CSRFProtect # From original, re-adding

import os
from datetime import datetime # Combined from both
from dotenv import load_dotenv
from functools import wraps # From original

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded.") # Added logging

# --- App Initialization and Configuration ---
app = Flask(__name__)
logger.info("Flask app initialized.")

# Secret Key
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-very-secret-key-for-dev') # Kept original default
logger.info(f"SECRET_KEY configured: {'SECRET_KEY environment variable used' if os.getenv('SECRET_KEY') else 'Using default SECRET_KEY'}")


# Instance directory for SQLite
instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance') # Used abspath for robustness
try:
    os.makedirs(instance_dir, exist_ok=True)
    logger.info(f"Instance directory '{instance_dir}' ensured.")
except OSError as e:
    logger.error(f"Error creating instance directory '{instance_dir}': {e}", exc_info=True)


# Database URI Configuration (Default to SQLite)
default_sqlite_uri = f'sqlite:///{os.path.join(instance_dir, "site.db")}'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', default_sqlite_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Log effective database URI
effective_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
if 'postgresql' in effective_db_uri.lower() and os.getenv('DATABASE_URL'):
    logger.info(f"Using PostgreSQL database URI from DATABASE_URL: {effective_db_uri}")
elif 'sqlite' in effective_db_uri.lower() and os.getenv('DATABASE_URL'):
    logger.info(f"Using SQLite database URI from DATABASE_URL: {effective_db_uri}")
elif default_sqlite_uri == effective_db_uri: # Check if it's the default SQLite URI
    logger.info(f"Using default SQLite database URI: {effective_db_uri} (DATABASE_URL not set)")
else: # Fallback for other specified URIs from DATABASE_URL
    logger.warning(f"Using custom database URI from DATABASE_URL: {effective_db_uri}")


# Session Configuration (Kept from original app.py)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.getenv('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    logger.info("Session cookie configured for production (Secure=True).")
else:
    app.config['SESSION_COOKIE_SECURE'] = False
    logger.info("Session cookie configured for development (Secure=False).")
app.config['SESSION_TYPE'] = 'filesystem'


# --- Extensions Initialization (from backend.extensions) ---
# db, migrate, bcrypt, login_manager are initialized here using .init_app()
# This relies on backend.extensions.py being set up correctly
try:
    from backend.extensions import db, migrate, bcrypt, login_manager
    db.init_app(app)
    migrate.init_app(app, db) # Flask-Migrate needs db instance here
    bcrypt.init_app(app)
    login_manager.init_app(app)
    logger.info("Flask extensions (SQLAlchemy, Migrate, Bcrypt, LoginManager) initialized.")
except ImportError:
    logger.error("Failed to import extensions from backend.extensions. Ensure extensions.py is correctly set up.", exc_info=True)
    # Handle error or re-raise
except Exception as e:
    logger.error(f"An error occurred during extensions initialization: {e}", exc_info=True)


# CSRF Protection (Re-added from original app.py)
csrf = CSRFProtect(app)
logger.info("CSRF protection enabled.")

# Flask Session (Re-added from original app.py)
Session(app) # Initialize Flask-Session
logger.info("Flask-Session initialized with type 'filesystem'.")


# --- Blueprints Registration (from original structure) ---
try:
    from backend.resume_builder import bp as resume_builder_bp
    from backend.cover_letter_app import bp as cover_letter_bp
    from backend.mock_interview_app import bp as mock_interview_bp

    app.register_blueprint(resume_builder_bp, url_prefix='/resume-builder')
    app.register_blueprint(cover_letter_bp, url_prefix='/cover-letter')
    app.register_blueprint(mock_interview_bp, url_prefix='/mock-interview')
    logger.info("Blueprints (resume_builder, cover_letter, mock_interview) registered.")
except ImportError:
    logger.error("Failed to import or register blueprints. Check blueprint definitions and imports.", exc_info=True)
except Exception as e:
    logger.error(f"An error occurred during blueprint registration: {e}", exc_info=True)


# --- Models Import (Primarily for Alembic, actual usage might be in blueprints/routes) ---
# This ensures models are known to SQLAlchemy for Alembic detection if not imported elsewhere.
# However, specific model imports are typically in routes or util functions.
# The user's example app.py had this, but in our refactored app, models are in backend.models
# and usually imported where needed or by blueprints.
# For now, let's rely on blueprint imports and backend.models being part of the package.
# If Alembic struggles, explicit imports might be added to backend/migrations/env.py or backend/__init__.py

# --- Login Manager Configuration (from original app.py and user's example) ---
if login_manager: # Check if login_manager was initialized successfully
    login_manager.login_view = 'login' # Original was 'login', user had 'auth.login'
    login_manager.login_message_category = 'info'
    logger.info(f"LoginManager configured with login_view: '{login_manager.login_view}'.")

    @login_manager.user_loader
    def load_user(user_id):
        from backend.models import User # Import here to avoid circularity at startup
        try:
            user = User.query.get(int(user_id))
            # logger.debug(f"User loader: loaded user {user_id} -> {user}") # Optional: debug logging
            return user
        except Exception as e:
            logger.error(f"Error in user_loader for user_id {user_id}: {e}", exc_info=True)
            return None
else:
    logger.warning("LoginManager not available, user session management will be affected.")


# --- Request Hooks (from original app.py) ---
@app.before_request
def setup_jinja_globals():
    if not hasattr(g, 'jinja_filters_setup'): # Ensure it runs once per app context
        def _jinja2_filter_datetime(value, fmt="%Y"): # Basic strftime filter
            if value is None: return ""
            if isinstance(value, datetime): return value.strftime(fmt)
            return value
        app.jinja_env.filters['strftime'] = _jinja2_filter_datetime
        g.jinja_filters_setup = True
    g.user = current_user # Set g.user for templates

# --- Routes (Combination of original and user's example for basic routes) ---
# Importing routes from backend.routes (original structure)
# and defining some basic routes here as per user's example app.py
try:
    from backend.routes import main_bp # Assuming main routes are in a blueprint in backend/routes.py
    app.register_blueprint(main_bp)
    logger.info("Main routes blueprint registered.")
except ImportError:
    logger.info("backend.routes.main_bp not found, defining basic routes directly in app.py.")
    # Define basic routes if main_bp doesn't exist (like in user's example)

    # WTForms (re-adding for user's example contact form, adjust if not needed)
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, SubmitField, SelectField # Added SelectField
    from wtforms.validators import DataRequired, Email, Optional, Length # Added Optional, Length
    from flask_login import login_required # Assuming login_required is desired


    class ContactForm(FlaskForm): # User's example form
        name = StringField('Name', validators=[DataRequired()])
        email = StringField('Email', validators=[DataRequired(), Email()])
        subject = StringField('Subject', validators=[DataRequired()]) # Simplified from user example
        message = TextAreaField('Message', validators=[DataRequired()])
        submit = SubmitField('Submit')

    @app.route('/')
    def index():
        # This route was previously in backend/routes.py, now potentially here.
        # Needs to be reconciled with blueprint structure. For now, simple render.
        return render_template('index.html') # Assuming a base index.html exists

    @app.route('/contact', methods=['GET', 'POST'])
    @login_required
    def contact():
        form = ContactForm()
        if form.validate_on_submit():
            # Using logger instead of docx for simplicity, original had docx
            logger.info(f"Contact Form Submission: Name: {form.name.data}, Email: {form.email.data}, Subject: {form.subject.data}, Message: {form.message.data}")
            flash('Your message has been submitted successfully.', 'success')
            return redirect(url_for('contact')) # Or 'index' if 'contact' is the current route
        return render_template('contact.html', form=form) # Assuming contact.html template

# Static file serving (from original app.py)
@app.route('/static/<path:path>')
def serve_frontend_static_file(path):
    static_dir = os.path.join(os.path.dirname(__file__), '../frontend/static')
    return send_from_directory(static_dir, path)

# Generic frontend file serving (from original app.py)
# Ensure this doesn't clash with blueprint routes or specific file handlers
# @app.route('/<path:filename>')
# @login_required # Consider if all frontend files need login
# def serve_frontend_file(filename):
#     frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
#     if '..' in filename or filename.startswith('/'): # Basic security
#         abort(404)
#     return send_from_directory(frontend_dir, filename)


# --- Main Execution ---
if __name__ == '__main__':
    logger.info('Starting application via __main__...')
    # SpaCy model check (from user's example, good addition)
    try:
        import spacy
        spacy.load('en_core_web_sm')
        logger.info("SpaCy en_core_web_sm model found.")
    except OSError:
        logger.warning('SpaCy en_core_web_sm model not found. Attempting to download...')
        try:
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
            logger.info("Successfully downloaded en_core_web_sm.")
        except Exception as e_spacy:
            logger.error(f"Failed to download en_core_web_sm: {e_spacy}", exc_info=True)

    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    logger.info(f"Running Flask app: host='0.0.0.0', port={port}, debug={debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

# --- Merging Notes ---
# This app.py is a MERGE of the original app.py's structure (blueprints, extensions, specific configs)
# and the user's provided app.py (SQLite default, instance dir creation, SpaCy check, simplified contact form).
# Some imports from the user's example (like FlaskForm, wtforms) were re-added where their example code (ContactForm) was used.
# The complex route structure from the original app.py (many API endpoints, Stripe, etc.) is NOT fully represented here;
# it's assumed those are mostly within their respective blueprints or in backend/routes.py.
# This script focuses on the app factory pattern, config, extensions, and basic routing examples.
# The original app.py had many more specific routes (register, login, logout, profile, etc.) which are likely
# in backend/routes.py or auth-related blueprints.
# Key thing is the SQLALCHEMY_DATABASE_URI change and instance_dir creation.
