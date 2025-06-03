import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

# Create models directory if it doesn't exist
MODELS_DIR = os.path.join(settings.BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

class ParkingAvailabilityModel:
    """
    Machine learning model for predicting parking spot availability.
    Uses RandomForest classifier with time-based features.
    """
    def __init__(self, spot_id):
        self.spot_id = spot_id
        self.model_path = os.path.join(MODELS_DIR, f'parking_model_{spot_id}.joblib')
        self.scaler_path = os.path.join(MODELS_DIR, f'parking_scaler_{spot_id}.joblib')
        
        # Load model if exists, otherwise create a new one
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
        else:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.scaler = StandardScaler()
    
    def _extract_features(self, timestamp):
        """
        Extract time-based features from timestamp.
        
        Args:
            timestamp: datetime object
            
        Returns:
            numpy array of features
        """
        # Time-based features
        hour = timestamp.hour
        minute = timestamp.minute
        day_of_week = timestamp.weekday()
        month = timestamp.month
        is_weekend = 1 if day_of_week >= 5 else 0  # 5,6 = weekend
        
        # Time periods (morning, afternoon, evening, night)
        if 6 <= hour < 12:
            time_period = 0  # morning
        elif 12 <= hour < 17:
            time_period = 1  # afternoon
        elif 17 <= hour < 22:
            time_period = 2  # evening
        else:
            time_period = 3  # night
        
        # Business hours (8am-6pm on weekdays)
        is_business_hours = 1 if (8 <= hour <= 18 and day_of_week < 5) else 0
        
        # Rush hours (8-10am and 5-7pm on weekdays)
        is_rush_hour = 1 if ((8 <= hour <= 10 or 17 <= hour <= 19) and day_of_week < 5) else 0
        
        # Sine and cosine transformations for cyclical features
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        
        # Combine all features
        features = np.array([
            hour, minute, day_of_week, month, is_weekend, 
            time_period, is_business_hours, is_rush_hour,
            hour_sin, hour_cos, day_sin, day_cos
        ]).reshape(1, -1)
        
        return features
    
    def train(self, history_data):
        """
        Train the model using historical occupancy data.
        
        Args:
            history_data: List of dictionaries with 'timestamp' and 'is_occupied' keys
            
        Returns:
            True if training was successful, False otherwise
        """
        if len(history_data) < 10:
            return False  # Not enough data for training
        
        # Prepare training data
        X = []
        y = []
        
        for entry in history_data:
            timestamp = entry['timestamp']
            features = self._extract_features(timestamp)[0]  # Flatten the array
            X.append(features)
            y.append(1 if entry['is_occupied'] else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Save model and scaler
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        return True
    
    def predict(self, timestamp):
        """
        Predict parking spot availability at the given timestamp.
        
        Args:
            timestamp: datetime object
            
        Returns:
            float: Probability that the spot will be available (0-1)
        """
        features = self._extract_features(timestamp)
        
        try:
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict probability of being occupied
            occupied_prob = self.model.predict_proba(features_scaled)[0][1]
            
            # Return probability of being available
            return 1 - occupied_prob
        except Exception as e:
            # If prediction fails, return None
            print(f"Error predicting with ML model: {e}")
            return None

def train_all_models(spot_ids=None):
    """
    Train models for all parking spots or specified spot IDs.
    
    Args:
        spot_ids: List of parking spot IDs to train models for (optional)
        
    Returns:
        dict: Dictionary with spot IDs as keys and training success as values
    """
    from .models import ParkingSpotOccupancyHistory
    from sensor.models import ParkingSpot
    
    results = {}
    
    # Get all parking spots or filter by spot_ids
    if spot_ids:
        spots = ParkingSpot.objects.filter(reference__in=spot_ids)
    else:
        spots = ParkingSpot.objects.all()
    
    for spot in spots:
        # Get historical data for this spot
        history = ParkingSpotOccupancyHistory.objects.filter(
            parking_spot=spot
        ).order_by('timestamp')
        
        if history.count() < 10:
            results[spot.reference] = False
            continue
        
        # Prepare data for training
        history_data = [
            {
                'timestamp': entry.timestamp,
                'is_occupied': entry.is_occupied
            }
            for entry in history
        ]
        
        # Train model
        model = ParkingAvailabilityModel(spot.reference)
        success = model.train(history_data)
        results[spot.reference] = success
    
    return results