# Smart Parking AI Module

This module provides AI-powered predictions and recommendations for the Smart Parking system.

## Features

- **Parking Spot Availability Prediction**: Uses machine learning to predict the probability of a parking spot being available at a specific time.
- **Parking Spot Recommendations**: Recommends the best parking spots based on user location and availability predictions.
- **Historical Data Collection**: Collects and stores historical parking spot occupancy data for training models.

## Machine Learning Model

The system uses a RandomForest classifier to predict parking spot availability. The model:

- Uses time-based features (hour, day of week, month, etc.)
- Considers business hours, weekends, and rush hours
- Handles cyclical time features using sine/cosine transformations
- Improves over time as more data is collected

## Fallback Mechanisms

The prediction system has multiple fallback mechanisms:

1. **ML Model**: First tries to use the trained machine learning model
2. **Statistical Method**: If ML model is not available or fails, uses historical statistics
3. **Heuristic Method**: If not enough historical data, uses simple rules based on time of day and day of week

## API Endpoints

### 1. Parking Availability Prediction

```
GET /api/ai/predictions/parking-spot/<uuid:spot_id>/
```

Parameters:
- `spot_id`: UUID of the parking spot
- `target_time` (optional): ISO format datetime for prediction (default: current time)

Response:
```json
{
  "spot_id": "550e8400-e29b-41d4-a716-446655440000",
  "probability_available": 0.85,
  "prediction_time": "2023-06-01T14:30:00Z",
  "prediction_method": "machine_learning",
  "confidence_level": "high",
  "data_points": 120,
  "has_ml_model": true
}
```

### 2. Recommended Parking Spots

```
GET /api/ai/recommendations/parking-spots/
```

Parameters:
- `latitude`: User's latitude
- `longitude`: User's longitude
- `radius` (optional): Search radius in kilometers (default: 1.0)
- `limit` (optional): Maximum number of spots to return (default: 5)

Response:
```json
[
  {
    "parking_spot": {
      "id": 1,
      "reference": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Spot A1",
      "is_lock": false,
      "is_occupied": false,
      "is_blocker_raised": true,
      "latitude1": 43.2351,
      "longitude1": 76.9099,
      "latitude2": 43.2352,
      "longitude2": 76.9099,
      "latitude3": 43.2352,
      "longitude3": 76.9100,
      "latitude4": 43.2351,
      "longitude4": 76.9100
    },
    "distance": 0.25,
    "probability_available": 0.85,
    "is_reserved": false,
    "score": 0.75
  },
  // More spots...
]
```

### 3. Update Occupancy History

```
POST /api/ai/update-occupancy-history/
```

Response:
```json
{
  "status": "success",
  "message": "Occupancy history updated"
}
```

## Management Commands

### Train AI Models

Train machine learning models for all parking spots:

```bash
python manage.py train_ai_models
```

Train a model for a specific parking spot:

```bash
python manage.py train_ai_models --spot-id=550e8400-e29b-41d4-a716-446655440000
```

Force retraining even if models already exist:

```bash
python manage.py train_ai_models --force
```

### Generate Sample Data

Generate sample historical data for parking spots to enable AI model training:

```bash
python manage.py generate_sample_data
```

Generate data for a specific number of days (default is 7):

```bash
python manage.py generate_sample_data --days=14
```

Generate a specific number of samples per day (default is 24, one per hour):

```bash
python manage.py generate_sample_data --samples-per-day=48
```

Generate data for a specific parking spot:

```bash
python manage.py generate_sample_data --spot-id=550e8400-e29b-41d4-a716-446655440000
```

Clear existing historical data before generating new data:

```bash
python manage.py generate_sample_data --clear
```

## Integration with Frontend

The frontend displays prediction information in the parking spot popups and provides an "AI Recommendations" button that shows the best available parking spots based on the user's location.

## Maintenance

- Models are automatically trained when new occupancy data is collected
- Models are stored in the `models` directory at the project root
- Each parking spot has its own model file named `parking_model_<spot_id>.joblib`
