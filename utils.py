import os
from werkzeug.utils import secure_filename
from PIL import Image
import io

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size

def compress_image(image, max_size_bytes=5*1024*1024):
    """Compress image to target size while maintaining aspect ratio"""
    if isinstance(image, (str, bytes)):
        img = Image.open(io.BytesIO(image) if isinstance(image, bytes) else image)
    else:
        img = Image.open(image)

    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Initial quality
    quality = 95
    output = io.BytesIO()
    
    # Try compressing until file size is under max_size_bytes
    while True:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality)
        if output.tell() <= max_size_bytes or quality <= 5:
            break
        quality -= 5
    
    output.seek(0)
    return output

def handle_file_upload(file, folder, app_root):
    """
    Handle file upload with compression
    Returns: filename if successful, None if failed
    """
    if not file or not allowed_file(file.filename):
        return None
        
    try:
        # Compress image
        compressed = compress_image(file)
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        if not filename:
            return None
            
        # Ensure target directory exists
        upload_path = os.path.join(app_root, 'static', 'images', folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Save compressed file
        file_path = os.path.join(upload_path, filename)
        with Image.open(compressed) as img:
            img.save(file_path, format='JPEG', quality=85)
        
        return filename
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
