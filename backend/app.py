# Configure logging FIRST, so 'logger' is always available
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from flask import Flask, request, render_template_string, send_file, flash, redirect, url_for, session, g, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from wtforms import TextAreaField, SelectField, SubmitField, BooleanField, FileField # Import FileField
from wtforms.validators import DataRequired, Optional # Import Optional for file fields
from markupsafe import escape # Corrected import from marksafe to markupsafe
from docx import Document
from docx.shared import Inches # For setting margins
from docx.enum.text import WD_ALIGN_PARAGRAPH # For paragraph alignment
from docx.oxml.ns import qn # For font settings (though direct setting on runs is often easier)
from docx.shared import Pt # For font sizes
from docx.shared import RGBColor # For font colors, if needed (though not used in this iteration)
from docx.oxml.ns import nsdecls # For borders
from docx.oxml import OxmlElement # For borders
from io import BytesIO
import spacy # Re-importing spacy for fallback functionality
from collections import Counter
import os
import re
import traceback
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Set, Tuple, Optional as TypingOptional # Renamed to avoid conflict
from functools import wraps

from werkzeug.utils import secure_filename # Explicitly import secure_filename

# For language detection
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
    logger.info("langdetect imported successfully for language detection.")
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not found. Language detection will be disabled. Install with 'pip install langdetect'.")
except Exception as e:
    LANGDETECT_AVAILABLE = False
    logger.error(f"Error loading langdetect: {e}. Language detection will be disabled.")


# For IBM Watson NLU integration
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions
from ibm_cloud_sdk_core.authenticators import Authenticator
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator
from ibm_cloud_sdk_core.api_exception import ApiException

# For Gemini API integration (text generation and now translation)
import requests
import json
import google.generativeai as genai
import stripe


# For PDF text extraction (attempt pdfplumber first, then PyPDF2 as fallback)
import io # Ensure io is imported for file stream handling
import pdfplumber # Ensure pdfplumber is imported
import docx # For python-docx

PDFPLUMBER_AVAILABLE = False
PYPDF2_AVAILABLE = False
try:
    # import pdfplumber # Already imported above
    PDFPLUMBER_AVAILABLE = True # Assume available if import didn't raise error
    logger.info("pdfplumber imported successfully. Enhanced PDF extraction available.")
except ImportError: # This except block might be less relevant if pdfplumber is directly imported
    logger.warning("pdfplumber not found (this should not happen if import successful). Attempting PyPDF2 as fallback for PDF extraction.")
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
        logger.info("PyPDF2 imported successfully. Basic PDF extraction available.")
    except ImportError:
        logger.error("Neither pdfplumber nor PyPDF2 found. PDF text extraction will be disabled.")
    except Exception as e:
        logger.error(f"Error loading PyPDF2: {e}. PDF extraction will be disabled.")
except Exception as e:
    logger.error(f"Error loading pdfplumber: {e}. Attempting PyPDF2 as fallback.")
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
        logger.info("PyPDF2 imported successfully. Basic PDF extraction available.")
    except ImportError:
        logger.error("Neither pdfplumber nor PyPDF2 found. PDF text extraction will be disabled.")
    except Exception as e:
        logger.error(f"Error loading PyPDF2: {e}. PDF extraction will be disabled.")


# --- PDF Generation Library (WeasyPrint) ---
# Removed WeasyPrint dependency and associated PDF download functionality as requested.
# Users can use browser's "Print to PDF" option.


# Load environment variables
load_dotenv()
DOMAIN_URL = os.getenv('DOMAIN_URL', 'http://127.0.0.1:5000')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_STARTER_PRICE_ID = os.getenv("STRIPE_STARTER_PRICE_ID")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
STRIPE_CREDIT_PACK_PRICE_ID = os.getenv("STRIPE_CREDIT_PACK_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET_KEY

if STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith('sk_test_'):
    logger.info("Stripe SDK initialized with a test secret key.")
elif STRIPE_SECRET_KEY:
    logger.info("Stripe SDK initialized with a live secret key.")
else:
    logger.warning("Stripe secret key not found. Stripe integration will be disabled.")

if not STRIPE_PUBLISHABLE_KEY:
    logger.warning("Stripe publishable key not found. Frontend checkout might not work.")
if not STRIPE_STARTER_PRICE_ID or not STRIPE_PRO_PRICE_ID:
    logger.warning("Stripe Price IDs for Starter/Pro tiers not found. Subscription functionality will be affected.")
if not STRIPE_WEBHOOK_SECRET:
    logger.warning("Stripe Webhook Secret not found. Webhook verification will fail.")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-very-secret-key-for-dev')

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                         'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '../instance/site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress a warning

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128)) # Stores the hashed password
    tier = db.Column(db.String(50), nullable=False, default='free') # e.g., 'free', 'premium'
    stripe_customer_id = db.Column(db.String(120), nullable=True, unique=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True, unique=True)

    def __repr__(self):
        return f'<User {self.email}>'

# You will need to import Werkzeug security helpers later for password hashing,
# e.g., from werkzeug.security import generate_password_hash, check_password_hash
# And add methods to the User model like set_password and check_password.
# For now, this basic structure is sufficient for schema creation.

class UserCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    credits_remaining = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('credits', lazy=True, uselist=False)) # Define relationship

    def __repr__(self):
        return f'<UserCredit user_id={self.user_id} credits={self.credits_remaining}>'

class FeatureUsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False)
    credits_used = db.Column(db.Integer, nullable=False, default=0) # For features that might use variable credits
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('usage_logs', lazy=True)) # Define relationship

    def __repr__(self):
        return f'<FeatureUsageLog user_id={self.user_id} feature={self.feature_name} time={self.timestamp}>'

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
csrf = CSRFProtect(app)

# --- Tier Access Control Decorator ---
def tier_required(required_tiers):
    if isinstance(required_tiers, str):
        required_tiers = [required_tiers]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # --- SIMULATION: Get user tier ---
            # In a real app, this would come from flask_login's current_user or g.user
            # For simulation, we'll try request.args, then default to 'free'
            # This also means API-style POST requests need to pass it in form/json data for now
            simulated_user_tier = 'free' # Default
            if request.method == 'POST':
                if request.form and 'user_tier' in request.form:
                    simulated_user_tier = request.form.get('user_tier')
                elif request.is_json and request.json and 'user_tier' in request.json:
                    simulated_user_tier = request.json.get('user_tier')
                # else: check session if it were set during a login
            elif request.method == 'GET':
                    simulated_user_tier = request.args.get('user_tier', 'free')

            # Store it in g for potential use in the route, though direct passing might be cleaner
            g.user_tier = simulated_user_tier
            # --- END SIMULATION ---

            # TODO: SIMULATION - Replace with actual user authentication.
            # In a real application, `g.user_tier` and `g.simulated_user_id` (as g.user.id)
            # would be derived from a logged-in user session (e.g., using Flask-Login's current_user).
            # The current method of getting tier/user_id from request parameters/body is for simulation purposes only
            # and is not secure for a production environment.
            # SIMULATION: Create a g.simulated_user_id for use in routes
            # This would typically be g.user.id from a logged-in user object
            if request.method == 'POST':
                g.simulated_user_id = request.form.get('user_id_simulation') if request.form else None
                if not g.simulated_user_id and request.is_json:
                    g.simulated_user_id = request.json.get('user_id_simulation') if request.json else None
            elif request.method == 'GET':
                g.simulated_user_id = request.args.get('user_id_simulation')

            if not g.simulated_user_id: # Fallback if not provided in request
                g.simulated_user_id = 'simulated_user_for_credits'
            # Ensure g.user_tier is also set as before
            g.user_tier = simulated_user_tier

            # Tier hierarchy: Pro includes Starter, Starter includes Free (conceptually for access)
            allowed = False
            if 'pro' in required_tiers and simulated_user_tier == 'pro':
                allowed = True
            elif 'starter' in required_tiers and simulated_user_tier in ['starter', 'pro']:
                allowed = True
            elif 'free' in required_tiers and simulated_user_tier in ['free', 'starter', 'pro']: # Anyone can access free features
                allowed = True

            # Specific check: If 'free' is the ONLY required tier, then only 'free' users (not paying users)
            # This is unlikely for this app, usually higher tiers get lower tier features.
            # The logic above already handles "at least X tier".

            if not allowed:
                # For API endpoints, return JSON error
                if request.blueprint or any(ep_path in request.path for ep_path in ['/analyze_resume', '/match_job', '/check_ats', '/translate_resume', '/get_smart_suggestions', '/get_job_market_insights', '/generate_cover_letter']):
                    return jsonify({"error": f"This feature requires one of the following tiers: {', '.join(required_tiers)}. Your current tier is '{simulated_user_tier}'."}), 403
                else: # For HTML pages, flash and redirect
                    flash(f"This feature requires one of the following tiers: {', '.join(required_tiers)}. Please upgrade. (Your simulated tier: '{simulated_user_tier}')", "error")
                    return redirect(url_for('index')) # Or a dedicated pricing page
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def serve_homepage():
    frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
    return send_from_directory(frontend_dir, 'new_homepage.html')

@app.route('/static/<path:path>')
def serve_frontend_static_file(path):
    static_dir = os.path.join(os.path.dirname(__file__), '../frontend/static')
    return send_from_directory(static_dir, path)

@app.route('/<path:filename>')
def serve_frontend_file(filename):
    frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
    # Basic security: prevent accessing files outside the intended frontend directory.
    if '..' in filename or filename.startswith('/'):
        abort(404)
    return send_from_directory(frontend_dir, filename)

@app.route('/contact.html')
def serve_contact_page():
    frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
    return send_from_directory(frontend_dir, 'contact.html')

@app.route('/submit_contact_form', methods=['POST'])
def handle_contact_submission():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # For now, just log the submission to the console.
        logger.info(f"Contact form submission received:")
        logger.info(f"  Name: {name}")
        logger.info(f"  Email: {email}")
        logger.info(f"  Message: {message}")

        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('serve_contact_page'))

    # Should not be reached if form method is POST and handled
    return redirect(url_for('serve_contact_page'))

# --- Jinja2 Custom Filter for strftime ---
@app.before_request
def setup_jinja_globals():
    """Register custom Jinja2 filter for datetime formatting."""
    if not hasattr(g, 'jinja_filters_setup'):
        def _jinja2_filter_datetime(value, fmt="%Y"):
            if value is None:
                return ""
            if isinstance(value, datetime):
                return value.strftime(fmt)
            return value

        app.jinja_env.filters['strftime'] = _jinja2_filter_datetime
        g.jinja_filters_setup = True


# --- IBM Watson NLP Configuration ---
WATSON_NLP_API_KEY = os.getenv('WATSON_NLP_API_KEY')
WATSON_NLP_URL = os.getenv('WATSON_NLP_URL')

nlu_client: TypingOptional[NaturalLanguageUnderstandingV1] = None # Using TypingOptional for type hint
WATSON_NLP_AVAILABLE = False
if WATSON_NLP_API_KEY and WATSON_NLP_URL:
    try:
        authenticator: Authenticator = IAMAuthenticator(WATSON_NLP_API_KEY)
        nlu_client = NaturalLanguageUnderstandingV1(
            version='2022-04-07',
            authenticator=authenticator
        )
        nlu_client.set_service_url(WATSON_NLP_URL)
        WATSON_NLP_AVAILABLE = True
        logger.info("Watson NLU client configured successfully.") # UPDATED
    except Exception as e:
        logger.error(f"Error configuring Watson NLU client: {e}") # UPDATED
        WATSON_NLP_AVAILABLE = False
else:
    logger.warning("Watson NLU API key or URL not found. Watson NLU features will be disabled.") # UPDATED

nlp = None # SpaCy will be loaded only if Watson NLP is not available.

# Common skills lists (can be expanded) - now industry-specific
ALL_TECHNICAL_SKILLS: Dict[str, Set[str]] = {
    'generic': {'microsoft office', 'data entry', 'customer service', 'project management', 'analysis'},
    'tech': {'python', 'java', 'sql', 'aws', 'docker', 'react', 'machine learning', 'api', 'git', 'agile', 'devops', 'kubernetes', 'node.js', 'javascript', 'html', 'css', 'c++', 'c#', 'php', 'ruby', 'cloud', 'cybersecurity', 'networks', 'rest', 'graphql', 'containerization', 'microservices', 'big data', 'nosql', 'rdbms', 'ci/cd', 'tdd', 'object-oriented programming', 'functional programming', 'linux', 'unix', 'windows server', 'virtualization', 'networking', 'security protocols', 'encryption', 'firewalls', 'vpn', 'sso', 'identity and access management', 'active directory', 'jira', 'confluence', 'tableau', 'power bi', 'excel vba', 'data warehousing', 'etl', 'apache kafka', 'spark', 'hadoop', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'computer vision', 'robotics', 'iot', 'blockchain', 'cryptography', 'qa testing', 'test automation', 'selenium', 'jenkins', 'ansible', 'chef', 'puppet', 'terraform', 'azure devops', 'gcp cloud run', 'lambda', 'ecs', 'ec2', 's3', 'rds', 'dynamodb', 'cognito', 'route 53', 'cloudwatch', 'cloudformation', 'sns', 'sqs', 'azure functions', 'azure ad', 'azure vm', 'azure blob storage', 'google compute engine', 'google kubernetes engine', 'google cloud storage', 'firestore', 'cloud spanner', 'bigquery', 'pub/sub', 'cloud kms'},
    'finance': {'financial analysis', 'accounting', 'auditing', 'excel', 'bloomberg terminal', 'risk management', 'valuation', 'investments', 'financial modeling', 'spss', 'quickbooks', 'sap erp', 'oracle financials', 'econometrics', 'derivative pricing', 'portfolio management', 'fixed income', 'equities', 'mergers and acquisitions', 'due diligence', 'compliance', 'regulatory reporting', 'anti-money laundering', 'kyc', 'fraud detection', 'financial planning', 'wealth management', 'tax preparation', 'irs regulations', 'corporate finance', 'private equity', 'hedge funds', 'venture capital', 'trading strategies', 'market research', 'data visualization', 'r', 'matlab', 'sas', 'stata'},
    'healthcare': {'patient care', 'medical records', 'electronic health records', 'hipaa', 'nursing', 'diagnosis', 'treatment', 'pharmacology', 'clinical research', 'medical coding', 'icd-10', 'cpt coding', 'health information systems', 'epic', 'cerner', 'meditech', 'radiology information systems', 'laboratory information systems', 'telemedicine', 'health policy', 'public health', 'epidemiology', 'biostatistics', 'medical terminology', 'anatomy', 'physiology', 'pathology', 'immunology', 'microbiology', 'molecular biology', 'genetics', 'clinical trials', 'drug development', 'fda regulations', 'gmp', 'glp', 'gcp', 'patient safety', 'infection control', 'wound care', 'critical care', 'emergency medicine', 'pediatrics', 'geriatrics', 'mental health', 'addiction treatment', 'rehabilitation', 'physical therapy', 'occupational therapy', 'speech therapy', 'dietetics', 'nutritional counseling', 'case management', 'discharge planning', 'health education', 'counseling', 'crisis intervention'},
    'marketing': {'digital marketing', 'seo', 'sem', 'social media', 'content creation', 'google analytics', 'crm', 'brand management', 'public relations', 'email marketing', 'market research', 'competitive analysis', 'consumer behavior', 'marketing strategy', 'campaign management', 'advertising', 'copywriting', 'graphic design', 'adobe creative suite', 'canva', 'video editing', 'youtube marketing', 'influencer marketing', 'affiliate marketing', 'ecommerce', 'shopify', 'magento', 'wordpress', 'salesforce marketing cloud', 'hubspot', 'mailchimp', 'adwords', 'facebook ads', 'instagram marketing', 'twitter marketing', 'linkedin marketing', 'tiktok marketing', 'community management', 'event planning', 'public speaking', 'negotiation', 'sales techniques', 'lead generation', 'customer relationship management', 'loyalty programs', 'data analysis', 'a/b testing', 'conversion rate optimization', 'ux/ui principles', 'storytelling', 'cross-cultural communication'},
    'legal': {'legal research', 'legal writing', 'litigation', 'contracts', 'regulatory compliance', 'westlaw', 'lexisnexis', 'case management', 'due diligence', 'corporate law', 'intellectual property', 'family law', 'criminal law', 'environmental law', 'employment law', 'real estate law', 'appellate advocacy', 'discovery', 'pleadings', 'motions', 'depositions', 'trial preparation', 'arbitration', 'mediation', 'client counseling', 'ethics', 'professional responsibility'}, # Added Legal
    'teaching_academic': {'curriculum development', 'classroom management', 'pedagogical methods', 'student assessment', 'educational technology', 'research methodology', 'grant writing', 'academic advising', 'mentoring', 'lesson planning', 'public speaking', 'data analysis', 'statistical analysis', 'qualitative research', 'quantitative research', 'lecturing', 'grading', 'course design', 'learning outcomes', 'student engagement', 'differentiated instruction', 'special education', 'adult education', 'online learning', 'learning management systems', 'blackboard', 'moodle', 'canvas'}, # Added Teaching/Academic
}

ALL_SOFT_SKILLS: Dict[str, Set[str]] = {
    'generic': {'communication', 'teamwork', 'problem solving', 'adaptability', 'leadership', 'critical thinking', 'creativity', 'time management', 'organization', 'interpersonal skills', 'attention to detail', 'flexibility', 'patience', 'integrity', 'work ethic', 'proactiveness', 'resourcefulness', 'collaboration', 'active listening', 'conflict resolution', 'emotional intelligence', 'decision making', 'negotiation', 'persuasion', 'presentation', 'public speaking', 'stress management', 'self-motivation', 'resilience', 'empathy', 'customer service', 'mentoring', 'coaching', 'delegation', 'strategic thinking', 'analytical thinking', 'innovation', 'organizational skills', 'project planning', 'report writing', 'research', 'data interpretation', 'troubleshooting'},
    'tech': {'collaboration', 'critical thinking', 'innovation', 'problem solving', 'communication', 'attention to detail', 'analytical skills', 'adaptability', 'team leadership', 'mentorship', 'documentation', 'agile mindset', 'logical reasoning', 'complex problem solving', 'debuggin', 'code review', 'technical writing', 'user empathy', 'cross-functional collaboration', 'system design', 'testing', 'quality assurance', 'data-driven decision making'},
    'finance': {'attention to detail', 'analytical thinking', 'ethics', 'negotiation', 'integrity', 'risk assessment', 'quantitative analysis', 'financial reporting', 'compliance', 'discretion', 'confidentiality', 'decision-making under pressure', 'strategic planning', 'market analysis', 'forecasting', 'budgeting', 'auditing', 'investment analysis', 'client relations', 'data accuracy', 'regulatory knowledge', 'problem-solving', 'structured thinking'},
    'healthcare': {'empathy', 'interpersonal skills', 'stress management', 'compassion', 'active listening', 'patient advocacy', 'confidentiality', 'ethical conduct', 'cultural competence', 'crisis management', 'critical thinking', 'decision making', 'communication (verbal and written)', 'documentation', 'teamwork', 'attention to detail', 'problem-solving', 'adaptability', 'professionalism', 'time management', 'organizational skills', 'counseling', 'health education', 'patient education', 'medical ethics', 'privacy'},
    'marketing': {'creativity', 'persuasion', 'presentation', 'networking', 'strategic thinking', 'storytelling', 'audience understanding', 'brand building', 'market analysis', 'campaign optimization', 'digital literacy', 'copywriting', 'visual communication', 'public speaking', 'salesmanship', 'customer engagement', 'relationship building', 'trend analysis', 'data interpretation', 'competitive analysis', 'innovative thinking', 'adaptability', 'problem-solving', 'cross-functional collaboration'},
    'legal': {'attention to detail', 'analytical skills', 'problem-solving', 'critical thinking', 'persuasion', 'active listening', 'client relations', 'time management', 'organizational skills', 'stress management', 'adaptability', 'professionalism', 'discretion', 'confidentiality', 'ethical decision-making', 'teamwork', 'communication'}, # Added Legal
    'teaching_academic': {'communication', 'public speaking', 'mentoring', 'critical thinking', 'problem solving', 'adaptability', 'creativity', 'time management', 'organization', 'interpersonal skills', 'patience', 'collaboration', 'active listening', 'feedback delivery', 'curiosity', 'intellectual rigor', 'empathy', 'presentation skills'}, # Added Teaching/Academic
}

