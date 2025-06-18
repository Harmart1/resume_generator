import os
import hashlib
import logging
import subprocess
import argparse
from pathlib import Path
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / 'backend' / 'migrations'
ALEMBIC_INI_PATH = MIGRATIONS_DIR / 'alembic.ini'
VERSIONS_DIR = MIGRATIONS_DIR / 'versions'
DATABASE_URL_ENV_VAR = 'DATABASE_URL'
DEFAULT_SQLITE_URL = 'sqlite:///instance/site.db'

# Placeholder for EXPECTED_CHECKSUMS - to be populated later
EXPECTED_CHECKSUMS = {
    "0001_initial_schema_baseline.py": "283349809890a343122535186977740208d95060708acedf993fef07b287796f",
    "0002_add_username_fields.py": "507e373c95c57382f7e96915d60153a0e28d980a7a4407f1991950fcf988769d",
    "0003_create_mock_interview_table.py": "2a0052ba6713d19597595b997f99990711a8367355b497a2cb177f96209a3e24",
    "0004_implement_new_credit_system.py": "0bf8d0a77d99878390bf48728380353126905f070ac580ac8f81be7b52e9663c",
}

# Placeholder for MIGRATIONS_TO_APPLY - to be populated later
MIGRATIONS_TO_APPLY = [
    {
        'filename': '0001_initial_schema_baseline.py',
        'content': """\"\"\"initial_schema_baseline

Revision ID: '0001'
Revises:
Create Date: '2025-06-14 06:31:00.000000'

\"\"\"
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('tier', sa.String(length=50), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=120), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=120), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    # Resumes table
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Cover Letters table
    op.create_table(
        'cover_letters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Feature Usage Logs table
    op.create_table(
        'feature_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('feature_name', sa.String(length=100), nullable=False),
        sa.Column('credits_used', sa.Integer(), nullable=False, default=0),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # User Credit table (old system)
    op.create_table(
        'user_credit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credits_remaining', sa.Integer(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('user_credit')
    op.drop_table('feature_usage_logs')
    op.drop_table('cover_letters')
    op.drop_table('resumes')
    op.drop_table('users')
"""
    },
    {
        'filename': '0002_add_username_fields.py',
        'content': """\"\"\"add_username_and_other_profile_fields_to_user

Revision ID: '0002'
Revises: '0001'
Create Date: '2025-06-14 06:32:00.000000'

\"\"\"
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('username', sa.String(length=80), nullable=False, server_default='temp_username'))
    op.add_column('users', sa.Column('industry_preference', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('contact_phone', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('profile_updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('users') as batch_op:
        batch_op.create_unique_constraint('uq_users_username', ['username'])
        batch_op.alter_column('username', server_default=None)

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_username', type_='unique')

    op.drop_column('users', 'profile_updated_at')
    op.drop_column('users', 'contact_phone')
    op.drop_column('users', 'industry_preference')
    op.drop_column('users', 'username')
"""
    },
    {
        'filename': '0003_create_mock_interview_table.py',
        'content': """\"\"\"create_mock_interview_table

Revision ID: '0003'
Revises: '0002'
Create Date: '2025-06-14 06:33:00.000000'

\"\"\"
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'mock_interview',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column('job_description', sa.Text(), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=True),
        sa.Column('scores', sa.JSON(), nullable=True),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('mock_interview')
"""
    },
    {
        'filename': '0004_implement_new_credit_system.py',
        'content': """\"\"\"implement_new_credit_system_and_drop_user_credit

Revision ID: '0004'
Revises: '0003'
Create Date: '2025-06-14 06:34:00.000000'

\"\"\"
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    # Create credits table
    op.create_table(
        'credits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credit_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('last_reset', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'credit_type', name='uq_user_credit_type')
    )
    # Drop user_credit table
    op.drop_table('user_credit')

def downgrade():
    # Recreate user_credit table
    op.create_table(
        'user_credit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credits_remaining', sa.Integer(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Drop credits table
    op.drop_table('credits')
"""
    },
]

def get_database_url():
    return os.getenv(DATABASE_URL_ENV_VAR, DEFAULT_SQLITE_URL)

def is_sqlite_db(db_url_to_check):
    return db_url_to_check.startswith('sqlite')

