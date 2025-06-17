from flask import Blueprint

eq_bp = Blueprint('eq_coach', __name__, template_folder='templates', static_folder='static')

from . import routes # noqa
