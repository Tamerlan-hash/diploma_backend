# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import ParkingSpot, Sensor, Blocker
from .serializers import ParkingSpotSerializer, SensorSerializer, BlockerSerializer

class RaiseBlockerAPIView(APIView):
    def post(self, request, reference):
        # Find the parking spot by reference
        try:
            import uuid
            try:
                uuid_obj = uuid.UUID(reference)
                parking_spot = get_object_or_404(ParkingSpot, reference=uuid_obj)
            except (ValueError, TypeError):
                # If not a valid UUID, try to get by name
                parking_spot = get_object_or_404(ParkingSpot, name=reference)
        except:
            # Fallback to original behavior
            parking_spot = get_object_or_404(ParkingSpot, reference=reference)

        # Raise the blocker
        blocker = parking_spot.blocker
        blocker.raise_blocker()

        # Return the updated parking spot with its related objects
        serializer = ParkingSpotSerializer(parking_spot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LowerBlockerAPIView(APIView):
    def post(self, request, reference):
        # Find the parking spot by reference
        try:
            import uuid
            try:
                uuid_obj = uuid.UUID(reference)
                parking_spot = get_object_or_404(ParkingSpot, reference=uuid_obj)
            except (ValueError, TypeError):
                # If not a valid UUID, try to get by name
                parking_spot = get_object_or_404(ParkingSpot, name=reference)
        except:
            # Fallback to original behavior
            parking_spot = get_object_or_404(ParkingSpot, reference=reference)

        # Lower the blocker
        blocker = parking_spot.blocker
        blocker.lower_blocker()

        # Return the updated parking spot with its related objects
        serializer = ParkingSpotSerializer(parking_spot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SetSensorOccupiedAPIView(APIView):
    def post(self, request, reference, occupied=True):
        # Find the parking spot by reference
        try:
            import uuid
            try:
                uuid_obj = uuid.UUID(reference)
                parking_spot = get_object_or_404(ParkingSpot, reference=uuid_obj)
            except (ValueError, TypeError):
                # If not a valid UUID, try to get by name
                parking_spot = get_object_or_404(ParkingSpot, name=reference)
        except:
            # Fallback to original behavior
            parking_spot = get_object_or_404(ParkingSpot, reference=reference)

        # Set the sensor status
        sensor = parking_spot.sensor
        sensor.set_occupied(occupied)

        # Return the updated parking spot with its related objects
        serializer = ParkingSpotSerializer(parking_spot)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def parking_spot_list(request):
    parking_spots = ParkingSpot.objects.all()
    serializer = ParkingSpotSerializer(parking_spots, many=True)
    return Response(serializer.data)


class SensorOccupyAPIView(APIView):
    """
    API endpoint for sensors to update their occupation status to occupied.
    Accepts a POST request with the sensor reference in the URL.
    """
    permission_classes = [permissions.AllowAny]
    def post(self, request, reference):
        try:
            # Find the sensor by reference
            sensor = get_object_or_404(Sensor, reference=reference)

            # Update the sensor status to occupied
            sensor.set_occupied(True)

            # Return the updated sensor
            serializer = SensorSerializer(sensor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SensorUnoccupyAPIView(APIView):
    """
    API endpoint for sensors to update their occupation status to unoccupied.
    Accepts a POST request with the sensor reference in the URL.
    """
    permission_classes = [permissions.AllowAny]
    def post(self, request, reference):
        try:
            # Find the sensor by reference
            sensor = get_object_or_404(Sensor, reference=reference)

            # Update the sensor status to unoccupied
            sensor.set_occupied(False)

            # Return the updated sensor
            serializer = SensorSerializer(sensor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BlockerStatusAPIView(APIView):
    """
    API endpoint for blockers to check their status.
    Accepts a GET request with the blocker reference in the URL.
    """
    permission_classes = [permissions.AllowAny]
    def get(self, request, reference):
        try:
            # Find the blocker by reference
            blocker = get_object_or_404(Blocker, reference=reference)

            # Return the blocker status
            serializer = BlockerSerializer(blocker)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response({'error': 'Blocker not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
