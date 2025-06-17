import os
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from PIL import Image, ImageDraw, ImageFont
from backend.models import db, BrandingAsset
from . import branding_bp # Use the Blueprint from __init__.py

# Helper function for image generation
def generate_linkedin_banner(name, profession, skills_list, output_path):
    try:
        width, height = 1584, 396  # Standard LinkedIn banner size
        background_color = (26, 140, 216)  # A professional blue
        img = Image.new('RGB', (width, height), color=background_color)
        draw = ImageDraw.Draw(img)

        # Attempt to load a font; provide a fallback or ensure font is available
        try:
            # Try a common font, adjust path if needed or use a default
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Common on Linux
            if not os.path.exists(font_path): # Fallback for other systems
                font_path = "arial.ttf" # May require Pillow to find it in system paths or project
            title_font = ImageFont.truetype(font_path, 60)
            text_font = ImageFont.truetype(font_path, 30)
        except IOError:
            # Fallback if specific font is not found
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            print(f"Warning: Specified font not found. Using default font for LinkedIn banner.")


        # Name and Profession
        draw.text((50, 50), name, font=title_font, fill=(255, 255, 255))
        draw.text((50, 120), profession, font=text_font, fill=(220, 220, 220))

        # Skills
        if skills_list:
            skills_text = "Skills: " + " | ".join(skills_list[:3]) # Show first 3 skills
            draw.text((50, 200), skills_text, font=text_font, fill=(255, 255, 255))

        img.save(output_path)
        return True
    except Exception as e:
        print(f"Error generating LinkedIn banner: {e}")
        # current_app.logger.error(f"Error generating LinkedIn banner: {e}", exc_info=True) # If app logger is set up
        return False

@branding_bp.route('/generate-assets', methods=['POST'])
@login_required
def generate_branding_assets():
    data = request.form
    name = data.get('name')
    profession = data.get('profession')
    skills = data.get('skills') # Comma-separated string

    if not all([name, profession, skills]):
        return jsonify({'error': 'Missing required fields: name, profession, skills'}), 400

    skills_list = [s.strip() for s in skills.split(',')]

    # 1. Generate Elevator Pitch
    elevator_pitch = f"I’m {name}, a {profession} passionate about {skills_list[0] if skills_list else 'my work'}. With a strong background in {', '.join(skills_list[1:]) if len(skills_list) > 1 else 'various areas'}, I excel at delivering impactful results and driving innovation."

    # Save elevator pitch
    pitch_asset = BrandingAsset(
        user_id=current_user.id,
        asset_type='elevator_pitch',
        content=elevator_pitch
    )
    db.session.add(pitch_asset)

    # 2. Generate LinkedIn Banner
    # Ensure 'instance/user_banners' directory exists
    # Note: In a serverless environment, writing to filesystem might be tricky.
    # Consider using a cloud storage service (e.g., S3) for a robust solution.
    # For this example, we save to 'instance/user_banners/<user_id>_banner.png'
    # This path needs to be accessible by the app.

    # Get instance path from app config if possible, otherwise construct carefully
    # This assumes 'instance' is at the project root, and 'app.py' is in 'backend'
    instance_folder = os.path.join(current_app.root_path, '..', 'instance')
    user_banners_dir = os.path.join(instance_folder, 'user_banners')
    os.makedirs(user_banners_dir, exist_ok=True)

    banner_filename = f"{current_user.id}_linkedin_banner.png"
    banner_relative_path = os.path.join('user_banners', banner_filename) # Relative to instance folder
    banner_full_path = os.path.join(user_banners_dir, banner_filename)

    banner_success = generate_linkedin_banner(name, profession, skills_list, banner_full_path)

    banner_asset_content = None
    if banner_success:
        # Store the relative path or a URL if serving files
        banner_asset_content = banner_relative_path
        banner_asset = BrandingAsset(
            user_id=current_user.id,
            asset_type='linkedin_banner',
            content=banner_asset_content
        )
        db.session.add(banner_asset)
    else:
        # Log error or notify user banner generation failed
        print(f"LinkedIn banner generation failed for user {current_user.id}")


    db.session.commit()

    response = {
        'elevator_pitch': elevator_pitch,
    }
    if banner_asset_content:
        # This URL would need a route to serve files from 'instance/user_banners'
        # e.g., @app.route('/user-assets/<path:filename>')
        # For now, just returning the path stored.
        response['linkedin_banner_path'] = banner_asset_content
    else:
        response['linkedin_banner_error'] = "Failed to generate banner image."


    return jsonify(response), 201

# Example route to serve generated banners (add to app.py or a general utility blueprint)
# This is just a placeholder to illustrate how files could be served.
# @app.route('/user_assets/<path:filename>') # Consider if this should be part of branding_bp
# @login_required
# def serve_user_asset(filename):
#     # Ensure app.instance_path is correctly configured
#     # instance_path = current_app.instance_path # usually project_root/instance
#     # For this structure: backend/../instance
#     instance_folder = os.path.join(current_app.root_path, '..', 'instance')
#     return send_from_directory(os.path.join(instance_folder), filename)
