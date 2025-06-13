def generate_resume_section_prompt(section_type, user_input, industry):
    """Generate AI prompts with ATS optimization"""
    ats_keywords = {
        'technology': "Python, Java, AWS, Agile, DevOps, CI/CD, Kubernetes",
        'marketing': "SEO, SEM, ROI, KPI, CRM, Google Analytics, Content Strategy",
        'academic': "Peer Review, Curriculum Development, Research Methodology, Pedagogy",
        'legal': "Litigation, Compliance, Contract Law, Legal Research, Deposition",
        'healthcare': "HIPAA, EHR, Patient Care, Clinical Documentation, ICD-10",
        'finance': "ROI, Forecasting, Financial Modeling, GAAP, Risk Management"
    }
    
    industry_keywords = ats_keywords.get(industry, "")def generate_resume_section_prompt(section_type, user_input, industry):
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
        Generate an ATS-optimized professional resume summary for a {industry} professional.
        Incorporate these keywords: {industry_keywords}
        
        Guidelines:
        - Include 3-5 industry-specific keywords
        - Keep to 3-4 sentences
        - Start with strongest selling point
        - Highlight {user_input.get('years_experience', 3)} years of experience
        - Focus on: {user_input.get('career_focus', '')}
        """
    }
    return prompts.get(section_type, "")
           
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
