from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate 
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import secrets
import os
import logging
from logging.handlers import RotatingFileHandler  # Add this import
from werkzeug.utils import secure_filename
from functools import wraps
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Product, Order, OrderItem, CartItem, Brand, Category
from forms import AdminLoginForm
from sqlalchemy.exc import SQLAlchemyError
import json
from pathlib import Path
from utils import handle_file_upload

# Load environment variables
# load_dotenv()

# Initialize Flask app and database BEFORE trying to add categories
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop5.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

csrf = CSRFProtect(app)

# Ensure CSRF protection is enabled
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Basic configurations for local development
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/images')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

# Simplified security settings for development
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Setup logging
if not os.path.exists('logs'):
    os.mkdir('logs')

# Configure logging
file_handler = RotatingFileHandler('logs/shop.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Shop startup')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Remove the duplicate User class definition and all other model definitions
# Keep only the routes and configurations

# Ensure instance directory exists and create config file if needed
instance_path = Path('instance')
instance_path.mkdir(exist_ok=True)
config_file = instance_path / 'config.json'

# Default settings
default_settings = {
    'SITE_NAME': 'Modern E-Shop',
    'SITE_DESCRIPTION': 'Your one-stop shop for modern products',
    'CONTACT_EMAIL': 'contact@moderneeshop.com',
    'CONTACT_PHONE': '+1 (555) 123-4567',
    'MAIL_SERVER': 'smtp.gmail.com',
    'MAIL_PORT': 587,
    'FACEBOOK_URL': 'https://facebook.com/moderneeshop',
    'TWITTER_URL': 'https://twitter.com/moderneeshop',
    'INSTAGRAM_URL': 'https://instagram.com/moderneeshop'
}

# Load existing config or create new one
if config_file.exists():
    with open(config_file) as f:
        app.config.update(json.load(f))
else:
    app.config.update(default_settings)
    with open(config_file, 'w') as f:
        json.dump(default_settings, f, indent=4)

# Add these categories at the top level of the file
default_categories = [
    ('Electronics',), 
    ('Clothing',), 
    ('Home',), 
    ('Books',)
]

# Move the category initialization to a function
def init_categories():
    with app.app_context():
        db.create_all()  # Create tables first
        # Add default categories if they don't exist
        for cat_name in ['Electronics', 'Clothing', 'Home', 'Books']:
            if not Category.query.filter_by(name=cat_name).first():
                db.session.add(Category(name=cat_name))
        db.session.commit()

# Routes
@app.route('/')
def index():
    # Fetch featured, new, and best-selling products
    featured_products = Product.query.limit(8).all()
    new_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    best_sellers = Product.query.order_by(Product.stock.desc()).limit(8).all()
    
    return render_template(
        'index.html',
        featured_products=featured_products,
        new_products=new_products,
        best_sellers=best_sellers
    )

@app.route('/products')
def products():
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Number of products per page
        search_query = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        
        # Base query with join to get active products
        query = Product.query.filter_by(status='active')
        
        # Apply search filter if provided
        if search_query:
            query = query.filter(Product.name.ilike(f'%{search_query}%'))
        
        # Apply category filter if provided
        if category:
            query = query.filter_by(category=category)
        
        # Get all unique categories for the filter
        categories = db.session.query(Category).all()
        
        # Paginate results
        products = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template(
            'products.html',
            products=products.items,
            pagination=products,
            categories=categories,
            current_category=category,
            search_query=search_query
        )
    except Exception as e:
        app.logger.error(f"Error in products route: {str(e)}")
        flash('An error occurred while loading products', 'error')
        return redirect(url_for('index'))

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    # Now we can safely access item.product
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = 10.00 if cart_items else 0
    tax = subtotal * 0.1
    total = subtotal + shipping + tax
    
    return render_template('cart.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        if not request.form.get('product_id'):
            flash('Product ID is required', 'error')
            return redirect(url_for('index'))

        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))

        # Validate product
        product = Product.query.get_or_404(product_id)
        if product.stock < quantity:
            flash(f'Not enough stock. Only {product.stock} available.', 'error')
            return redirect(url_for('index'))

        # Handle logged-in users only (guests must log in)
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

        db.session.commit()
        flash('Added to cart successfully', 'success')
        return redirect(url_for('product_detail', id=product_id))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding to cart: {str(e)}")
        flash('Failed to add product to cart', 'error')
        return redirect(url_for('product_detail', id=product_id))

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    try:
        item_id = request.form.get('item_id')
        quantity = int(request.form.get('quantity', 0))
        
        cart_item = CartItem.query.get_or_404(item_id)
        
        if cart_item.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
            
        db.session.commit()
        
        # Calculate new totals
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        cart_count = len(cart_items)
        
        return jsonify({
            'message': 'Cart updated',
            'subtotal': f"${subtotal:.2f}",
            'cart_count': cart_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return redirect(url_for('cart'))
    
    if request.method == 'POST':
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        shipping = 10.00
        tax = subtotal * 0.1
        total = subtotal + shipping + tax
        
        order = Order(
            user_id=current_user.id,
            total=total,
            shipping_address=request.form['address'],
            status='pending'
        )
        db.session.add(order)
        
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)
            db.session.delete(item)
        
        db.session.commit()
        return redirect(url_for('order_confirmation', order_id=order.id))
    
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = 10.00
    tax = subtotal * 0.1
    total = subtotal + shipping + tax
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         shipping=shipping,
                         tax=tax,
                         total=total)

