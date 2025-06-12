def build_cover_letter_prompt(form_data, existing_cover_text):
    """Construct optimized prompt for Mistral API"""
    # Base prompt
    prompt = f"""
    You are an expert career consultant creating a tailored cover letter for a job application.
    The applicant is applying for a {form_data['job_title']} position at {form_data['company_name'] or 'a leading company'}.
    
    APPLICANT INFORMATION:
    - Name: {form_data['your_name']}
    - Email: {form_data['your_email']}
    
    JOB REQUIREMENTS:
    {form_data['job_description'][:1800]}
    
    APPLICANT'S RESUME CONTENT:
    {form_data['resume_text'][:1800] if form_data['resume_text'] else 'Not provided'}
    """
    
    # Refinement strategies
    refinement_type = form_data['refinement_type']
    if refinement_type == 'refine' and existing_cover_text:
        prompt += f"""
        ---
        REFINEMENT INSTRUCTIONS:
        - Refine this existing cover letter: {existing_cover_text[:1800]}
        - Focus on these key improvements: {form_data['key_points'] or 'Enhance professionalism and job relevance'}
        - Maintain the original structure while improving content
        - Strengthen connections to job requirements
        """
    elif refinement_type == 'enhance' and existing_cover_text:
        prompt += f"""
        ---
        ENHANCEMENT INSTRUCTIONS:
        - Enhance this cover letter with resume content: {existing_cover_text[:1800]}
        - Incorporate these key resume points: {form_data['key_points'] or 'Highlight relevant skills and experiences'}
        - Add 1-2 concrete examples from resume
        - Strengthen quantitative achievements
        """
    else:
        prompt += f"""
        ---
        KEY POINTS TO HIGHLIGHT:
        {form_data['key_points'] or 'Emphasize relevant skills and experiences'}
        """
    
    # Tone instructions
    tone_map = {
        'professional': "Formal business tone, polished language",
        'enthusiastic': "Energetic and passionate tone, showing excitement",
        'concise': "Direct and to-the-point, maximum impact with minimum words",
        'storytelling': "Narrative style, connecting experiences to job needs"
    }
    
    # Formatting instructions
    prompt += f"""
    ---
    TONE: {tone_map.get(form_data['tone'], 'professional')}
    KEYWORD INTEGRATION: Naturally include 3-5 keywords from the job description
    QUANTIFICATION: Include at least 2 quantifiable achievements
    STRUCTURE:
      - Opening paragraph: Express interest and position relevance
      - Middle paragraphs: Demonstrate qualifications with specific examples
      - Closing paragraph: Express enthusiasm and call to action
    LENGTH: 3-4 paragraphs, approximately 250-400 words
    FORMATTING:
      - Use standard business letter format
      - Include placeholders for date, company address
      - Separate paragraphs with blank lines
      - Do not include any markdown or special formatting
    """
    
    return prompt
