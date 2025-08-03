# AI Stock Market Analyzer

## Overview

This is a Flask-based web application that provides AI-powered stock market analysis and prediction capabilities. Users can upload CSV files containing historical stock data and receive machine learning-powered price predictions. The application features user authentication, file upload management, and multiple ML models for enhanced prediction accuracy.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **UI Framework**: Bootstrap 5 with dark theme (Replit-themed CSS)
- **Icons**: Font Awesome 6.0
- **Responsive Design**: Mobile-first approach with Bootstrap grid system
- **Client-side Interactions**: Enhanced JavaScript for file uploads, form validation, and UI enhancements
- **Theme**: Dark theme with gradient backgrounds and smooth animations

### Backend Architecture
- **Web Framework**: Flask (Python) with ProxyFix middleware for deployment
- **Database ORM**: SQLAlchemy with DeclarativeBase pattern
- **Session Management**: Flask sessions with configurable secret keys
- **File Handling**: Werkzeug utilities for secure file uploads with 50MB limit
- **Authentication**: Password hashing with Werkzeug security utilities
- **Logging**: Comprehensive logging system for debugging and monitoring

### Machine Learning Architecture
- **ML Framework**: scikit-learn with multiple model support
- **Models**: Linear Regression, Ridge, Lasso, and Random Forest Regressor
- **Model Selection**: Cross-validation for automatic best model selection
- **Data Processing**: pandas for CSV handling with flexible column mapping
- **Preprocessing**: RobustScaler for outlier-resistant feature scaling
- **Feature Engineering**: Automated technical indicators and time series features

## Key Components

### Database Models
1. **User Model** (users table): 
   - Manages user authentication with username/email
   - Includes timestamps and indexing for performance
   - Cascading relationships for data integrity
2. **Upload Model** (uploads table): 
   - Tracks uploaded CSV files with metadata
   - Supports large files (BigInteger for file size)
   - Links to user and prediction records
3. **Prediction Model** (predictions table): 
   - Stores ML prediction results and confidence scores
   - JSON field for detailed prediction analytics
   - Tracks model type used for each prediction

### Core Modules
1. **app.py**: Main Flask application with comprehensive route handling
2. **models.py**: SQLAlchemy database models with proper relationships and constraints
3. **ml_predictor.py**: Enhanced StockPredictor class with multiple ML algorithms
4. **main.py**: Application entry point for development server

### Template Structure
- **base.html**: Master template with responsive navigation and dark theme
- **dashboard.html**: User statistics, prediction history, and analytics
- **upload.html**: File upload interface with drag-and-drop support
- **prediction_results.html**: Detailed prediction display with charts and insights
- **login.html**: Authentication form with auto-registration capability

## Data Flow

### File Upload Process
1. User uploads CSV file through web interface
2. File validation and secure storage in uploads directory
3. Flexible column mapping for various CSV formats
4. Data cleaning and preprocessing pipeline
5. Feature engineering with technical indicators
6. Model training and selection using cross-validation
7. Prediction generation with confidence scoring
8. Results storage in database with detailed analytics

### Authentication Flow
1. Email/password based login system
2. Automatic user registration for new emails
3. Session-based authentication with secure cookies
4. Password hashing using Werkzeug utilities
5. User-specific data access and authorization

## External Dependencies

### Python Packages
- **Flask**: Web framework and templating
- **SQLAlchemy**: Database ORM and migrations
- **scikit-learn**: Machine learning models and preprocessing
- **pandas**: Data manipulation and CSV processing
- **numpy**: Numerical computations
- **Werkzeug**: Security utilities and file handling

### Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme
- **Font Awesome 6**: Icon library
- **Custom CSS**: Enhanced styling with gradients and animations
- **JavaScript**: File upload enhancements and form validation

### Database Support
- **Primary**: PostgreSQL with persistent storage
- **Connection**: Environment-based DATABASE_URL configuration
- **Features**: Connection pooling, auto-reconnection, optimized indexing, and performance optimization
- **Persistence**: All data persists across sessions and deployments

## Deployment Strategy

### Database Configuration
- PostgreSQL production setup with persistent storage
- Environment-based DATABASE_URL configuration (required)
- Optimized connection pooling (pool_size: 10, max_overflow: 20)
- Automatic table creation with comprehensive indexing
- Data persistence across all sessions and deployments

### Application Configuration
- Environment variable based configuration
- Secure session management with configurable secrets
- File upload limits and security restrictions
- Proxy-aware setup for deployment behind reverse proxies

### Performance Optimizations
- Database connection pooling with configurable parameters
- Indexed database columns for query performance
- Robust scaler for handling outliers in ML pipeline
- Cascading deletes for data integrity and cleanup

### Security Features
- Password hashing with Werkzeug security
- Secure file upload with filename sanitization
- Session-based authentication with secure cookies
- Input validation and SQL injection prevention through ORM