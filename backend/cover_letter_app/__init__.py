from flask import Blueprint

# Templates are still in frontend/templates, not frontend/templates/cover_letter
# Static folder is not used by this blueprint directly based on original setup.
cover_letter_bp = Blueprint(
    'cover_letter',
    __name__,
    template_folder='../../frontend/templates', # Points to frontend/templates
    static_folder='../../frontend/static' # General static folder
)

# Import routes after blueprint definition to avoid circular imports
from . import routes
