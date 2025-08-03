import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler, RobustScaler
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class StockPredictor:
    """Enhanced AI-powered stock price prediction using machine learning"""
    
    def __init__(self):
        self.models = {
            'linear': LinearRegression(),
            'ridge': Ridge(alpha=1.0),
            'lasso': Lasso(alpha=0.1),
            'forest': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        self.scaler = RobustScaler()  # More robust to outliers
        self.best_model = None
        self.best_model_name = None
        self.is_trained = False
        
    def predict_from_csv(self, filepath):
        """
        Process CSV file and generate stock price predictions with flexible data handling
        
        Args:
            filepath (str): Path to the uploaded CSV file
            
        Returns:
            dict: Prediction results with success status, predicted price, and details
        """
        try:
            # Read CSV file with optimized settings
            df = pd.read_csv(filepath, parse_dates=True, infer_datetime_format=True)
            
            # Log initial data info
            logging.info(f"Loaded CSV with {len(df)} rows and columns: {list(df.columns)}")
            
            # Flexible column detection and mapping
            df = self._map_columns(df)
            
            # Validate minimum requirements
            if df is None or len(df) < 5:
                return {
                    'success': False,
                    'error': 'Insufficient data. Need at least 5 data points for prediction.'
                }
            
            # Clean and prepare data
            df = self._clean_data(df)
            
            if len(df) < 5:
                return {
                    'success': False,
                    'error': 'Insufficient valid data after cleaning. Need at least 5 data points.'
                }
            
            # Enhanced feature engineering
            features_df = self._engineer_features(df)
            
            # Prepare training data
            X, y = self._prepare_training_data(features_df)
            
            if len(X) < 3:
                return {
                    'success': False,
                    'error': 'Insufficient data after feature engineering. Need more historical data.'
                }
            
            # Train multiple models and select best
            model_results = self._train_multiple_models(X, y)
            
            # Make predictions
            prediction_results = self._make_predictions(X, y, features_df)
            
            # Calculate additional metrics with USD to INR conversion
            usd_to_inr = 83.0  # Fixed conversion rate
            
            latest_price_usd = df['Close'].iloc[-1]
            predicted_price_usd = prediction_results['predicted_price']
            
            # Convert to INR
            latest_price_inr = latest_price_usd * usd_to_inr
            predicted_price_inr = predicted_price_usd * usd_to_inr
            
            price_change_inr = predicted_price_inr - latest_price_inr
            price_change_percent = (price_change_inr / latest_price_inr) * 100
            
            return {
                'success': True,
                'predicted_price': round(predicted_price_inr, 2),
                'confidence_score': round(prediction_results['confidence_score'], 3),
                'model_type': prediction_results['model_type'],
                'prediction_details': {
                    'latest_price': round(latest_price_inr, 2),
                    'predicted_change': round(price_change_inr, 2),
                    'predicted_change_percent': round(price_change_percent, 2),
                    'data_points_used': len(df),
                    'features_used': prediction_results['features_used'],
                    'mse': round(prediction_results['mse'], 4),
                    'r2_score': round(prediction_results['r2_score'], 3),
                    'mae': round(prediction_results['mae'], 4),
                    'model_comparison': model_results
                }
            }
            
        except Exception as e:
            logging.error(f"Prediction error: {e}")
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}'
            }
    
    def _map_columns(self, df):
        """Intelligently map CSV columns to required fields"""
        # Common column name patterns
        date_patterns = ['date', 'time', 'timestamp', 'day', 'datetime']
        price_patterns = ['close', 'price', 'closing', 'adj close', 'adjusted close']
        volume_patterns = ['volume', 'vol', 'shares', 'quantity']
        high_patterns = ['high', 'max', 'maximum', 'peak']
        low_patterns = ['low', 'min', 'minimum', 'bottom']
        open_patterns = ['open', 'opening', 'start']
        
        # Convert column names to lowercase for matching
        col_mapping = {}
        df_cols = [col.lower().strip() for col in df.columns]
        
        # Find date column
        date_col = None
        for i, col in enumerate(df_cols):
            if any(pattern in col for pattern in date_patterns):
                date_col = df.columns[i]
                break
        
        # If no date column found, try to use first column or create index
        if date_col is None:
            if len(df) > 0:
                # Create date index based on row number
                df['Date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
                date_col = 'Date'
        
        # Find price column (most important)
        price_col = None
        for i, col in enumerate(df_cols):
            if any(pattern in col for pattern in price_patterns):
                price_col = df.columns[i]
                break
        
        # If no price column found, use first numeric column
        if price_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                price_col = numeric_cols[0]
        
        if price_col is None:
            return None  # Can't proceed without price data
        
        # Create standardized dataframe
        result_df = pd.DataFrame()
        result_df['Date'] = df[date_col] if date_col else pd.date_range(start='2023-01-01', periods=len(df), freq='D')
        result_df['Close'] = pd.to_numeric(df[price_col], errors='coerce')
        
        # Find other columns if available
        for i, col in enumerate(df_cols):
            original_col = df.columns[i]
            if any(pattern in col for pattern in volume_patterns):
                result_df['Volume'] = pd.to_numeric(df[original_col], errors='coerce')
            elif any(pattern in col for pattern in high_patterns):
                result_df['High'] = pd.to_numeric(df[original_col], errors='coerce')
            elif any(pattern in col for pattern in low_patterns):
                result_df['Low'] = pd.to_numeric(df[original_col], errors='coerce')
            elif any(pattern in col for pattern in open_patterns):
                result_df['Open'] = pd.to_numeric(df[original_col], errors='coerce')
        
        return result_df
    
    def _clean_data(self, df):
        """Clean and validate the stock data"""
        # Convert Date column to datetime
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        except:
            # If date parsing fails, create sequential dates
            df['Date'] = pd.date_range(start='2023-01-01', periods=len(df), freq='D')
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Remove rows with missing Close prices
        df = df.dropna(subset=['Close'])
        
        # Ensure Close prices are numeric and positive
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close'])
        df = df[df['Close'] > 0]
        
        # Remove extreme outliers (prices more than 10x the median)
        if len(df) > 5:
            median_price = df['Close'].median()
            df = df[df['Close'] <= median_price * 10]
            df = df[df['Close'] >= median_price * 0.1]
        
        return df
    
    def _engineer_features(self, df):
        """Create enhanced features for the machine learning model"""
        features_df = df.copy()
        
        # Basic technical indicators
        for window in [3, 5, 10, 20]:
            if len(df) >= window:
                features_df[f'ma_{window}'] = features_df['Close'].rolling(window=window).mean()
                features_df[f'std_{window}'] = features_df['Close'].rolling(window=window).std()
        
        # Price changes and returns
        features_df['price_change'] = features_df['Close'].pct_change()
        features_df['price_change_abs'] = features_df['price_change'].abs()
        
        # Momentum indicators
        for lag in [1, 2, 3, 5]:
            if len(df) > lag:
                features_df[f'return_{lag}d'] = features_df['Close'].pct_change(periods=lag)
                features_df[f'price_lag_{lag}'] = features_df['Close'].shift(lag)
        
        # Volatility measures
        if len(df) >= 5:
            features_df['volatility_5d'] = features_df['price_change'].rolling(window=5).std()
        
        # Time-based features
        features_df['day_of_week'] = features_df['Date'].dt.dayofweek
        features_df['month'] = features_df['Date'].dt.month
        features_df['quarter'] = features_df['Date'].dt.quarter
        
        # Advanced features if OHLCV data available
        if 'High' in features_df.columns and 'Low' in features_df.columns:
            features_df['high_low_ratio'] = features_df['High'] / features_df['Low']
            features_df['price_position'] = (features_df['Close'] - features_df['Low']) / (features_df['High'] - features_df['Low'] + 1e-8)
        
        if 'Open' in features_df.columns:
            features_df['open_close_ratio'] = features_df['Open'] / features_df['Close']
            features_df['gap'] = (features_df['Open'] - features_df['Close'].shift(1)) / features_df['Close'].shift(1)
        
        if 'Volume' in features_df.columns:
            features_df['Volume'] = pd.to_numeric(features_df['Volume'], errors='coerce').fillna(0)
            if features_df['Volume'].sum() > 0:
                features_df['volume_ma_5'] = features_df['Volume'].rolling(window=5).mean()
                features_df['volume_ratio'] = features_df['Volume'] / (features_df['volume_ma_5'] + 1)
                features_df['price_volume'] = features_df['Close'] * features_df['Volume']
        
        return features_df
    
    def _prepare_training_data(self, df):
        """Prepare features and targets for training"""
        # Select features that are likely to be available and predictive
        feature_columns = []
        
        # Always include basic features
        if 'Date' in df.columns:
            df['date_ordinal'] = df['Date'].map(pd.Timestamp.toordinal)
            feature_columns.append('date_ordinal')
        
        # Add lag features (most important for time series)
        for lag in [1, 2, 3]:
            col = f'price_lag_{lag}'
            if col in df.columns:
                feature_columns.append(col)
        
        # Add moving averages
        for window in [3, 5, 10]:
            col = f'ma_{window}'
            if col in df.columns:
                feature_columns.append(col)
        
        # Add volatility and returns
        for col in ['price_change', 'volatility_5d', 'return_1d', 'return_2d']:
            if col in df.columns:
                feature_columns.append(col)
        
        # Add time features
        for col in ['day_of_week', 'month']:
            if col in df.columns:
                feature_columns.append(col)
        
        # Add OHLCV features if available
        for col in ['high_low_ratio', 'open_close_ratio', 'volume_ratio', 'price_position']:
            if col in df.columns:
                feature_columns.append(col)
        
        # Create feature matrix and target vector
        if not feature_columns:
            # Fallback: use simple date and lag features
            df['simple_trend'] = np.arange(len(df))
            df['close_lag_1'] = df['Close'].shift(1)
            feature_columns = ['simple_trend', 'close_lag_1']
        
        X = df[feature_columns].copy()
        y = df['Close'].copy()
        
        # Handle missing values
        X = X.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Remove rows where target is missing
        valid_indices = ~y.isnull()
        X = X[valid_indices]
        y = y[valid_indices]
        
        return X, y
    
    def _train_multiple_models(self, X, y):
        """Train multiple models and compare performance"""
        model_scores = {}
        
        if len(X) > 10:
            # Use cross-validation for larger datasets
            for name, model in self.models.items():
                try:
                    scores = cross_val_score(model, X, y, cv=min(5, len(X)//3), scoring='r2')
                    model_scores[name] = {
                        'mean_score': scores.mean(),
                        'std_score': scores.std(),
                        'scores': scores.tolist()
                    }
                except:
                    model_scores[name] = {'mean_score': 0, 'std_score': 1, 'scores': []}
        else:
            # For small datasets, use simple train-test split
            if len(X) > 5:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            for name, model in self.models.items():
                try:
                    model.fit(X_train_scaled, y_train)
                    score = model.score(X_test_scaled, y_test)
                    model_scores[name] = {'mean_score': score, 'std_score': 0, 'scores': [score]}
                except:
                    model_scores[name] = {'mean_score': 0, 'std_score': 1, 'scores': []}
        
        # Select best model
        if model_scores:
            self.best_model_name = max(model_scores.keys(), key=lambda k: model_scores[k]['mean_score'])
            self.best_model = self.models[self.best_model_name]
        else:
            self.best_model_name = 'linear'
            self.best_model = self.models['linear']
        
        return model_scores
    
    def _make_predictions(self, X, y, df):
        """Train the best model and make predictions"""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train the best model
        self.best_model.fit(X_scaled, y)
        self.is_trained = True
        
        # Make predictions on training data for evaluation
        y_pred = self.best_model.predict(X_scaled)
        
        # Calculate metrics
        mse = mean_squared_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        
        # Predict next price point
        latest_features = X.iloc[-1:].copy()
        
        # Adjust features for next time step
        if 'date_ordinal' in latest_features.columns:
            latest_features['date_ordinal'] = latest_features['date_ordinal'] + 1
        
        # For other features, use the latest values or trends
        latest_features_scaled = self.scaler.transform(latest_features)
        next_price_prediction = self.best_model.predict(latest_features_scaled)[0]
        
        # Calculate confidence score based on model performance
        confidence_score = max(0, min(1, r2)) if r2 > 0 else 0
        
        # Apply trend adjustment for more realistic predictions
        if len(y) >= 5:
            recent_trend = (y.iloc[-1] - y.iloc[-5]) / 5
            next_price_prediction += recent_trend * 0.3  # Dampen trend effect
        
        return {
            'predicted_price': float(next_price_prediction),
            'confidence_score': float(confidence_score),
            'mse': float(mse),
            'r2_score': float(r2),
            'mae': float(mae),
            'features_used': list(X.columns),
            'model_type': f'Enhanced {self.best_model_name.title()} Regression'
        }
