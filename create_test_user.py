"""
Helper script to create a test user in the database.
This script is useful for testing the signin authentication system.

Usage:
    python create_test_user.py --email user@example.com --password yourpassword --name "Test User"
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession
from db import SessionLocal
from models.user import User
from services.auth import AuthService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_user(email: str, password: str, full_name: str = None):
    """
    Create a new user in the database with hashed password.
    
    Args:
        email: User email address
        password: Plain text password (will be hashed)
        full_name: Optional full name
    """
    async with SessionLocal() as session:
        try:
            # Check if user already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.warning(f"User with email {email} already exists!")
                return
            
            # Create new user with hashed password
            hashed_password = AuthService.hash_password(password)
            new_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                is_active=True
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            logger.info(f"✓ Successfully created user: {email} (ID: {new_user.id})")
            logger.info(f"  Full Name: {full_name or 'N/A'}")
            logger.info(f"  Active: {new_user.is_active}")
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await session.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description="Create a test user for authentication")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--name", help="User full name", default=None)
    
    args = parser.parse_args()
    
    asyncio.run(create_user(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
