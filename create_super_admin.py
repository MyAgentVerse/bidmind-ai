"""
Script to create a super admin user.
Run with: python create_super_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.core.security import password_manager
from app.models import User, Organization, UserOrganization
from app.db.base import Base

settings = get_settings()

# Create database engine
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Check if super admin already exists
    admin_email = "dawoodshabbir734@gmail.com"
    existing_admin = db.query(User).filter(User.email == admin_email).first()

    if existing_admin:
        print(f"❌ Super admin with email {admin_email} already exists!")
        sys.exit(1)

    # Create super admin user
    super_admin = User(
        email=admin_email,
        full_name="Super Admin",
      password_hash=password_manager.hash_password("@Dfimbk734*@"),
        is_active=True,
        is_verified=True
    )

    db.add(super_admin)
    db.flush()

    # Create admin organization
    admin_org = Organization(
        name="Super Admin Organization",
        description="Super admin workspace"
    )

    db.add(admin_org)
    db.flush()

    # Link admin to organization with owner role
    user_org = UserOrganization(
        user_id=super_admin.id,
        organization_id=admin_org.id,
        role="owner"
    )

    db.add(user_org)
    db.commit()

    print(f"✅ Super admin created successfully!")
    print(f"   Email: {admin_email}")
    print(f"   Password: @Dfimbk734*@")
    print(f"   User ID: {super_admin.id}")
    print(f"   Organization ID: {admin_org.id}")

except Exception as e:
    db.rollback()
    print(f"❌ Error creating super admin: {str(e)}")
    sys.exit(1)
finally:
    db.close()
