import os
from functools import wraps
from flask import g, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user

# Constants
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")

# Credit Type Constants (uncommented as they are used by routes)
CREDIT_TYPE_RESUME_AI = 'resume_ai'
CREDIT_TYPE_COVER_LETTER_AI = 'cover_letter_ai'
CREDIT_TYPE_DEEP_DIVE = 'deep_dive'

# Monthly Credit Quotas for Starter Tier (uncommented)
STARTER_MONTHLY_RESUME_AI_CREDITS = 10
STARTER_MONTHLY_COVER_LETTER_AI_CREDITS = 5
STARTER_MONTHLY_DEEP_DIVE_CREDITS = 1
PRO_UNLIMITED_CREDITS = 99999 # Represents a large number for "unlimited"


def tier_required(required_tiers):
    if isinstance(required_tiers, str):
        required_tiers = [required_tiers]
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Ensure current_user is loaded, might need g.user assignment if not automatically handled
            # In typical Flask-Login setup, current_user should be available.
            # If g.user is specifically needed by the decorator logic elsewhere, ensure it's set.
            # For now, assume current_user is sufficient.
            user_tier = current_user.tier

            allowed = False
            if 'pro' in required_tiers and user_tier == 'pro':
                allowed = True
            elif 'starter' in required_tiers and user_tier in ['starter', 'pro']:
                allowed = True
            elif 'free' in required_tiers and user_tier in ['free', 'starter', 'pro']: # free tier can access free features
                allowed = True

            if not allowed:
                # Check if it's an API endpoint (common pattern in this app)
                is_api_endpoint = any(ep_path in request.path for ep_path in [
                    '/analyze_resume', '/match_job', '/check_ats',
                    '/translate_resume', '/get_smart_suggestions',
                    '/get_job_market_insights', '/generate_cover_letter', # from app.py
                    '/get-recommendations' # from resume_builder/routes.py
                ])

                if is_api_endpoint or (request.blueprint and request.endpoint and '.' in request.endpoint): # More robust API check
                    return jsonify({"error": f"This feature requires one of the following tiers: {', '.join(required_tiers)}. Your current tier is '{user_tier}'."}), 403
                else:
                    flash(f"This feature requires one of the following tiers: {', '.join(required_tiers)}. Please upgrade. (Your tier: '{user_tier}')", "warning")
                    # Try to redirect to 'index' in the main app, or a relevant dashboard/upgrade page
                    # Fallback to request.referrer if 'index' is not suitable for all cases
                    return redirect(url_for('index', **request.args))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Copied from app.py, to be adjusted for new location
# def get_or_create_credit_record(user_id, credit_type): # Needs db, Credit, User, logger, constants
#     from .models import Credit, User # Assuming Credit model would be here
#     from .extensions import db
#     credit_record = Credit.query.filter_by(user_id=user_id, credit_type=credit_type).first()
#     if not credit_record:
#         logger.info(f"Creating new credit record for user {user_id}, type {credit_type}")
#         credit_record = Credit(user_id=user_id, credit_type=credit_type, amount=0, last_reset=datetime.utcnow()) # datetime needs import
#         db.session.add(credit_record)
#         try:
#             db.session.commit()
#         except Exception as e:
#             db.session.rollback()
#             logger.error(f"Error committing new credit record for user {user_id}, type {credit_type}: {e}")
#             raise
#     return credit_record

def consume_credit(user_id, credit_type, amount_to_consume=1): # Needs User, logger, get_or_create_credit_record (or its logic), db
    from .models import User # Credit model is commented out
    # from .extensions import db # db needed if get_or_create_credit_record is inlined or db.session.commit active

    user = User.query.get(user_id)
    if not user:
        logger.error(f"User not found for ID {user_id} during credit consumption.")
        return False

    if user.tier == 'pro':
        return True

    # try:
    #     credit_record = get_or_create_credit_record(user_id, credit_type) # This is commented out
    #     if credit_record and credit_record.amount >= amount_to_consume:
    #         credit_record.amount -= amount_to_consume
    #         db.session.commit()
    #         logger.info(f"Consumed {amount_to_consume} credit(s) for user {user_id}, type {credit_type}. Remaining: {credit_record.amount}")
    #         return True
    #     else:
    #         logger.warning(f"Insufficient credits for user {user_id}, type {credit_type}. Has: {credit_record.amount if credit_record else 'None'}, Needs: {amount_to_consume}")
    #         return False
    # except Exception as e:
    #     logger.error(f"Error in consume_credit for user {user_id}, type {credit_type}: {e}")
    #     return False
    logger.warning(f"consume_credit called for user {user_id}, type {credit_type}, but core credit logic is commented out. Returning False by default for non-pro.")
    return False # Default for non-pro if credit logic is bypassed/commented
