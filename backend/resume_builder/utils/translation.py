import requests
import json
import os
import logging

logger = logging.getLogger(__name__)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")

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
    if not MISTRAL_API_KEY:
        logger.warning("Mistral API key not configured. Cannot detect language. Defaulting to 'en'.")
        return 'en'
    if not text.strip():
        return 'en'
    
    prompt = f"Detect the language of this text: '{text}'. Return only the ISO 639-1 language code."
    
    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
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
    except Exception as e:
        logger.error(f"Language detection error: {str(e)}", exc_info=True)
        return 'en' # Fallback to English

def translate_text(text, target_lang='en', source_lang=None):
    """Translate text to target language"""
    if not MISTRAL_API_KEY:
        logger.warning("Mistral API key not configured. Cannot translate text. Returning original text.")
        return text
    if not text.strip():
        return text
        
    if source_lang and source_lang == target_lang:
        return text
        
    prompt = (f"Translate the following text to {SUPPORTED_LANGUAGES.get(target_lang, 'English')} "
              f"({target_lang}). Maintain professional tone suitable for a resume:\n\n{text}")
    
    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
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
        logger.error(f"Translation error: {str(e)}")
        return text

SECTION_TITLES = {
    'en': {
        'summary': 'Professional Summary',
        'experience': 'Work Experience',
        'skills': 'Skills',
        'education': 'Education',
        'projects': 'Projects',
        'languages': 'Languages',
        'volunteer': 'Volunteer Experience',
        'contact': 'Contact',
        'download': 'Download as PDF',
        'create_another': 'Create Another Resume'
    },
    'es': {
        'summary': 'Resumen Profesional',
        'experience': 'Experiencia Laboral',
        'skills': 'Habilidades',
        'education': 'Educación',
        'projects': 'Proyectos',
        'languages': 'Idiomas',
        'volunteer': 'Experiencia Voluntaria',
        'contact': 'Contacto',
        'download': 'Descargar como PDF',
        'create_another': 'Crear otro currículum'
    },
    'fr': {
        'summary': 'Résumé Professionnel',
        'experience': 'Expérience Professionnelle',
        'skills': 'Compétences',
        'education': 'Éducation',
        'projects': 'Projets',
        'languages': 'Langues',
        'volunteer': 'Bénévolat',
        'contact': 'Contact',
        'download': 'Télécharger en PDF',
        'create_another': 'Créer un autre CV'
    },
    'de': {
        'summary': 'Professionelle Zusammenfassung',
        'experience': 'Berufserfahrung',
        'skills': 'Fähigkeiten',
        'education': 'Ausbildung',
        'projects': 'Projekte',
        'languages': 'Sprachen',
        'volunteer': 'Ehrenamtliche Tätigkeit',
        'contact': 'Kontakt',
        'download': 'Als PDF herunterladen',
        'create_another': 'Weiteren Lebenslauf erstellen'
    },
    'zh': {
        'summary': '专业摘要',
        'experience': '工作经验',
        'skills': '技能',
        'education': '教育背景',
        'projects': '项目',
        'languages': '语言',
        'volunteer': '志愿者经历',
        'contact': '联系方式',
        'download': '下载PDF',
        'create_another': '创建另一个简历'
    },
    'ja': {
        'summary': 'プロフェッショナルサマリー',
        'experience': '職務経験',
        'skills': 'スキル',
        'education': '学歴',
        'projects': 'プロジェクト',
        'languages': '言語',
        'volunteer': 'ボランティア経験',
        'contact': '連絡先',
        'download': 'PDFでダウンロード',
        'create_another': '別の履歴書を作成'
    }
}
