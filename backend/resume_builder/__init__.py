from flask import Blueprint

# Define the blueprint. Adjust template_folder if necessary.
# Assuming resume_builder templates are in 'frontend/templates/resume_builder/'
bp = Blueprint('resume_builder',
               __name__,
               template_folder='../../frontend/templates/resume_builder',
               static_folder='../../frontend/static', # If it has specific static files
               static_url_path='/resume-builder/static') # URL path for its static files

from . import routes  # Import routes to register them with the blueprint