def get_json_type(): # For use in new migration templates
    return 'sa.Text()' if is_sqlite_db(get_database_url()) else 'sa.JSON()'

def make_sure_instance_folder_exists():
    db_url = get_database_url()
    if is_sqlite_db(db_url):
        db_path_str = db_url.split('sqlite:///')[-1]
        if db_path_str:
            # Handle absolute paths for SQLite (e.g. sqlite:////path/to/db)
            if os.path.isabs(db_path_str):
                db_path = Path(db_path_str)
            else:
                # Assume relative to project root for instance folder if not absolute
                db_path = Path(__file__).resolve().parent / db_path_str

            instance_folder = db_path.parent
            if not instance_folder.exists():
                logger.info(f"Creating instance folder: {instance_folder}")
                instance_folder.mkdir(parents=True, exist_ok=True)
            else:
                logger.info(f"Instance folder {instance_folder} already exists.")
        else:
            logger.warning(f"Could not determine instance folder from DB URL: {db_url}")

logger.info("Helper functions (get_database_url, is_sqlite_db, get_json_type, make_sure_instance_folder_exists) appended to setup_migrations.py.")

def run_alembic_command(alembic_cfg, cmd, *args, **kwargs):
    logger.info(f"Running Alembic: {cmd} with args: {args}, kwargs: {kwargs}")
    try:
        method = getattr(command, cmd)
        method(alembic_cfg, *args, **kwargs)
        logger.info(f"Alembic command '{cmd}' executed successfully.")
    except Exception as e:
        logger.error(f"Error running Alembic command '{cmd}': {e}", exc_info=True)
        raise

def get_alembic_config():
    if not ALEMBIC_INI_PATH.is_file():
        logger.error(f"Alembic ini file not found at {ALEMBIC_INI_PATH}")
        raise FileNotFoundError(f"Alembic ini file not found at {ALEMBIC_INI_PATH}")

    # Create a new Config object each time or ensure it's fresh
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))

    # Dynamically set crucial options that might be relative in alembic.ini
    alembic_cfg.set_main_option('script_location', str(MIGRATIONS_DIR.resolve()))
    alembic_cfg.set_main_option('sqlalchemy.url', get_database_url()) # Ensure this uses the latest from env

    # Set version_locations if not absolute in alembic.ini
    # Example: version_locations = %(here)s/versions -> backend/migrations/versions
    # If alembic.ini has `version_locations = versions` (relative to MIGRATIONS_DIR)
    # this should be fine. If it's `%(here)s/versions`, also fine if `here` is MIGRATIONS_DIR.
    # For safety, can resolve and set it:
    # effective_versions_dir = (MIGRATIONS_DIR / "versions").resolve()
    # alembic_cfg.set_main_option('version_locations', str(effective_versions_dir))

    logger.info(f"Alembic config loaded. Script location: {alembic_cfg.get_main_option('script_location')}, DB URL: {alembic_cfg.get_main_option('sqlalchemy.url')}")
    return alembic_cfg

