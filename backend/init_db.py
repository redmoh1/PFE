"""
Database initialization and seed data.

Creates initial companies and admin users for testing.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.connection import init_db, SessionLocal, reset_db
from backend.database.models import User, Company, UserRole
from backend.auth import get_password_hash


def seed_database():
    """Create initial seed data for testing.
    
    Creates:
    - 2 demo companies
    - Admin, analyst, and viewer users for each company
    """
    db = SessionLocal()
    
    try:
        print("Creating seed data...")
        
        # Create companies
        company1 = Company(
            name="Acme Corp",
            slug="acme-corp",
            description="Demo company for testing",
            data_directory="Acme Corp",
        )
        
        company2 = Company(
            name="TechCo Industries",
            slug="techco-industries",
            description="Another demo company",
            data_directory="TechCo",
        )
        
        db.add(company1)
        db.add(company2)
        db.commit()
        db.refresh(company1)
        db.refresh(company2)
        
        print(f"✓ Created company: {company1.name} (ID: {company1.id})")
        print(f"✓ Created company: {company2.name} (ID: {company2.id})")
        
        # Create users for Company 1 (Acme Corp)
        users = [
            User(
                email="admin@acme.com",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                company_id=company1.id,
            ),
            User(
                email="analyst@acme.com",
                full_name="Data Analyst",
                hashed_password=get_password_hash("analyst123"),
                role=UserRole.ANALYST,
                company_id=company1.id,
            ),
            User(
                email="viewer@acme.com",
                full_name="View Only User",
                hashed_password=get_password_hash("viewer123"),
                role=UserRole.VIEWER,
                company_id=company1.id,
            ),
            # Users for Company 2
            User(
                email="admin@techco.com",
                full_name="TechCo Admin",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                company_id=company2.id,
            ),
        ]
        
        for user in users:
            db.add(user)
        
        db.commit()
        
        print("\n✓ Created users:")
        for user in users:
            print(f"  - {user.email} ({user.role.value}) @ {user.company.name}")
        
        print("\n" + "="*70)
        print("SEED DATA CREATED SUCCESSFULLY")
        print("="*70)
        print("\nTest Credentials (Acme Corp):")
        print("  Admin:   admin@acme.com / admin123")
        print("  Analyst: analyst@acme.com / analyst123")
        print("  Viewer:  viewer@acme.com / viewer123")
        print("\nTest Credentials (TechCo):")
        print("  Admin:   admin@techco.com / admin123")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Initialize database and create seed data."""
    print("Initializing database...")
    
    # Ask user if they want to reset existing database
    if Path("data/sales_intelligence.db").exists():
        response = input("\nDatabase already exists. Reset and recreate? (yes/no): ")
        if response.lower() in ["yes", "y"]:
            print("Resetting database...")
            reset_db()
        else:
            print("Using existing database...")
            init_db()
    else:
        init_db()
    
    print("Database initialized successfully\n")
    
    # Create seed data
    seed_database()


if __name__ == "__main__":
    main()
