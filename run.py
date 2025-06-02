import os
from app import app, db
from models import User, Category, Product
import logging
import webbrowser
from threading import Timer
from werkzeug.security import generate_password_hash

def setup_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        'static/images',
        'static/images/products', 
        'static/images/avatars',
        'static/images/suppliers',
        'logs'
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def open_browser():
    """Open the browser to the local development server"""
    webbrowser.open_new('http://127.0.0.1:5000/')

def initialize_application():
    """Initialize the database and start the application"""
    setup_directories()
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Add categories first
        categories = {
            'Electronics': Category(name='Electronics'),
            'Clothing': Category(name='Clothing'),
            'Home': Category(name='Home'),
            'Books': Category(name='Books')
        }
        
        for category in categories.values():
            db.session.add(category)
        
        # Add some test products
        test_products = [
            {
                'name': 'Test Product 1',
                'description': 'This is a test product in Electronics category',
                'price': 99.99,
                'stock': 10,
                'category': 'Electronics',
                'image': 'default-product.jpg',
                'status': 'active'
            },
            {
                'name': 'Test Product 2',
                'description': 'This is a test product in Clothing category',
                'price': 49.99,
                'stock': 20,
                'category': 'Clothing',
                'image': 'default-product.jpg',
                'status': 'active'
            }
        ]
        
        for product_data in test_products:
            category_name = product_data.pop('category')
            product = Product(**product_data)
            product.category_obj = categories[category_name]
            db.session.add(product)
        
        # Add admin user
        admin = User(
            name='Admin User',
            email='admin@admin.com',
            password=generate_password_hash('admin'),
            user_type='admin'
        )
        db.session.add(admin)
        
        db.session.commit()
        print("Database initialized successfully with test data!")

    app.run(debug=True)

if __name__ == '__main__':
    initialize_application()