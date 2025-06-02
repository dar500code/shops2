import os

def create_upload_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directories = [
        'static/images',
        'static/images/products',
        'static/images/brands',
        'static/images/avatars',
        'instance',
        'logs'
    ]
    
    for directory in directories:
        path = os.path.join(base_dir, directory)
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")

if __name__ == '__main__':
    create_upload_directories()
