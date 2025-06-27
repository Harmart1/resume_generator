# backend/app.py
import os
import logging
from datetime import datetime
from functools import wraps # Added for tier_required

from flask import Flask, render_template, redirect, url_for, flash, session, g, request, jsonify, send_from_directory, abort
from sqlalchemy import text # ADDED for db connection validation
# Removed current_user from flask_login import here, will be imported where needed or via g.user
from flask_wtf import FlaskForm # For ContactForm example
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, TextAreaField, SubmitField, SelectField # Added SelectField
from wtforms.validators import DataRequired, Email, Optional, Length # Added Optional, Length

from dotenv import load_dotenv

# Configure logging (from user's script)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded.")

# Define project root and global static folder paths first
# Assuming app.py is in backend/, project_root is one level up (e.g., src/)
# and static files are in project_root/frontend/static/
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GLOBAL_STATIC_FOLDER = os.path.join(_project_root, 'frontend', 'static')

# --- App Initialization and Configuration ---
app = Flask(__name__,
            instance_relative_config=True,
            static_folder=GLOBAL_STATIC_FOLDER, # Explicitly set static folder
            static_url_path='/static') # Explicitly set static URL path
logger.info(f"Flask app initialized. Static folder set to: {GLOBAL_STATIC_FOLDER}, Static URL path: /static")

# Secret Key (ensure this is strong and unique in production)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-default-secret-key-change-me')
if app.config['SECRET_KEY'] == 'your-default-secret-key-change-me':
    logger.warning("Using default SECRET_KEY. Please set a strong SECRET_KEY environment variable for production.")
else:
    logger.info("SECRET_KEY configured from environment variable.")


# Instance directory for SQLite (from user's script)
# Corrected path to be relative to app.root_path if instance folder is at project root
# Assuming app.py is in backend/, and instance/ is at project root (../instance)
instance_path = os.path.join(app.root_path, '..', 'instance')
try:
    os.makedirs(instance_path, exist_ok=True)
    logger.info(f"Instance directory '{instance_path}' ensured.")
except OSError as e:
    logger.error(f"Error creating instance directory '{instance_path}': {e}", exc_info=True)


