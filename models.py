from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import enum
import json
from sqlalchemy.types import TypeDecorator, TEXT

db = SQLAlchemy()

class JSONType(TypeDecorator):
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class UserType(enum.Enum):
    BUYER = 'buyer'
    ADMIN = 'admin'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('ix_users_email', 'email', unique=True),
        db.Index('ix_users_user_type', 'user_type'),
        {'extend_existing': True}  # Add this line
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)  # Changed from first_name/last_name to name
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Changed from password_hash to password
    user_type = db.Column(db.String(20), nullable=False, default='buyer')  # Changed from Enum to String
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar = db.Column(db.String(200), default='default-avatar.png')
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    bio = db.Column(db.Text)
    website = db.Column(db.String(200))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<User {self.email}>'

    def get_cart_count(self):
        return CartItem.query.filter_by(user_id=self.id).count()

    def get_avatar_url(self):
        return f"/static/images/avatars/{self.avatar}"

class Category(db.Model):
    __tablename__ = 'categories'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define products relationship without backref
    products = db.relationship('Product', back_populates='category_obj')

    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    additional_images = db.Column(JSONType, default=list)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add these if not present
    discount_price = db.Column(db.Float)
    discount_start = db.Column(db.DateTime)
    discount_end = db.Column(db.DateTime)

    # Add rating fields
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    total_ratings = db.Column(db.Integer, default=0)
    
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'))  # Add this line
    
    @property
    def average_rating(self):
        """Calculate average rating"""
        if self.rating_count == 0:
            return 0
        return self.total_ratings / self.rating_count

    def add_rating(self, rating_value):
        """Add a new rating"""
        self.total_ratings += rating_value
        self.rating_count += 1
        self.rating = self.average_rating

    # Relationships
    category_obj = db.relationship('Category', back_populates='products')
    brand = db.relationship('Brand', backref=db.backref('products', lazy=True))

    __table_args__ = (
        db.Index('ix_products_price', 'price'),
        db.Index('ix_products_created_at', 'created_at'),
    )

    def __repr__(self):
        return f'<Product {self.name}>'

class OrderStatus(enum.Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    RETURNED = 'returned'

class PaymentMethod(enum.Enum):
    CREDIT_CARD = 'credit_card'
    PAYPAL = 'paypal'
    CASHAPP = 'cashapp'

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_address = db.Column(JSONType, nullable=False)  # Replace JSONB with JSONType
    billing_address = db.Column(JSONType)  # Replace JSONB with JSONType
    payment_method = db.Column(db.Enum(PaymentMethod))
    payment_status = db.Column(db.String(20), default='unpaid')
    tracking_number = db.Column(db.String(100))
    shipping_cost = db.Column(db.Numeric(10, 2), default=0.0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('ix_orders_status', 'status'),
        db.Index('ix_orders_created_at', 'created_at'),
    )

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0.0)
    
    @property
    def total_price(self):
        return (self.price - self.discount) * self.quantity

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    session_id = db.Column(db.String(100), index=True)  # For guest users
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add this relationship
    product = db.relationship('Product', backref='cart_items')

    @property
    def subtotal(self):
        return self.quantity * self.product.price if self.product else 0

class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    logo = db.Column(db.String(200), default='default-brand.png')
    description = db.Column(db.Text)
    website = db.Column(db.String(200))
    country_of_origin = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Brand {self.name}>'
