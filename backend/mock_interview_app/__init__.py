import os # Added for path manipulation
from flask import Blueprint

# Define paths relative to this file's location (backend/mock_interview_app/__init__.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'templates', 'mock_interview')
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'static')

mock_interview_bp = Blueprint('mock_interview',
                              __name__,
                              template_folder=TEMPLATE_FOLDER,
                              static_folder=STATIC_FOLDER)

from . import routes
