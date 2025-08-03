import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging

class StockPredictor:
    """AI-powered stock price prediction using machine learning"""
    
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def predict_from_csv(self, filepath):
        """
        Process CSV file and generate stock price predictions
        
        Args:
            filepath (str): Path to the uploaded CSV file
            
        Returns:
            dict: Prediction results with success status, predicted price, and details
        """
        try:
            # Read CSV file
            df = pd.read_csv(filepath)
            
            # Validate required columns
            required_columns = ['Date', 'Close']
            if not all(col in df.columns for col in required_columns):
                return {
                    'success': False,
                    'error': f'CSV must contain columns: {", ".join(required_columns)}. Found: {", ".join(df.columns)}'
                }
            
            # Clean and prepare data
            df = self._clean_data(df)
            
            if len(df) < 10:
                return {
                    'success': False,
                    'error': 'Insufficient data. Need at least 10 data points for prediction.'
                }
            
            # Feature engineering
            features = self._engineer_features(df)
            
            # Prepare training data
            X, y = self._prepare_training_data(features)
            
            if len(X) < 5:
                return {
                    'success': False,
                    'error': 'Insufficient data after preprocessing. Need more historical data.'
                }
            
            # Train model and make prediction
            prediction_results = self._train_and_predict(X, y)
            
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
                'model_type': 'Linear Regression',
                'prediction_details': {
                    'latest_price': round(latest_price_inr, 2),
                    'predicted_change': round(price_change_inr, 2),
                    'predicted_change_percent': round(price_change_percent, 2),
                    'data_points_used': len(df),
                    'features_used': prediction_results['features_used'],
                    'mse': round(prediction_results['mse'], 4),
                    'r2_score': round(prediction_results['r2_score'], 3)
                }
            }
            
        except Exception as e:
            logging.error(f"Prediction error: {e}")
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}'
            }
    
    def _clean_data(self, df):
        """Clean and validate the stock data"""
        # Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Remove rows with missing Close prices
        df = df.dropna(subset=['Close'])
        
        # Ensure Close prices are numeric
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close'])
        
        # Remove any obviously invalid prices (negative or zero)
        df = df[df['Close'] > 0]
        
        return df
    
    def _engineer_features(self, df):
        """Create features for the machine learning model"""
        features_df = df.copy()
        
        # Technical indicators
        features_df['price_ma_5'] = features_df['Close'].rolling(window=5).mean()
        features_df['price_ma_10'] = features_df['Close'].rolling(window=10).mean()
        
        # Price changes and volatility
        features_df['price_change'] = features_df['Close'].pct_change()
        features_df['price_volatility'] = features_df['price_change'].rolling(window=5).std()
        
        # Trend indicators
        features_df['trend_5d'] = (features_df['Close'] - features_df['Close'].shift(5)) / features_df['Close'].shift(5)
        
        # Day of week and month (cyclical features)
        features_df['day_of_week'] = features_df['Date'].dt.dayofweek
        features_df['month'] = features_df['Date'].dt.month
        
        # Add volume if available
        if 'Volume' in df.columns:
            features_df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
            features_df['volume_ma_5'] = features_df['Volume'].rolling(window=5).mean()
            features_df['price_volume_ratio'] = features_df['Close'] / (features_df['Volume'] + 1)
        
        # Add OHLC features if available
        for col in ['Open', 'High', 'Low']:
            if col in df.columns:
                features_df[col] = pd.to_numeric(df[col], errors='coerce')
                if col == 'High' and 'Low' in df.columns:
                    features_df['high_low_ratio'] = features_df['High'] / features_df['Low']
                if col == 'Open':
                    features_df['open_close_ratio'] = features_df['Open'] / features_df['Close']
        
        return features_df
    
    def _prepare_training_data(self, df):
        """Prepare features and targets for training using Date as ordinal and Close price"""
        # Convert Date to ordinal numbers (days since a reference date)
        df['date_ordinal'] = df['Date'].map(pd.Timestamp.toordinal)
        
        # Use simple but effective features: date ordinal and moving averages
        feature_columns = ['date_ordinal']
        
        # Add moving averages if we have enough data
        if len(df) >= 5:
            df['close_ma_3'] = df['Close'].rolling(window=3).mean()
            df['close_ma_5'] = df['Close'].rolling(window=5).mean()
            feature_columns.extend(['close_ma_3', 'close_ma_5'])
        
        # Add lag features
        df['close_lag_1'] = df['Close'].shift(1)
        df['close_lag_2'] = df['Close'].shift(2)
        feature_columns.extend(['close_lag_1', 'close_lag_2'])
        
        # Create feature matrix and target vector
        X = df[feature_columns].ffill().bfill()
        y = df['Close']
        
        # Remove rows where any feature or target is still NaN
        valid_indices = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[valid_indices]
        y = y[valid_indices]
        
        return X, y
    
    def _train_and_predict(self, X, y):
        """Train the model and make predictions"""
        # Split data for training and testing
        if len(X) > 20:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        else:
            # For small datasets, use all data for training
            X_train, X_test, y_train, y_test = X, X.iloc[-1:], y, y.iloc[-1:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train the model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Make predictions on test set for evaluation
        y_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Predict next price point (extrapolate to next day)
        latest_features = X.iloc[-1:].copy()
        
        # Increment date ordinal by 1 for next day prediction
        if 'date_ordinal' in latest_features.columns:
            latest_features['date_ordinal'] = latest_features['date_ordinal'] + 1
        
        latest_features_scaled = self.scaler.transform(latest_features)
        next_price_prediction = self.model.predict(latest_features_scaled)[0]
        
        # Calculate confidence score based on R² score (convert to percentage)
        confidence_score = max(0, min(1, r2)) if r2 > 0 else 0
        
        return {
            'predicted_price': float(next_price_prediction),
            'confidence_score': float(confidence_score),
            'mse': float(mse),
            'r2_score': float(r2),
            'features_used': list(X.columns)
        }
