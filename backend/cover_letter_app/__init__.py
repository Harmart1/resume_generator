from flask import Blueprint

# Templates are in frontend/templates/cover_letter
# Static folder can remain general if not specifically used by this blueprint,
# or can be set to a specific static folder for this blueprint if needed.
cover_letter_bp = Blueprint(
    'cover_letter',
    __name__,
    template_folder='../../frontend/templates/cover_letter', # Corrected path
    static_folder='../../frontend/static' # General static folder, adjust if needed
)

# Import routes after blueprint definition to avoid circular imports
from . import routes
