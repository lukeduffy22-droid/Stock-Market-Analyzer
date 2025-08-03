from app import app
from extensions import db
from app import app  # This must be the app where db.init_app(app) is called
from extensions import db
from models import User
from werkzeug.security import generate_password_hash

# Get user input
email = input("Enter admin email: ")
password = input("Enter admin password: ")

# Always do DB stuff inside app context
with app.app_context():
    # Create DB tables if not exist (optional)
    db.create_all()

    if not User.query.filter_by(email=email).first():
        password_hash = generate_password_hash(password)
        new_user = User(email=email,password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print(" User already exists.")