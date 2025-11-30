"""Change user language to French"""
from database import SessionLocal
from models.user import User

def set_user_language_french(telegram_id=8213628656):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            print(f"Current language: {user.language}")
            user.language = 'fr'
            db.commit()
            print(f"✅ Language changed to: fr")
        else:
            print(f"❌ User {telegram_id} not found")
    finally:
        db.close()

if __name__ == "__main__":
    set_user_language_french()
