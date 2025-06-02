from app import app, db
from models import Category, User
from werkzeug.security import generate_password_hash
import os

def init_db():
    # Delete the database file if it exists
    db_path = 'shop4.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

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
        
        # Add all categories
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
        
        # Commit all changes
        try:
            db.session.commit()
            print("Successfully initialized database!")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            raise

if __name__ == '__main__':
    init_db()
