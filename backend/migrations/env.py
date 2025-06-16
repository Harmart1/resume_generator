from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os

# Add the project's root directory to sys.path to help find the backend package.
# Assumes env.py is in backend/migrations/.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Insert at beginning for precedence

# --- Import models for Alembic's awareness ---
# These are important for autogenerate support, especially if dynamic detection via app context faces issues.
try:
    from backend.models import User, Resume, CoverLetter, FeatureUsageLog, Credit # Base is not used if db.Model is the base
    from backend.mock_interview_app.models import MockInterview
    # It's also common to just import 'db' from backend.extensions
    # from backend.extensions import db
    # target_metadata_declarative = db.metadata # This would be the ideal if app context isn't used
except ImportError as e:
    print(f"Error importing models in env.py: {e}. Check sys.path and ensure models are correctly defined.")
    print(f"Current sys.path: {sys.path}")
    raise # Re-raise to make it clear if models can't be found

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Default target_metadata. This will be overridden in online mode by current_app's metadata.
# For offline mode, or if online mode fails to get app context, this provides a fallback.
# This requires that all models are imported above and registered with a common MetaData instance
# (e.g., if they all use db.Model from Flask-SQLAlchemy, then db.metadata is the one).
# For now, setting to None and relying on online mode to populate it from current_app.
# If using user's suggestion of explicit Base.metadata, ensure Base is correctly defined and used by models.
target_metadata = None

def get_sqlalchemy_url():
    # Try to get the URL from FLASK_APP's config first
    try:
        from flask import current_app
        if current_app:
            return current_app.config.get('SQLALCHEMY_DATABASE_URI')
        # If no current_app, it might be an environment where FLASK_APP is not yet fully loaded.
    except RuntimeError: # Typically "Working outside of application context."
        pass # Fall through to alembic.ini configuration

    # Fallback to alembic.ini if not in app context or if current_app doesn't have the URI
    # This is standard Alembic behavior.
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available. (Corrected comment)
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_sqlalchemy_url()

    # For offline mode, we must have target_metadata.
    # If current_app wasn't available, we need a fallback.
    # This assumes `db.metadata` from `backend.extensions` is the one.
    # This part is tricky if not running within Flask app context.
    effective_target_metadata = target_metadata
    if effective_target_metadata is None:
        try:
            from backend.extensions import db
            effective_target_metadata = db.metadata
        except ImportError:
            print("Error: Could not import db from backend.extensions for offline metadata.")
            # As a last resort if direct model imports were successful and they share a common declarative base:
            # from backend.models import Base # (If such a Base exists)
            # effective_target_metadata = Base.metadata
            # This part requires careful setup of how models define their metadata if not using Flask-SQLAlchemy's db.metadata
            effective_target_metadata = None # Must be set for context.configure

    context.configure(
        url=url,
        target_metadata=effective_target_metadata, # Ensure this is not None
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # Enable type comparison
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # This is the typical Flask-Migrate approach.
    from flask import current_app

    # Configure Alembic context with settings from the Flask app
    # This ensures Alembic uses the same database URL and metadata as the app
    connectable = current_app.extensions['migrate'].db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=current_app.extensions['migrate'].db.metadata,
            compare_type=True, # Enable type comparison
            # include_schemas=True, # If using schemas
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode...")
    run_migrations_online()
