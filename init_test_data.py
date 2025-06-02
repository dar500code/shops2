from app import app, db, Product, Brand
import os
import shutil
from datetime import datetime, timedelta

def create_test_products():
    # Sample product data
    products = [
        {
            'name': 'Premium Wireless Headphones',
            'description': 'High-quality wireless headphones with noise cancellation',
            'price': 199.99,
            'category': 'Electronics',
            'image': 'headphones.jpg',
            'stock': 50,
            'rating': 4.5,
            'is_new': True
        },
        {
            'name': 'Smart Fitness Watch',
            'description': 'Track your fitness goals with this smart watch',
            'price': 149.99,
            'category': 'Electronics',
            'image': 'smartwatch.jpg',
            'stock': 30,
            'rating': 4.2,
            'discount_price': 129.99
        },
        {
            'name': 'Designer Leather Bag',
            'description': 'Elegant leather bag perfect for any occasion',
            'price': 299.99,
            'category': 'Fashion',
            'image': 'leather-bag.jpg',
            'stock': 20,
            'rating': 4.8
        },
        {
            'name': 'Professional Camera Kit',
            'description': 'Complete camera kit for professional photography',
            'price': 899.99,
            'category': 'Electronics',
            'image': 'camera.jpg',
            'stock': 15,
            'rating': 4.9,
            'is_new': True
        },
        {
            'name': 'Modern Coffee Maker',
            'description': 'Programmable coffee maker with multiple features',
            'price': 79.99,
            'category': 'Home',
            'image': 'coffee-maker.jpg',
            'stock': 40,
            'rating': 4.3,
            'discount_price': 59.99
        }
    ]

    # Create products directory if it doesn't exist
    products_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'products')
    os.makedirs(products_dir, exist_ok=True)

    # Copy sample images from assets to products directory
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets', 'sample-products')
    
    # Create and add products to database
    for product_data in products:
        # Copy image file
        image_filename = product_data['image']
        src_path = os.path.join(assets_dir, image_filename)
        dst_path = os.path.join(products_dir, image_filename)
        
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
        
        # Create product
        product = Product(
            name=product_data['name'],
            description=product_data['description'],
            price=product_data['price'],
            category=product_data['category'],
            image=image_filename,
            stock=product_data['stock'],
            rating=product_data['rating'],
            is_new=product_data.get('is_new', False),
            discount_price=product_data.get('discount_price'),
            created_at=datetime.utcnow() - timedelta(days=product_data.get('days_old', 0))
        )
        db.session.add(product)

    try:
        db.session.commit()
        print("Test products created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating test products: {e}")

if __name__ == '__main__':
    with app.app_context():
        create_test_products()
