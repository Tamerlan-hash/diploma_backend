from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone

from sensor.models import ParkingSpot
from sensor.serializers import ParkingSpotSerializer
from .utils import predict_parking_availability, get_recommended_parking_spots, update_occupancy_history


class ParkingAvailabilityPredictionView(APIView):
    """
    API endpoint for predicting parking spot availability.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get prediction for parking spot availability",
        manual_parameters=[
            openapi.Parameter(
                'spot_id', 
                openapi.IN_PATH, 
                description="Parking spot ID", 
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'target_time', 
                openapi.IN_QUERY, 
                description="Target time for prediction (ISO format)", 
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Prediction result",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'spot_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'probability_available': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'prediction_time': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: "Parking spot not found",
        }
    )
    def get(self, request, spot_id):
        # Get target time from query params or use current time
        target_time_str = request.query_params.get('target_time')
        if target_time_str:
            try:
                target_time = timezone.datetime.fromisoformat(target_time_str)
            except ValueError:
                return Response(
                    {"error": "Invalid target_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_time = timezone.now()

        try:
            # Get prediction
            probability = predict_parking_availability(spot_id, target_time)

            if probability is None:
                return Response(
                    {"error": "Parking spot not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if ML model exists for this spot
            from .ml_models import ParkingAvailabilityModel
            import os

            ml_model = ParkingAvailabilityModel(spot_id)
            model_exists = os.path.exists(ml_model.model_path)

            # Get historical data count for confidence information
            from .models import ParkingSpotOccupancyHistory
            from sensor.models import ParkingSpot

            try:
                parking_spot = ParkingSpot.objects.get(reference=spot_id)
                history_count = ParkingSpotOccupancyHistory.objects.filter(
                    parking_spot=parking_spot
                ).count()
            except:
                history_count = 0

            # Determine prediction method and confidence
            if model_exists:
                prediction_method = "machine_learning"
                confidence_level = "high" if history_count >= 50 else "medium"
            else:
                prediction_method = "statistical" if history_count >= 5 else "heuristic"
                confidence_level = "medium" if history_count >= 20 else "low"

            return Response({
                'spot_id': spot_id,
                'probability_available': probability,
                'prediction_time': target_time.isoformat(),
                'prediction_method': prediction_method,
                'confidence_level': confidence_level,
                'data_points': history_count,
                'has_ml_model': model_exists
            })
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error predicting availability for spot {spot_id}: {str(e)}")

            # Return a friendly error message
            return Response(
                {"error": "An error occurred while processing your request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommendedParkingSpotsView(APIView):
    """
    API endpoint for getting recommended parking spots.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get recommended parking spots based on location",
        manual_parameters=[
            openapi.Parameter(
                'latitude', 
                openapi.IN_QUERY, 
                description="User's latitude", 
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'longitude', 
                openapi.IN_QUERY, 
                description="User's longitude", 
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'radius', 
                openapi.IN_QUERY, 
                description="Search radius in kilometers", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'limit', 
                openapi.IN_QUERY, 
                description="Maximum number of spots to return", 
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of recommended parking spots",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'parking_spot': openapi.Schema(type=openapi.TYPE_OBJECT),
                            'distance': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'probability_available': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'is_reserved': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'score': openapi.Schema(type=openapi.TYPE_NUMBER),
                        }
                    )
                )
            ),
            400: "Invalid parameters",
        }
    )
    def get(self, request):
        # Get parameters from query params
        try:
            latitude = float(request.query_params.get('latitude'))
            longitude = float(request.query_params.get('longitude'))
        except (TypeError, ValueError):
            return Response(
                {"error": "latitude and longitude are required and must be valid numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        radius = request.query_params.get('radius')
        if radius:
            try:
                radius = float(radius)
            except ValueError:
                return Response(
                    {"error": "radius must be a valid number"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            radius = 1.0  # Default radius: 1 km

        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                return Response(
                    {"error": "limit must be a valid integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            limit = 5  # Default limit: 5 spots

        try:
            # Get recommendations
            recommendations = get_recommended_parking_spots(latitude, longitude, radius, limit)

            # Serialize the response
            result = []
            for rec in recommendations:
                try:
                    spot_data = ParkingSpotSerializer(rec['parking_spot']).data
                    result.append({
                        'parking_spot': spot_data,
                        'distance': rec['distance'],
                        'probability_available': rec['probability_available'],
                        'is_reserved': rec['is_reserved'],
                        'score': rec['score'],
                    })
                except Exception as e:
                    # Log the error but continue with other recommendations
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error serializing recommendation: {str(e)}")

            return Response(result)
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting recommendations: {str(e)}")

            # Return a friendly error message
            return Response(
                {"error": "An error occurred while processing your request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_occupancy_history_view(request):
    """
    API endpoint for manually triggering the update of occupancy history.
    This would typically be called by a scheduled task.
    """
    try:
        update_occupancy_history()
        return Response({"status": "success", "message": "Occupancy history updated"})
    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
