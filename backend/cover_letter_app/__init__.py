import os # Added for path manipulation
from flask import Blueprint

# Define paths relative to this file's location (backend/cover_letter_app/__init__.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'templates', 'cover_letter')
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'frontend', 'static')

# Templates are in frontend/templates/cover_letter
# Static folder can remain general if not specifically used by this blueprint,
# or can be set to a specific static folder for this blueprint if needed.
cover_letter_bp = Blueprint(
    'cover_letter',
    __name__,
    template_folder=TEMPLATE_FOLDER, # Corrected path
    static_folder=STATIC_FOLDER # General static folder, adjust if needed
)

# Import routes after blueprint definition to avoid circular imports
from . import routes
