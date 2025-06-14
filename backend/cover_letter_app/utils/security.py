from flask import request, jsonify
from functools import wraps
import time
from collections import defaultdict

# Simple in-memory rate limiter
request_log = defaultdict(list)
MAX_REQUESTS = 5  # Max requests per minute
TIME_WINDOW = 60  # 60 seconds

def rate_limited(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        # Remove old requests
        request_log[ip] = [t for t in request_log[ip] if current_time - t < TIME_WINDOW]
        
        if len(request_log[ip]) >= MAX_REQUESTS:
            return jsonify({
                "error": "Too many requests",
                "message": f"Limit is {MAX_REQUESTS} requests per minute"
            }), 429
            
        request_log[ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

def validate_input_length(job_desc, resume_text, cover_text):
    """Validate input sizes to prevent abuse"""
    max_length = 5000  # characters per field
    
    if len(job_desc) > max_length:
        return "Job description is too long (max 5000 characters)"
    if resume_text and len(resume_text) > max_length:
        return "Resume content is too long (max 5000 characters)"
    if cover_text and len(cover_text) > max_length:
        return "Cover letter is too long (max 5000 characters)"
    return None
