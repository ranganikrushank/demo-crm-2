# create_admin.py

from app import db, app, User

with app.app_context():
    admin = User(username="admin", password="admin293", role="admin")
    db.session.add(admin)
    db.session.commit()
    print("✅ Admin user created: username=admin, password=admin123")