# Basic synonym map for keyword normalization
SYNONYM_MAP: Dict[str, str] = {
    'aws': 'amazon web services',
    'microsoft azure': 'azure',
    'gcp': 'google cloud platform',
    'js': 'javascript',
    'ml': 'machine learning',
    'ai': 'artificial intelligence',
    'css3': 'css',
    'html5': 'html',
    'sql server': 'sql',
    'postgres': 'sql',
    'mysql': 'sql',
    'crm': 'customer relationship management',
    'erp': 'enterprise enterprise planning',
    'ux': 'user experience',
    'ui': 'user interface',
    'agile methodologies': 'agile',
    'scrum': 'agile',
    'kanban': 'agile',
    'jira': 'agile', # Often associated with agile project management
    'oop': 'object-oriented programming',
    'api': 'application programming interface',
    'rest': 'restful api',
    'nosql': 'no-sql',
    'rdbms': 'relational database management system',
    'ci/cd': 'continuous integration continuous delivery',
    'qa': 'quality assurance',
    'ehr': 'electronic health records',
    'e-commerce': 'ecommerce',
    'seo': 'search engine optimization',
    'sem': 'search engine marketing',
    'saas': 'software as a service',
    'paas': 'platform as a service',
    'iaas': 'infrastructure as a service',
    'bi': 'business intelligence',
    'etl': 'extract transform load',
    'ui/ux': 'user interface user experience',
    'devops': 'development operations',
    'itil': 'information technology infrastructure library',
    'pm': 'project management',
    'pmp': 'project management professional',
    'cfa': 'chartered financial analyst',
    'cpa': 'certified public accountant',
    'hr': 'human resources',
    'kpis': 'key performance indicators',
    'roi': 'return on investment',
    'gdpr': 'general data protection regulation',
    'ccpa': 'california privacy act',
}


# --- Keyword Extraction & Matching Functions (using IBM Watson NLU or SpaCy fallback) ---

def normalize_text(text: str) -> str:
    """Applies basic normalization and synonym replacement."""
    text = text.lower()
    for synonym, canonical in SYNONYM_MAP.items():
        # Use regex to replace whole words only
        text = re.sub(r'\b' + re.escape(synonym) + r'\b', canonical, text)
    return text

def extract_keywords_watson(text: str, max_keywords: int = 100) -> List[str]:
    """
    Extracts keywords and entities using IBM Watson Natural Language Understanding SDK.
    """
    global nlu_client
    if not WATSON_NLP_AVAILABLE or nlu_client is None or not text:
        logger.warning("IBM Watson NLU client is not configured or text is empty. Skipping Watson NLU keyword extraction.")
        return []

    text_to_analyze = text[:49000]

    try:
        response = nlu_client.analyze(
            text=text_to_analyze,
            features=Features(
                keywords=KeywordsOptions(limit=max_keywords, sentiment=False, emotion=False),
                entities=EntitiesOptions(limit=max_keywords, sentiment=False, emotion=False, mentions=False)
            )
        ).get_result()

        extracted_kws = set()
        if 'keywords' in response:
            for kw in response['keywords']:
                extracted_kws.add(normalize_text(kw['text']))

        if 'entities' in response:
            for entity in response['entities']:
                extracted_kws.add(normalize_text(entity['text']))

        return sorted(list(extracted_kws))[:max_keywords]

    except ApiException as e:
        logger.error(f"IBM Watson NLU SDK API error: {e.code} - {e.message}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Watson NLU SDK call: {e}")
        return []

def extract_keywords_spacy(text: str, max_keywords: int = 100) -> List[str]:
    """
    Enhanced keyword extraction with ranking, filtering, and normalization using SpaCy.
    Prioritizes nouns, proper nouns, verbs, and adjectives.
    """
    global nlp
    if not nlp or not text:
        logger.warning("SpaCy model is not loaded or text is empty. Skipping SpaCy keyword extraction.")
        return []

    text = normalize_text(text)
    doc = nlp(text)

    keywords = []
    for token in doc:
        if (not token.is_stop and
            not token.is_punct and
            not token.is_digit and
            token.is_alpha and
            len(token.text) > 2 and
            token.pos_ in ['NOUN', 'PROPN', 'VERB', 'ADJ', 'X']):

            if token.pos_ == 'PROPN' or token.text.istitle() or token.text.isupper():
                keywords.append(token.text.lower())
            else:
                keywords.append(token.lemma_)

    for i in range(len(doc) - 1):
        bigram = doc[i:i+2].text.lower()
        if bigram in SYNONYM_MAP:
            keywords.append(SYNONYM_MAP[bigram])
        elif bigram.replace('-', ' ') in SYNONYM_MAP:
            keywords.append(SYNONYM_MAP[bigram.replace('-', ' ')])

    for i in range(len(doc) - 2):
        trigram = doc[i:i+3].text.lower()
        if trigram in SYNONYM_MAP:
            keywords.append(SYNONYM_MAP[trigram])
        elif trigram.replace('-', ' ') in SYNONYM_MAP:
            keywords.append(SYNONYM_MAP[trigram.replace('-', ' ')])

    keyword_counts = Counter(keywords)
    common_undesirable_words = {'work', 'use', 'company', 'team', 'project', 'develop', 'manage', 'system', 'data', 'create', 'build', 'implement', 'lead', 'design', 'process', 'solution'}

    filtered_keywords = [
        kw for kw, count in keyword_counts.most_common(max_keywords * 2)
        if kw not in common_undesirable_words and len(kw) > 1
    ]

    return filtered_keywords[:max_keywords]


def match_resume_to_job(resume_text: str, job_description: str, industry: str) -> Dict:
    """
    Enhanced matching with keyword importance scoring and categorization.
    Uses IBM Watson NLU if available, otherwise falls back to SpaCy.
    """
    extracted_resume_keywords: List[str] = []
    extracted_job_keywords: List[str] = []

    if WATSON_NLP_AVAILABLE:
        logger.info("Using IBM Watson NLU for keyword extraction.")
        extracted_resume_keywords = extract_keywords_watson(resume_text, max_keywords=200)
        extracted_job_keywords = extract_keywords_watson(job_description, max_keywords=150)
    elif nlp: # Fallback to SpaCy if Watson is not available and SpaCy is loaded
        logger.info("Using SpaCy as fallback for keyword extraction.")
        extracted_resume_keywords = extract_keywords_spacy(resume_text, max_keywords=200)
        extracted_job_keywords = extract_keywords_spacy(job_description, max_keywords=150)
    else:
        logger.warning("Neither IBM Watson NLP nor SpaCy model is available. Cannot perform keyword analysis.")
        return {
            "matched_keywords": [],
            "missing_keywords": [],
            "match_score": 0,
            "missing_by_category": {'technical': [], 'soft': [], 'other': []}
        }

    # Get industry-specific skills
    technical_skills = ALL_TECHNICAL_SKILLS.get('generic', set()).union(ALL_TECHNICAL_SKILLS.get(industry, set()))
    soft_skills = ALL_SOFT_SKILLS.get('generic', set()).union(ALL_SOFT_SKILLS.get(industry, set()))

    resume_normalized = {normalize_text(kw) for kw in extracted_resume_keywords}
    job_normalized = {normalize_text(kw) for kw in extracted_job_keywords}

    # Calculate match metrics
    matched = sorted(list(resume_normalized.intersection(job_normalized)))
    missing = sorted(list(job_normalized.difference(resume_normalized)))

    # Avoid division by zero if job description has no keywords
    score = round((len(matched) / max(len(job_normalized), 1)) * 100, 2)

    # Categorize missing keywords for better suggestions
    categorized_missing = {
        'technical': [kw for kw in missing if kw in technical_skills],
        'soft': [kw for kw in missing if kw in soft_skills],
        'other': [kw for kw in missing if kw not in technical_skills and kw not in soft_skills]
    }

    return {
        "matched_keywords": matched,
        "missing_keywords": missing,
        "match_score": score,
        "missing_by_category": categorized_missing
    }


# --- Suggestion and Enhancement Functions ---

def suggest_insertions_for_keywords(missing_keywords: List[str], industry: str = 'generic') -> List[str]:
    """
    Generates suggestions based on categorized missing keywords.
    """
    suggestions = []

    # Get industry-specific skills for categorization
    technical_skills = ALL_TECHNICAL_SKILLS.get('generic', set()).union(ALL_TECHNICAL_SKILLS.get(industry, set()))
    soft_skills = ALL_SOFT_SKILLS.get('generic', set()).union(ALL_SOFT_SKILLS.get(industry, set()))

    tech_kws = [kw for kw in missing_keywords if kw in technical_skills]
    if tech_kws:
        suggestions.append(f"**Technical Skills:** Consider adding projects or experiences demonstrating proficiency in: {', '.join(tech_kws[:5])}.")

    soft_kws = [kw for kw in missing_keywords if kw in soft_skills]
    if soft_kws:
        suggestions.append(f"**Soft Skills:** Integrate examples illustrating your abilities in: {', '.join(soft_kws[:3])} using the STAR method.")

    other_kws = [kw for kw in missing_keywords if kw not in technical_skills and kw not in soft_skills]
    if other_kws:
        suggestions.append(f"**Keywords:** Look for opportunities to naturally incorporate terms like: {', '.join(other_kws[:4])} into your experience descriptions or summary.")

    if industry and industry != 'generic':
        suggestions.append(f"**Industry Tailoring:** Ensure all examples and descriptions are tailored to resonate specifically with the {industry} industry.")

    if not suggestions:
        suggestions.append("Great job! Your resume aligns well with the job description. Consider minor refinements for even stronger impact.")

    return suggestions

