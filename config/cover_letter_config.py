# config/cover_letter_config.py
import os

class CoverLetterConfig:
    SECRET_KEY = os.environ.get('COVER_LETTER_SECRET_KEY', 'default-secret')
    MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'txt']
    MAX_REQUESTS_PER_MINUTE = 5
