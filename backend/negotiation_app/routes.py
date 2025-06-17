from flask import request, jsonify
from flask_login import login_required, current_user
from backend.models import db, NegotiationScript
from . import negotiation_bp # Use the Blueprint from __init__.py

# Basic script templates - these can be expanded significantly
SCRIPT_TEMPLATES = {
    "entry_level_tech": [
        "Thank you for the offer. I'm very excited about the opportunity to join as a [Role]. Based on my research and understanding of the role's responsibilities, I was expecting a salary closer to [Desired Salary]. Is there any flexibility here?",
        "I understand the current offer is [Offered Salary]. Given my skills in [Skill1] and [Skill2], which I believe will bring significant value, I'd like to discuss if we can reach [Desired Salary].",
        "Could you help me understand how the compensation was determined for this role? I want to make sure I align my expectations correctly."
    ],
    "mid_level_marketing": [
        "I appreciate the offer for the [Role] position. I'm confident I can deliver strong results. Regarding compensation, my research indicates that similar roles with my experience level ([Experience] years) in [Location, if provided] typically command a salary in the range of [Desired Range Low] to [Desired Range High]. Can we explore options to get closer to that?",
        "Thank you for this offer. Before I accept, I wanted to discuss the salary. With my track record of [Achievement1] and [Achievement2], I believe a salary of [Desired Salary] would be more aligned with the value I bring.",
        "Is there room to negotiate on other aspects of the compensation package, such as a signing bonus or professional development budget, if the base salary is firm?"
    ],
    "senior_management": [
        "Thank you for extending the offer for the [Role] position. I'm enthusiastic about the strategic impact I can make. Based on my [Experience] years in leadership and the market rate for this level of responsibility, I'm looking for a total compensation package around [Desired Total Comp], with a base salary of [Desired Base Salary].",
        "I'm very interested in this role. The offer is competitive, but I'd like to understand if there's flexibility in the equity component or performance bonuses to bridge the gap towards my target compensation.",
        "Given the scope of the role and my proven ability to [Key Leadership Skill], I am confident that a salary of [Desired Salary] is a fair reflection of my market value. How can we work together to reach this figure?"
    ]
}

# A simple way to choose a template category based on experience
def get_template_category(experience_str):
    try:
        # Assuming experience is like "X years" or a category like "entry", "mid", "senior"
        experience_lower = experience_str.lower()
        if "year" in experience_lower:
            years = int(experience_lower.split()[0])
            if years <= 2: return "entry_level_tech" # Defaulting tech for now
            elif years <= 7: return "mid_level_marketing" # Defaulting marketing for now
            else: return "senior_management"
        if "entry" in experience_lower: return "entry_level_tech"
        if "mid" in experience_lower or "intermediate" in experience_lower: return "mid_level_marketing"
        if "senior" in experience_lower or "lead" in experience_lower or "manager" in experience_lower : return "senior_management"
    except ValueError:
        pass # Could not parse years
    return "entry_level_tech" # Default

@negotiation_bp.route('/generate-script', methods=['POST'])
@login_required
def generate_negotiation_script():
    data = request.form
    role = data.get('role')
    experience = data.get('experience') # e.g., "5 years", "entry-level", "senior"
    # location = data.get('location') # For future use with salary APIs

    if not role or not experience:
        return jsonify({'error': 'Missing required fields: role, experience'}), 400

    template_category = get_template_category(experience)
    scripts = SCRIPT_TEMPLATES.get(template_category, SCRIPT_TEMPLATES["entry_level_tech"]) # Fallback

    # For this example, we'll just pick the first script from the category
    # In a real app, you might offer multiple or use more complex logic
    selected_script_template = scripts[0]

    # Basic placeholder replacement (can be more sophisticated)
    # This is highly simplified. A real system would need more robust templating.
    # For now, we're not dynamically inserting [Desired Salary] etc. as that needs more input.
    # The user would fill these in.
    final_script = selected_script_template.replace("[Role]", role)
                                          # .replace("[Experience]", experience) # This is already used for category

    # Save to database
    negotiation_entry = NegotiationScript(
        user_id=current_user.id,
        role=role,
        experience=experience, # Store the user's input for experience
        script_text=final_script
    )
    db.session.add(negotiation_entry)
    db.session.commit()

    return jsonify({
        'role': role,
        'experience_category': template_category,
        'script': final_script,
        'message': "This is a starting point. You'll need to fill in specifics like desired salary and your unique skills/achievements."
    }), 200