# Database URI Configuration (Default to SQLite, from user's script)
default_sqlite_db_path = os.path.join(instance_path, "site.db")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{default_sqlite_db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Log effective database URI (from user's script)
effective_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
if 'postgresql' in effective_db_uri and os.getenv('DATABASE_URL'):
    logger.info(f"Using PostgreSQL database URI from DATABASE_URL: {effective_db_uri}")
elif 'sqlite' in effective_db_uri and os.getenv('DATABASE_URL'):
    logger.info(f"Using SQLite database URI from DATABASE_URL: {effective_db_uri}")
elif 'sqlite:///instance/site.db' in effective_db_uri: # Specifically check if it's the new default
    logger.info(f"Using default SQLite database URI: {effective_db_uri} (DATABASE_URL not set)")
else:
    logger.info(f"Using custom database URI from DATABASE_URL: {effective_db_uri}")


# Session Configuration (Combining original and user's suggestions)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # User suggestion
if os.getenv('FLASK_ENV') == 'production': # Original logic
    app.config['SESSION_COOKIE_SECURE'] = True
    logger.info("Session cookie configured for production (Secure=True).")
else:
    app.config['SESSION_COOKIE_SECURE'] = False # User suggestion, good for dev
    logger.info("Session cookie configured for development (Secure=False).")
app.config['SESSION_TYPE'] = 'filesystem' # Original, fine for now
# User suggested Redis for production, which is a good future enhancement.


# --- Extensions Initialization (from backend.extensions) ---
try:
    from backend.extensions import db, migrate, bcrypt, login_manager
    db.init_app(app)
    # Corrected: Flask-Migrate needs db AFTER app context for db.metadata
    # migrate.init_app(app, db) # This will be called after models are imported usually
    # For now, assuming migrate object is created in extensions.py and then init_app here.
    # The directory for migrations should be configured when Migrate object is created.
    # E.g. Migrate(directory='backend/migrations') in extensions.py
    migrate_dir = os.path.join(app.root_path, 'migrations') # app.root_path is backend/
    migrate.init_app(app, db, directory=migrate_dir)
    logger.info(f"Flask-Migrate initialized with directory: {migrate_dir}")

    bcrypt.init_app(app)
    login_manager.init_app(app)
    logger.info("Flask extensions (SQLAlchemy, Migrate, Bcrypt, LoginManager) initialized.")

    # Database connection validation
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1')) # Use text() for literal SQL
            logger.info("Database connection established successfully.")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}", exc_info=True)

    # --- Login Manager Configuration (moved inside the try block) ---
    login_manager.login_view = 'main.login' # Assuming login route is in main_bp now
    login_manager.login_message_category = 'info'
    logger.info(f"LoginManager configured with login_view: '{login_manager.login_view}'.")

    @login_manager.user_loader
    def load_user(user_id):
        from backend.models import User # Import here
        try:
            user = User.query.get(int(user_id))
            return user
        except Exception as e:
            logger.error(f"Error in user_loader for user_id {user_id}: {e}", exc_info=True)
            return None

except ImportError:
    logger.error("Failed to import extensions from backend.extensions. Ensure extensions.py is correctly set up.", exc_info=True)
    # Set extensions to None or handle them if import fails and they are checked later outside this block
    db, migrate, bcrypt, login_manager = None, None, None, None
    logger.warning("Extensions (db, migrate, bcrypt, login_manager) set to None due to import failure.")
except Exception as e:
    logger.error(f"An error occurred during extensions initialization: {e}", exc_info=True)
    db, migrate, bcrypt, login_manager = None, None, None, None
    logger.warning("Extensions (db, migrate, bcrypt, login_manager) set to None due to initialization error.")


# CSRF Protection
csrf = CSRFProtect(app)
logger.info("CSRF protection enabled.")

# Flask Session
from flask_session import Session # Ensure import is here
Session(app)
logger.info("Flask-Session initialized with type 'filesystem'.")


# --- Blueprints Registration ---
try:
    from backend.resume_builder import bp as resume_builder_bp
    from backend.cover_letter_app import cover_letter_bp # Corrected import
    from backend.mock_interview_app import mock_interview_bp # Corrected import
    # Import main_bp for core routes like /, /contact etc.
    from backend.routes import main_bp # Renamed to avoid clash if user had main_bp

    app.register_blueprint(resume_builder_bp, url_prefix='/resume-builder')
    app.register_blueprint(cover_letter_bp, url_prefix='/cover-letter') # Use the correctly imported name
    app.register_blueprint(mock_interview_bp, url_prefix='/mock-interview') # Use the correctly imported name
    app.register_blueprint(main_bp) # Register core routes
    logger.info("Blueprints (resume_builder, cover_letter, mock_interview, main_bp) registered.")
except ImportError as e:
    logger.error(f"Failed to import or register blueprints: {e}. Check blueprint definitions and imports.", exc_info=True)
except Exception as e:
    logger.error(f"An error occurred during blueprint registration: {e}", exc_info=True)


# --- Models Import ---
# Models are now in backend.models and imported by blueprints or when needed (e.g. user_loader)
# No global model import here is needed if blueprints handle their model interactions.

# --- Check if login_manager was initialized before using it (it might be None) ---
if login_manager:
    logger.info(f"LoginManager was initialized. Proceeding with request hooks dependent on it.")
    # The user_loader is already set if login_manager was initialized.
    # Additional configurations or checks that depend on login_manager can go here.
else:
    logger.warning("LoginManager not available, user session management will be affected. Skipping request hooks dependent on it.")

# --- Request Hooks ---
from flask_login import current_user # Import current_user for g.user

@app.before_request
def setup_jinja_globals():
    if not hasattr(g, 'jinja_filters_setup'):
        def _jinja2_filter_datetime(value, fmt="%Y-%m-%d %H:%M"): # More useful default format
            if value is None: return ""
            if isinstance(value, datetime): return value.strftime(fmt)
            return value
        app.jinja_env.filters['strftime'] = _jinja2_filter_datetime
        g.jinja_filters_setup = True
    g.user = current_user

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # For Cache-Control, it's often better to set it specifically for static vs dynamic content,
    # but a general one can be a start. For static files, Flask's send_from_directory
    # might already set some cache headers. We can refine this later if needed.
    # response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0' # Example: very restrictive
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache' # for HTTP/1.0 caches
    response.headers['Expires'] = '0' # for proxy caches
    return response

# --- Custom static file route removed. ---
# Flask's built-in static handling will be used, configured by:
# app = Flask(__name__, static_folder=GLOBAL_STATIC_FOLDER, static_url_path='/static')
# where GLOBAL_STATIC_FOLDER is the absolute path to project_root/frontend/static/


# --- Main Execution (for development) ---
if __name__ == '__main__':
    logger.info('Starting application via __main__...')
    # SpaCy model check (from user's example)
    try:
        import spacy
        spacy.load('en_core_web_sm') # User had en_core_web_sm
        logger.info("SpaCy en_core_web_sm model found.")
    except OSError:
        logger.error('SpaCy en_core_web_sm model not found. Attempting to download...')
        try:
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
            logger.info("Successfully downloaded en_core_web_sm.")
        except Exception as e_spacy:
            logger.error(f"Failed to download Spacy model 'en_core_web_sm': {e_spacy}. This could be due to network issues, an incorrect model name, or insufficient permissions. Please check your internet connection and the model name.", exc_info=True)

    port = int(os.getenv('PORT', 5000))
    # Debug mode should come from FLASK_DEBUG=1 env var ideally, not FLASK_ENV
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    logger.info(f"Running Flask app: host='0.0.0.0', port={port}, debug={debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
