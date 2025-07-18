# create_employees.py

from app import db, app, User

with app.app_context():
    emp1 = User(username="Krushank", password="@krushank293", role="employee1")
    emp2 = User(username="Krushank", password="@293Krushank", role="employee2")

    db.session.add(emp1)
    db.session.add(emp2)
    db.session.commit()

    print("✅ Employee users created: employee1 / emp123, employee2 / emp123")