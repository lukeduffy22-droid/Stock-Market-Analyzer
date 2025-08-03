import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager
import pandas as pd
from datetime import datetime
from ml_predictor import StockPredictor
import os
from dotenv import load_dotenv
from extensions import db
from models import User, Upload, Prediction
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

##class Base(DeclarativeBase):
  ##  pass
##db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure PostgreSQL database (permanent storage)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required for persistent storage")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
}
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import User, Upload, Prediction

with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def format_inr_currency(amount):
    """Format amount as Indian Rupees with commas"""
    if amount is None or amount == '':
        return "₹0.00"
    try:
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

# Add template filter for currency formatting
app.jinja_env.filters['inr'] = format_inr_currency

def login_required(f):
    """Decorator to require login for certain routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page - redirect to login"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.email.split('@')[0]  # optional username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')
@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing prediction history"""
    try:
        user_id = session['user_id']
        
        # Get recent predictions for this user
        recent_predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).limit(10).all()
        
        # Process prediction data for template
        processed_predictions = []
        for prediction in recent_predictions:
            prediction_info = {
                'id': prediction.id,
                'created_at': prediction.created_at,
                'predicted_price': prediction.predicted_price,
                'confidence_score': prediction.confidence_score,
                'model_type': prediction.model_type,
                'upload': prediction.upload,
                'latest_price': None,
                'predicted_change': None,
                'predicted_change_percent': None
            }
            
            # Parse prediction data safely
            if prediction.prediction_data:
                try:
                    import ast
                    details = ast.literal_eval(prediction.prediction_data)
                    prediction_info['latest_price'] = details.get('latest_price', prediction.predicted_price * 0.95)
                    prediction_info['predicted_change'] = details.get('predicted_change', prediction.predicted_price - prediction_info['latest_price'])
                    prediction_info['predicted_change_percent'] = details.get('predicted_change_percent', 0)
                except:
                    # Fallback values if parsing fails
                    prediction_info['latest_price'] = prediction.predicted_price * 0.95
                    prediction_info['predicted_change'] = prediction.predicted_price - prediction_info['latest_price']
                    prediction_info['predicted_change_percent'] = (prediction_info['predicted_change'] / prediction_info['latest_price'] * 100)
            else:
                # Fallback values if no prediction data
                prediction_info['latest_price'] = prediction.predicted_price * 0.95
                prediction_info['predicted_change'] = prediction.predicted_price - prediction_info['latest_price']
                prediction_info['predicted_change_percent'] = (prediction_info['predicted_change'] / prediction_info['latest_price'] * 100)
            
            processed_predictions.append(prediction_info)
        
        # Get upload history
        uploads = Upload.query.filter_by(user_id=user_id).order_by(Upload.created_at.desc()).limit(5).all()
        
        app.logger.info(f"Dashboard loaded for user {user_id} with {len(processed_predictions)} predictions")
        
        return render_template('dashboard.html', predictions=processed_predictions, uploads=uploads)
        
    except Exception as e:
        app.logger.error(f"Dashboard error for user {session.get('user_id')}: {e}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    """Handle CSV file upload and prediction"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('No file selected.', 'danger')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected.', 'danger')
                return redirect(request.url)
            
            if file and file.filename:
                # Accept any file extension but validate content
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                app.logger.info(f"Saving file to: {filepath}")
                file.save(filepath)
                
                # Verify file exists and is readable
                if not os.path.exists(filepath):
                    flash('Error saving file. Please try again.', 'danger')
                    return redirect(request.url)
                
                # Get file size for storage
                file_size = os.path.getsize(filepath)
                
                # Test CSV reading with flexible parsing
                try:
                    # Try different separators and encodings
                    df = None
                    for sep in [',', ';', '\t']:
                        for encoding in ['utf-8', 'latin-1', 'cp1252']:
                            try:
                                df = pd.read_csv(filepath, sep=sep, encoding=encoding, nrows=5)
                                if len(df.columns) > 1:  # Valid CSV structure
                                    break
                            except:
                                continue
                        if df is not None and len(df.columns) > 1:
                            break
                    
                    if df is None or len(df.columns) <= 1:
                        flash('Unable to parse file. Please ensure it\'s a valid CSV format.', 'danger')
                        os.remove(filepath)
                        return redirect(request.url)
                    
                    # Re-read full file with correct parameters
                    df = pd.read_csv(filepath, sep=sep, encoding=encoding)
                    app.logger.info(f"CSV loaded successfully with {len(df)} rows and columns: {list(df.columns)}")
                    
                except Exception as csv_error:
                    flash(f'Invalid file format: {str(csv_error)}', 'danger')
                    app.logger.error(f"CSV reading error: {csv_error}")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return redirect(request.url)
                
                # Record the upload
                upload = Upload()
                upload.user_id = session['user_id']
                upload.filename = filename
                upload.original_filename = file.filename
                upload.file_size = file_size
                db.session.add(upload)
                db.session.commit()
                app.logger.info(f"Upload recorded with ID: {upload.id}")
                
                # Process the file and make predictions
                app.logger.info("Starting prediction process...")
                predictor = StockPredictor()
                results = predictor.predict_from_csv(filepath)
                app.logger.info(f"Prediction results: {results.get('success', False)}")
                
                if results['success']:
                    # Save prediction results
                    prediction = Prediction()
                    prediction.user_id = session['user_id']
                    prediction.upload_id = upload.id
                    prediction.predicted_price = results['predicted_price']
                    prediction.confidence_score = results['confidence_score']
                    prediction.model_type = results['model_type']
                    prediction.prediction_data = str(results['prediction_details'])
                    db.session.add(prediction)
                    db.session.commit()
                    app.logger.info(f"Prediction saved with ID: {prediction.id}")
                    
                    flash('File uploaded and prediction completed successfully!', 'success')
                    return render_template('prediction_results.html', results=results, upload=upload)
                else:
                    error_msg = results.get('error', 'Unknown prediction error')
                    flash(f'Prediction failed: {error_msg}', 'danger')
                    app.logger.error(f"Prediction failed: {error_msg}")
                    
            else:
                flash('Please upload a valid file.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'danger')
            app.logger.error(f"Upload processing error: {e}")
    
    return render_template('upload.html')

@app.route('/prediction/<int:prediction_id>')
@login_required
def view_prediction(prediction_id):
    """View detailed prediction results"""
    try:
        prediction = Prediction.query.filter_by(id=prediction_id, user_id=session['user_id']).first()
        
        if not prediction:
            flash('Prediction not found.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Format prediction data for display with safe defaults
        prediction_details = {
            'latest_price': 0.0,
            'predicted_change': 0.0,
            'predicted_change_percent': 0.0,
            'data_points': 0,
            'features_used': []
        }
        
        if prediction.prediction_data:
            try:
                import re
                import json
                
                # Clean numpy types from the stored data string more thoroughly
                cleaned_data = prediction.prediction_data
                
                # Replace numpy types with regular Python types
                cleaned_data = re.sub(r'np\.float64\(([\d\.-]+)\)', r'\1', cleaned_data)
                cleaned_data = re.sub(r'np\.int64\((\d+)\)', r'\1', cleaned_data)
                cleaned_data = re.sub(r'np\.array\([^)]+\)', r'[]', cleaned_data)
                
                # Replace single quotes with double quotes for JSON parsing
                cleaned_data = re.sub(r"'([^']*)':", r'"\1":', cleaned_data)
                cleaned_data = re.sub(r": '([^']*)'", r': "\1"', cleaned_data)
                
                try:
                    # Try JSON parsing first
                    stored_data = json.loads(cleaned_data)
                except json.JSONDecodeError:
                    # Fall back to manual parsing for simple cases
                    try:
                        # Use eval with a restricted environment for safety
                        safe_dict = {"__builtins__": {}}
                        stored_data = eval(cleaned_data, safe_dict)
                    except:
                        # Last resort: extract key-value pairs manually
                        stored_data = {}
                        # Extract numeric values with regex
                        patterns = {
                            'latest_price': r"'latest_price':\s*([\d\.-]+)",
                            'predicted_change': r"'predicted_change':\s*([\d\.-]+)", 
                            'predicted_change_percent': r"'predicted_change_percent':\s*([\d\.-]+)",
                            'data_points_used': r"'data_points_used':\s*(\d+)",
                            'mse': r"'mse':\s*([\d\.-]+)",
                            'r2_score': r"'r2_score':\s*([\d\.-]+)",
                            'mae': r"'mae':\s*([\d\.-]+)"
                        }
                        
                        for key, pattern in patterns.items():
                            match = re.search(pattern, prediction.prediction_data)
                            if match:
                                try:
                                    stored_data[key] = float(match.group(1))
                                except ValueError:
                                    stored_data[key] = 0.0
                
                # Safely update prediction details
                if isinstance(stored_data, dict):
                    prediction_details.update(stored_data)
                    
            except Exception as e:
                app.logger.warning(f"Could not parse prediction data for ID {prediction_id}: {e}")
                # Continue with default values
        
        # Ensure numeric values are properly set
        predicted_price = prediction.predicted_price or 0.0
        latest_price = prediction_details.get('latest_price', 0.0)
        
        # Calculate changes if not already present
        if latest_price > 0:
            predicted_change = predicted_price - latest_price
            predicted_change_percent = (predicted_change / latest_price) * 100 if latest_price > 0 else 0.0
        else:
            predicted_change = 0.0
            predicted_change_percent = 0.0
            
        prediction_details.update({
            'latest_price': latest_price,
            'predicted_change': predicted_change,
            'predicted_change_percent': predicted_change_percent
        })
        
        results = {
            'success': True,
            'predicted_price': predicted_price,
            'confidence_score': prediction.confidence_score or 0.0,
            'model_type': prediction.model_type or 'Unknown',
            'prediction_details': prediction_details
        }
        
        app.logger.info(f"Displaying prediction {prediction_id} for user {session['user_id']}")
        return render_template('prediction_results.html', results=results, prediction=prediction, upload=prediction.upload)
        
    except Exception as e:
        app.logger.error(f"Error viewing prediction {prediction_id}: {e}")
        flash('An error occurred while loading the prediction. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
