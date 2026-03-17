import os
import sys
import bcrypt

# Add the project root to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_employee.api.database import SessionLocal
from ai_employee.api.models import UserDB
from ai_employee.utils.security import SecurityLevel

def seed_admin_user():
    print("🚀 Seeding Admin User to Neon PostgreSQL...")
    db = SessionLocal()
    try:
        email = "sheikhmhamza37@gmail.com"
        password = "adminhamza@"
        
        # Hard-coded hash or manually compute with bcrypt
        # bcrypt.hashpw(password, salt)
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Passlib format for bcrypt is usually $2b$12$...
        # Python standard bcrypt hash is exactly what we need
        
        existing_user = db.query(UserDB).filter(UserDB.username == email).first()
        
        if existing_user:
            print(f"ℹ️ User {email} already exists. Updating password...")
            existing_user.hashed_password = hashed_password
            existing_user.full_name = "Sheikh Muhammad Hamza (Admin)"
            existing_user.level = SecurityLevel.ADMIN.value
        else:
            print(f"📝 Creating new Admin User: {email}")
            new_user = UserDB(
                username=email,
                email=email,
                full_name="Sheikh Muhammad Hamza (Admin)",
                hashed_password=hashed_password,
                level=SecurityLevel.ADMIN.value,
                permissions=["admin", "read", "write"]
            )
            db.add(new_user)
        
        db.commit()
        print("✅ Admin User seeded successfully!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        
    except Exception as e:
        print(f"❌ Error seeding user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin_user()
