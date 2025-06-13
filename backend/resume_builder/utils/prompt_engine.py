def generate_resume_section_prompt(section_type, user_input, industry):
    """Generate AI prompts for different resume sections"""
    industry_tips = {
        'technology': "Focus on technical skills, projects, and quantifiable achievements",
        'marketing': "Highlight campaigns, ROI metrics, and digital marketing skills",
        'academic': "Emphasize publications, research, and teaching experience",
        'legal': "Showcase case experience, legal research, and specialized knowledge",
        'healthcare': "Focus on patient care, medical procedures, and certifications",
        'finance': "Highlight financial analysis, risk management, and certifications"
    }
    
    prompts = {
        'summary': f"""
        Generate a professional resume summary for a {industry} professional with these details:
        - Key skills: {user_input.get('technical_skills', '')}
        - Experience: {user_input.get('experience_years', 0)} years
        - Career focus: {user_input.get('career_focus', '')}
        
        Guidelines:
        - Keep it to 3-4 sentences
        - Include industry keywords: {industry_tips.get(industry, '')}
        - Optimize for ATS systems
        - Start with strongest selling point
        """,
        
        'experience': f"""
        Refine this job description for a resume in the {industry} industry:
        Original: {user_input['achievements']}
        
        Guidelines:
        - Start each bullet point with a strong action verb
        - Quantify achievements where possible
        - Focus on results rather than responsibilities
        - Use industry-specific terminology: {industry_tips.get(industry, '')}
        - Keep to 3-5 bullet points
        - Optimize for ATS
        """,
        
        'skills': f"""
        Format these skills for a {industry} resume:
        Technical Skills: {user_input.get('technical_skills', '')}
        Soft Skills: {user_input.get('soft_skills', '')}
        
        Guidelines:
        - Categorize skills appropriately
        - Include industry-specific keywords
        - Order from most to least relevant
        - Use standard industry terminology
        """
    }
    
    return prompts.get(section_type, "")