def verify_db_connection():
    db_url = get_database_url()
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection: # Ensure connection is actively used or tested
            connection.execute(sa.text("SELECT 1")) # Simple query to test connection
            logger.info(f"DB connection OK for: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        return True
    except Exception as e:
        logger.error(f"DB connection failed for {db_url}: {e}", exc_info=True)
        return False

logger.info("Alembic helper functions (run_alembic_command, get_alembic_config, verify_db_connection) appended to setup_migrations.py.")

def get_current_revision_from_db(alembic_cfg):
    # Ensure alembic_cfg has sqlalchemy.url set
    db_url = alembic_cfg.get_main_option('sqlalchemy.url')
    if not db_url:
        logger.error("sqlalchemy.url not set in Alembic config for get_current_revision_from_db")
        return None

    engine = create_engine(db_url)
    db_inspector = inspect(engine) # Use 'db_inspector' to avoid conflict if 'inspector' is used elsewhere

    if not db_inspector.has_table('alembic_version'):
        logger.info("No alembic_version table found, database is likely uninitialized.")
        return None

    try:
        with engine.connect() as connection:
            result = connection.execute(sa.text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            current_rev = row[0] if row else None
            logger.info(f"Current DB revision from table: {current_rev}")
            return current_rev
    except Exception as e:
        # Log specific error and re-raise or return None
        logger.error(f"Error fetching revision from alembic_version table: {e}", exc_info=True)
        return None # Or handle more gracefully depending on expected use

def stamp_db_to_revision(alembic_cfg, revision_id):
    logger.info(f"Stamping database to revision: {revision_id}")
    try:
        run_alembic_command(alembic_cfg, 'stamp', revision_id)
        logger.info(f"Database successfully stamped to revision {revision_id}.")
    except Exception as e:
        # Error is already logged by run_alembic_command, re-raise if necessary
        # Or add more specific error handling here for stamp failures
        logger.error(f"Failed to stamp database to revision {revision_id}.", exc_info=True)
        raise # Re-raise to indicate failure to the caller

def ensure_migrations_are_written():
    if not VERSIONS_DIR.exists():
        logger.info(f"Creating versions directory: {VERSIONS_DIR}")
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    all_files_ok = True
    current_db_is_sqlite = is_sqlite_db(get_database_url())
    json_type_to_use = 'sa.Text()' if current_db_is_sqlite else 'sa.JSON()'

    logger.info(f"Ensuring migration files. Using JSON type: {json_type_to_use}")

    if not MIGRATIONS_TO_APPLY:
        logger.warning("MIGRATIONS_TO_APPLY list is empty. No migration files to write from the list.")
        return # Nothing to do if the list is empty

    for migration_info in MIGRATIONS_TO_APPLY:
        filename = migration_info.get('filename')
        content_template = migration_info.get('content')

        if not filename or content_template is None: # content can be empty string, so check for None
            logger.error(f"Invalid migration_info in MIGRATIONS_TO_APPLY: {migration_info}. Missing 'filename' or 'content'.")
            all_files_ok = False
            continue

        # Prepare content: replace sa.JSON() with sa.Text() if SQLite, and sa.Text() with sa.JSON() if PG and original was Text for JSON.
        # This simple replacement assumes migration templates use sa.JSON() by default for JSON types.
        # A more robust way would be specific placeholders like {{JSON_TYPE}} in templates.
        # For now, this addresses the common case.
        content = content_template
        if current_db_is_sqlite:
            content = content.replace("sa.JSON()", "sa.Text()")
        else:
            # If we are on PostgreSQL, and the template might have used sa.Text() for SQLite compatibility,
            # we might want to change it back to sa.JSON(). This is trickier.
            # For now, assume templates are written with sa.JSON() and only change for SQLite.
            pass


        filepath = VERSIONS_DIR / filename

        # Normalize content for checksum calculation and writing (LF line endings)
        # The content from MIGRATIONS_TO_APPLY should already be in a consistent format (LF)
        # if it was prepared correctly.
        content_normalized_for_template_checksum = content.replace('\r\n', '\n').replace('\r', '\n')
        template_checksum = hashlib.sha256(content_normalized_for_template_checksum.encode('utf-8')).hexdigest()

        expected_checksum_from_dict = EXPECTED_CHECKSUMS.get(filename)

        if filepath.exists():
            try:
                current_content = filepath.read_text(encoding='utf-8')
                current_content_normalized = current_content.replace('\r\n', '\n').replace('\r', '\n')
                current_checksum = hashlib.sha256(current_content_normalized.encode('utf-8')).hexdigest()
            except Exception as e:
                logger.error(f"Error reading or checksumming existing file {filepath}: {e}", exc_info=True)
                all_files_ok = False
                # Decide if to try overwriting or just fail
                logger.warning(f"Attempting to overwrite problematic file {filepath} due to read/checksum error.")
                # Fall through to write logic below by setting current_checksum to indicate difference


            if expected_checksum_from_dict and current_checksum == expected_checksum_from_dict:
                logger.info(f"Migration {filename} exists and checksum matches EXPECTED_CHECKSUMS ('{expected_checksum_from_dict[:7]}...').")
                continue # File is good as per official checksum
            elif current_checksum == template_checksum:
                logger.info(f"Migration {filename} exists and content matches current template ('{template_checksum[:7]}...').")
                if expected_checksum_from_dict and current_checksum != expected_checksum_from_dict:
                    logger.warning(f"  Note: Official checksum in EXPECTED_CHECKSUMS ('{expected_checksum_from_dict[:7]}...') differs. The file matches the *current* template derived from MIGRATIONS_TO_APPLY.")
                continue # File is good as per current template
            else:
                logger.warning(f"Checksum mismatch for {filename}.")
                logger.warning(f"  Path: {filepath}")
                logger.warning(f"  Expected (from dict): {expected_checksum_from_dict[:7]}..." if expected_checksum_from_dict else "N/A")
                logger.warning(f"  Actual (on disk):   {current_checksum[:7]}...")
                logger.warning(f"  Template (derived): {template_checksum[:7]}...")
                logger.warning(f"  Will overwrite {filename} with content from MIGRATIONS_TO_APPLY.")
                # Fall through to write logic
        else:
            logger.info(f"Migration file {filename} does not exist. Will create it.")

        # Write/overwrite the file
        logger.info(f"Writing migration file: {filepath}")
        try:
            # Ensure consistent LF line endings on write
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content_normalized_for_template_checksum) # Write the already normalized content

            # Verify checksum after writing
            written_content = filepath.read_text(encoding='utf-8')
            written_content_normalized = written_content.replace('\r\n', '\n').replace('\r', '\n')
            actual_checksum_after_write = hashlib.sha256(written_content_normalized.encode('utf-8')).hexdigest()

            logger.info(f"  Written {filename} with actual checksum: {actual_checksum_after_write[:7]}...")

            if expected_checksum_from_dict and actual_checksum_after_write != expected_checksum_from_dict:
                 logger.warning(f"  Checksum after writing {filename} ('{actual_checksum_after_write[:7]}...') still does not match EXPECTED_CHECKSUMS ('{expected_checksum_from_dict[:7]}...'). This is unexpected if the template was supposed to match the expected checksum.")
            elif actual_checksum_after_write != template_checksum:
                 logger.error(f"  Critical: Checksum after writing {filename} ('{actual_checksum_after_write[:7]}...') does not match the template checksum ('{template_checksum[:7]}...') it was just written from. This indicates a write/read consistency problem.")
                 all_files_ok = False

        except IOError as e:
            logger.error(f"Error writing migration file {filepath}: {e}", exc_info=True)
            all_files_ok = False
            # Consider if to re-raise or try to continue with other files

    if not all_files_ok:
        raise IOError("One or more migration files could not be written or verified correctly. Check logs.")

    logger.info("All migration files in MIGRATIONS_TO_APPLY checked/written successfully.")

logger.info("Migration management functions (get_current_revision_from_db, stamp_db_to_revision, ensure_migrations_are_written) appended.")

def main_migrate(interactive_mode=False): # Added default for interactive_mode
    logger.info("Migration process starting...")
    make_sure_instance_folder_exists() # Ensures instance/ exists for SQLite if using default path

    if not verify_db_connection():
        logger.error("Database connection failed. Aborting migration process.")
        if os.getenv("CI"): # Fail hard in CI environments
            raise ConnectionError("DB connection failed in CI environment. Cannot proceed with migration.")
        return False # Indicate failure for other environments

    # ensure_migrations_are_written() will be called before alembic commands that need scripts
    # For example, before 'upgrade' or 'revision --autogenerate' if scripts are managed by this file.
    # If scripts are expected to be solely managed by Alembic's own history, this call might be different.
    # For now, let's assume it's needed to ensure our defined scripts are on disk.
    try:
        ensure_migrations_are_written()
    except Exception as e:
        logger.error(f"ensure_migrations_are_written failed: {e}", exc_info=True)
        return False # Cannot proceed if scripts can't be ensured

    alembic_cfg = get_alembic_config()
    current_rev_db = get_current_revision_from_db(alembic_cfg)

    latest_known_script_id = None
    if MIGRATIONS_TO_APPLY: # Check if list is not empty
        try:
            # Get the revision part, e.g., '0004' from '0004_....py'
            latest_known_script_id = MIGRATIONS_TO_APPLY[-1]['filename'].split('_')[0]
        except (IndexError, KeyError) as e:
            logger.error(f"Could not determine latest_known_script_id from MIGRATIONS_TO_APPLY: {e}")
            # Decide behavior: maybe proceed without it, or fail. For now, proceed.
            latest_known_script_id = None


    if current_rev_db is None:
        if latest_known_script_id:
            logger.info(f"Database appears uninitialized (no alembic_version table or no revision). Stamping to latest known script revision: {latest_known_script_id}")
            try:
                stamp_db_to_revision(alembic_cfg, latest_known_script_id)
                current_rev_db = get_current_revision_from_db(alembic_cfg) # Re-check revision after stamp
            except Exception as e:
                # Stamp failure is critical if we expect to bring DB to a known state
                logger.error(f"Failed to stamp uninitialized database to {latest_known_script_id}: {e}", exc_info=True)
                return False # Indicate failure
        else:
            logger.warning("Database is uninitialized and MIGRATIONS_TO_APPLY is empty or malformed. Cannot determine a version to stamp to. 'upgrade head' will run and might pick up existing scripts if Alembic finds them, or do nothing if no scripts exist.")
            # No explicit stamp, 'upgrade head' will be the first Alembic command to modify schema.

    logger.info(f"Attempting to upgrade database to 'head'. Current DB revision (after potential stamp): {current_rev_db}")
    try:
        run_alembic_command(alembic_cfg, 'upgrade', 'head')
        final_rev_db = get_current_revision_from_db(alembic_cfg) # Get revision after upgrade
        logger.info(f"Database migration upgrade command completed. Database is now at revision: {final_rev_db}")

        # Verification step (optional but good)
        if latest_known_script_id and final_rev_db:
            if not final_rev_db.startswith(latest_known_script_id):
                 logger.warning(f"After upgrade, the final DB revision '{final_rev_db}' does not seem to start with the latest known script ID prefix '{latest_known_script_id}'. This might be okay if new migrations were generated outside of MIGRATIONS_TO_APPLY or if using full revision hashes.")
        elif final_rev_db is None and latest_known_script_id is not None:
            logger.error(f"Critical: DB revision is None after upgrade, but expected something around {latest_known_script_id}.")
            return False # This suggests a major issue with the upgrade or revision tracking

        return True # Indicate success
    except Exception as e:
        # Error already logged by run_alembic_command
        logger.error(f"Database migration upgrade failed during 'upgrade head' command.", exc_info=True)
        # Log revision at time of failure
        failed_rev_db = get_current_revision_from_db(alembic_cfg)
        logger.error(f"Revision at time of failure (from DB): {failed_rev_db}")
        return False # Indicate failure

def generate_migration_script(message):
    logger.info(f"Attempting to generate new migration script with message: '{message}'")

    if not verify_db_connection(): # Initial check
        logger.error("Database connection failed. Cannot proceed with generating migration script.")
        return False

    # It's crucial that the database is up-to-date with all existing migrations *before*
    # autogenerate is called. Autogenerate compares models against the current DB state.
    logger.info("Ensuring database schema is up-to-date before generating new migration...")
    if not main_migrate(): # Run the full migration logic to bring DB to head
        logger.error("Database schema could not be brought up-to-date. Cannot reliably autogenerate a new migration script. Please resolve migration issues first.")
        return False
    logger.info("Database schema confirmed to be up-to-date.")

    alembic_cfg = get_alembic_config()
    try:
        # The 'message' is used by Alembic to help name the file (e.g., <revision>_<message>.py)
        # autogenerate=True tells Alembic to compare models with the DB and generate diffs
        run_alembic_command(alembic_cfg, 'revision', message=message, autogenerate=True)
        logger.info(f"Successfully generated new migration script for '{message}'.")
        logger.info("IMPORTANT: Review the generated script in the 'versions' directory.")
        logger.info("After review, manually update 'EXPECTED_CHECKSUMS' and 'MIGRATIONS_TO_APPLY' in this script (setup_migrations.py) to include the new migration in automated deployments and version management.")
        return True
    except Exception as e:
        # Error already logged by run_alembic_command
        logger.error(f"Failed to generate new migration script: {e}", exc_info=True)
        return False

def calculate_checksums(filenames_args):
    if not VERSIONS_DIR.exists():
        print(f"Versions directory does not exist: {VERSIONS_DIR}")
        logger.warning(f"Versions directory {VERSIONS_DIR} not found for checksum calculation.")
        return # Or raise error, depending on desired strictness

    files_to_checksum = []
    if filenames_args: # If specific filenames are provided
        files_to_checksum = [VERSIONS_DIR / fn for fn in filenames_args]
    else: # Otherwise, checksum all .py files in the versions directory
        files_to_checksum = [f for f in VERSIONS_DIR.iterdir() if f.is_file() and f.name.endswith('.py')]

    if not files_to_checksum:
        msg = f"No .py files found in {VERSIONS_DIR} to checksum."
        print(msg)
        logger.info(msg)
        return

    print("Checksums (SHA256):") # For direct CLI output
    logger.info("Calculating Checksums (SHA256):") # For logs
    for fp in files_to_checksum:
        if fp.is_file(): # Make sure it's a file
            content = ''
            try:
                # Read with universal newlines mode, then normalize to LF for checksum consistency
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Normalize newlines to LF ('\n') before checksumming
                content_normalized = content.replace('\r\n', '\n').replace('\r', '\n')

                chksum = hashlib.sha256(content_normalized.encode('utf-8')).hexdigest()
                # Output for easy copy-pasting into EXPECTED_CHECKSUMS dict
                checksum_output_line = f'"{fp.name}": "{chksum}",'
                print(checksum_output_line)
                logger.info(f"  {checksum_output_line}")
            except Exception as e:
                error_msg = f"Error checksumming {fp.name}: {e}"
                print(error_msg)
                logger.error(error_msg, exc_info=True)
        else:
            not_found_msg = f"File not found or is not a file: {fp}"
            print(not_found_msg)
            logger.warning(not_found_msg)

logger.info("Main operational functions (main_migrate, generate_migration_script, calculate_checksums) appended.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Manage database migrations for the Flask application.",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )

    # Use subparsers to define actions like 'migrate', 'generate', 'checksum'
    subparsers = parser.add_subparsers(
        dest='action',
        help="Action to perform. Use '<action> --help' for more details on specific actions.",
        required=True # Python 3.7+ makes dest required if subparsers are used
    )

    # --- migrate action ---
    migrate_parser = subparsers.add_parser(
        'migrate',
        help="Apply pending migrations to the database to bring it to the latest version ('head').",
        description="This action will connect to the database, ensure migration scripts are correctly in place, and then run 'alembic upgrade head'. It handles stamping for uninitialized databases."
    )
    migrate_parser.add_argument(
        '--interactive',
        action='store_true',
        help="Run in interactive mode (currently no specific interactive features, placeholder)."
    )

    # --- generate action ---
    generate_parser = subparsers.add_parser(
        'generate',
        help="Generate a new Alembic migration script based on detected model changes.",
        description="This action first ensures the database is up-to-date with current migrations, then runs 'alembic revision --autogenerate -m <message>'. The generated script should be reviewed and then added to this script's MIGRATIONS_TO_APPLY list."
    )
    generate_parser.add_argument(
        '-m', '--message',
        required=True,
        help="Short descriptive message for the new migration script (e.g., 'add_user_bio_field'). This is used by Alembic for the filename."
    )

    # --- checksum action ---
    checksum_parser = subparsers.add_parser(
        'checksum',
        help="Calculate and print SHA256 checksums for migration script files.",
        description="Calculates SHA256 checksums for specified .py files in the versions directory, or all .py files if none are specified. Useful for updating EXPECTED_CHECKSUMS."
    )
    checksum_parser.add_argument(
        'filenames',
        nargs='*', # Zero or more filenames
        help="Optional: Specific filenames in the versions directory (e.g., '0001_...py'). If empty, checksums all .py files found there."
    )

    args = parser.parse_args()

    exit_code = 0
    if args.action == 'migrate':
        if not main_migrate(interactive_mode=args.interactive):
            logger.error("Migration process reported failure.")
            exit_code = 1
    elif args.action == 'generate':
        if not generate_migration_script(args.message):
            logger.error("Migration script generation reported failure.")
            exit_code = 1
    elif args.action == 'checksum':
        # calculate_checksums currently prints to stdout and logs, doesn't return success/fail
        # Assume success unless an exception occurs within it (which it should handle or log)
        try:
            calculate_checksums(args.filenames)
        except Exception as e:
            logger.error(f"Error during checksum calculation: {e}", exc_info=True)
            exit_code = 1
    else:
        # Should not happen if subparsers are 'required'
        logger.error(f"Unknown action: {args.action}")
        parser.print_help()
        exit_code = 1

    if exit_code == 0:
        logger.info(f"Action '{args.action}' completed successfully.")
    else:
        logger.error(f"Action '{args.action}' failed or completed with errors.")

    exit(exit_code)
