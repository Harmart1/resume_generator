from flask import Blueprint

skill_gap_bp = Blueprint('skill_gap_analysis', __name__, template_folder='templates', static_folder='static')

from . import routes # noqa
