# backend/cover_letter/__init__.py

from flask import Blueprint

# Create a blueprint for cover letter routes
bp = Blueprint('cover_letter', __name__, 
              template_folder='../../../frontend/templates/cover_letter',
              static_folder='../../../frontend/static')

# Import routes at the bottom to avoid circular dependencies
from backend.cover_letter_app import routes
