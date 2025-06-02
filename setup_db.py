from app import app, db
from models import User, Category
from werkzeug.security import generate_password_hash
import os

def setup_database():
    # Delete existing database
    db_path = 'shop5.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    # Create required directories
    directories = [
        'static/images/products',
        'static/images/avatars',
        'static/images/brands',
        'instance'
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

    with app.app_context():
        # Create all tables
        db.create_all()
        print("Created database tables")

        # Create initial categories
        categories = [
            Category(name='Electronics', description='Electronics and gadgets'),
            Category(name='Clothing', description='Fashion and apparel'),
            Category(name='Home', description='Home and furniture'),
            Category(name='Books', description='Books and publications')
        ]
        
        for category in categories:
            db.session.add(category)
        
        # Create admin user
        admin = User(
            name='Admin User',
            email='admin@admin.com',
            password=generate_password_hash('admin'),
            user_type='admin'
        )
        db.session.add(admin)
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    setup_database()
