import os
import tempfile
import logging
from PyPDF2 import PdfReader
from docx import Document
import textract

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_file(file_path):
    """Extract text from uploaded files with enhanced error handling"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""
    
    try:
        if file_path.endswith('.pdf'):
            logger.info(f"Processing PDF file: {file_path}")
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                return '\n\n'.join([page.extract_text() for page in reader.pages])
                
        elif file_path.endswith('.docx'):
            logger.info(f"Processing DOCX file: {file_path}")
            doc = Document(file_path)
            return '\n\n'.join([para.text for para in doc.paragraphs])
            
        elif file_path.endswith('.doc'):
            logger.info(f"Processing DOC file: {file_path}")
            return textract.process(file_path).decode('utf-8')
            
        elif file_path.endswith('.txt'):
            logger.info(f"Processing TXT file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return ""
            
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return ""
