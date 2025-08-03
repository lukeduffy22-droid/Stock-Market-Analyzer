from extensions import db
from datetime import datetime

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploads = db.relationship('Upload', backref='user', lazy=True, cascade='all, delete-orphan')
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade='all, delete-orphan')

class Upload(db.Model):
    """Model to track uploaded CSV files"""
    __tablename__ = 'uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)  # Support larger files up to 50MB
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    predictions = db.relationship('Prediction', backref='upload', lazy=True, cascade='all, delete-orphan')

class Prediction(db.Model):
    """Model to store prediction results"""
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False, index=True)
    predicted_price = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float)
    model_type = db.Column(db.String(50), default='Enhanced Linear Regression')
    prediction_data = db.Column(db.Text)  # JSON string of detailed prediction data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
