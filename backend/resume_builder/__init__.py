import os # Added for path manipulation
from flask import Blueprint

# Define paths relative to this file's location (backend/resume_builder/__init__.py)
# os.path.dirname(__file__) is backend/resume_builder/
# os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) is project_root/ (e.g., src/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'templates', 'resume_builder')
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'static')


# Define the blueprint. Adjust template_folder if necessary.
# Assuming resume_builder templates are in 'frontend/templates/resume_builder/'
bp = Blueprint('resume_builder',
               __name__,
               template_folder=TEMPLATE_FOLDER,
               static_folder=STATIC_FOLDER, # If it has specific static files
               static_url_path='/resume-builder/static') # URL path for its static files

from . import routes  # Import routes to register them with the blueprint