@app.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('order_confirmation.html', order=order)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
            
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            # Validate form data
            if not all([name, email, password]):
                flash('All fields are required', 'error')
                return redirect(url_for('register'))
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return redirect(url_for('register'))
            
            # Create new user
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                user_type='buyer',
                avatar='default.jpg'  # Add default avatar
            )
            
            # Save to database
            db.session.add(user)
            db.session.commit()
            
            # Log in the new user
            login_user(user)
            flash('Registration successful! Welcome to our shop.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))

    form = AdminLoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            
            if user and user.user_type == 'admin' and check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('Login successful', 'success')
                return redirect(url_for('admin_dashboard'))
            
            flash('Invalid email or password', 'error')
            app.logger.warning(f"Failed login attempt for admin: {form.email.data}")
            
        except Exception as e:
            app.logger.error(f"Error during admin login: {str(e)}")
            flash('An error occurred', 'error')
    
    return render_template('admin/login.html', form=form)

@app.route('/admin')
def admin_redirect():
    """Redirect /admin to the admin dashboard or login page"""
    if current_user.is_authenticated and current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    tab = request.args.get('tab', 'overview')
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('profile.html', 
                         user=current_user, 
                         active_tab=tab,
                         orders=orders)

@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/profile/settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    if request.method == 'POST':
        try:
            # Handle avatar upload
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    current_user.avatar = filename

            # Update user information
            current_user.name = request.form.get('name')
            current_user.email = request.form.get('email')
            
            # Update optional fields only if they exist in the form
            if 'phone' in request.form:
                current_user.phone = request.form.get('phone')
            if 'address' in request.form:
                current_user.address = request.form.get('address')
            if 'bio' in request.form:
                current_user.bio = request.form.get('bio')
            if 'website' in request.form:
                current_user.website = request.form.get('website')

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile_settings'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error updating profile: {str(e)}')
            flash('An error occurred while updating your profile.', 'error')

    return render_template('profile/settings.html', user=current_user)

