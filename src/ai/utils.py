import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg
from sensor.models import ParkingSpot
from .models import ParkingSpotOccupancyHistory, ParkingAvailabilityPrediction
from .ml_models import ParkingAvailabilityModel, train_all_models


def predict_parking_availability(parking_spot_id, target_time=None):
    """
    Predict the probability of a parking spot being available at a given time.
    Uses machine learning model if available, otherwise falls back to statistical or heuristic methods.

    Args:
        parking_spot_id: The ID of the parking spot
        target_time: The time for which to make the prediction (default: current time)

    Returns:
        float: Probability that the spot will be available (0-1)
    """
    if target_time is None:
        target_time = timezone.now()

    # Get the parking spot
    try:
        parking_spot = ParkingSpot.objects.get(reference=parking_spot_id)
    except ParkingSpot.DoesNotExist:
        return None

    # Check if there's already a prediction for this time (within the same minute)
    # Use a range query instead of exact match to avoid microsecond precision issues
    prediction_time_min = target_time.replace(second=0, microsecond=0)
    prediction_time_max = prediction_time_min + timedelta(minutes=1)

    existing_prediction = ParkingAvailabilityPrediction.objects.filter(
        parking_spot=parking_spot,
        prediction_time__gte=prediction_time_min,
        prediction_time__lt=prediction_time_max
    ).first()

    if existing_prediction:
        return existing_prediction.probability_available

    # Try to use ML model for prediction
    ml_model = ParkingAvailabilityModel(parking_spot_id)
    ml_prediction = ml_model.predict(target_time)

    if ml_prediction is not None:
        # ML model prediction successful
        probability_available = ml_prediction
    else:
        # ML model not available or prediction failed, fall back to statistical/heuristic methods

        # Get historical data for this parking spot on the same day of week and hour
        day_of_week = target_time.weekday()
        hour_of_day = target_time.hour

        historical_data = ParkingSpotOccupancyHistory.objects.filter(
            parking_spot=parking_spot,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day
        )

        # If we have enough historical data, use statistical method
        if historical_data.count() >= 5:
            # Calculate the probability of the spot being available based on historical data
            available_count = historical_data.filter(is_occupied=False).count()
            probability_available = available_count / historical_data.count()
        else:
            # Not enough historical data, use a simple heuristic
            # Weekday business hours (8am-6pm) are typically busier
            is_weekday = day_of_week < 5  # Monday-Friday
            is_business_hours = 8 <= hour_of_day <= 18

            if is_weekday and is_business_hours:
                probability_available = 0.3  # 30% chance of being available during busy hours
            else:
                probability_available = 0.7  # 70% chance of being available during off-hours

    # Store the prediction with error handling
    try:
        # Round the prediction time to the nearest minute to avoid precision issues
        rounded_time = target_time.replace(second=0, microsecond=0)

        ParkingAvailabilityPrediction.objects.create(
            parking_spot=parking_spot,
            prediction_time=rounded_time,
            probability_available=probability_available
        )
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error creating prediction for spot {parking_spot_id}: {e}")
        # We can still return the calculated probability even if storing fails

    return probability_available


def get_recommended_parking_spots(latitude, longitude, radius=1.0, limit=5):
    """
    Get recommended parking spots based on location and availability prediction.

    Args:
        latitude: User's latitude
        longitude: User's longitude
        radius: Search radius in kilometers
        limit: Maximum number of spots to return

    Returns:
        list: List of recommended parking spots with availability predictions
    """
    # Get all parking spots
    all_spots = ParkingSpot.objects.all()

    # Calculate distance and get spots within radius
    spots_with_distance = []
    for spot in all_spots:
        # Use the center point of the parking spot
        spot_lat = (spot.latitude1 + spot.latitude2 + spot.latitude3 + spot.latitude4) / 4
        spot_lng = (spot.longitude1 + spot.longitude2 + spot.longitude3 + spot.longitude4) / 4

        # Calculate distance using Haversine formula
        distance = calculate_distance(latitude, longitude, spot_lat, spot_lng)

        if distance <= radius:
            spots_with_distance.append((spot, distance))

    # Sort by distance
    spots_with_distance.sort(key=lambda x: x[1])

    # Get availability predictions for the closest spots
    now = timezone.now()
    recommendations = []

    for spot, distance in spots_with_distance[:limit]:
        try:
            # Get or create prediction
            probability_available = predict_parking_availability(spot.reference, now)

            # Default values in case of errors
            is_reserved = False

            try:
                # Check if the spot is currently reserved
                is_reserved = spot.is_reserved()
            except Exception as e:
                print(f"Error checking reservation status for spot {spot.reference}: {e}")
                # Continue with default value

            # Calculate a score based on availability and distance
            # Higher score = better recommendation
            if is_reserved:
                availability_score = 0
            else:
                availability_score = probability_available if probability_available is not None else 0.5

            # Normalize distance to 0-1 range (closer = higher score)
            distance_score = 1 - (distance / radius)

            # Combined score (70% availability, 30% distance)
            score = (0.7 * availability_score) + (0.3 * distance_score)

            recommendations.append({
                'parking_spot': spot,
                'distance': distance,
                'probability_available': probability_available if probability_available is not None else 0.5,
                'is_reserved': is_reserved,
                'score': score
            })
        except Exception as e:
            print(f"Error processing recommendation for spot {spot.reference}: {e}")
            # Skip this spot and continue with the next one

    # Sort by score (highest first)
    recommendations.sort(key=lambda x: x['score'], reverse=True)

    return recommendations


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def update_occupancy_history(train_models=True):
    """
    Update the occupancy history for all parking spots and optionally train ML models.
    This should be called periodically to collect data for predictions.

    Args:
        train_models: Whether to train ML models after updating history (default: True)

    Returns:
        dict: Dictionary with results of the operation
    """
    now = timezone.now()
    updated_spots = []
    errors = []

    for spot in ParkingSpot.objects.all():
        # Get the current occupancy state from the sensor
        try:
            sensor = spot.sensor
            is_occupied = sensor.is_occupied

            # Record the occupancy state
            ParkingSpotOccupancyHistory.objects.create(
                parking_spot=spot,
                timestamp=now,
                is_occupied=is_occupied,
                day_of_week=now.weekday(),
                hour_of_day=now.hour
            )
            updated_spots.append(spot.reference)
        except Exception as e:
            error_msg = f"Error updating occupancy history for spot {spot.reference}: {e}"
            print(error_msg)
            errors.append(error_msg)

    # Train models if requested and if we have updated spots
    training_results = {}
    if train_models and updated_spots:
        try:
            # Only train models for spots that were updated
            training_results = train_all_models(spot_ids=updated_spots)
            print(f"Trained models for {sum(training_results.values())} spots")
        except Exception as e:
            error_msg = f"Error training models: {e}"
            print(error_msg)
            errors.append(error_msg)

    return {
        'updated_spots': updated_spots,
        'errors': errors,
        'training_results': training_results
    }
