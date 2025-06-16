from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os

# Add the project's root directory to sys.path to help find the backend package.
# This assumes env.py is in backend/migrations/.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import models and db instance ---
# Explicitly import all models and the db instance for Alembic's awareness.
try:
    from backend.extensions import db # Import the SQLAlchemy instance
    from backend.models import User, Resume, CoverLetter, FeatureUsageLog, Credit
    from backend.mock_interview_app.models import MockInterview
    # If you had a common Base = declarative_base(), it would be:
    # from backend.models import Base
    # target_metadata = Base.metadata
    # But with Flask-SQLAlchemy, db.metadata is the one.
except ImportError as e:
    print(f"Error importing models or db in env.py: {e}. Check sys.path and ensure models/extensions are correctly defined.")
    print(f"Current sys.path: {sys.path}")
    raise # Re-raise to make it clear if models or db can't be found

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# For 'autogenerate' support, Alembic needs to know about your models' metadata.
# Using db.metadata from the imported Flask-SQLAlchemy instance.
target_metadata = db.metadata

def get_sqlalchemy_url():
    # Try to get the URL from FLASK_APP's config first
    try:
        from flask import current_app
        # This check is important to see if we are in an app_context
        if current_app and 'SQLALCHEMY_DATABASE_URI' in current_app.config:
            url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
            if url:
                return url
    except RuntimeError: # "Working outside of application context"
        pass # Fall through to alembic.ini configuration

    # Fallback to alembic.ini if not in app context or if current_app doesn't have the URI
    # This is standard Alembic behavior.
    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url and target_metadata and hasattr(target_metadata.bind, 'url'): # Last resort from bound metadata
        db_url = str(target_metadata.bind.url)
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata, # Uses db.metadata from imported extensions
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # From user feedback
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # This is the typical Flask-Migrate approach.
    # It relies on the Flask app context being available.
    from flask import current_app

    # Use the engine from the Flask app's SQLAlchemy instance
    connectable = current_app.extensions['migrate'].db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=current_app.extensions['migrate'].db.metadata, # Primary source of metadata in online mode
            compare_type=True, # From user feedback
            # include_schemas=True, # Uncomment if using multiple schemas
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode...")
    run_migrations_online()