# Admin routes
# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'recent_orders': Order.query.order_by(Order.created_at.desc()).limit(5).all(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
        'low_stock_products': Product.query.filter(Product.stock < 10).all(),
        'active_deals': Product.query.filter(
            Product.discount_price.isnot(None),
            Product.discount_end > datetime.utcnow()
        ).count(),
        'new_arrivals': Product.query.filter(
            Product.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count(),
        'total_brands': Brand.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_product():
    if request.method == 'POST':
        try:
            image_files = []
            app_root = os.path.dirname(os.path.abspath(__file__))
            
            # Handle image uploads
            for i in range(1, 4):
                file_key = f'image{i}'
                if file_key in request.files and request.files[file_key].filename:
                    file = request.files[file_key]
                    filename = handle_file_upload(file, 'products', app_root)
                    if filename:
                        image_files.append(filename)
                    else:
                        flash(f'Error processing image {i}', 'error')
                        continue

            if not image_files:
                flash('At least one valid image is required', 'error')
                return redirect(url_for('admin_new_product'))

            # Create product
            product = Product(
                name=request.form['name'],
                description=request.form['description'],
                price=float(request.form['price']),
                stock=int(request.form['stock']),
                category=request.form['category'],
                image=image_files[0],  # First image is main
                additional_images=image_files[1:] if len(image_files) > 1 else [],  # Rest are additional
                status=request.form.get('status', 'active')
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product created successfully!', 'success')
            return redirect(url_for('admin_products'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating product: {str(e)}')
            flash('Error creating product. Please try again.', 'error')
            return redirect(url_for('admin_new_product'))

    categories = [(c.name,) for c in Category.query.all()]
    return render_template('admin/new_product.html', categories=categories)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    brands = Brand.query.all()
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.category = request.form['category']
        product.stock = int(request.form['stock'])
        product.brand_id = request.form.get('brand_id', type=int)
        product.discount_price = request.form.get('discount_price', type=float)
        
        if request.form.get('discount_start'):
            product.discount_start = datetime.strptime(
                request.form['discount_start'], '%Y-%m-%dT%H:%M'
            )
        if request.form.get('discount_end'):
            product.discount_end = datetime.strptime(
                request.form['discount_end'], '%Y-%m-%dT%H:%M'
            )
        
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image = filename

        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template(
        'admin/edit_product.html',
        product=product,
        brands=brands
    )

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:id>')
@login_required
@admin_required
def admin_order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<int:id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_order(id):
    order = Order.query.get_or_404(id)
    status = request.form.get('status')
    if status:
        order.status = status
        db.session.commit()
        flash('Order status updated successfully', 'success')
    return redirect(url_for('admin_order_detail', id=id))

@app.route('/admin/brands')
@login_required
@admin_required
def admin_brands():
    try:
        brands = Brand.query.order_by(Brand.name).all()
        return render_template('admin/brands.html', brands=brands)
    except Exception as e:
        app.logger.error(f"Error loading brands: {str(e)}")
        flash('Error loading brands', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/brands/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_brand(id):
    brand = Brand.query.get_or_404(id)
    try:
        db.session.delete(brand)
        db.session.commit()
        flash('Brand deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting brand. It may have associated products.', 'error')
        app.logger.error(f"Error deleting brand: {str(e)}")
    return redirect(url_for('admin_brands'))

@app.route('/admin/brands/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_brand():
    if request.method == 'POST':
        brand = Brand(
            name=request.form['name'],
            description=request.form.get('description', ''),
            website=request.form.get('website', '')
        )
        
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'brands', filename))
                brand.logo = filename
        
        db.session.add(brand)
        db.session.commit()
        flash('Brand created successfully', 'success')
        return redirect(url_for('admin_brands'))
    
    return render_template('admin/new_brand.html')

@app.route('/admin/brands/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_brand(id):
    brand = Brand.query.get_or_404(id)
    
    if request.method == 'POST':
        brand.name = request.form['name']
        brand.description = request.form.get('description', '')
        brand.website = request.form.get('website', '')
        
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'brands', filename))
                brand.logo = filename
        
        db.session.commit()
        flash('Brand updated successfully', 'success')
        return redirect(url_for('admin_brands'))
    
    return render_template('admin/edit_brand.html', brand=brand)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:id>')
@login_required
@admin_required
def admin_user_detail(id):
    user = User.query.get_or_404(id)
    return render_template('admin/user_detail.html', user=user)

@app.route('/admin/user/<int:id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_user(id):
    try:
        user = User.query.get_or_404(id)
        user_type = request.form.get('user_type')
        
        # Only update user_type if it's valid
        if user_type in ['admin', 'buyer']:
            user.user_type = user_type
            
        # Sync with user's profile updates
        user.name = user.name
        user.email = user.email
        user.phone = user.phone
        user.address = user.address
        user.bio = user.bio
        user.website = user.website
        
        db.session.commit()
        flash('User information updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating user: {str(e)}")
        flash('Error updating user information', 'error')
        
    return redirect(url_for('admin_user_detail', id=id))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        try:
            # Update settings
            updated_settings = {
                'SITE_NAME': request.form.get('site_name', app.config['SITE_NAME']),
                'SITE_DESCRIPTION': request.form.get('site_description', app.config['SITE_DESCRIPTION']),
                'CONTACT_EMAIL': request.form.get('contact_email', app.config['CONTACT_EMAIL']),
                'CONTACT_PHONE': request.form.get('contact_phone', app.config['CONTACT_PHONE']),
                'MAIL_SERVER': request.form.get('smtp_host', app.config['MAIL_SERVER']),
                'MAIL_PORT': int(request.form.get('smtp_port', app.config['MAIL_PORT'])),
                'FACEBOOK_URL': request.form.get('facebook_url', app.config['FACEBOOK_URL']),
                'TWITTER_URL': request.form.get('twitter_url', app.config['TWITTER_URL']),
                'INSTAGRAM_URL': request.form.get('instagram_url', app.config['INSTAGRAM_URL'])
            }

            # Update app config and save to file
            app.config.update(updated_settings)
            with open(config_file, 'w') as f:
                json.dump(updated_settings, f, indent=4)

            flash('Settings saved successfully!', 'success')
            return redirect(url_for('admin_settings'))

        except Exception as e:
            app.logger.error(f"Error saving settings: {str(e)}")
            flash('Error saving settings. Please try again.', 'error')

    return render_template('admin/settings.html', config=app.config)

@app.route('/admin/view_order/<int:id>')
@login_required
@admin_required
def admin_view_order(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/view_order.html', order=order)

@app.route('/deals')
def deals():
    # Get products with discounts or special offers
    deals = Product.query.filter(Product.discount_price.isnot(None)).all()
    return render_template('deals.html', deals=deals)

@app.route('/new-arrivals')
def new_arrivals():
    # Get products from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_products = Product.query.filter(
        Product.created_at >= thirty_days_ago
    ).order_by(Product.created_at.desc()).all()
    return render_template('new_arrivals.html', products=new_products)

@app.route('/brands')
def brands():
    # In a real app, you would fetch this from a database
    brands = [
        {'name': 'Apple', 'logo': 'apple.png', 'product_count': 15},
        {'name': 'Samsung', 'logo': 'samsung.png', 'product_count': 20},
        {'name': 'Nike', 'logo': 'nike.png', 'product_count': 30},
        {'name': 'Adidas', 'logo': 'adidas.png', 'product_count': 25},
        {'name': 'Sony', 'logo': 'sony.png', 'product_count': 18},
        {'name': 'LG', 'logo': 'lg.png', 'product_count': 12}
    ]
    return render_template('brands.html', brands=brands)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Log the message or send an email (placeholder logic)
        app.logger.info(f"Contact form submitted: {name}, {email}, {message}")
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        cart_count = 0
    return dict(cart_count=cart_count)

@app.context_processor
def inject_categories():
    # Add some default categories if none exist
    default_categories = [('Electronics',), ('Clothing',), ('Home',), ('Books',)]
    return dict(categories=default_categories)

@app.context_processor
def inject_site_config():
    """Make site configuration available in all templates"""
    return {
        'config': app.config
    }

def allowed_file(filename, filesize=None):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Check file extension
    is_allowed = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    # Check file size if provided
    if filesize and filesize > MAX_FILE_SIZE:
        return False
    
    return is_allowed

@app.route('/admin/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product', 'error')
        app.logger.error(f"Error deleting product: {str(e)}")
    return redirect(url_for('admin_products'))

@app.route('/review/<int:review_id>/like', methods=['POST'])
@login_required
def like_review(review_id):
    try:
        review = Review.query.get_or_404(review_id)
        
        # Check if user already liked the review
        if current_user in review.likes_users:
            review.likes_users.remove(current_user)
            review.likes -= 1
        else:
            review.likes_users.append(current_user)
            review.likes += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'likes': review.likes,
            'is_liked': current_user in review.likes_users
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Load config from file or set defaults
config_file = Path('instance/config.json')
if config_file.exists():
    with open(config_file) as f:
        saved_config = json.load(f)
    app.config.update(saved_config)
else:
    app.config.update(
        SITE_NAME='Modern E-Shop',
        SITE_DESCRIPTION='Your one-stop shop for modern products',
        CONTACT_EMAIL='contact@moderneeshop.com',
        CONTACT_PHONE='+1 (555) 123-4567',
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        FACEBOOK_URL='https://facebook.com/moderneeshop',
        TWITTER_URL='https://twitter.com/moderneeshop',
        INSTAGRAM_URL='https://instagram.com/moderneeshop'
    )

with app.app_context():
    init_categories()

if __name__ == '__main__':
    init_categories()
    app.run(debug=True)