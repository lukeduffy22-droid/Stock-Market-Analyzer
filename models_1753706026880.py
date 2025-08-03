from app import db
from datetime import datetime

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploads = db.relationship('Upload', backref='user', lazy=True, cascade='all, delete-orphan')
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade='all, delete-orphan')

class Upload(db.Model):
    """Model to track uploaded CSV files"""
    __tablename__ = 'uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    predictions = db.relationship('Prediction', backref='upload', lazy=True, cascade='all, delete-orphan')

class Prediction(db.Model):
    """Model to store prediction results"""
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    predicted_price = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float)
    model_type = db.Column(db.String(50), default='Linear Regression')
    prediction_data = db.Column(db.Text)  # JSON string of detailed prediction data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
