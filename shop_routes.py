from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_wtf.csrf import CSRFProtect
import secrets

# Import existing models and extensions instead of creating new ones
from app import app, db, Product, Cart, CartItem
from models import User, Order, OrderItem

# Keep the products_db as temporary data for testing
products_db = {
    # ...existing product data...
}

@app.before_request
def set_session_user_id():
    if 'user_id' not in session:
        session['user_id'] = 'user123'

# Update route to use database models instead of dummy data
@app.route('/products')
def products_view():
    # ... existing products route code ...
    # But modify to use Product model instead of products_db
    filtered_products = Product.query
    
    if category_filter:
        filtered_products = filtered_products.filter_by(category=category_filter)
    
    if search_query:
        filtered_products = filtered_products.filter(
            Product.name.ilike(f'%{search_query}%') |
            Product.description.ilike(f'%{search_query}%')
        )

    # ... rest of the filtering logic ...
    return render_template('products.html', products=paginated_products)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart_view():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity')

    try:
        product = Product.query.get_or_404(product_id)
        if product.stock < quantity:
            return jsonify({'error': f'Not enough stock. Only {product.stock} available.'}), 400

        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()

        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)

        product.stock -= quantity
        db.session.commit()

        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({
            'message': f'{quantity} of {product.name} added to cart!',
            'cart_count': cart_count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ... add other routes as needed ...
