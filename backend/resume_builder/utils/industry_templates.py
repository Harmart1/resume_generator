def get_industry_template(industry):
    """Return CSS template for different industries"""
    # ... other industry designs ... (Comment moved here)
    templates = {
        'technology': """
            /* Tech Industry - Modern, Clean */
            .resume-header { 
                background: linear-gradient(135deg, #6f42c1 0%, #3a1c71 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
            }
            .desired-title {
                font-size: 1.2rem;
                color: #d8c7ff;
                margin-top: 10px;
            }
            h1 { color: white; border: none; }
            .contact-info a { color: #d8c7ff; }
            .section-title { 
                color: #6f42c1; 
                border-bottom: 2px solid #6f42c1;
                padding-bottom: 5px;
            }
            .skill-badge { 
                background-color: #f0e6ff; 
                color: #6f42c1;
                font-weight: 600;
            }
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
            /* Professional Default */
            .resume-header { 
                background: linear-gradient(135deg, #8B0000 0%, #5a0000 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
            }
            .desired-title {
                font-size: 1.2rem;
                color: #ffd8d8;
                margin-top: 10px;
            }
            h1 { color: white; border: none; }
            .contact-info a { color: #ffd8d8; }
            .section-title { 
                color: #8B0000; 
                border-bottom: 2px solid #8B0000;
                padding-bottom: 5px;
            }
            .skill-badge { 
                background-color: #ffe6e6; 
                color: #8B0000;
                font-weight: 600;
            }
        """
    }
    return templates.get(industry, templates['default'])