def _generate_descriptive_language_llm(prompt_text: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Calls the Gemini API to generate descriptive language based on a prompt.
    """
    # NOTE: If running locally outside Canvas, you may need to uncomment and set your API key here:
    api_key = "AIzaSyCHZBiMT8I6oFfHJloX_vvbDqvREfhyVOA"
    # api_key = "" # Leave empty for Canvas environment to inject API key automatically
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    chat_history = []
    chat_history.append({ # Changed .push() to .append()
        "role": "user",
        "parts": [{"text": prompt_text}]
    })

    payload = {"contents": chat_history}

    try:
        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            return generated_text.strip()
        else:
            logger.warning(f"LLM response did not contain expected content: {result}")
            return ""
    except requests.exceptions.Timeout:
        logger.error("Gemini API request timed out.")
        return ""
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Gemini API connection error: {e}")
        return ""
    except requests.exceptions.HTTPError as e:
        logger.error(f"Gemini API HTTP error: {e.response.status_code} - {e.response.text}")
        return ""
    except json.JSONDecodeError:
        logger.error("Gemini API returned invalid JSON response.")
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred during Gemini API call: {e}")
        return ""

def _translate_text_gemini(text: str, target_lang_code: str, source_lang_code: str = "auto") -> str:
    """
    Translates text using the Gemini API.
    """
    if not text or not target_lang_code:
        return text

    if source_lang_code == "auto":
        source_lang_phrase = "the original language"
    else:
        source_lang_phrase = f"'{source_lang_code}'"

    # Use a direct prompt for translation
    prompt = (
        f"Translate the following text from {source_lang_phrase} to '{target_lang_code}'. "
        "Maintain the original formatting, including bullet points, line breaks, "
        "and any bolded or emphasized text. Only provide the translated text. "
        "Do not add any conversational remarks or explanations.\n\n"
        f"Text to translate:\n```\n{text}\n```"
    )

    translated_text = _generate_descriptive_language_llm(prompt, model_name="gemini-2.0-flash")
    return translated_text if translated_text else text # Return original if translation fails

def apply_llm_enhancements(organized_sections: Dict[str, str], missing_keywords: List[str], industry: str) -> Dict[str, str]:
    """
    Applies LLM-generated enhancements to the organized resume sections.
    """
    modified_sections = organized_sections.copy()

    technical_skills = ALL_TECHNICAL_SKILLS.get('generic', set()).union(ALL_TECHNICAL_SKILLS.get(industry, set()))
    soft_skills = ALL_SOFT_SKILLS.get('generic', set()).union(ALL_SOFT_SKILLS.get(industry, set()))

    tech_kws_to_add = [kw for kw in missing_keywords if kw in technical_skills]
    soft_kws_to_add = [kw for kw in missing_keywords if kw in soft_skills]
    other_kws_to_add = [kw for kw in missing_keywords if kw not in technical_skills and kw not in soft_skills]

    if tech_kws_to_add:
        prompt = (
            f"Given these technical skills: {', '.join(tech_kws_to_add)}. "
            "Draft 1-2 concise, professional bullet points for a resume's 'Skills' or 'Experience' section. "
            "Focus on demonstrating application, not just listing. Use strong action verbs. "
            "Example: 'Developed software solutions utilizing Python, Java, and SQL for data management.'"
        )
        generated_tech_text = _generate_descriptive_language_llm(prompt)
        if generated_tech_text:
            target_section = 'skills' if 'skills' in modified_sections else 'experience'
            if target_section in modified_sections and modified_sections[target_section].strip():
                modified_sections[target_section] += f"\n• {generated_tech_text}"
            else:
                modified_sections[target_section] = f"• {generated_tech_text}"
            logger.info(f"Added technical skills enhancement: {generated_tech_text}")

    if soft_kws_to_add:
        prompt = (
            f"Given these soft skills: {', '.join(soft_kws_to_add)}. "
            "Draft 1-2 concise, professional bullet points for a resume's 'Experience' or 'Summary' section. "
            "Focus on demonstrating application through action verbs and outcomes. "
            "Example: 'Collaborated effectively in cross-functional teams to deliver projects ahead of schedule.'"
        )
        generated_soft_text = _generate_descriptive_language_llm(prompt)
        if generated_soft_text:
            target_section = 'experience' if 'experience' in modified_sections else 'summary'
            if target_section in modified_sections and modified_sections[target_section].strip():
                modified_sections[target_section] += f"\n• {generated_soft_text}"
            else:
                modified_sections[target_section] = f"• {generated_soft_text}"
            logger.info(f"Added soft skills enhancement: {generated_soft_text}")

    if other_kws_to_add:
        prompt = (
            f"Given these general keywords: {', '.join(other_kws_to_add)}. "
            "Draft 1-2 concise, professional sentences or bullet points for a resume's 'Summary' or 'Experience' section. "
            "Incorporate these terms naturally. "
            "Example: 'Utilized best practices in project management to ensure successful project delivery.'"
        )
        generated_other_text = _generate_descriptive_language_llm(prompt)
        if generated_other_text:
            target_section = 'summary' if 'summary' in modified_sections else 'experience'
            if target_section in modified_sections and modified_sections[target_section].strip():
                modified_sections[target_section] += f"\n{generated_other_text}" if target_section == 'summary' else f"\n• {generated_other_text}"
            else:
                modified_sections[target_section] = generated_other_text if target_section == 'summary' else f"• {generated_other_text}"
            logger.info(f"Added general keywords enhancement: {generated_other_text}")

    return modified_sections


def auto_insert_keywords(resume_text: str, missing_keywords: List[str], context: Dict = None) -> str:
    """
    A simple auto-insertion logic for missing keywords.
    Attempts to insert into an existing skills section or adds a new one.
    Note: This is largely superseded by apply_llm_enhancements for broader drafting.
    """
    if not missing_keywords:
        return resume_text

    keywords_to_add = sorted(list(set(missing_keywords)))
    insert_str = ", ".join(keywords_to_add[:10])

    skills_section_match = re.search(r'(?i)(^\s*skills\s*[:\n])([^\n]*)', resume_text, re.MULTILINE | re.DOTALL)

    if skills_section_match:
        header_text = skills_section_match.group(1)
        existing_skills_line = skills_section_match.group(2).strip()

        if existing_skills_line:
            replacement = f"{header_text}{existing_skills_line}, {insert_str}"
        else:
            replacement = f"{header_text}\n{insert_str}"

        return re.sub(r'(?i)(^\s*skills\s*[:\n])([^\n]*)', replacement, resume_text, count=1, flags=re.MULTILINE | re.DOTALL)

    return resume_text + f"\n\nSkills\n{'-'*6}\n{insert_str}"

def highlight_keywords_in_html(text: str, keywords: List[str]) -> str:
    """Highlights keywords in an HTML string."""
    highlighted_text = escape(text)
    for keyword in sorted(list(set(keywords)), key=len, reverse=True):
        normalized_keyword = normalize_text(keyword)
        highlighted_text = re.sub(
            r'\b(' + re.escape(normalized_keyword) + r')\b',
            r'<mark class="bg-yellow-300 text-yellow-900 rounded px-0.5 font-semibold">\1</mark>',
            highlighted_text,
            flags=re.IGNORECASE
        )
    return highlighted_text.replace('\n', '<br>')

def extract_quantifiable_achievements(experience_text: str) -> List[str]:
    """
    Extracts phrases that indicate quantifiable achievements from experience text.
    """
    if not experience_text:
        return []

    achievements = []
    patterns = [
        r"(?:increased|reduced|achieved|boosted|grew|saved|managed|generated|processed|delivered|improved|optimized|cut|accelerated|expanded|launched|developed|implemented)\s+.*?(?:by|to|over|up to|more than|exceeding)\s+[\d,\.]+\%?",
        r"[\d,\.]+\s*(?:million|thousand|k|m)?\s*\$?\s*\w+\s+(?:savings|revenue|projects|clients|transactions|users|views|sales|profits|efficiency|performance)",
        r"(?:led|headed|spearheaded|oversaw)\s+[\d,]+\s+(?:projects|teams|initiatives)",
        r"processed\s+[\d,]+\s+transactions",
        r"(?:improved|optimized)\s+[\w\s]+\s+efficiency\s+by\s+[\d,\.]+\%?",
    ]

    lines = re.split(r'\n[•*-]|\n\s{2,}[•*-]|\n\s{4,}', experience_text)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                achievements.append(line)
                break

    return list(set(achievements))

def extract_text_from_file(file_storage) -> str:
    """
    Extracts text from uploaded .txt, .docx, or .pdf files.
    """
    if not file_storage:
        return ""

    filename = secure_filename(file_storage.filename)
    file_extension = os.path.splitext(filename)[1].lower()

    text_content = ""
    file_bytes_io = BytesIO(file_storage.read()) # Read file content into BytesIO
    file_bytes_io.seek(0) # Rewind to the beginning

    if file_extension == '.txt':
        text_content = file_bytes_io.read().decode('utf-8')
    elif file_extension == '.docx':
        try:
            doc = Document(file_bytes_io)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            flash(f"Error extracting text from DOCX file: {e}", "error")
    elif file_extension == '.pdf':
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_bytes_io) as pdf:
                    for page in pdf.pages:
                        text_content += page.extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from PDF with pdfplumber: {e}")
                flash(f"Error extracting text from PDF (pdfplumber failed): {e}", "error")
                text_content = "" # Clear content to try fallback or signal failure
        elif PYPDF2_AVAILABLE:
            try:
                reader = PyPDF2.PdfReader(file_bytes_io)
                for page_num in range(len(reader.pages)):
                    text_content += reader.pages[page_num].extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from PDF with PyPDF2: {e}")
                flash(f"Error extracting text from PDF (PyPDF2 failed): {e}", "error")
        else:
            flash("PDF extraction libraries (pdfplumber, PyPDF2) are not installed. Cannot process PDF files.", "error")
            logger.warning("PDF extraction libraries not available.")
    else:
        flash("Unsupported file type. Please upload a .txt, .docx, or .pdf file.", "error")

    return text_content


# --- Flask Forms ---

# List of common languages for translation dropdown
COMMON_LANGUAGES = [
    ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('de', 'German'),
    ('zh', 'Chinese (Simplified)'), ('hi', 'Hindi'), ('ar', 'Arabic'), ('pt', 'Portuguese'),
    ('ru', 'Russian'), ('ja', 'Japanese'), ('ko', 'Korean'), ('it', 'Italian'),
    ('nl', 'Dutch'), ('sv', 'Swedish'), ('pl', 'Polish'), ('tr', 'Turkish')
]

class ResumeForm(FlaskForm):
    resume_text = TextAreaField(
        'Resume Content (Paste Here)',
        validators=[Optional()], # Make optional as file upload is an alternative
        render_kw={"rows": 10, "placeholder": "Paste your full resume text here...", "aria-label": "Resume Content Textarea"}
    )
    resume_file = FileField(
        'Or Upload Resume (TXT, DOCX, PDF)',
        validators=[Optional()], # Optional
        render_kw={"aria-label": "Resume File Upload"}
    )

    job_description = TextAreaField(
        'Job Description (Paste Here - Optional)',
        validators=[Optional()], # Make optional as file upload is an alternative
        render_kw={"rows": 7, "placeholder": "Paste the target job description here...", "aria-label": "Job Description Textarea"}
    )
    job_description_file = FileField(
        'Or Upload Job Description (TXT, DOCX, PDF - Optional)',
        validators=[Optional()], # Optional
        render_kw={"aria-label": "Job Description File Upload"}
    )

    industry = SelectField('Industry', choices=[
        ('generic', 'Generic/General'),
        ('tech', 'Technology/Software'),
        ('finance', 'Finance/Banking'),
        ('healthcare', 'Healthcare/Medical'),
        ('marketing', 'Marketing/Sales'),
        ('legal', 'Legal'),
        ('teaching_academic', 'Teaching / Academic'),
    ], default='tech', render_kw={"aria-label": "Select Industry Focus"})

    # New fields for multilingual support
    enable_translation = BooleanField('Translate Output', render_kw={"aria-label": "Enable translation of output"})
    target_language = SelectField('Translate Output To', choices=COMMON_LANGUAGES, validators=[Optional()], default='en', render_kw={"aria-label": "Select target language for translation"})

    insert_keywords = BooleanField('Automatically add missing keywords to resume text (simple insertion)', render_kw={"aria-label": "Auto-insert missing keywords"})
    highlight_keywords = BooleanField('Highlight job keywords in the preview', render_kw={"aria-label": "Highlight job keywords"})
    auto_draft_enhancements = BooleanField('Automatically draft and insert suggested enhancements (AI-powered)', render_kw={"aria-label": "Auto-draft suggested enhancements"})

    include_action_verb_list = BooleanField('Include Action Verb List', render_kw={"aria-label": "Include strong action verb list"})
    include_summary_best_practices = BooleanField('Include Resume Summary Tips', render_kw={"aria-label": "Include resume summary best practices"})
    include_ats_formatting_tips = BooleanField('Include ATS Formatting Tips', render_kw={"aria-label": "Include ATS formatting tips"})

    submit = SubmitField('Analyze and Optimize Resume', render_kw={"aria-label": "Analyze and Organize Resume Button"})


# --- Core Application Logic (Parsing, Previews, etc.) ---

def parse_contact_info(text: str) -> Dict[str, str]:
    """
    Parses contact information from the beginning of the resume text.
    """
    contact_info = {}
    search_area = "\n".join(text.split('\n')[:8])

    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', search_area)
    if email_match:
        contact_info['email'] = email_match.group(0)

    phone_match = re.search(r'(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)', search_area)
    if phone_match:
        contact_info['phone'] = phone_match.group(0)

    linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]{5,}\b', search_area)
    if linkedin_match:
        contact_info['linkedin'] = linkedin_match.group(0)

    lines = [line.strip() for line in search_area.split('\n') if line.strip()]
    for line in lines:
        if (1 < len(line.split()) < 5 and
            not re.search(r'\d', line) and
            not re.search(r'(@|\.com|linkedin\.com|phone|email)', line, re.IGNORECASE) and
            not re.search(r'(summary|experience|skills|education|profile)', line, re.IGNORECASE)):
            if 'name' not in contact_info:
                contact_info['name'] = line
            break

    return contact_info


def parse_resume(text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parses potentially disorganized resume text into structured sections and extracts contact info.
    """
    logger.info("Parsing and organizing resume text with enhanced logic.")
    if not text or not text.strip():
        return {}, {}

    contact_info_dict = parse_contact_info(text)

    lines_to_process = []
    original_lines = text.replace('\r\n', '\n').split('\n')
    for line in original_lines:
        is_contact_line = False
        for val in contact_info_dict.values():
            if val and val.lower() in line.lower():
                is_contact_line = True
                break
        if not is_contact_line:
            lines_to_process.append(line)

    processed_text = "\n".join(lines_to_process)

    filtered_lines = []
    for line in processed_text.split('\n'):
        line_stripped = line.strip()
        if (not line_stripped or
            len(line_stripped) < 5 or
            len(line_stripped) > 150 or
            re.search(r'(?:^\s*import\s+\w+)|(?:^\s*def\s+\w+\s*\(.*\):)|(?:^\s*class\s+\w+:)|(?:^\s*<[^>]+>)|(?:^(?:git|npm|pip|sudo)\s+)', line_stripped, re.IGNORECASE) or
            (re.search(r'http[s]?://[^\s]+', line_stripped, re.IGNORECASE) and not any(ci_val and ci_val in line_stripped for ci_val in contact_info_dict.values())) or
            re.search(r'(?:^[-=_]{3,}$)|(?:^your name here)|(?:^add description here)|(?:^quantify achievements)', line_stripped, re.IGNORECASE) or
            re.search(r'lorem ipsum', line_stripped, re.IGNORECASE)
        ):
            logger.debug(f"Filtered out potentially irrelevant line: {line_stripped}")
            continue
        filtered_lines.append(line_stripped)
    processed_text = "\n".join(filtered_lines)


    section_patterns = {
        'summary': r'(?i)^\s*(summary|professional summary|objective|profile|about me|career overview)\s*$',
        'experience': r'(?i)^\s*(experience|work experience|employment history|professional experience|career history|work history|job experience)\s*$',
        'education': r'(?i)^\s*(education|academic background|qualifications|academic history|scholastic history|courses|relevant coursework)\s*$',
        'skills': r'(?i)^\s*(skills|technical skills|core competencies|abilities|proficiencies|areas of expertise|skill set)\s*$',
        'projects': r'(?i)^\s*(projects|personal projects|portfolio|key projects|selected projects|project experience)\s*$',
        'awards': r'(?i)^\s*(awards\s*(?:&|and)?\s*recognition|awards|honors|achievements|distinctions|recognitions)\s*$',
        'certifications': r'(?i)^\s*(certifications|licenses|qualifications|professional certifications|licences)\s*$',
        'volunteer': r'(?i)^\s*(volunteer experience|community involvement|volunteering)\s*$',
        'publications': r'(?i)^\s*(publications|research\s*(?:&|and)?\s*publications|presentations|papers|research papers|published works|conference papers|journals)\s*$',
        'languages': r'(?i)^\s*(languages|linguistic skills)\s*$',
        'interests': r'(?i)^\s*(interests|hobbies|personal interests)\s*$',
        'references': r'(?i)^\s*(references|referees)\s*$',
        'research_experience': r'(?i)^\s*(research experience|research interests|research projects|academic research)\s*$',
        'professional_memberships': r'(?i)^\s*(professional affiliations|memberships|associations|professional organizations)\s*$',
        'presentations': r'(?i)^\s*(presentations|talks|invited talks|speaking engagements)\s*$',
        'patents': r'(?i)^\s*(patents|patent applications)\s*$',
        'grants': r'(?i)^\s*(grants|funding|fellowships)\s*$',
        'extracurriculars': r'(?i)^\s*(extracurricular activities|activities)\s*$',
        'coursework': r'(?i)^\s*(coursework|relevant courses)\s*$',
        'thesis': r'(?i)^\s*(thesis|dissertation)\s*$',
        'bar_admissions': r'(?i)^\s*(bar admissions|admissions)\s*$',
        'professional_development': r'(?i)^\s*(professional development|continuing education)\s*$',
    }

    current_section_name = 'unclassified'
    section_content_lines: Dict[str, List[str]] = {current_section_name: []}

    lines = [line.strip() for line in processed_text.split('\n')]

    for line in lines:
        if not line:
            continue

        found_header = False

        if line.isupper() and 2 < len(line) < 50:
            for name, pattern_regex in section_patterns.items():
                if re.match(pattern_regex, line):
                    current_section_name = name
                    section_content_lines.setdefault(current_section_name, [])
                    found_header = True
                    logger.debug(f"Identified ALL CAPS header: {line} -> {name}")
                    break
            if found_header:
                continue

        if not found_header:
            for name, pattern_regex in section_patterns.items():
                if re.match(pattern_regex, line):
                    current_section_name = name
                    section_content_lines.setdefault(current_section_name, [])
                    found_header = True
                    logger.debug(f"Identified header: {line} -> {name}")
                    break

        if not found_header:
            section_content_lines[current_section_name].append(line)

    sections = {}
    unclassified_content = "\n".join(section_content_lines.get('unclassified', []))
    if unclassified_content and len(unclassified_content) < 300:
        sections['summary'] = unclassified_content
    elif unclassified_content:
        sections['other'] = unclassified_content

    for name, content_list in section_content_lines.items():
        if name != 'unclassified' and content_list:
            sections[name] = "\n".join(content_list).strip()

    sections = {k: v for k, v in sections.items() if v}

    return contact_info_dict, sections

# Mapping for optimized header wording
HEADER_OPTIMIZATION_MAP: Dict[str, str] = {
    'summary': 'Summary',
    'professional summary': 'Summary',
    'objective': 'Summary',
    'profile': 'Summary',
    'about me': 'Summary',
    'career overview': 'Summary',
    'experience': 'Experience',
    'work experience': 'Experience',
    'employment history': 'Experience',
    'professional experience': 'Experience',
    'career history': 'Experience',
    'work history': 'Experience',
    'job experience': 'Experience',
    'education': 'Education',
    'academic background': 'Education',
    'qualifications': 'Education',
    'academic history': 'Education',
    'scholastic history': 'Education',
    'courses': 'Education',
    'relevant coursework': 'Education',
    'skills': 'Skills',
    'technical skills': 'Skills',
    'core competencies': 'Skills',
    'abilities': 'Skills',
    'proficiencies': 'Skills',
    'areas of expertise': 'Skills',
    'skill set': 'Skills',
    'projects': 'Projects',
    'personal projects': 'Projects',
    'portfolio': 'Projects',
    'key projects': 'Projects',
    'selected projects': 'Projects',
    'project experience': 'Projects',
    'awards': 'Awards & Recognition',
    'honors': 'Awards & Recognition',
    'achievements': 'Awards & Recognition',
    'distinctions': 'Awards & Recognition',
    'recognitions': 'Awards & Recognition',
    'certifications': 'Certifications',
    'licenses': 'Certifications',
    'professional certifications': 'Certifications',
    'licences': 'Certifications',
    'volunteer': 'Volunteer Experience',
    'volunteer experience': 'Volunteer Experience',
    'community involvement': 'Volunteer Experience',
    'volunteering': 'Volunteer Experience',
    'publications': 'Publications',
    'research': 'Publications',
    'presentations': 'Presentations',
    'papers': 'Publications',
    'research papers': 'Publications',
    'published works': 'Publications',
    'conference papers': 'Publications',
    'journals': 'Publications',
    'languages': 'Languages',
    'linguistic skills': 'Languages',
    'interests': 'Interests',
    'hobbies': 'Interests',
    'personal interests': 'Interests',
    'references': 'References',
    'referees': 'References',
    'research_experience': 'Research Experience',
    'research interests': 'Research Experience',
    'research projects': 'Research Experience',
    'academic research': 'Research Experience',
    'professional_memberships': 'Professional Memberships',
    'professional affiliations': 'Professional Memberships',
    'memberships': 'Professional Memberships',
    'associations': 'Professional Memberships',
    'professional organizations': 'Professional Memberships',
    'talks': 'Presentations',
    'invited talks': 'Presentations',
    'speaking engagements': 'Presentations',
    'patents': 'Patents',
    'patent applications': 'Patents',
    'grants': 'Grants',
    'funding': 'Grants',
    'fellowships': 'Grants',
    'extracurriculars': 'Extracurricular Activities',
    'extracurricular activities': 'Extracurricular Activities',
    'activities': 'Extracurricular Activities',
    'coursework': 'Relevant Coursework',
    'relevant courses': 'Relevant Coursework',
    'thesis': 'Thesis/Dissertation',
    'dissertation': 'Thesis/Dissertation',
    'bar_admissions': 'Bar Admissions',
    'professional_development': 'Professional Development',
    'other': 'Miscellaneous'
}


def organize_resume_data(contact_info: Dict, sections: Dict, additional_tips_content: List[str]) -> Tuple[str, Dict]:
    """
    Takes parsed sections and contact info and formats them into a clean, organized resume string and dictionary.
    """
    organized_text_list: List[str] = []
    organized_sections_dict: Dict[str, str] = {}

    section_order = [
        'contact', 'summary', 'experience', 'education', 'skills', 'projects',
        'research_experience', 'publications', 'presentations', 'awards', 'certifications', 'grants',
        'professional_memberships', 'bar_admissions', 'professional_development',
        'volunteer', 'languages', 'interests', 'references', 'extracurriculars', 'coursework', 'thesis', 'other'
    ]

    contact_header_lines = []
    if contact_info.get('name'):
        contact_header_lines.append(f"{contact_info['name']}")

    contact_details = []
    if contact_info.get('email'):
        contact_details.append(contact_info['email'])
    if contact_info.get('phone'):
        contact_details.append(contact_info['phone'])
    if contact_info.get('linkedin'):
        contact_details.append(contact_info['linkedin'])

    if contact_details:
        contact_header_lines.append(" | ".join(contact_details))

    if contact_header_lines:
        formatted_contact_content = "\n".join(contact_header_lines)
        organized_text_list.append(formatted_contact_content)
        organized_sections_dict['contact'] = formatted_contact_content

    for section_name_raw in section_order:
        content = sections.get(section_name_raw, '').strip()
        section_name_optimized = HEADER_OPTIMIZATION_MAP.get(section_name_raw, section_name_raw.replace('_', ' ').title())

        if section_name_raw == 'contact' or not content:
            continue

        formatted_content = ""

        if section_name_raw in ['experience', 'education', 'projects', 'volunteer', 'publications',
                                'research_experience', 'presentations', 'extracurriculars',
                                'bar_admissions', 'professional_development']:

            # Updated splitting pattern for job/education entries
            # This pattern attempts to be more robust by looking for common starting points of new entries:
            # - A line starting with multiple capitalized words (potential title/company)
            # - Followed by an optional line with location, and then a date range.
            # - Or just a distinct date range on its own line after potential title/company.
            # It allows for varying levels of spacing/newlines between entries.
            split_pattern = r'\n{2,}(?=\s*(?:' \
                            r'[A-Z][a-zA-Z\s,&\'-]+(?:(?:\s*\||\s*[-–]\s*)[A-Z][a-zA-Z\s,&\'-]+)*\s*\n\s*(?:[A-Z][a-zA-Z\s,&\'-]+\s*,\s*)?(?:\d{4}|\w+\s+\d{4})\s*[-–]\s*(?:present|\d{4}|today)' \
                            r'|' \
                            r'[A-Z][a-zA-Z\s,&\'-]+(?:(?:\s*\||\s*[-–]\s*)[A-Z][a-zA-Z\s,&\'-]+)*\s*\n\s*(?:[A-Z][a-zA-Z\s,&\'-]+(?:(?:\s*\||\s*[-–]\s*)[A-Z][a-zA-Z\s,&\'-]+)*\s*\n\s*)?(?:\d{4}|\w+\s+\d{4})\s*[-–]\s*(?:present|\d{4}|today)' \
                            r'|' \
                            r'(?:[A-Z][a-zA-Z\s,\'-]*\s*){1,5}(?:\s*\||\s*[-–])' \
                            r'))'

            entries = re.split(split_pattern, content)
            entries = [entry.strip() for entry in entries if entry.strip()]

            formatted_entries = []
            for entry in entries:
                entry_lines = [line.strip() for line in entry.strip().split('\n') if line.strip()]
                if not entry_lines:
                    continue

                # Logic to identify the main header and sub-bullets
                # The first non-empty line is assumed to be part of the header.
                # Look for date patterns on subsequent lines to extend the header.
                main_header_parts = []
                description_lines = []

                # Take the first line as part of the header
                if entry_lines:
                    main_header_parts.append(entry_lines[0])

                    # Iterate through subsequent lines to find location/date info
                    i = 1
                    while i < len(entry_lines):
                        current_line = entry_lines[i]
                        # Check for common date patterns (e.g., "Month Year - Present", "YYYY -今")
                        # or common location patterns like "City, State"
                        if re.search(r'(\d{4}|[A-Za-z]+\s+\d{4})\s*[-–]\s*(\d{4}|present|today|[A-Za-z]+\s+\d{4})', current_line, re.IGNORECASE) or \
                           re.search(r'[A-Za-z\s]+, [A-Z]{2}', current_line) or \
                           re.search(r'[A-Za-z\s]+, \w{2,}', current_line): # For full city, country/province
                            main_header_parts.append(current_line)
                            i += 1
                        else:
                            # Stop adding to header once a bullet point or non-header-like line is found
                            break
                    description_lines = entry_lines[i:] # The rest are description lines

                if main_header_parts:
                    joined_header = '\n'.join(main_header_parts) # Fix: Join outside f-string
                    formatted_entry_content = [f"**{joined_header}**"]
                else:
                    formatted_entry_content = []

                for desc_line in description_lines:
                    # Clean bullet points if present, then add our own
                    cleaned_desc_line = re.sub(r'^\s*[•*-]\s*', '', desc_line).strip()
                    if cleaned_desc_line:
                        formatted_entry_content.append(f"  • {cleaned_desc_line}")

                formatted_entries.append("\n".join(formatted_entry_content))
            formatted_content = "\n\n".join(formatted_entries)

        elif section_name_raw == 'skills':
            # Handle skills as a comma-separated list if they are line-separated initially
            if '\n' in content and not re.search(r',|\s\s+', content):
                cleaned_skills = [re.sub(r'^[•*-]\s*', '', s).strip() for s in content.split('\n')]
                formatted_content = ", ".join(filter(None, cleaned_skills))
            else:
                formatted_content = content

        else:
            lines = [line.strip() for line in content.split('\n')]
            formatted_lines = []
            for line in lines:
                if not line: continue
                # Preserve existing bullet points, or add one if line doesn't start with one
                if line.startswith(('•', '*', '-')):
                    cleaned_line = re.sub(r'^[•*-]\s*', '', line).strip()
                    formatted_lines.append(f"• {cleaned_line}")
                else:
                    formatted_lines.append(line)
            formatted_content = "\n".join(formatted_lines)

        organized_text_list.append(f"{section_name_optimized}\n" + "="*len(section_name_optimized) + "\n" + formatted_content)
        organized_sections_dict[section_name_raw] = formatted_content

    if additional_tips_content:
        tips_section_title = "Resume Optimization Tips"
        tips_content = "\n".join([f"• {tip}" for tip in additional_tips_content])
        organized_text_list.append(f"{tips_section_title}\n" + "="*len(tips_section_title) + "\n" + tips_content)
        organized_sections_dict['resume_optimization_tips'] = tips_content


    final_organized_text = "\n\n".join(organized_text_list)
    return final_organized_text.strip(), organized_sections_dict


def generate_enhanced_preview(contact_info: Dict, organized_sections: Dict, original_resume_html: str, match_data: Dict, highlight_keywords_flag: bool, detected_lang: str, target_lang: str) -> str:
    """Generates a professional HTML preview with side-by-side comparison."""
    if not organized_sections and not contact_info:
        return "<p class='text-gray-400 text-center py-8 font-inter'>No content to preview. Please paste your resume above.</p>"

    # Helper function for glassmorphism card style
    def get_glass_card_classes(extra_classes=""):
        # Adjusted for darker background: more opaque dark, subtle glowing border, distinct shadow
        return f"bg-gray-800 bg-opacity-70 backdrop-filter backdrop-blur-lg rounded-2xl shadow-xl border border-electric-cyan border-opacity-40 {extra_classes}"

    html_content = '<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">'

    # Left Pane: Original Resume (if available)
    html_content += f"""
    <div class="{get_glass_card_classes('p-6 sm:p-8 md:p-10')}">
        <h2 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-4 text-center border-b-2 border-neon-purple pb-2 font-sora">Original Resume</h2>
        <p class="text-sm text-secondary-light text-center mb-3 font-inter">Detected Language: <span class="font-semibold text-primary-light">{detected_lang.upper()}</span></p>
        <div class="bg-gray-900 bg-opacity-80 p-4 sm:p-6 rounded-lg text-gray-200 overflow-auto h-[450px] sm:h-[550px] text-sm sm:text-base whitespace-pre-wrap">
            {original_resume_html}
        </div>
    </div>
    """

    # Right Pane: Organized Resume Preview
    html_content += f"""
    <div class="{get_glass_card_classes('p-6 sm:p-8 md:p-10')}">
        <h2 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-4 text-center border-b-2 border-neon-purple pb-2 font-sora">Optimized Resume Preview</h2>
        <p class="text-sm text-secondary-light text-center mb-3 font-inter">Output Language: <span class="font-semibold text-primary-light">{target_lang.upper()}</span></p>
        <div class="bg-gray-900 bg-opacity-80 p-4 sm:p-6 rounded-lg text-gray-200 overflow-auto h-[450px] sm:h-[550px] text-sm sm:text-base">
    """

    # Custom rendering for the Contact/Header section
    if contact_info:
        html_content += '<section class="mb-6 text-center pb-4 border-b border-gray-700 border-opacity-70">'
        if contact_info.get('name'):
            # Text color adjusted to a brighter accent color
            html_content += f'<h1 class="text-3xl sm:text-4xl font-extrabold text-electric-cyan mb-2 font-sora">{escape(contact_info["name"])}</h1>'

        details = []
        if contact_info.get('email'):
            details.append(f'<a href="mailto:{escape(contact_info["email"])}" class="text-tech-blue hover:underline">{escape(contact_info["email"])}</a>')
        if contact_info.get('phone'):
            details.append(escape(contact_info["phone"]))
        if contact_info.get('linkedin'):
            details.append(f'<a href="{escape(contact_info["linkedin"])}" target="_blank" class="text-tech-blue hover:underline">{escape(contact_info["linkedin"])}</a>')

        if details:
            # Text color adjusted for dark readability
            separator_span = '<span class="text-gray-500 font-normal mx-2">|</span>'
            html_content += f"<p class=\"text-base sm:text-lg text-gray-400 font-inter\">{separator_span.join(details)}</p>"
        html_content += '</section>'

    def format_section_html(title_raw, content_html):
        if not content_html: return ""
        title_optimized = HEADER_OPTIMIZATION_MAP.get(title_raw, title_raw.replace('_', ' ').title())
        if title_raw == 'resume_optimization_tips':
             title_optimized = "Resume Optimization Tips"

        return f"""
        <section class="mb-5">
            <h4 class="text-xl sm:text-2xl font-bold text-neon-purple border-b border-tech-blue border-opacity-70 pb-2 mb-3 capitalize font-sora">{title_optimized}</h4>
            <div class="text-sm sm:text-base text-gray-300 leading-relaxed break-words font-inter" style="white-space: pre-line;">
                {content_html}
            </div>
        </section>
        """

    section_order_html = [
        'summary', 'experience', 'education', 'skills', 'projects',
        'research_experience', 'publications', 'presentations', 'awards', 'certifications', 'grants',
        'professional_memberships', 'bar_admissions', 'professional_development',
        'volunteer', 'languages', 'interests', 'references', 'extracurriculars', 'coursework', 'thesis', 'other',
        'resume_optimization_tips'
    ]

    for sec_name_raw in section_order_html:
        content_to_process = organized_sections.get(sec_name_raw)
        if content_to_process:
            processed_content_html = ""
            if highlight_keywords_flag and match_data:
                all_job_keywords = list(set(match_data.get('matched_keywords', []) + match_data.get('missing_keywords', [])))
                processed_content_html = highlight_keywords_in_html(content_to_process, all_job_keywords)
            else:
                temp_html_content = escape(content_to_process)
                # Strong text in electric cyan for visibility on dark background
                temp_html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong><span class="text-electric-cyan">\1</span></strong>', temp_html_content)
                # This complex regex handles both '  • ' and '• ' by converting them to proper HTML list items
                # It first converts '  • ' (indented bullet) to a nested list item
                temp_html_content = re.sub(r'^ {2}• (.*)$', r'  <ul class="list-disc ml-8"><li class="mb-1">\1</li></ul>', temp_html_content, flags=re.MULTILINE)
                # Then converts '• ' (top-level bullet) to a main list item
                temp_html_content = re.sub(r'^• (.*)$', r'<ul class="list-disc ml-4"><li class="mb-1">\1</li></ul>', temp_html_content, flags=re.MULTILINE)

                # Correct for multiple ul tags appearing on subsequent bullet lines
                # This ensures that a series of bullet points under one section are contained within a single <ul>.
                # Find all </ul><br>\n<ul...> patterns and replace them to merge lists.
                temp_html_content = re.sub(r'</ul>\s*<br>\s*<ul class="list-disc ml-4">', '', temp_html_content, flags=re.DOTALL)
                temp_html_content = re.sub(r'</ul>\s*<br>\s* <ul class="list-disc ml-8">', '', temp_html_content, flags=re.DOTALL)

                # Replace newline characters with <br> for general flow, but ensure they don't break list structure.
                # This step should be done after handling bullet points.
                processed_content_html = temp_html_content.replace('\n', '<br>')

            html_content += format_section_html(sec_name_raw, processed_content_html)

    html_content += '</div></div>' # Close organized resume and main grid container
    return html_content

def export_to_word(text: str):
    """
    Exports the given text to a Word document with professional formatting
    that aims to visually appear substantively similar to the live preview.
    """
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    default_font_name = 'Calibri'
    default_font_size = Pt(11)

    style = doc.styles['Normal']
    font = style.font
    font.name = default_font_name
    font.size = default_font_size
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(0)

    if 'Custom Heading 1' not in doc.styles:
        obj_styles = doc.styles
        new_style = obj_styles.add_style('Custom Heading 1', 1)
        new_style.base_style = obj_styles['Heading 1']
        new_style.font.size = Pt(14)
        new_style.font.bold = True
        new_style.font.name = default_font_name
        p_format = new_style.paragraph_format
        p_format.space_before = Pt(12)
        p_format.space_after = Pt(6)

        pPr = p_format._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        pPr.insert_element_before(pBdr, 'w:shd', 'w:tabs', 'w:suppressAutoHyphens', 'w:kinsoku', 'w:wordWrap', 'w:overflowPunct', 'w:topLinePunct', 'w:autoSpaceDN', 'w:autoSpaceDE', 'w:autoSpaceDZ', 'w:lvlText', 'w:lvlJc')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '12')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), '00FFFF') # Electric Cyan for consistency with GUI
        pBdr.append(bottom)

    if 'Custom Subheading' not in doc.styles:
        obj_styles = doc.styles
        new_style = obj_styles.add_style('Custom Subheading', 1)
        new_style.base_style = obj_styles['Normal']
        new_style.font.size = Pt(12)
        new_style.font.bold = True
        new_style.font.name = default_font_name
        new_style.paragraph_format.space_before = Pt(6)
        new_style.paragraph_format.space_after = Pt(3)

    def apply_default_run_style(run):
        run.font.name = default_font_name
        run.font.size = default_font_size

    sections_split = re.split(r'\n([A-Za-z &]+)\n=+\n', text)

    content_before_first_header = sections_split[0].strip()

    if content_before_first_header:
        contact_lines = content_before_first_header.split('\n')
        if contact_lines:
            name_paragraph = doc.add_paragraph(contact_lines[0].strip())
            name_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            name_run = name_paragraph.runs[0]
            name_run.font.size = Pt(24)
            name_run.bold = True
            name_run.font.name = default_font_name

            if len(contact_lines) > 1:
                details_paragraph = doc.add_paragraph(contact_lines[1].strip())
                details_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                details_run = details_paragraph.runs[0]
                details_run.font.size = Pt(10)
                details_run.font.name = default_font_name

            doc.add_paragraph(style='Normal').paragraph_format.space_after = Pt(12)

    for i in range(1, len(sections_split), 2):
        title = sections_split[i].strip()
        content = sections_split[i+1].strip()

        if title:
            heading = doc.add_paragraph(title, style='Custom Heading 1')

        if content:
            lines = content.split('\n')
            for j, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    if j > 0 and lines[j-1].strip():
                        doc.add_paragraph(style='Normal').paragraph_format.space_after = Pt(6)
                    continue

                if re.fullmatch(r'\*\*.*?\*\*', line_stripped):
                    subheading_text = line_stripped.strip('**').strip()
                    sub_heading_para = doc.add_paragraph(subheading_text, style='Custom Subheading')
                elif line_stripped.startswith('• '):
                    p = doc.add_paragraph(line_stripped[2:].strip(), style='List Bullet')
                    for run in p.runs:
                        apply_default_run_style(run)
                    p.paragraph_format.left_indent = Inches(0.25)
                    p.paragraph_format.first_line_indent = Inches(-0.25)
                    p.paragraph_format.space_after = Pt(3)
                elif line_stripped.startswith('  • '):
                    p = doc.add_paragraph(line_stripped[4:].strip(), style='List Bullet 2')
                    for run in p.runs:
                        apply_default_run_style(run)
                    p.paragraph_format.left_indent = Inches(0.5)
                    p.paragraph_format.first_line_indent = Inches(-0.25)
                    p.paragraph_format.space_after = Pt(3)
                else:
                    p = doc.add_paragraph(line_stripped, style='Normal')
                    for run in p.runs:
                        apply_default_run_style(run)

            doc.add_paragraph(style='Normal').paragraph_format.space_after = Pt(12)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


