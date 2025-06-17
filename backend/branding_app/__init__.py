from flask import Blueprint

branding_bp = Blueprint('branding_kit', __name__, template_folder='templates', static_folder='static')

from . import routes # noqa
