from app import app, db, Product
from werkzeug.security import generate_password_hash
import random
import logging
from typing import List, Dict
import asyncio

logger = logging.getLogger(__name__)

async def seed_database():
    try:
        with app.app_context():
            # Updated 2025 products
            products: List[Dict] = [
                {
                    'name': 'AI-Powered Smart Glasses',
                    'description': 'AR-enabled smart glasses with AI assistant',
                    'price': 699.99,
                    'original_price': 899.99,
                    'category': 'Electronics',
                    'image': 'smart-glasses.jpg',
                    'stock': 15
                },
                # ... add more modern products ...
            ]

            for product_data in products:
                product = Product(**{
                    **product_data,
                    'rating': round(random.uniform(4.0, 5.0), 1),
                    'is_public': True,
                    'is_active': True
                })
                db.session.add(product)

            await asyncio.to_thread(db.session.commit)
            logger.info("Database seeded successfully!")
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    asyncio.run(seed_database())
                    'is_public': True,
                    'is_active': True
                })
                db.session.add(product)

            await asyncio.to_thread(db.session.commit)
            logger.info("Database seeded successfully!")
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    asyncio.run(seed_database())
