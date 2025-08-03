import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
from ml_predictor import StockPredictor

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///stock_analyzer.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import User, Upload, Prediction

with app.app_context():
    db.create_all()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def format_inr_currency(amount):
    """Format amount as Indian Rupees with commas"""
    return f"₹{amount:,.2f}"

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
    """Home page - always show login UI"""
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login - auto-creates account if email doesn't exist"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Email exists - check password and log in
            if check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['username'] = user.username
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'danger')
        else:
            # Email doesn't exist - create new account automatically
            password_hash = generate_password_hash(password)
            
            # Generate username from email
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.query.filter_by(username=username).first():
                username = f"{original_username}{counter}"
                counter += 1
            
            new_user = User()
            new_user.username = username
            new_user.email = email
            new_user.password_hash = password_hash
            
            try:
                db.session.add(new_user)
                db.session.commit()
                session['user_id'] = new_user.id
                session['username'] = new_user.username
                flash(f'Account created and logged in successfully! Welcome, {new_user.username}!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('Login failed. Please try again.', 'danger')
                app.logger.error(f"Auto-registration error: {e}")
    
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
            
            if file and file.filename and file.filename.lower().endswith('.csv'):
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
                
                # Test CSV reading
                try:
                    test_df = pd.read_csv(filepath)
                    app.logger.info(f"CSV loaded successfully with {len(test_df)} rows and columns: {list(test_df.columns)}")
                except Exception as csv_error:
                    flash(f'Invalid CSV file format: {str(csv_error)}', 'danger')
                    app.logger.error(f"CSV reading error: {csv_error}")
                    return redirect(request.url)
                
                # Record the upload
                upload = Upload()
                upload.user_id = session['user_id']
                upload.filename = filename
                upload.original_filename = file.filename
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
                flash('Please upload a valid CSV file.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'danger')
            app.logger.error(f"Upload processing error: {e}")
    
    return render_template('upload.html')

@app.route('/prediction/<int:prediction_id>')
@login_required
def view_prediction(prediction_id):
    """View detailed prediction results"""
    prediction = Prediction.query.filter_by(id=prediction_id, user_id=session['user_id']).first()
    
    if not prediction:
        flash('Prediction not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('prediction_results.html', prediction=prediction)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)