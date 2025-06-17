from flask import Blueprint

negotiation_bp = Blueprint('negotiation_coach', __name__, template_folder='templates', static_folder='static')

from . import routes # noqa
