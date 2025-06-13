import requests
import json
from config.resume_builder_config import ResumeBuilderConfig

config = ResumeBuilderConfig()

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'ar': 'Arabic',
    'hi': 'Hindi'
}

def detect_language(text):
    """Detect language of input text using Mistral"""
    if not text.strip():
        return 'en'
    
    prompt = f"Detect the language of this text: '{text}'. Return only the ISO 639-1 language code."
    
    try:
        response = requests.post(
            config.MISTRAL_API_URL,
            headers={
                "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 10
            },
            timeout=15
        )
        response.raise_for_status()
        lang_code = response.json()["choices"][0]["message"]["content"].strip().lower()
        return lang_code if lang_code in SUPPORTED_LANGUAGES else 'en'
    except Exception:
        return 'en'

def translate_text(text, target_lang='en', source_lang=None):
    """Translate text to target language"""
    if not text.strip():
        return text
        
    if source_lang and source_lang == target_lang:
        return text
        
    prompt = (f"Translate the following text to {SUPPORTED_LANGUAGES.get(target_lang, 'English')} "
              f"({target_lang}). Maintain professional tone suitable for a resume:\n\n{text}")
    
    try:
        response = requests.post(
            config.MISTRAL_API_URL,
            headers={
                "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 2000
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text
