from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from textblob import TextBlob
import spacy
from backend.models import db, EQFeedback # Corrected import path for models
from backend.models import MockInterview # Assuming MockInterview is in backend.models
# If MockInterview is in a blueprint (e.g. mock_interview_app.models), adjust path

# Use the Blueprint created in __init__.py
# This assumes eq_bp is defined in the same directory's __init__.py and imported
from . import eq_bp

# Load spacy model (consider doing this once at app startup or Blueprint setup)
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    # This is a fallback, ideally model is downloaded during build/deploy
    print("Downloading en_core_web_sm...")
    spacy.cli.download('en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

@eq_bp.route('/<int:interview_id>', methods=['POST']) # Route path simplified
@login_required
def eq_coach_analyze(interview_id): # Renamed function to be more descriptive
    answer = request.form.get('answer')
    if not answer:
        return jsonify({'error': 'No answer provided'}), 400

    interview = MockInterview.query.get_or_404(interview_id)
    if interview.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    blob = TextBlob(answer)
    sentiment_score = blob.sentiment.polarity

    doc = nlp(answer.lower())
    eq_keywords = ['team', 'collaboration', 'empathy', 'support', 'understand', 'listen', 'feedback', 'resolve', 'connect'] # Expanded list
    keyword_count = sum(1 for token in doc if token.text in eq_keywords)

    # Adjusted scoring to be more nuanced
    empathy_score = 0
    if sentiment_score > 0.1: # Positive sentiment contributes
        empathy_score += (sentiment_score * 40) # Max 40 points from sentiment
    empathy_score += (keyword_count * 10) # Max 10 points per keyword
    empathy_score = min(100, empathy_score) # Cap at 100

    if empathy_score >= 75:
        feedback_text = "Excellent demonstration of emotional intelligence! Your response shows strong empathy and awareness."
    elif empathy_score >= 50:
        feedback_text = "Good effort in showing emotional intelligence. Consider elaborating on teamwork or understanding others' perspectives to enhance this further."
    elif empathy_score >= 25:
        feedback_text = "There's room to improve your demonstration of emotional intelligence. Try to incorporate more keywords like 'team', 'empathy', or 'collaboration' and express more positive sentiment."
    else:
        feedback_text = "Your response could benefit from a stronger focus on emotional intelligence. Consider how you can show more empathy, collaboration, or understanding in your answers."


    eq_feedback_entry = EQFeedback( # Renamed variable for clarity
        user_id=current_user.id,
        interview_id=interview_id,
        empathy_score=empathy_score,
        feedback=feedback_text # Use dynamic feedback
    )
    db.session.add(eq_feedback_entry)
    db.session.commit()

    return jsonify({
        'empathy_score': empathy_score,
        'feedback': feedback_text
    })
