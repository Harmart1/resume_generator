from flask import Blueprint

mock_interview_bp = Blueprint('mock_interview', __name__, template_folder='../../frontend/templates/mock_interview', static_folder='../../frontend/static')

from . import routes
