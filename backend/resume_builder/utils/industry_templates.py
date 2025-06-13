def get_industry_template(industry):
    """Return CSS template for different industries"""
    templates = {
        'technology': """
            /* Tech Industry Styles */
            .resume-header { background-color: #f8f9fa; border-bottom: 2px solid #6f42c1; }
            h1 { color: #6f42c1; }
            .section-title { border-bottom: 1px solid #6f42c1; }
            .skill-badge { background-color: #e9ecef; color: #6f42c1; }
        """,
        
        'marketing': """
            /* Marketing Industry Styles */
            .resume-header { background-color: #f8f9fa; border-bottom: 2px solid #20c997; }
            h1 { color: #20c997; }
            .section-title { border-bottom: 1px solid #20c997; }
            .skill-badge { background-color: #e9ecef; color: #20c997; }
        """,
        
        'academic': """
            /* Academic Industry Styles */
            .resume-header { background-color: #f8f9fa; border-bottom: 2px solid #fd7e14; }
            h1 { color: #fd7e14; }
            .section-title { border-bottom: 1px solid #fd7e14; }
            .publication-item { font-style: italic; }
        """,
        
        'legal': """
            /* Legal Industry Styles */
            .resume-header { background-color: #f8f9fa; border-bottom: 2px solid #dc3545; }
            h1 { color: #dc3545; }
            .section-title { border-bottom: 1px solid #dc3545; }
            .case-list { margin-left: 20px; }
        """,
        
        'default': """
            /* Default Resume Styles */
            .resume-header { background-color: #f8f9fa; border-bottom: 2px solid #8B0000; }
            h1 { color: #8B0000; }
            .section-title { border-bottom: 1px solid #8B0000; }
        """
    }
    return templates.get(industry, templates['default'])
