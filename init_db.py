from app import app, db
from models import User, Category, Product
from werkzeug.security import generate_password_hash
import os

def init_db():
    # Delete existing database
    db_file = 'shop5.db'
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing database: {db_file}")

    with app.app_context():
        # Create all tables
        db.create_all()
        print("Created all tables")

        # Create categories
        categories = [
            Category(name='Electronics'),
            Category(name='Clothing'),
            Category(name='Home'),
            Category(name='Books')
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

if __name__ == '__main__':
    init_db()
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    init_db()