# --- HTML Template (defined as a multi-line string) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Revisume.ai</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Sora:wght@400;600;700&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        /* Custom Colors for Dark Mode */
        .bg-gradient-dark {
            background: linear-gradient(135deg, #1A1A2E 0%, #0F0F1A 100%); /* Dark blue-purple to very dark blue */
        }
        /* Primary accent colors - vibrant */
        .text-tech-blue { color: #007BFF; } /* Brighter, more accessible blue */
        .text-electric-cyan { color: #00D8FF; } /* Brighter cyan */
        .text-neon-purple { color: #8A2BE2; } /* Deeper purple */

        /* Neutral text colors for dark theme */
        .text-primary-light { color: #E0E0E0; } /* Light gray for main text */
        .text-secondary-light { color: #A0AEC0; } /* Medium-light gray for secondary text */

        /* Adjusted colors for dark background borders and highlights */
        .header-text-color { color: #00D8FF; } /* Electric Cyan for branding text */
        .border-accent-dark { border-color: #00D8FF; } /* Electric Cyan for borders */
        .text-strong-accent { color: #00FFFF; } /* Pure Cyan for strong text in preview */
        .text-highlight-score { color: #7D00FF; } /* Neon purple for scores */


        /* Font Families */
        .font-inter { font-family: 'Inter', sans-serif; }
        .font-sora { font-family: 'Sora', sans-serif; }
        .font-space-grotesk { font-family: 'Space Grotesk', sans-serif; }

        body {
            font-family: 'Inter', sans-serif;
            background-color: #1A1A2E; /* Fallback for gradient */
            color: #E0E0E0; /* Default text color for dark mode */
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        @media (min-width: 640px) { /* sm breakpoint */
            .container {
                padding: 1.5rem;
            }
        }
        @media (min-width: 1024px) { /* lg breakpoint */
            .container {
                padding: 2rem;
            }
        }

        /* Glassmorphism Effect for Dark Mode */
        .glass-card {
            background-color: rgba(26, 26, 46, 0.7); /* Darker, more opaque */
            backdrop-filter: blur(15px); /* Stronger blur for depth */
            border-radius: 1.25rem; /* Slightly more rounded */
            border: 1px solid rgba(0, 216, 255, 0.4); /* Brighter, more visible border */
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4); /* Stronger, dark shadow */
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
        }
        .glass-card-inner {
            background-color: rgba(15, 15, 26, 0.8); /* Very dark inner for contrast */
            border-radius: 1rem; /* Consistent rounding */
            border: 1px solid rgba(0, 216, 255, 0.2); /* Faint border */
        }

        /* Flash Messages - vibrant on dark */
        .flash-message {
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 0.75rem;
            font-weight: 600; /* Bolder for visibility */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            text-align: center;
            border-left: 5px solid;
            transition: all 0.3s ease-in-out;
            font-family: 'Sora', sans-serif;
        }
        .flash-message.error {
            color: #FF7043; /* Orange-red for error */
            background-color: rgba(255, 112, 67, 0.15);
            border-color: #FF7043;
        }
        .flash-message.success {
            color: #69F0AE; /* Light green for success */
            background-color: rgba(105, 240, 174, 0.15);
            border-color: #69F0AE;
        }
        .flash-message.info {
            color: #81D4FA; /* Light blue for info */
            background-color: rgba(129, 212, 250, 0.15);
            border-color: #81D4FA;
        }

        /* Custom scrollbar for textareas */
        textarea::-webkit-scrollbar {
            width: 8px;
        }
        textarea::-webkit-scrollbar-track {
            background: #2D3748; /* Dark track */
            border-radius: 10px;
        }
        textarea::-webkit-scrollbar-thumb {
            background: #007BFF; /* Tech blue thumb */
            border-radius: 10px;
        }
        textarea::-webkit-scrollbar-thumb:hover {
            background: #00D8FF; /* Electric cyan on hover */
        }

        /* Highlighted text in preview */
        mark {
            background-color: rgba(0, 255, 255, 0.3); /* Subtle cyan with alpha */
            color: #1A1A2E; /* Very dark text for contrast */
            border-radius: 0.3rem; /* Slightly more rounded highlight */
            padding: 0 0.3rem;
            font-weight: 700; /* Bolder highlight */
        }

        /* Buttons with glow effect */
        .btn-glow {
            position: relative;
            z-index: 1;
            overflow: hidden;
            border-radius: 9999px; /* Fully rounded */
        }
        .btn-glow::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at center, rgba(0,216,255,0.4), transparent 70%); /* Brighter glow */
            transition: transform 0.6s ease-out;
            transform: scale(0);
            z-index: -1;
            opacity: 0;
        }
        .btn-glow:hover::before {
            transform: scale(1);
            opacity: 1;
        }
        .btn-primary {
            background: linear-gradient(45deg, #007BFF, #00D8FF); /* Brighter gradient */
            color: white;
            transition: all 0.3s ease;
            font-family: 'Sora', sans-serif;
            font-weight: 700;
        }
        .btn-primary:hover {
            box-shadow: 0 0 20px rgba(0, 216, 255, 0.8); /* More prominent glow */
            transform: translateY(-3px);
        }
        .btn-download { /* For PDF/DOCX downloads */
            background: linear-gradient(45deg, #8A2BE2, #007BFF); /* Neon purple to Tech blue, cohesive */
            color: white;
            transition: all 0.3s ease;
            font-family: 'Sora', sans-serif;
            font-weight: 700;
        }
        .btn-download:hover {
            box-shadow: 0 0 20px rgba(138, 43, 226, 0.8); /* More prominent glow */
            transform: translateY(-3px);
        }
        .btn-disabled {
            background-color: #2D3748; /* Darker disabled background */
            color: #4A5568; /* Darker disabled text */
            cursor: not-allowed;
            box-shadow: none;
            font-family: 'Sora', sans-serif;
            font-weight: 600;
        }

        /* Specific styles for analysis cards for Dark Mode */
        .analysis-card {
            border-radius: 0.8rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); /* Stronger shadow on dark */
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease;
            background-color: rgba(26, 26, 46, 0.6); /* Semi-transparent dark blue-purple */
            border: 1px solid rgba(0, 216, 255, 0.2); /* Consistent light accent border */
            color: #E0E0E0; /* Light text */
        }
        .analysis-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        }

        .analysis-card-blue {
            border-left: 5px solid #007BFF;
        }
        .analysis-card-green {
            border-left: 5px solid #00D8FF;
        }
        .analysis-card-red {
            border-left: 5px solid #FF7043; /* Orange-red for errors/missing */
        }
        .analysis-card-yellow {
            border-left: 5px solid #FFEB3B; /* Yellow for suggestions */
        }
        .analysis-card-purple {
            border-left: 5px solid #8A2BE2;
        }

        .analysis-card h3 {
            color: #00D8FF; /* Electric cyan for headings within analysis cards */
            display: flex;
            align-items: center;
            font-family: 'Sora', sans-serif;
            font-weight: 700;
        }
        .analysis-card svg {
            color: #00FFFF; /* Pure Cyan for icons */
            filter: drop-shadow(0 0 5px rgba(0, 255, 255, 0.7)); /* Stronger icon glow */
        }
        .analysis-card ul li strong {
            color: #7D00FF; /* Neon purple for strong text in lists */
        }
        .analysis-card strong {
             font-weight: 700;
        }

        /* Checkbox styling - more integrated */
        input[type="checkbox"] {
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            display: inline-block;
            vertical-align: middle;
            width: 1.6rem;
            height: 1.6rem;
            border-radius: 0.35rem;
            border: 2px solid #007BFF; /* Tech blue border */
            background-color: rgba(0, 0, 0, 0.2); /* Slightly transparent dark */
            cursor: pointer;
            transition: background-color 0.2s, border-color 0.2s, box-shadow 0.2s;
        }

        input[type="checkbox"]:checked {
            background-color: #00D8FF; /* Electric cyan when checked */
            border-color: #00D8FF;
            box-shadow: 0 0 10px rgba(0, 216, 255, 0.8); /* Stronger glow */
        }

        input[type="checkbox"]:checked::after {
            content: '\\2713'; /* Checkmark character */
            color: #1A1A2E; /* Dark text for checkmark */
            font-size: 1.3rem;
            line-height: 1;
            display: block;
            text-align: center;
            margin-top: -1px;
        }

        input[type="checkbox"]:focus {
            outline: none;
            box-shadow: 0 0 0 4px rgba(0, 123, 255, 0.6); /* Tech blue focus ring */
        }

        /* Header (top part) adjustments for dark mode */
        header {
            background-color: rgba(15, 15, 26, 0.8); /* Darker translucent header */
            border-bottom: 1px solid rgba(0, 216, 255, 0.3); /* More visible cyan border */
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.3); /* Stronger shadow */
        }
        header h1 {
            color: #00D8FF; /* Electric cyan for logo text */
            font-weight: 700;
        }
        header nav ul li a {
            color: #E0E0E0; /* Light text for navigation links */
            font-weight: 500;
        }
        header nav ul li a:hover {
            color: #00FFFF; /* Pure Cyan on hover */
        }

        /* Footer adjustments for dark mode */
        footer {
            background-color: rgba(15, 15, 26, 0.8); /* Darker translucent footer */
            border-top: 1px solid rgba(0, 216, 255, 0.3); /* More visible cyan border */
            box-shadow: 0 -3px 15px rgba(0, 0, 0, 0.3); /* Stronger shadow */
        }
        footer p {
            color: #E0E0E0; /* Light text for footer */
            font-weight: 500;
        }
        footer p.text-gray-500 { /* For the sub-text "Crafted with AI..." */
            color: #A0AEC0; /* Medium-light gray for sub-text */
        }

    </style>
</head>
<body class="bg-gradient-dark font-inter min-h-screen flex flex-col">
    <header class="p-4 shadow-lg md:p-6">
        <div class="container flex flex-col sm:flex-row justify-between items-center text-center sm:text-left">
            <div class="flex items-center mb-2 sm:mb-0">
                <img src="/static/logo.png" alt="Revisume.ai Logo" class="h-10 sm:h-12 mr-3" onerror="this.onerror=null;this.src='https://placehold.co/48x48/1A1A2E/00D8FF?text=AI';">
                <h1 class="text-2xl sm:text-3xl font-space-grotesk font-bold header-text-color">Revisume.ai</h1>
            </div>
            <nav class="mt-2 sm:mt-0">
                <ul class="flex space-x-4 sm:space-x-6 text-base sm:text-lg">
                    <li><a href="#analyzer" class="hover:text-electric-cyan transition duration-300 ease-in-out font-medium text-primary-light">Analyzer</a></li>
                    <li><a href="#results" class="hover:text-electric-cyan transition duration-300 ease-in-out font-medium text-primary-light">Results</a></li>
                    <li><a href="#pricing-section" class="hover:text-electric-cyan transition duration-300 ease-in-out font-medium text-primary-light">Pricing</a></li>
                </ul>
            </nav>
            <!-- Conceptual User Status (for when real auth is added)
            <div class="text-sm text-secondary-light ml-auto">
                Logged in as: <span id="simulated-user-email">user@example.com</span>
                (Tier: <span id="simulated-user-tier">Free</span>) | Credits: <span id="simulated-user-credits">0</span>
                <button onclick="logout()" class="ml-2 text-tech-blue hover:underline">Logout</button>
            </div>
            -->
            <div class="text-sm text-secondary-light ml-auto p-2 bg-gray-700 rounded">
                SIMULATED: User: <input type="text" id="sim_user_id_input" value="user123" class="bg-gray-600 text-white text-xs p-1 rounded w-20">
                Tier:
                <select id="sim_tier_select" class="bg-gray-600 text-white text-xs p-1 rounded">
                    <option value="free">Free</option>
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                </select>
                <button onclick="updateSimulatedUserDisplay()" class="text-xs p-1 bg-tech-blue rounded hover:bg-electric-cyan">Set</button>
            </div>
        </div>
    </header>

    <main class="container py-6 sm:py-10 flex-grow">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-6 sm:mb-8">
                    {% for category, message in messages %}
                        <div class="flash-message {{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <div id="analyzer" class="glass-card p-6 sm:p-8 md:p-10 mb-10 sm:mb-12">
            <h2 class="text-3xl sm:text-4xl font-sora font-extrabold text-electric-cyan mb-4 sm:mb-6 text-center leading-tight">Optimize Your Resume for Success</h2>
            <p class="text-center text-secondary-light mb-6 sm:mb-8 max-w-2xl mx-auto text-base sm:text-lg">Paste your resume and an optional job description below, or upload files, for AI-powered analysis and optimization.</p>

            <form method="POST" enctype="multipart/form-data" class="space-y-6 sm:space-y-8">
                {{ form.csrf_token }}

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
                    <div>
                        {{ form.resume_text.label(class="block text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2") }}
                        {{ form.resume_text(class="w-full p-3 sm:p-4 rounded-lg shadow-inner focus:ring-electric-cyan focus:border-electric-cyan transition duration-200 resize-y glass-card-inner border border-electric-cyan border-opacity-30 text-primary-light placeholder-secondary-light", style="min-height: 160px;") }}
                        {% for error in form.resume_text.errors %}
                            <p class="text-red-400 text-sm mt-1">{{ error }}</p>
                        {% endfor %}
                        <div class="mt-4">
                            {{ form.resume_file.label(class="block text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2") }}
                            {{ form.resume_file(class="w-full text-primary-light text-sm p-3 sm:p-4 border rounded-lg cursor-pointer bg-gray-700 bg-opacity-60 border-electric-cyan border-opacity-30 focus:outline-none focus:border-electric-cyan glass-card-inner") }}
                            {% for error in form.resume_file.errors %}
                                <p class="text-red-400 text-sm mt-1">{{ error }}</p>
                            {% endfor %}
                            <p class="text-xs text-secondary-light mt-1">Accepted formats: TXT, DOCX, PDF</p>
                        </div>
                    </div>

                    <div>
                        {{ form.job_description.label(class="block text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2") }}
                        {{ form.job_description(class="w-full p-3 sm:p-4 rounded-lg shadow-inner focus:ring-electric-cyan focus:border-electric-cyan transition duration-200 resize-y glass-card-inner border border-electric-cyan border-opacity-30 text-primary-light placeholder-secondary-light", style="min-height: 160px;") }}
                        {% for error in form.job_description.errors %}
                            <p class="text-red-400 text-sm mt-1">{{ error }}</p>
                        {% endfor %}
                        <div class="mt-4">
                            {{ form.job_description_file.label(class="block text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2") }}
                            {{ form.job_description_file(class="w-full text-primary-light text-sm p-3 sm:p-4 border rounded-lg cursor-pointer bg-gray-700 bg-opacity-60 border-electric-cyan border-opacity-30 focus:outline-none focus:border-electric-cyan glass-card-inner") }}
                            {% for error in form.job_description_file.errors %}
                                <p class="text-red-400 text-sm mt-1">{{ error }}</p>
                            {% endfor %}
                            <p class="text-xs text-secondary-light mt-1">Accepted formats: TXT, DOCX, PDF</p>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6 items-start">
                    <div>
                        {{ form.industry.label(class="block text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2") }}
                        {{ form.industry(class="w-full p-3 sm:p-4 rounded-lg shadow-sm focus:ring-electric-cyan focus:border-electric-cyan transition duration-200 glass-card-inner border border-electric-cyan border-opacity-30 text-primary-light") }}
                    </div>
                    <div class="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2 sm:mt-0">
                        <div class="flex items-center space-x-3">
                            {{ form.insert_keywords(class="checkbox-custom") }}
                            {{ form.insert_keywords.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                        </div>
                        <div class="flex items-center space-x-3">
                            {{ form.highlight_keywords(class="checkbox-custom") }}
                            {{ form.highlight_keywords.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                        </div>
                        <div class="flex items-center space-x-3 col-span-full">
                            {{ form.auto_draft_enhancements(class="checkbox-custom") }}
                            {{ form.auto_draft_enhancements.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6 items-start pt-4 border-t border-accent-dark mt-6 sm:mt-8">
                    <div class="md:col-span-3 text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2">Multilingual Options:</div>
                    <div class="flex items-center space-x-3">
                        {{ form.enable_translation(class="checkbox-custom") }}
                        {{ form.enable_translation.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                    </div>
                    <div>
                        {{ form.target_language.label(class="block text-base sm:text-lg font-sora font-semibold text-secondary-light mb-2") }}
                        {{ form.target_language(class="w-full p-3 sm:p-4 rounded-lg shadow-sm focus:ring-electric-cyan focus:border-electric-cyan transition duration-200 glass-card-inner border border-electric-cyan border-opacity-30 text-primary-light") }}
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6 items-start pt-4 border-t border-accent-dark mt-6 sm:mt-8">
                    <div class="md:col-span-3 text-lg sm:text-xl font-sora font-semibold text-tech-blue mb-2">Include General Resume Tips:</div>
                    <div class="flex items-center space-x-3">
                        {{ form.include_action_verb_list(class="checkbox-custom") }}
                        {{ form.include_action_verb_list.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                    </div>
                    <div class="flex items-center space-x-3">
                        {{ form.include_summary_best_practices(class="checkbox-custom") }}
                        {{ form.include_summary_best_practices.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                    </div>
                    <div class="flex items-center space-x-3">
                        {{ form.include_ats_formatting_tips(class="checkbox-custom") }}
                        {{ form.include_ats_formatting_tips.label(class="text-base sm:text-lg text-secondary-light font-medium cursor-pointer") }}
                    </div>
                </div>

                <div class="text-center pt-4">
                    <button type="button" onclick="submitMainFormWithSimulation()" class="btn-glow btn-primary inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 font-bold rounded-full shadow-lg text-white text-lg sm:text-xl transition duration-300 ease-in-out transform hover:scale-105 w-full sm:w-auto">Analyze and Optimize Resume</button>
                </div>
            </form>
            <div class="mt-6 text-center text-sm text-secondary-light">
                <p><strong class="text-electric-cyan">Free Tier:</strong> Basic analysis, 1 "Quick ATS Check" (simulated monthly), limited suggestions.</p>
                <p><strong class="text-neon-purple">Starter Tier:</strong> Unlimited basic analysis & ATS Checks, Smart Bullet Points, 1 "Deep Dive" credit/month.</p>
                <p><strong class="text-tech-blue">Pro Tier:</strong> All Starter features, Unlimited "Deep Dives", AI Cover Letter drafts.</p>
            </div>
        </div>

          <div id="pricing-section" class="glass-card p-6 sm:p-8 md:p-10 my-10 sm:my-12">
              <h2 class="text-3xl sm:text-4xl font-sora font-extrabold text-electric-cyan mb-8 text-center">Our Plans</h2>
              <div class="grid md:grid-cols-3 gap-6">
                  <!-- Free Tier -->
                  <div class="border border-gray-700 rounded-lg p-6 bg-gray-800 bg-opacity-50">
                      <h3 class="text-2xl font-bold text-primary-light mb-2">Free</h3>
                      <p class="text-3xl font-bold text-electric-cyan mb-4">$0</p>
                      <ul class="space-y-2 text-secondary-light mb-6">
                          <li>✓ 1 Resume Upload + Quick ATS Check / month (simulated)</li>
                          <li>✓ Basic Job Match Suggestions</li>
                          <li>- Watermarked PDF Download (conceptual)</li>
                      </ul>
                      <button class="w-full btn-disabled p-3 rounded-lg">Current Plan (Simulated)</button>
                  </div>
                  <!-- Starter Tier -->
                  <div class="border border-gray-700 rounded-lg p-6 bg-gray-800 bg-opacity-50">
                      <h3 class="text-2xl font-bold text-primary-light mb-2">Starter</h3>
                      <p class="text-3xl font-bold text-neon-purple mb-4">$9 <span class="text-sm">/mo</span></p>
                      <ul class="space-y-2 text-secondary-light mb-6">
                          <li>✓ Unlimited Uploads & ATS Checks</li>
                          <li>✓ Full PDF/DOCX Exports</li>
                          <li>✓ Smart Bullet-Point Suggestions</li>
                          <li>✓ 1 "Deep Dive" AI Analysis Credit / month</li>
                      </ul>
                      <button onclick="redirectToCheckout(STRIPE_STARTER_PRICE_ID_JS_VAR)" class="w-full btn-glow btn-primary p-3 rounded-lg">Subscribe to Starter</button>
                  </div>
                  <!-- Pro Tier -->
                  <div class="border border-gray-700 rounded-lg p-6 bg-gray-800 bg-opacity-50">
                      <h3 class="text-2xl font-bold text-primary-light mb-2">Pro</h3>
                      <p class="text-3xl font-bold text-tech-blue mb-4">$19 <span class="text-sm">/mo</span></p>
                      <ul class="space-y-2 text-secondary-light mb-6">
                          <li>✓ All Starter Features</li>
                          <li>✓ Unlimited "Deep Dives"</li>
                          <li>✓ AI Cover Letter Drafts</li>
                          <li>✓ Priority Email Support (conceptual)</li>
                      </ul>
                      <button onclick="redirectToCheckout(STRIPE_PRO_PRICE_ID_JS_VAR)" class="w-full btn-glow btn-primary p-3 rounded-lg" style="background: linear-gradient(45deg, #8A2BE2, #007BFF);">Subscribe to Pro</button>
                  </div>
              </div>
              <div class="mt-8 text-center">
                  <h3 class="text-xl font-bold text-primary-light mb-3">Need More Credits?</h3>
                  <p class="text-secondary-light mb-4">Purchase additional "Deep Dive" credits for your Starter plan.</p>
                  <button onclick="redirectToCheckout(STRIPE_CREDIT_PACK_PRICE_ID_JS_VAR)" class="btn-glow btn-download px-6 py-3 rounded-lg">Buy 5 Credits for $10</button>
              </div>
          </div>

        {% if preview %}
            <div id="results" class="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-10 mb-10 sm:mb-12">
                <!-- Resume Previews Section (Left and Right) -->
                <div class="lg:col-span-2">
                    {{ preview | safe }} {# This now contains the two-column layout #}
                </div>

                <!-- Analysis & Suggestions Section (Bottom) -->
                <div class="lg:col-span-2 glass-card p-6 sm:p-8 md:p-10">
                    <h2 class="text-3xl sm:text-4xl font-sora font-extrabold text-electric-cyan mb-4 sm:mb-6 text-center leading-tight">Analysis & Suggestions</h2>

                    {% if match_data %}
                        <div class="mb-6 p-4 sm:p-6 rounded-lg shadow-md analysis-card analysis-card-blue">
                            <h3 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-3 flex items-center">
                                <svg class="w-7 h-7 sm:w-8 sm:h-8 text-electric-cyan mr-2 sm:mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                                Job Match Score: <span class="text-highlight-score ml-2 text-2xl sm:text-3xl">{{ match_data.match_score }}%</span>
                            </h3>
                            <p class="text-primary-light text-sm sm:text-base font-inter">This score indicates how well your resume's keywords align with the job description's requirements. Aim for a higher score!</p>
                        </div>

                        <div class="mb-6 p-4 sm:p-6 rounded-lg shadow-md analysis-card analysis-card-green">
                            <h3 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-3 flex items-center">
                                <svg class="w-7 h-7 sm:w-8 sm:h-8 text-electric-cyan mr-2 sm:mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                Matched Keywords ({{ match_data.matched_keywords|length }}):
                            </h3>
                            <p class="text-primary-light break-words text-sm sm:text-base font-inter">{{ match_data.matched_keywords|join(', ') if match_data.matched_keywords else 'No direct matches found. Try refining your resume or the job description.' }}</p>
                        </div>

                        <div class="mb-6 p-4 sm:p-6 rounded-lg shadow-md analysis-card analysis-card-red">
                            <h3 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-3 flex items-center">
                                <svg class="w-7 h-7 sm:w-8 sm:h-8 text-electric-cyan mr-2 sm:mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                                Missing Keywords ({{ match_data.missing_keywords|length }}):
                            </h3>
                            {% if match_data.missing_by_category %}
                                <ul class="list-disc list-inside text-primary-light space-y-2 text-sm sm:text-base font-inter">
                                    {% if match_data.missing_by_category.technical %}
                                        <li><strong>Technical:</strong> <span class="break-words">{{ match_data.missing_by_category.technical|join(', ') }}</span></li>
                                    {% endif %}
                                    {% if match_data.missing_by_category.soft %}
                                        <li><strong>Soft Skills:</strong> <span class="break-words">{{ match_data.missing_by_category.soft|join(', ') }}</span></li>
                                    {% endif %}
                                    {% if match_data.missing_by_category.other %}
                                        <li><strong>Other:</strong> <span class="break-words">{{ match_data.missing_by_category.other|join(', ') }}</span></li>
                                    {% endif %}
                                </ul>
                            {% else %}
                                <p class="text-primary-light text-sm sm:text-base font-inter">No missing keywords! Your resume is highly aligned with the job description.</p>
                            {% endif %}
                        </div>
                    {% else %}
                        <p class="text-primary-light text-center py-6 text-base sm:text-lg font-inter">Paste a job description to get a detailed keyword analysis and match score.</p>
                    {% endif %}

                    {% if insert_recs %}
                        <div class="mb-6 p-4 sm:p-6 rounded-lg shadow-md analysis-card analysis-card-yellow">
                            <h3 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-3 flex items-center">
                                <svg class="w-7 h-7 sm:w-8 sm:h-8 text-electric-cyan mr-2 sm:mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.325 5.586a1 1 0 00-1.414-1.414L13.21 5.394a1 1 0 101.414 1.414l.707-.707zM17 10a1 1 0 00-2 0v1a1 1 0 102 0v-1zM14.636 14.636a1 1 0 001.414 1.414l.707-.707a1 1 0 10-1.414-1.414l-.707.707zM10 15a1 1 0 100 2h1a1 1 0 100-2h-1zM5.364 14.636a1 1 0 00-1.414-.707l-.707.707a1 1 0 101.414 1.414l.707-.707zM3 11a1 1 0 102 0v-1a1 1 0 10-2 0v1zM4.675 5.586a1 1 0 00-.707-.707l-.707.707a1 1 0 001.414 1.414l.707-.707z"></path></svg>
                                Enhancement Suggestions:
                            </h3>
                            <ul class="list-disc list-inside text-primary-light space-y-2 text-sm sm:text-base font-inter">
                                {% for rec in insert_recs %}
                                    <li>{{ rec | safe }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    {% endif %}

                    {% if quantifiable_achievements %}
                        <div class="mb-6 p-4 sm:p-6 rounded-lg shadow-md analysis-card analysis-card-purple">
                            <h3 class="text-xl sm:text-2xl font-bold text-electric-cyan mb-3 flex items-center">
                                <svg class="w-7 h-7 sm:w-8 sm:h-8 text-electric-cyan mr-2 sm:mr-3" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M3 3a1 1 0 000 2h11a1 1 0 100-2H3zm0 4a1 1 0 000 2h7a1 1 0 100-2H3zm0 4a1 1 0 100 2h4a1 1 0 100-2H3zm0 4a1 1 0 100 2h11a1 1 0 100-2H3z" clip-rule="evenodd"></path></svg>
                                Potential Quantifiable Achievements:
                            </h3>
                            <p class="text-primary-light mb-3 text-sm sm:text-base font-inter">Review these phrases from your experience section. Ensure they highlight your impact with numbers and strong action verbs!</p>
                            <ul class="list-disc list-inside text-primary-light space-y-1 text-sm sm:text-base font-inter">
                                {% for achievement in quantifiable_achievements %}
                                    <li>{{ achievement }}</li>
                                {% endfor %}
                            </ul>
                            <p class="text-secondary-light text-xs sm:text-sm mt-3 font-inter">Example: "Increased sales by 15% ($50K) in Q3 2023."</p>
                        </div>
                    {% endif %}

                    <div class="text-center mt-6 sm:mt-10 space-y-4 sm:space-x-4 flex flex-col sm:flex-row justify-center items-center">
                        {% if word_available %}
                            <a href="{{ url_for('download_word') }}" class="btn-glow btn-download inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 font-bold rounded-full shadow-lg text-white text-base sm:text-lg transition duration-300 ease-in-out transform hover:scale-105 w-full sm:w-auto">
                                Download DOCX
                            </a>
                        {% else %}
                            <button disabled class="btn-disabled inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 font-bold rounded-full shadow-md text-base sm:text-lg w-full sm:w-auto">
                                Download DOCX
                            </button>
                        {% endif %}

                        <button disabled class="btn-disabled inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 font-bold rounded-full shadow-md text-base sm:text-lg w-full sm:w-auto">
                            Download PDF (Unavailable)
                        </button>
                        <p class="text-sm text-secondary-light mt-2 text-center sm:text-left w-full sm:w-auto font-inter">To download as PDF, please use your browser's "Print to PDF" option from the preview, or download the DOCX file.</p>
                    </div>
                </div>
            </div>
        {% endif %}
    </main>

    <footer class="p-4 text-center mt-auto md:p-6">
        <div class="container">
            <p class="text-base sm:text-lg font-sora text-primary-light">&copy; {{ now | strftime('%Y') }} Revisume.ai. All rights reserved.</p>
            <p class="text-xs sm:text-sm mt-2 text-secondary-light font-inter">Crafted with cutting-edge AI for your career success. 🚀</p>
        </div>
    </footer>
    <script>
        // Make Stripe Price IDs available to JS (these will be {{ ... }} in Flask template)
        const STRIPE_STARTER_PRICE_ID_JS_VAR = "{{ STRIPE_STARTER_PRICE_ID_TEMPLATE_VAR }}";
        const STRIPE_PRO_PRICE_ID_JS_VAR = "{{ STRIPE_PRO_PRICE_ID_TEMPLATE_VAR }}";
        const STRIPE_CREDIT_PACK_PRICE_ID_JS_VAR = "{{ STRIPE_CREDIT_PACK_PRICE_ID_TEMPLATE_VAR }}";

        let currentSimulatedUserId = 'user123'; // Default
        let currentSimulatedTier = 'free';

        function updateSimulatedUserDisplay() {
            currentSimulatedUserId = document.getElementById('sim_user_id_input').value || 'user123';
            currentSimulatedTier = document.getElementById('sim_tier_select').value || 'free';
            // Could update a visible display here if one existed like the commented out one
            console.log(`Simulated User ID set to: ${currentSimulatedUserId}, Tier: ${currentSimulatedTier}`);
            alert(`Simulated user set to ID: ${currentSimulatedUserId}, Tier: ${currentSimulatedTier}. Some features might require form resubmission or page reload to reflect changes in simulated server-side checks.`);
        }

        async function redirectToCheckout(priceId) {
            if (!priceId || priceId.includes("YOUR_")) {
                alert("Stripe Price ID is not configured correctly for this button.");
                return;
            }
            console.log(`Redirecting to checkout for price_id: ${priceId} and user: ${currentSimulatedUserId}`);
            try {
                const response = await fetch('/create-checkout-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ price_id: priceId, user_id_simulation: currentSimulatedUserId })
                });
                const session = await response.json();
                if (session.url) {
                    window.location.href = session.url;
                } else if (session.error) {
                    alert('Error creating checkout session: ' + session.error);
                    console.error('Checkout session error:', session.error);
                }
            } catch (error) {
                alert('Failed to initiate checkout. See console for details.');
                console.error('redirectToCheckout error:', error);
            }
        }

        // Placeholder for feature access simulation or actual API calls with simulated data
        async function simulateFeatureAccess(requiredTier, featureName) {
            alert(`Simulating access to '${featureName}' for tier '${currentSimulatedTier}'. Required: '${requiredTier}'.`);
            // Example: try to call an actual endpoint with simulated data
            if (featureName === 'generate_cover_letter') {
                try {
                    const response = await fetch('/generate_cover_letter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id_simulation: currentSimulatedUserId, user_tier: currentSimulatedTier, some_data: 'test' })
                    });
                    const result = await response.json();
                    alert(JSON.stringify(result));
                } catch (error) {
                    console.error('Error simulating feature access:', error);
                    alert('Error calling feature endpoint.');
                }
            }
        }

        // Function to handle the main form submission with simulated data
        function submitMainFormWithSimulation() {
              const formElement = document.querySelector('form'); // Assumes one main form
              if (!formElement) {
                  alert('Main form not found!');
                  return;
              }
              // Add simulated tier and user_id as hidden inputs before submitting
              let tierInput = formElement.querySelector('input[name="user_tier"]');
              if (!tierInput) {
                  tierInput = document.createElement('input');
                  tierInput.type = 'hidden';
                  tierInput.name = 'user_tier';
                  formElement.appendChild(tierInput);
              }
              tierInput.value = currentSimulatedTier;

              let userIdInput = formElement.querySelector('input[name="user_id_simulation"]');
              if (!userIdInput) {
                  userIdInput = document.createElement('input');
                  userIdInput.type = 'hidden';
                  userIdInput.name = 'user_id_simulation';
                  formElement.appendChild(userIdInput);
              }
              userIdInput.value = currentSimulatedUserId;

              // Now submit the form
              // formElement.submit(); // This would be a full page reload
              // Instead, for SPA-like feel with current setup, it might be better to handle via fetch if index() POST can return JSON.
              // For now, alert and log. The tier_required decorator on POST index() isn't implemented yet.
              // alert(`Main form would be submitted with User ID: ${currentSimulatedUserId}, Tier: ${currentSimulatedTier}. This part needs backend handling on the main form route.`);
              // console.log(`Submitting main form with User ID: ${currentSimulatedUserId}, Tier: ${currentSimulatedTier}`);
              // Actually, the main index() POST doesn't have tier checks yet.
              // The feature-specific API calls like /get_smart_suggestions are separate.
              // So, this function might not be strictly needed if main form processing is always "free" for the initial parse.
              // Let's keep it for now for completeness of simulation.
              formElement.submit(); // Proceed with actual form submission for now
        }

        // Initialize simulated user display on load
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('sim_user_id_input').value = currentSimulatedUserId;
            document.getElementById('sim_tier_select').value = currentSimulatedTier;
        });

    </script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    global nlp
    if not WATSON_NLP_AVAILABLE:
        if nlp is None:
            try:
                _nlp_instance = spacy.load("en_core_web_sm")
                nlp = _nlp_instance
                logger.info("SpaCy model 'en_core_web_sm' loaded as fallback. Watson NLP was not available.")
            except OSError:
                logger.error("SpaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
                nlp = None
            except Exception as e:
                logger.error(f"Failed to load SpaCy model as fallback: {e}")
                nlp = None

        if not WATSON_NLP_AVAILABLE and nlp is None:
            flash("Neither IBM Watson NLP nor SpaCy model is loaded. Keyword analysis and advanced parsing will be disabled. Please configure IBM Watson NLP credentials or run: `python -m spacy download en_core_web_sm` to enable full features.", "error")
        elif not WATSON_NLP_AVAILABLE and nlp is not None:
            flash("IBM Watson NLP is not configured. Falling back to SpaCy for keyword analysis. For better results, configure WATSON_NLP_API_KEY and WATSON_NLP_URL.", "info")

    form = ResumeForm()
    preview = ""
    match_data = {}
    insert_recs = []
    quantifiable_achievements = []
    word_available = False
    original_resume_for_preview = ""
    detected_language = 'en' # Default
    target_language = 'en' # Default

    if form.validate_on_submit():
        try:
            resume_text = form.resume_text.data
            job_desc = form.job_description.data

            # Prioritize file uploads over pasted text
            if form.resume_file.data:
                uploaded_resume_text = extract_text_from_file(form.resume_file.data)
                if uploaded_resume_text:
                    resume_text = uploaded_resume_text
                else:
                    flash("Failed to extract text from uploaded resume file. Please check file format or try pasting text.", "error")
                    return redirect(url_for('index'))

            if form.job_description_file.data:
                uploaded_job_desc_text = extract_text_from_file(form.job_description_file.data)
                if uploaded_job_desc_text:
                    job_desc = uploaded_job_desc_text
                else:
                    flash("Failed to extract text from uploaded job description file. Please check file format or try pasting text.", "error")
                    return redirect(url_for('index'))

            # Ensure there's content to process
            if not resume_text or not resume_text.strip():
                flash("Please provide resume content either by pasting text or uploading a file.", "error")
                return redirect(url_for('index'))

            original_resume_for_preview = resume_text

            logger.info(f"Processing submission for industry: {form.industry.data}")

            # Language Detection for the input resume
            if LANGDETECT_AVAILABLE and resume_text.strip():
                try:
                    detected_language = detect(resume_text)
                    logger.info(f"Detected resume language: {detected_language}")
                except LangDetectException:
                    logger.warning("Could not detect language for resume text, defaulting to English.")
                    detected_language = 'en'
            else:
                detected_language = 'en' # Fallback if langdetect is not available

            target_language = form.target_language.data if form.enable_translation.data else detected_language
            if form.enable_translation.data and target_language != detected_language:
                flash(f"Output will be translated from {detected_language.upper()} to {target_language.upper()}.", "info")
            elif form.enable_translation.data and target_language == detected_language:
                flash(f"Translation enabled, but source and target languages are the same ({detected_language.upper()}). No translation performed.", "info")


            contact_info, parsed_sections = parse_resume(resume_text)
            if not parsed_sections and not contact_info.get('name'):
                flash('Could not parse the resume. Please check the content or try different formatting.', 'error')
                return redirect(url_for('index'))

            additional_tips_content = []
            if form.include_action_verb_list.data:
                additional_tips_content.append(
                    "Strong Action Verbs: Achieved, Analyzed, Built, Collaborated, Coordinated, Developed, Directed, Eliminated, Engineered, Enhanced, Facilitated, Generated, Implemented, Improved, Increased, Initiated, Led, Managed, Optimized, Organized, Performed, Pioneered, Planned, Reduced, Resolved, Spearheaded, Streamlined, Supervised, Trained, Transformed, Utilized."
                )
            if form.include_summary_best_practices.data:
                additional_tips_content.append(
                    "Resume Summary Best Practices: Keep it concise (3-5 lines). Highlight your top achievements and relevant skills. Tailor it to the job description by including key requirements. Use strong action verbs. Focus on what you can *do* for the employer."
                )
            if form.include_ats_formatting_tips.data:
                additional_tips_content.append(
                    "ATS (Applicant Tracking System) Formatting Tips: Use standard section headings. Avoid complex graphics, tables, or excessive columns. Use a clean, readable font (e.g., Calibri, Arial, Times New Roman). Ensure keywords from the job description are present. Avoid using headers/footers for critical information if possible, as some older ATS might struggle."
                )

            current_llm_nlp_status = WATSON_NLP_AVAILABLE or (nlp is not None)
            if job_desc and job_desc.strip() and current_llm_nlp_status:
                match_data = match_resume_to_job(resume_text, job_desc, form.industry.data)
                insert_recs = suggest_insertions_for_keywords(match_data.get('missing_keywords', []), form.industry.data)
            else:
                match_data = {}
                insert_recs = []

            if form.auto_draft_enhancements.data and job_desc and job_desc.strip() and current_llm_nlp_status:
                if match_data.get('missing_keywords'):
                    original_parsed_sections = parsed_sections.copy()
                    modified_sections_by_llm = apply_llm_enhancements(original_parsed_sections, match_data.get('missing_keywords', []), form.industry.data)

                    organized_text, organized_sections_dict = organize_resume_data(contact_info, modified_sections_by_llm, additional_tips_content)
                    flash('AI-powered enhancements drafted and inserted into the preview.', 'success')
                else:
                    organized_text, organized_sections_dict = organize_resume_data(contact_info, parsed_sections, additional_tips_content)
                    flash('No missing keywords found for AI-powered drafting. Resume is already well-aligned!', 'info')
            else:
                organized_text, organized_sections_dict = organize_resume_data(contact_info, parsed_sections, additional_tips_content)

                if form.insert_keywords.data and job_desc and job_desc.strip() and current_llm_nlp_status:
                    temp_match_data = match_resume_to_job(organized_text, job_desc, form.industry.data)
                    text_after_simple_insert = auto_insert_keywords(organized_text, temp_match_data.get('missing_keywords', []))

                    contact_info_after_simple_insert, parsed_sections_after_simple_insert = parse_resume(text_after_simple_insert)
                    organized_text, organized_sections_dict = organize_resume_data(contact_info_after_simple_insert, parsed_sections_after_simple_insert, additional_tips_content)
                    flash('Missing keywords have been automatically inserted into the preview (simple insertion).', 'success')

            if job_desc and job_desc.strip() and current_llm_nlp_status:
                match_data = match_resume_to_job(organized_text, job_desc, form.industry.data)
                insert_recs = suggest_insertions_for_keywords(match_data.get('missing_keywords', []), form.industry.data)

            if current_llm_nlp_status and organized_sections_dict.get('experience'):
                quantifiable_achievements = extract_quantifiable_achievements(organized_sections_dict['experience'])
                if quantifiable_achievements:
                    flash(f"Found {len(quantifiable_achievements)} potential quantifiable achievements. Review suggestions below!", "info")

            # --- Apply Translation if enabled and languages differ ---
            if form.enable_translation.data and target_language != detected_language:
                flash(f"Translating generated content to {target_language.upper()}...", "info")

                # Translate main organized text
                organized_text = _translate_text_gemini(organized_text, target_language, detected_language)

                # Translate each section in the dictionary
                translated_sections_dict = {}
                for key, value in organized_sections_dict.items():
                    translated_sections_dict[key] = _translate_text_gemini(value, target_language, detected_language)
                organized_sections_dict = translated_sections_dict

                # Translate match data keywords (if applicable, though these might be less impactful)
                # Note: Translating keywords might affect future matching if resume is re-processed in original language.
                # For simplicity, we'll translate the *display* of keywords here for the preview.
                if match_data:
                    match_data['matched_keywords'] = [_translate_text_gemini(kw, target_language, detected_language) for kw in match_data.get('matched_keywords', [])]
                    match_data['missing_keywords'] = [_translate_text_gemini(kw, target_language, detected_language) for kw in match_data.get('missing_keywords', [])]
                    for cat in match_data['missing_by_category']:
                        match_data['missing_by_category'][cat] = [_translate_text_gemini(kw, target_language, detected_language) for kw in match_data['missing_by_category'][cat]]

                # Translate enhancement suggestions
                insert_recs = [_translate_text_gemini(rec, target_language, detected_language) for rec in insert_recs]
                quantifiable_achievements = [_translate_text_gemini(ach, target_language, detected_language) for ach in quantifiable_achievements]

                flash("Translation complete.", "success")

            preview = generate_enhanced_preview(contact_info, organized_sections_dict, escape(original_resume_for_preview).replace('\n', '<br>'), match_data, form.highlight_keywords.data, detected_language, target_language)

            word_file_bytes = export_to_word(organized_text)
            session['word_file'] = word_file_bytes.getvalue()
            word_available = True

            session['html_preview_content'] = preview

            if not match_data and job_desc and job_desc.strip():
                 flash('Resume organized successfully. Keyword analysis was not performed as NLP model was not loaded.', 'info')
            elif not match_data:
                 flash('Resume organized successfully. Add a job description for keyword analysis.', 'success')
            elif not form.auto_draft_enhancements.data and not form.insert_keywords.data:
                 flash('Resume organized and analyzed successfully! Check enhancement suggestions for manual improvements.', 'success')

        except Exception as e:
            logger.error(f"An unexpected error occurred during form processing: {e}\n{traceback.format_exc()}")
            flash('An unexpected error occurred. Please try again or simplify your input. Check console for details.', 'error')

    # Pass detected_language and target_language to the template even on GET requests
    return render_template_string(HTML_TEMPLATE,
                                form=form,
                                preview=preview,
                                match_data=match_data,
                                insert_recs=insert_recs,
                                quantifiable_achievements=quantifiable_achievements,
                                word_available=word_available,
                                now=datetime.now(),
                                detected_language=detected_language, # Pass detected_language from the last processing or default
                                target_language=form.target_language.data, # Pass current form value for consistency
                                STRIPE_STARTER_PRICE_ID_TEMPLATE_VAR=STRIPE_STARTER_PRICE_ID,
                                STRIPE_PRO_PRICE_ID_TEMPLATE_VAR=STRIPE_PRO_PRICE_ID,
                                STRIPE_CREDIT_PACK_PRICE_ID_TEMPLATE_VAR=STRIPE_CREDIT_PACK_PRICE_ID)

@app.route('/download-word')
@tier_required(['starter', 'pro'])
def download_word():
    word_file_bytes = session.get('word_file')
    if word_file_bytes:
        return send_file(
            BytesIO(word_file_bytes),
            as_attachment=True,
            download_name=f"Organized_Resume_{datetime.now().strftime('%Y%m%d')}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    flash("No resume available for download. Please generate one first.", "error")
    return redirect(url_for('index'))

# Removed the /download-pdf route and its function as requested.

@app.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    global nlu_client, WATSON_NLP_AVAILABLE # Ensure access to global Watson NLU client

    resume_content_string = None
    filename = "pasted_text.txt" # Default filename for pasted text

    if request.content_type.startswith('application/json'):
        data = request.get_json()
        if not data:
            logger.error("No JSON data received for /analyze_resume with application/json content type.")
            return jsonify({"error": "No JSON data received."}), 400
        resume_content_string = data.get('resume_text')
        filename = data.get('filename', 'pasted_text.txt') # Use provided filename or default
        if not resume_content_string or not resume_content_string.strip():
            logger.warning("Empty resume_text received in JSON payload for /analyze_resume.")
            return jsonify({"error": "resume_text cannot be empty."}), 400
    elif request.content_type.startswith('multipart/form-data'):
        if 'resume' not in request.files:
            logger.error("No resume file part in /analyze_resume request (form-data).")
            return jsonify({"error": "No resume file part in the request"}), 400

        file = request.files['resume']
        if file.filename == '':
            logger.warning("No file selected in /analyze_resume request (form-data).")
            return jsonify({"error": "No selected file"}), 400

        if file:
            filename = secure_filename(file.filename)
            if filename.lower().endswith('.pdf'):
                resume_content_string = extract_text_from_pdf(file)
            elif filename.lower().endswith('.docx'):
                resume_content_string = extract_text_from_docx(file)
            elif filename.lower().endswith('.txt'):
                try:
                    file.seek(0)
                    resume_content_string = file.read().decode('utf-8')
                except Exception as e:
                    logger.error(f"Error reading .txt file {filename} in /analyze_resume: {e}")
                    return jsonify({"error": f"Error reading text file: {filename}"}), 500
            else:
                logger.warning(f"Unsupported file type uploaded to /analyze_resume (form-data): {filename}")
                return jsonify({"error": "Unsupported file type. Please upload a .txt, .pdf, or .docx file."}), 415

            if resume_content_string is None: # Indicates extraction failure for PDF/DOCX
                logger.error(f"Failed to extract text from uploaded file {filename} in /analyze_resume.")
                return jsonify({"error": f"Failed to extract text from {filename}."}), 500
    else:
        logger.error(f"Unsupported content type for /analyze_resume: {request.content_type}")
        return jsonify({"error": "Unsupported content type."}), 415

    # Common validation for extracted/received text
    if resume_content_string is None: # Should be caught by specific handlers, but as a safeguard
        logger.error("Resume content string is None before NLU analysis in /analyze_resume, this should not happen.")
        return jsonify({"error": "Failed to process resume content."}), 500
    if not resume_content_string.strip():
        logger.warning(f"No text content found in '{filename}' after processing in /analyze_resume.")
        return jsonify({"error": f"No text content found in {filename}."}), 400

    # Ensure resume_text is the extracted/received string for subsequent logic
    resume_text = resume_content_string

    if not WATSON_NLP_AVAILABLE or nlu_client is None:
        logger.error("Watson NLU client not configured. Cannot perform resume analysis in /analyze_resume.")
        return jsonify({"error": "Watson NLU client not configured. Please check server setup."}), 500

    # This try-except block should not be indented under the above if condition.
    # It is for the NLU analysis itself.
    try:
        logger.info(f"Analyzing resume '{filename}' with Watson NLU...")
        response = nlu_client.analyze(
            text=resume_text,
            features=Features(
                keywords=KeywordsOptions(limit=20, sentiment=False, emotion=False),
                entities=EntitiesOptions(limit=20, sentiment=False, emotion=False)
            )
            # language='en' # Optionally specify language if known, otherwise Watson detects
        ).get_result()

        keywords = response.get('keywords', [])
        entities = response.get('entities', [])

        logger.info(f"Successfully analyzed '{filename}' with Watson NLU.")
        return jsonify({
            "filename": filename,
            "message": "Resume analyzed successfully",
            "keywords": keywords,
            "entities": entities
        }), 200

    except ApiException as e:
        logger.error(f"Watson NLU API error during analysis of '{filename}': {e.code} - {e.message}")
        return jsonify({"error": f"Watson NLU API error: {e.message}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error during Watson NLU analysis of '{filename}': {e}")
        return jsonify({"error": "Analysis failed due to an unexpected server error."}), 500

    logger.error("File object was not valid in /analyze_resume for an unknown reason (should have been caught earlier).")
    return jsonify({"error": "An unexpected error occurred with the file processing."}), 500


@app.route('/match_job', methods=['POST'])
def match_job():
    global nlu_client, WATSON_NLP_AVAILABLE, gemini_model # Ensure access to global clients

    data = request.get_json()
    if not data:
        logger.error("No JSON data received for /match_job.")
        return jsonify({"error": "No data provided."}), 400

    job_description = data.get('job_description')
    resume_keywords_data = data.get('resume_keywords', []) # List of {'text': ..., 'relevance': ...}
    resume_entities_data = data.get('resume_entities', []) # List of {'type': ..., 'text': ...}

    if not job_description or not job_description.strip():
        logger.error("Job description not provided in /match_job request.")
        return jsonify({"error": "Job description is required."}), 400

    if not resume_keywords_data and not resume_entities_data:
        logger.warning("Resume keywords and entities are missing from the /match_job request.")
        # Depending on desired behavior, could return an error or proceed with limited functionality
        # For now, we'll proceed, but Gemini suggestions might be less effective.

    job_desc_keywords_list = []
    job_desc_entities_list = []
    job_description_analysis_results = {"keywords": [], "entities": []}

    if not WATSON_NLP_AVAILABLE or nlu_client is None:
        logger.warning("Watson NLU client not configured. Job description analysis will be skipped for /match_job.")
        # Proceed without Watson analysis, match score will be affected.
    else:
        try:
            logger.info(f"Analyzing job description with Watson NLU for /match_job...")
            jd_analysis_response = nlu_client.analyze(
                text=job_description,
                features=Features(
                    keywords=KeywordsOptions(limit=30),
                    entities=EntitiesOptions(limit=30)
                )
            ).get_result()
            job_desc_keywords_list = jd_analysis_response.get('keywords', [])
            job_desc_entities_list = jd_analysis_response.get('entities', [])
            job_description_analysis_results = {
                "keywords": job_desc_keywords_list,
                "entities": job_desc_entities_list
            }
            logger.info("Job description analysis complete.")
        except ApiException as e:
            logger.error(f"Watson NLU API error during job description analysis: {e.code} - {e.message}")
            # Proceed, but job_description_analysis will be empty or partial
        except Exception as e:
            logger.error(f"Unexpected error during Watson NLU job description analysis: {e}")
            # Proceed

    # Comparison Logic (Heuristic-based)
    resume_keyword_texts = {kw['text'].lower() for kw in resume_keywords_data if kw.get('text')}
    # Consider adding entity texts from resume to resume_keyword_texts if appropriate for matching
    # for entity in resume_entities_data:
    #     if entity.get('text'):
    #         resume_keyword_texts.add(entity['text'].lower())

    job_desc_keyword_texts = {kw['text'].lower() for kw in job_desc_keywords_list if kw.get('text')}
    # Similarly, consider adding entity texts from job description
    # for entity in job_desc_entities_list:
    #     if entity.get('text'):
    #         job_desc_keyword_texts.add(entity['text'].lower())

    common_keywords = resume_keyword_texts.intersection(job_desc_keyword_texts)
    match_score_percentage = 0
    if job_desc_keyword_texts: # Avoid division by zero
        match_score_percentage = round((len(common_keywords) / len(job_desc_keyword_texts)) * 100, 2)

    missing_keywords_in_resume = sorted(list(job_desc_keyword_texts - resume_keyword_texts))

    ai_suggestions_list = ["Suggestions feature temporarily unavailable."]
    if not gemini_model:
        logger.warning("Gemini client not configured. Skipping AI suggestions for /match_job.")
    else:
        try:
            # Construct prompt for Gemini
            resume_skills_summary = ", ".join(list(resume_keyword_texts)[:15]) # Top 15 resume keywords
            jd_skills_summary = ", ".join(list(job_desc_keyword_texts)[:15]) # Top 15 JD keywords

            prompt_for_gemini = (
                f"Resume Skills: {resume_skills_summary}\n"
                f"Job Description Key Skills: {jd_skills_summary}\n"
                f"Keywords Missing from Resume (but in Job Description): {', '.join(missing_keywords_in_resume[:10])}\n\n"
                "Based on this, provide 2-3 concise, actionable suggestions for the user to improve their resume to better match this specific job description. Focus on incorporating missing elements or rephrasing existing skills to align with the job's requirements."
            )
            logger.info("Generating AI suggestions with Gemini for /match_job...")
            gemini_response = gemini_model.generate_content(prompt_for_gemini)

            if gemini_response and gemini_response.text:
                # Simple parsing: split by newline, filter empty. More robust parsing might be needed.
                ai_suggestions_list = [s.strip() for s in gemini_response.text.split('\n') if s.strip() and not s.strip().startswith(("*", "-"))]
                if not ai_suggestions_list: # Fallback if splitting results in empty list
                     ai_suggestions_list = [gemini_response.text.strip()]
                logger.info("AI suggestions generated successfully.")
            else:
                logger.warning("Gemini response for suggestions was empty or invalid.")
                ai_suggestions_list = ["Could not generate AI suggestions at this time."]

        except Exception as e:
            logger.error(f"Error during Gemini API call for suggestions: {e}")
            ai_suggestions_list = ["Error generating AI suggestions."]

    return jsonify({
        "message": "Job match analysis complete.",
        "match_score": f"{match_score_percentage}%",
        "job_description_analysis": job_description_analysis_results,
        "missing_resume_keywords": missing_keywords_in_resume,
        "ai_suggestions": ai_suggestions_list
    }), 200


@app.route('/check_ats', methods=['POST'])
@tier_required(['free'])
def check_ats():
    global nlu_client, WATSON_NLP_AVAILABLE, gemini_model # Ensure access to global clients

    if 'resume' not in request.files:
        logger.error("No resume file part in /check_ats request.")
        return jsonify({"error": "No resume file part in the request"}), 400

    file = request.files['resume']
    filename = secure_filename(file.filename)

    if file.filename == '':
        logger.warning("No file selected in /check_ats request.")
        return jsonify({"error": "No selected file"}), 400

    resume_content_string = None
    if filename.lower().endswith('.pdf'):
        resume_content_string = extract_text_from_pdf(file)
    elif filename.lower().endswith('.docx'):
        resume_content_string = extract_text_from_docx(file)
    elif filename.lower().endswith('.txt'):
        try:
            file.seek(0)
            resume_content_string = file.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading .txt file {filename} for /check_ats: {e}")
            return jsonify({"error": f"Error reading text file: {filename}"}), 500
    else:
        logger.warning(f"Unsupported file type uploaded to /check_ats: {filename}")
        return jsonify({"error": "Unsupported file type. Please upload a .txt, .pdf, or .docx file."}), 415

    if resume_content_string is None:
        logger.error(f"Failed to extract text from {filename} in /check_ats.")
        return jsonify({"error": f"Failed to extract text from {filename}."}), 500
    # No separate check for empty string here, as generic tips can still be provided.
    # If NLU analysis is desired for empty string, it will likely not yield specific results.

    ats_suggestions = [
        "Use standard, readable fonts (e.g., Arial, Calibri, Times New Roman). Font size should be 10-12 points.",
        "Avoid using tables, columns, or text boxes for critical information like skills or experience, as some ATS may not parse these correctly.",
        "Ensure your contact information (name, phone, email, LinkedIn URL) is at the top and clearly identifiable.",
        "Use consistent formatting for dates (e.g., MM/YYYY or Month YYYY) and job titles throughout your resume.",
        "Spell check and proofread carefully; typos can cause your resume to be filtered out by ATS or viewed negatively by recruiters.",
        "Submit your resume in a compatible file format, typically .docx or PDF (unless .txt is specifically requested)."
    ]

    # Perform NLU analysis if content was extracted (even if empty, NLU might handle it gracefully or return nothing)
    if resume_content_string.strip(): # Only proceed with NLU if there's actual text
        if WATSON_NLP_AVAILABLE and nlu_client:
            try:
                logger.info(f"Analyzing '{filename}' with Watson NLU for ATS check...")
                analysis_results = nlu_client.analyze(
                    text=resume_content_string,
                    features=Features(
                        keywords={'limit': 50, 'sentiment': False, 'emotion': False},
                        entities={'limit': 50, 'sentiment': False, 'emotion': False}
                    )
                ).get_result()

                nlu_keywords = [kw['text'].lower() for kw in analysis_results.get('keywords', [])]
                standard_sections = ["experience", "education", "skills", "contact", "summary", "objective", "projects", "awards", "certifications", "languages", "volunteer"]
                found_sections_count = 0
                for section in standard_sections:
                    if any(section in kw for kw in nlu_keywords):
                        found_sections_count +=1
                    else:
                        ats_suggestions.append(f"Consider adding a clear '{section.capitalize()}' section if applicable to your experience.")

                if len(nlu_keywords) < 10 and len(resume_content_string) > 200:
                    ats_suggestions.append("Ensure your resume text is machine-readable and not primarily image-based. If your resume is text-based but few keywords were extracted by NLU, review its clarity and keyword optimization for ATS.")
                elif found_sections_count < 2 and len(resume_content_string) > 200:
                     ats_suggestions.append("Your resume seems to be missing several standard sections or they are not clearly identified. Ensure clear headings like 'Experience', 'Education', and 'Skills'.")
            except ApiException as e:
                logger.error(f"Watson NLU API error during ATS check for '{filename}': {e.code} - {e.message}")
                ats_suggestions.append("Could not perform detailed NLU analysis for section detection due to an API error.")
            except Exception as e:
                logger.error(f"Unexpected error during Watson NLU analysis for ATS check: {e}")
                ats_suggestions.append("An unexpected error occurred during detailed resume analysis.")
        else:
            ats_suggestions.append("Watson NLU client not available for detailed structural analysis. Displaying generic ATS tips.")
    else:
        logger.warning(f"No text content found in '{filename}' for ATS check, providing generic tips.")
        ats_suggestions.append("The uploaded file appears to be empty or no text could be extracted. Please check the file content.")


    final_suggestions = ats_suggestions
    if gemini_model and ats_suggestions:
        try:
            gemini_prompt = "Review the following ATS compatibility suggestions for a resume. Rephrase them to be more encouraging, clear, and actionable for a job seeker. Ensure each suggestion is a separate point. Suggestions:\n" + "\n".join(ats_suggestions)
            logger.info(f"Refining ATS suggestions for '{filename}' using Gemini...")
            gemini_response = gemini_model.generate_content(gemini_prompt)

            if gemini_response and gemini_response.text:
                refined_list = [s.strip().lstrip("-* ").strip() for s in gemini_response.text.split('\n') if s.strip()]
                if refined_list: # Use refined suggestions if Gemini provided valid output
                    final_suggestions = refined_list
                    logger.info("Successfully refined ATS suggestions with Gemini.")
                else:
                    logger.warning("Gemini refinement resulted in empty suggestions, using original.")
            else:
                logger.warning("Gemini response for ATS suggestion refinement was empty or invalid.")
        except Exception as e:
            logger.error(f"Error during Gemini API call for refining ATS suggestions: {e}")
            # Fallback to using pre-Gemini suggestions is implicit as final_suggestions isn't updated

    return jsonify({
        "filename": filename,
        "message": "ATS compatibility check complete.",
        "suggestions": final_suggestions
    }), 200


@app.route('/translate_resume', methods=['POST'])
def translate_resume():
    global gemini_model # Ensure we're using the globally configured model
    if not gemini_model:
        logger.error("Gemini client not configured. Cannot perform translation.")
        return jsonify({"error": "Gemini client not configured. Please check API key."}), 500

    data = request.get_json()
    if not data:
        logger.error("No JSON data received for /translate_resume.")
        return jsonify({"error": "No data provided."}), 400

    resume_text = data.get('resume_text')
    target_language = data.get('target_language')
    original_text_snippet = resume_text[:100] + "..." if len(resume_text) > 100 else resume_text

    if not resume_text or not resume_text.strip():
        logger.error("Resume text not provided for /translate_resume.")
        return jsonify({"error": "Resume text is required."}), 400

    if not target_language:
        logger.error("Target language not provided for /translate_resume.")
        return jsonify({"error": "Target language is required."}), 400

    identified_language_code = "unknown" # Default

    try:
        # Language Identification Prompt
        # Shorten text for language ID to avoid excessive token usage if text is very long
        text_for_id = resume_text[:500]
        lang_id_prompt = f"Identify the language of the following text and return only the two-letter ISO 639-1 language code (e.g., 'en', 'es', 'fr'). Text: \"{text_for_id}\""

        logger.info(f"Attempting language identification for text snippet: {text_for_id[:50]}...")
        lang_id_response = gemini_model.generate_content(lang_id_prompt)

        if lang_id_response and lang_id_response.candidates and lang_id_response.candidates[0].content.parts:
            identified_language_code = lang_id_response.text.strip().lower()
            # Basic validation for a two-letter code
            if not (len(identified_language_code) == 2 and identified_language_code.isalpha()):
                logger.warning(f"Gemini returned an invalid language code: '{identified_language_code}'. Defaulting to 'unknown'.")
                identified_language_code = "unknown" # Fallback if not a valid 2-letter code
            else:
                logger.info(f"Identified language code: {identified_language_code}")
        else:
            logger.warning("Language identification failed or returned empty response.")
            # Proceed with "unknown" or a default like "en" if preferred

        # Translation Prompt
        if identified_language_code != "unknown" and identified_language_code != target_language:
            translation_prompt = f"Translate the following text from {identified_language_code} to {target_language}: {resume_text}"
        else: # If language ID failed or source is same as target (though translation to same lang might still be useful for rephrasing)
            translation_prompt = f"Translate the following text to {target_language}: {resume_text}"

        logger.info(f"Attempting translation to {target_language} for text snippet: {resume_text[:50]}...")
        translation_response = gemini_model.generate_content(translation_prompt)

        if translation_response and translation_response.candidates and translation_response.candidates[0].content.parts:
            translated_text = translation_response.text.strip()
            logger.info(f"Translation to {target_language} successful.")
            return jsonify({
                "message": "Resume translated successfully.",
                "original_text_snippet": original_text_snippet,
                "identified_language_code": identified_language_code,
                "target_language": target_language,
                "translated_text": translated_text
            }), 200
        else:
            logger.error("Translation API call did not return expected content.")
            return jsonify({"error": "Translation failed. API did not return content."}), 500

    except Exception as e:
        logger.error(f"Error during Gemini API call for translation: {e}")
        # Check for specific Gemini API error types if the SDK provides them, otherwise generic
        if "API key not valid" in str(e): # Example of more specific error checking
             return jsonify({"error": "Translation failed. Invalid Gemini API key."}), 500
        return jsonify({"error": "Translation failed due to an API error or unexpected issue."}), 500


@app.route('/get_smart_suggestions', methods=['POST'])
@tier_required(['starter', 'pro'])
def get_smart_suggestions():
    global gemini_model # Ensure access to global Gemini model

    # user_tier = request.form.get('user_tier', 'free') # Handled by decorator
    # if user_tier != 'premium': # Handled by decorator
    #     logger.warning(f"Access denied for /get_smart_suggestions due to user_tier: {user_tier}")
    #     return jsonify({"error": "Access denied. Smart Suggestions is a premium feature. Please upgrade."}), 403

    if not gemini_model:
        logger.error("Gemini client not configured. Cannot provide smart suggestions.")
        return jsonify({"error": "Gemini client not configured."}), 500

    if 'resume' not in request.files:
        logger.error("No resume file part in /get_smart_suggestions request.")
        return jsonify({"error": "No resume file part in the request"}), 400

    file = request.files['resume']
    filename = secure_filename(file.filename)

    if file.filename == '':
        logger.warning("No file selected in /get_smart_suggestions request.")
        return jsonify({"error": "No selected file"}), 400

    if file:
        resume_content_string = None
        if filename.lower().endswith('.pdf'):
            resume_content_string = extract_text_from_pdf(file)
        elif filename.lower().endswith('.docx'):
            resume_content_string = extract_text_from_docx(file)
        elif filename.lower().endswith('.txt'):
            try:
                file.seek(0)
                resume_content_string = file.read().decode('utf-8')
            except Exception as e:
                logger.error(f"Error reading .txt file {filename} for /get_smart_suggestions: {e}")
                return jsonify({"error": f"Error reading text file: {filename}"}), 500
        else:
            logger.warning(f"Unsupported file type uploaded to /get_smart_suggestions: {filename}")
            return jsonify({"error": "Unsupported file type. Please upload a .txt, .pdf, or .docx file."}), 415

        if resume_content_string is None:
            logger.error(f"Failed to extract text from {filename} in /get_smart_suggestions.")
            return jsonify({"error": f"Failed to extract text from {filename}."}), 500
        if not resume_content_string.strip():
            logger.warning(f"No text content found in {filename} after extraction in /get_smart_suggestions.")
            return jsonify({"error": f"No text content found in {filename}."}), 400

        # resume_content_string is now guaranteed to be populated with text

        prompt_text = f"""Analyze the following resume text and provide actionable suggestions to improve it. Focus on:
1. Rephrasing sentences for greater impact and clarity (try to provide specific examples of original vs. suggested phrase).
2. Identifying opportunities to quantify achievements (suggest where and how to add numbers or metrics).
3. Recommendations for improving overall structure, flow, or content based on best practices for modern resumes (e.g., sections to add/remove, conciseness).
4. Ensuring a professional tone throughout the resume.
Provide at least 3-5 distinct suggestions. Format suggestions clearly, ideally as a list or bullet points.

Resume Text:
---
{resume_content_string}
---"""

        try:
            logger.info(f"Generating smart suggestions for '{filename}' using Gemini...")
            response = gemini_model.generate_content(prompt_text)

            suggestions_list = []
            if response and response.text:
                # Simple split by newline. Gemini might use markdown for lists.
                # Filter out empty lines or potential markdown list markers if they are not part of the suggestion.
                suggestions_list = [s.strip() for s in response.text.split('\n') if s.strip() and not s.strip().startswith(("* ", "- "))]
                # If the above results in an empty list but there was text, use the whole text as one suggestion.
                if not suggestions_list and response.text.strip():
                    suggestions_list = [response.text.strip()]

            logger.info(f"Successfully generated smart suggestions for '{filename}'.")
            return jsonify({
                "filename": filename,
                "message": "Smart suggestions generated successfully.",
                "suggestions": suggestions_list
            }), 200

        except Exception as e:
            logger.error(f"Error during Gemini API call for smart suggestions for '{filename}': {e}")
            return jsonify({"error": "Failed to generate smart suggestions due to an API error."}), 500

    # This part should ideally not be reached if checks above are correct
    logger.error("File object was not valid in /get_smart_suggestions for an unknown reason.")
    return jsonify({"error": "An unexpected error occurred with the file processing for smart suggestions."}), 500


@app.route('/get_job_market_insights', methods=['POST'])
@tier_required(['starter', 'pro']) # Ensures g.user_tier and g.simulated_user_id are set
def get_job_market_insights():
    # global gemini_model # Already global
    # data = request.get_json() # Original logic for getting data
    # user_tier = data.get('user_tier', 'free') # Old tier check, remove this as decorator handles it

    # New logic based on decorator's g values
    current_simulated_tier = getattr(g, 'user_tier', 'free')
    simulated_user_id_email_prefix = getattr(g, 'simulated_user_id', None)

    if not simulated_user_id_email_prefix:
        return jsonify({"error": "Simulated user ID not found. Please include 'user_id_simulation' in your request."}), 400

    # SIMULATION: Find user by the simulated ID (which we'll treat as email prefix)
    user = User.query.filter_by(email=f"{simulated_user_id_email_prefix}@example.com").first()

    if not user:
        # If user doesn't exist, it's tricky. For simulation, we might deny or create.
        # Let's assume webhook should have created the user. If not, deny.
        logger.warning(f"Simulated user with email prefix {simulated_user_id_email_prefix} not found during credit check.")
        return jsonify({"error": "Simulated user not found. Ensure user exists via webhook simulation."}), 404

    if current_simulated_tier == 'starter':
        user_credits = UserCredit.query.filter_by(user_id=user.id).first()
        if not user_credits or user_credits.credits_remaining <= 0:
            # Log this attempt
            usage_log_no_credit = FeatureUsageLog(user_id=user.id, feature_name='get_job_market_insights_attempt', credits_used=0)
            db.session.add(usage_log_no_credit)
            db.session.commit()
            return jsonify({"error": "You have no 'deep dive' credits remaining. Upgrade to Pro or purchase a credit pack."}), 403

        # Consume credit
        user_credits.credits_remaining -= 1
        usage_log = FeatureUsageLog(user_id=user.id, feature_name='get_job_market_insights', credits_used=1)
        db.session.add(usage_log)
        # db.session.commit() # Commit will happen with the main feature logic or at end of request
        logger.info(f"Starter tier user {user.email} consumed 1 credit for job market insights. Remaining: {user_credits.credits_remaining}")

    elif current_simulated_tier == 'pro':
        # Pro tier has unlimited access, but we can still log usage for analytics
        usage_log_pro = FeatureUsageLog(user_id=user.id, feature_name='get_job_market_insights', credits_used=0) # 0 credits used for pro
        db.session.add(usage_log_pro)
        logger.info(f"Pro tier user {user.email} accessed job market insights (unlimited).")

    # Original feature logic (ensure data is correctly sourced from request)
    data = request.get_json()
    if not data: # This check might be redundant if POST and decorator runs, but good for safety
        logger.error("No JSON data received for /get_job_market_insights.")
        return jsonify({"error": "No data provided."}), 400

    # The old tier check `if user_tier != 'premium'` is removed as decorator handles access.
    # The `user_tier` variable from `data.get('user_tier', 'free')` should not be used for logic anymore.

    if not gemini_model:
        logger.error("Gemini client not configured. Cannot provide job market insights.")
        return jsonify({"error": "Gemini client not configured."}), 500

    resume_keywords_data = data.get('resume_keywords', [])
    resume_entities_data = data.get('resume_entities', [])

    # ... (rest of the original /get_job_market_insights logic for calling Gemini) ...
    # Ensure to commit db.session changes at the end if the Gemini call is successful
    # For example, after successfully getting insights:
    # try:
    #    ... (Gemini call) ...
    #    db.session.commit() # Commit credit change and usage log
    #    return jsonify(...)
    # except Exception as e:
    #    db.session.rollback() # Rollback if Gemini or other logic fails
    #    logger.error(...)
    #    return jsonify(...)
    # This part is simplified for the subtask: assume the commit happens after successful processing.

    # --- Placeholder for the rest of the original function's logic ---
    identified_skills = set()
    for kw in resume_keywords_data:
        if kw.get('text'): identified_skills.add(kw['text'].strip().lower())
    for entity in resume_entities_data:
        if entity.get('text'): identified_skills.add(entity['text'].strip().lower())
    unique_skills_list = sorted(list(identified_skills))
    if not unique_skills_list:
        db.session.rollback() # Rollback credit usage if no skills to process
        return jsonify({"message": "No skills to process for insights.", "insights_text": "", "identified_skills_for_insights": []}), 200

    skills_string = ", ".join(unique_skills_list)
    prompt_text = (
        f"Based on the following list of skills and keywords from a resume: {skills_string}.\n\n"
        "Provide general insights about potential career paths, related skills that might be valuable to learn, "
        "and general areas of demand for these skills. Frame this as general guidance based on common knowledge, "
        "not as real-time, specific job market data. "
        "Provide insights as a few distinct points or a short, informative paragraph. Make it encouraging."
    )
    try:
        logger.info(f"Generating job market insights using Gemini based on skills: {skills_string[:200]}...")
        response = gemini_model.generate_content(prompt_text)
        insights_text = "No specific insights generated."
        if response and response.text: insights_text = response.text.strip()

        db.session.commit() # Commit credit consumption and logging
        return jsonify({
            "message": "Successfully generated general career and skill insights.",
            "insights_text": insights_text,
            "identified_skills_for_insights": unique_skills_list
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during Gemini API call for job market insights: {e}")
        return jsonify({"error": "Failed to generate job market insights due to an API error."}), 500
    # --- End of placeholder for original function's logic ---

# --- Gemini Client Configuration ---
# Note: GEMINI_API_KEY is already retrieved after load_dotenv() earlier in the file.
# This block assumes GEMINI_API_KEY and genai (google.generativeai) are available.
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro') # Or other appropriate model
        logger.info("Gemini client configured successfully.")
    except Exception as e:
        logger.error(f"Error configuring Gemini client: {e}")
        gemini_model = None # Ensure it's None on failure
else:
    logger.warning("GEMINI_API_KEY not found. Gemini features will be disabled.")

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    price_id = data.get('price_id')
    # SIMULATION: In a real app, user_id would come from the logged-in user.
    # For now, client sends a simulation or we generate one.
    # TODO: SIMULATION - Replace with actual authenticated user ID.
    # `user_id_simulation` is used here because there's no actual user login system.
    # In production, this should be the ID of the currently authenticated user.
    # This ID is passed to Stripe as `client_reference_id`.
    user_id_simulation = data.get('user_id_simulation', 'simulated_user_123')

    if not price_id:
        return jsonify({'error': 'Price ID is required'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            client_reference_id=user_id_simulation,
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription' if price_id in [STRIPE_STARTER_PRICE_ID, STRIPE_PRO_PRICE_ID] else 'payment', # 'payment' for one-time credit packs
            success_url=DOMAIN_URL + url_for('index', payment='success', session_id='{CHECKOUT_SESSION_ID}', _external=False) + '&sim_user=' + user_id_simulation, # Pass sim_user back
            cancel_url=DOMAIN_URL + url_for('index', payment='cancel', _external=False),
        )
        # For 'payment' mode (credit packs), we might need to handle it differently if it's not a subscription.
        # The example assumes credit packs might also be set up as 'payment' mode subscriptions if they grant ongoing access to something,
        # or just 'payment' if it's a one-time purchase. The provided plan implies "sell tokens", so 'payment' mode is more likely for credits.

        return jsonify({'sessionId': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    event = None

    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret is not configured.")
        return jsonify({'error': 'Webhook secret not configured'}), 500

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e: # Invalid payload
        logger.error(f"Invalid webhook payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e: # Invalid signature
        logger.error(f"Webhook signature verification failed: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"Webhook construction error: {e}")
        return jsonify({'error': 'Webhook error'}), 500


    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # `client_reference_id` was set during checkout session creation.
        # TODO: SIMULATION - This relies on user_id_simulation passed during checkout.
        user_id_simulation = session.get('client_reference_id')
        stripe_customer_id = session.get('customer')
        stripe_subscription_id = session.get('subscription') # This is for subscriptions
        payment_intent_id = session.get('payment_intent') # This is for one-time payments

        logger.info(f"Checkout session completed for simulated user: {user_id_simulation}")
        logger.info(f"Stripe Customer ID: {stripe_customer_id}, Subscription ID: {stripe_subscription_id}, Payment Intent ID: {payment_intent_id}")

        # SIMULATION: Find or create user
        # TODO: SIMULATION - User lookup and creation logic is simplified.
        # In a production system, user retrieval would be based on the authenticated user context
        # or a more robust mapping from `client_reference_id` or `stripe_customer_id`
        # to an existing user in your database. New user creation would typically occur
        # during a separate registration step, not directly in the webhook without prior context.
        # The creation of a new User here with a simulated email and password_hash is purely for
        # making the simulation work end-to-end without a real registration flow.
        user = User.query.filter_by(email=f"{user_id_simulation}@example.com").first() # Simulate finding user by an email
        if not user:
            logger.info(f"Simulated user {user_id_simulation} not found. Creating one for simulation.")
            # In a real app, user creation/retrieval is complex.
            # Hashing passwords is not done here as it's simulation.
            user = User(email=f"{user_id_simulation}@example.com", password_hash="simulated_hash")
            # Assign a default tier or determine from product

        user.stripe_customer_id = stripe_customer_id

        # Determine if it was a subscription or a one-time payment (e.g., credit pack)
        # TODO: SIMULATION - User tier and credit updates are performed on the simulated/retrieved user.
        # Ensure atomicity and error handling in a production system.
        if stripe_subscription_id: # It's a subscription
            user.stripe_subscription_id = stripe_subscription_id
            # Determine tier from the price_id associated with the subscription
            # This requires fetching the subscription or line items if not directly available
            try:
                line_items = stripe.checkout.Session.list_line_items(session.id, limit=1)
                price_id = line_items.data[0].price.id
                if price_id == STRIPE_STARTER_PRICE_ID:
                    user.tier = 'starter'
                    # Grant initial credit for Starter tier
                    user_credits = UserCredit.query.filter_by(user_id=user.id).first()
                    if not user_credits:
                        user_credits = UserCredit(user_id=user.id)
                        db.session.add(user_credits)
                    user_credits.credits_remaining = 1 # Grant 1 credit for Starter tier
                    user_credits.last_updated = datetime.utcnow()
                    logger.info(f"Initialized/Reset credits for Starter tier user {user.email} to 1.")
                elif price_id == STRIPE_PRO_PRICE_ID:
                    user.tier = 'pro'
                else:
                    logger.warning(f"Unknown subscription price_id {price_id} in checkout session.")
                logger.info(f"Simulated user {user_id_simulation} tier updated to {user.tier}")
            except Exception as e:
                logger.error(f"Error fetching line items to determine tier: {e}")

        elif payment_intent_id: # It's a one-time payment (likely credit pack)
            try:
                line_items = stripe.checkout.Session.list_line_items(session.id, limit=1)
                price_id = line_items.data[0].price.id
                if user and price_id == STRIPE_CREDIT_PACK_PRICE_ID: # Make sure user object exists
                    user_credits = UserCredit.query.filter_by(user_id=user.id).first()
                    if not user_credits:
                        user_credits = UserCredit(user_id=user.id, credits_remaining=0)
                        db.session.add(user_credits)
                    credits_to_add = 5 # This should be configured based on the price_id if multiple packs exist
                    user_credits.credits_remaining += credits_to_add
                    user_credits.last_updated = datetime.utcnow()
                    logger.info(f"Added {credits_to_add} credits to simulated user {user.email}. New balance: {user_credits.credits_remaining}")
                else:
                    logger.warning(f"Unknown one-time payment price_id {price_id} in checkout session or user not found.")
            except Exception as e:
                logger.error(f"Error fetching line items for one-time payment: {e}")

        db.session.add(user) # Add if new, or session handles updates
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error during webhook processing for checkout.session.completed: {e}")


    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        stripe_customer_id = invoice.get('customer')
        stripe_subscription_id = invoice.get('subscription')
        # Potentially update subscription status or grant credits if it's a recurring credit model
        logger.info(f"Invoice payment succeeded for customer {stripe_customer_id}, subscription {stripe_subscription_id}")
        # Find user by stripe_customer_id
        user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
        if user:
            # Ensure tier is still active, or grant monthly credits if applicable
            if user.stripe_subscription_id == stripe_subscription_id:
                # Example: if it's a Starter plan that gets monthly credits
                # This logic needs to be robust against multiple webhook deliveries
                # if user.tier == 'starter':
                #    # Add monthly credits for starter plan, ensure idempotency
                #    pass
                logger.info(f"Subscription {stripe_subscription_id} for user {user.email} payment successful. Tier: {user.tier}")
            else:
                logger.warning(f"Invoice for customer {stripe_customer_id} linked to subscription {stripe_subscription_id}, but user {user.email} has a different subscription {user.stripe_subscription_id}")
        else:
            logger.warning(f"User not found for stripe_customer_id {stripe_customer_id} from invoice.payment_succeeded.")


    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        stripe_customer_id = invoice.get('customer')
        logger.warning(f"Invoice payment failed for customer {stripe_customer_id}. Consider tier downgrade logic.")
        # Potentially downgrade user's tier or revoke access
        user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
        if user:
            # user.tier = 'free' # Example downgrade
            # user.stripe_subscription_id = None # Clear subscription ID
            # db.session.commit()
            logger.info(f"Simulated downgrade for user {user.email} due to payment failure.")


    else:
        logger.info(f"Unhandled Stripe event type: {event['type']}")

    return jsonify({'status': 'success'}), 200

@app.route('/generate_cover_letter', methods=['POST'])
@tier_required('pro')
def generate_cover_letter():
    # Simulate getting data, user_tier is already in g if needed
    # user_tier = g.user_tier
    # For now, just a placeholder response
    # In future, this would call a Gemini function similar to other AI features
    logger.info(f"Cover letter generation requested for (simulated) tier: {g.user_tier}")
    return jsonify({
        "message": "Cover letter generation endpoint for Pro tier.",
        "cover_letter_draft": "This is a placeholder for an AI-generated cover letter."
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') == 'development'

    print("=" * 50)
    print("🚀 Starting AI Resume Analyzer")
    if not WATSON_NLP_AVAILABLE:
        print("⚠️  WARNING: IBM Watson NLP credentials not found or configured.")
        print("   Attempting to use SpaCy as a fallback for keyword analysis. Please ensure")
        print("   WATSON_NLP_API_KEY and WATSON_NLP_URL are set in your environment variables,")
        print("   or run 'python -m spacy download en_core_web_sm' for SpaCy.")
    else:
        print("✅ IBM Watson NLP integration enabled for keyword analysis.")
    print(f"🔧 Debug mode: {debug_mode}")
    print(f"🌐 Server running at http://127.0.0.1:{port}")
    print(f"📝 PDF text extraction (pdfplumber): {PDFPLUMBER_AVAILABLE}")
    print(f"📝 PDF text extraction (PyPDF2 fallback): {PYPDF2_AVAILABLE}")
    print(f"🗣️ Language detection (langdetect): {LANGDETECT_AVAILABLE}")
    print("=" * 50)

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
