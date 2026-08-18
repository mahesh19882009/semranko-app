"""Safe admin account identification script."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.db.models import Base, User
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
db = Session(engine)

print("=" * 60)
print("ADMIN ACCOUNT IDENTIFICATION")
print("=" * 60)

# Count users with isAdmin=True
admin_count = db.scalar(select(func.count()).select_from(User).where(User.isAdmin == True))
print(f"\nDB users with isAdmin=true: {admin_count}")

if admin_count > 0:
    admin_users = db.scalars(select(User).where(User.isAdmin == True)).all()
    print("\nAdmin users:")
    for user in admin_users:
        email_masked = user.email[:3] + "***" + user.email.split("@")[1] if "@" in user.email else "***"
        print(f"  - ID: {user.id}, Email: {email_masked}, Name: {user.name}")

# Check ADMIN_EMAILS configuration
admin_emails_config = settings.ADMIN_EMAILS or ""
admin_emails_list = [email.strip().lower() for email in admin_emails_config.split(",") if email.strip()]
print(f"\nADMIN_EMAILS configured: {'Yes' if admin_emails_list else 'No'}")
if admin_emails_list:
    print(f"ADMIN_EMAILS value (length {len(admin_emails_config)}): {'*' * len(admin_emails_config)}")

# Check if any configured emails exist in DB
if admin_emails_list:
    configured_users = db.scalars(select(User).where(User.email.in_(admin_emails_list))).all()
    print(f"\nDB users matching ADMIN_EMAILS: {len(configured_users)}")
    for user in configured_users:
        email_masked = user.email[:3] + "***" + user.email.split("@")[1] if "@" in user.email else "***"
        print(f"  - ID: {user.id}, Email: {email_masked}, isAdmin: {user.isAdmin}")

print("\n" + "=" * 60)
print("To designate an admin account:")
print("1. Update User.isAdmin column to true via controlled operation")
print("2. OR set ADMIN_EMAILS environment variable with the email")
print("=" * 60)

db.close()
