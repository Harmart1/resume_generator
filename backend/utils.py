import os
from functools import wraps
from flask import g, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
import logging # ADDED
from datetime import datetime # ADDED
from .extensions import db # ADDED for credit helpers
from .models import User, Credit # ADDED for credit helpers

logger = logging.getLogger(__name__) # ENSURED logger is initialized

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

# --- Credit Management Helper Functions ---
# (Adapted from their original definitions in app.py)

def get_or_create_credit_record(user_id, credit_type):
    # Imports are now at the top of utils.py
    credit_record = Credit.query.filter_by(user_id=user_id, credit_type=credit_type).first()
    if not credit_record:
        logger.info(f"Creating new credit record for user {user_id}, type {credit_type}")
        # Determine initial amount based on user's tier and credit type (example logic)
        user = User.query.get(user_id)
        initial_amount = 0
        if user: # Check if user exists
            if user.tier == 'starter':
                if credit_type == CREDIT_TYPE_RESUME_AI:
                    initial_amount = STARTER_MONTHLY_RESUME_AI_CREDITS
                elif credit_type == CREDIT_TYPE_COVER_LETTER_AI:
                    initial_amount = STARTER_MONTHLY_COVER_LETTER_AI_CREDITS
                elif credit_type == CREDIT_TYPE_DEEP_DIVE:
                    initial_amount = STARTER_MONTHLY_DEEP_DIVE_CREDITS
            elif user.tier == 'pro':
                initial_amount = PRO_UNLIMITED_CREDITS

        credit_record = Credit(user_id=user_id, credit_type=credit_type, amount=initial_amount, last_reset=datetime.utcnow())
        db.session.add(credit_record)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing new credit record for user {user_id}, type {credit_type}: {e}")
            raise # Or return None, to be handled by caller
    return credit_record

def get_user_credits(user_id, credit_type):
    # Imports are at the top
    credit_record = get_or_create_credit_record(user_id, credit_type)
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User not found for ID {user_id} in get_user_credits.")
        return 0 # Or raise error

    if user.tier == 'starter' and credit_record:
        today = datetime.utcnow()
        if credit_record.last_reset and (today.year > credit_record.last_reset.year or today.month > credit_record.last_reset.month):
            # Reset credits for the new month
            if credit_type == CREDIT_TYPE_RESUME_AI:
                credit_record.amount = STARTER_MONTHLY_RESUME_AI_CREDITS
            elif credit_type == CREDIT_TYPE_COVER_LETTER_AI:
                credit_record.amount = STARTER_MONTHLY_COVER_LETTER_AI_CREDITS
            elif credit_type == CREDIT_TYPE_DEEP_DIVE:
                credit_record.amount = STARTER_MONTHLY_DEEP_DIVE_CREDITS
            credit_record.last_reset = today
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error committing credit reset for user {user_id}, type {credit_type}: {e}")
                # Potentially re-raise or handle gracefully
    return credit_record.amount if credit_record else 0

def consume_credit(user_id, credit_type, amount_to_consume=1):
    # Imports are at the top
    user = User.query.get(user_id)
    if not user:
        logger.error(f"User not found for ID {user_id} during credit consumption.")
        return False

    if user.tier == 'pro': # Pro users have "unlimited" for features that use this function
        return True

    try:
        credit_record = get_or_create_credit_record(user_id, credit_type)
        if credit_record.last_reset is None: # Ensure last_reset is set if it's a new record from get_or_create
            get_user_credits(user_id, credit_type) # This will set and commit last_reset if needed
            credit_record = Credit.query.filter_by(user_id=user_id, credit_type=credit_type).first() # Re-fetch

        # Check for monthly reset if needed (copied from get_user_credits)
        if user.tier == 'starter':
            today = datetime.utcnow()
            if credit_record.last_reset and (today.year > credit_record.last_reset.year or today.month > credit_record.last_reset.month):
                if credit_type == CREDIT_TYPE_RESUME_AI: credit_record.amount = STARTER_MONTHLY_RESUME_AI_CREDITS
                elif credit_type == CREDIT_TYPE_COVER_LETTER_AI: credit_record.amount = STARTER_MONTHLY_COVER_LETTER_AI_CREDITS
                elif credit_type == CREDIT_TYPE_DEEP_DIVE: credit_record.amount = STARTER_MONTHLY_DEEP_DIVE_CREDITS
                credit_record.last_reset = today
                # Commit is handled below or by get_or_create_credit_record

        if credit_record and credit_record.amount >= amount_to_consume:
            credit_record.amount -= amount_to_consume
            db.session.commit()
            logger.info(f"Consumed {amount_to_consume} credit(s) for user {user_id}, type {credit_type}. Remaining: {credit_record.amount}")
            return True
        else:
            current_amount = credit_record.amount if credit_record else 0
            logger.warning(f"Insufficient credits for user {user_id}, type {credit_type}. Has: {current_amount}, Needs: {amount_to_consume}")
            return False
    except Exception as e:
        logger.error(f"Error in consume_credit for user {user_id}, type {credit_type}: {e}")
        db.session.rollback() # Rollback on error
        return False

def reset_monthly_credits_for_user(user_id_or_obj):
    # Imports are at the top
    if isinstance(user_id_or_obj, User):
        user = user_id_or_obj
    else:
        user = User.query.get(user_id_or_obj)

    if not user or user.tier != 'starter':
        logger.info(f"User {user.id if user else 'Unknown'} is not starter or does not exist. No credits reset.")
        return False

    logger.info(f"Attempting monthly credit reset for Starter user {user.id} ({user.email})")
    changes_made = False
    current_time = datetime.utcnow()

    credit_configs = {
        CREDIT_TYPE_RESUME_AI: STARTER_MONTHLY_RESUME_AI_CREDITS,
        CREDIT_TYPE_COVER_LETTER_AI: STARTER_MONTHLY_COVER_LETTER_AI_CREDITS,
        CREDIT_TYPE_DEEP_DIVE: STARTER_MONTHLY_DEEP_DIVE_CREDITS,
    }

    for credit_type, monthly_amount in credit_configs.items():
        try:
            credit_record = get_or_create_credit_record(user.id, credit_type)
            # No need to check last_reset here, as this function is for explicit reset (e.g. on subscription renewal)
            credit_record.amount = monthly_amount
            credit_record.last_reset = current_time
            db.session.add(credit_record)
            changes_made = True
            logger.info(f"Reset credits for user {user.id}, type {credit_type} to {monthly_amount}.")
        except Exception as e:
            logger.error(f"Error resetting {credit_type} for user {user.id}: {e}")
            db.session.rollback()
            # Continue to try other credit types

    if changes_made:
        try:
            db.session.commit()
            logger.info(f"Successfully committed monthly credit resets for user {user.id}.")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing all credit resets for user {user.id}: {e}")
            return False
    return False
