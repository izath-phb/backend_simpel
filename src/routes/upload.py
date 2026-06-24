import os
from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
import uuid

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/', methods=['POST'])
@jwt_required()
def upload_file():
    # check if the post request has the file part
    if 'image' not in request.files:
        return {'message': 'No image part in the request'}, 400
        
    file = request.files['image']
    
    if file.filename == '':
        return {'message': 'No selected file'}, 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add random uuid to prevent overwriting
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Ensure static/uploads exists
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Generate the absolute public URL for the image
        # Note: In production, you might need to use a domain name or Cloudinary instead of localhost
        host_url = request.host_url.rstrip('/')
        public_url = f"{host_url}/static/uploads/{unique_filename}"
        
        return {'message': 'File successfully uploaded', 'imageUrl': public_url}, 201
        
    return {'message': 'Allowed file types are png, jpg, jpeg, webp, gif'}, 400
