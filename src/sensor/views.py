# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Sensor
from .serializers import SensorSerializer

class LockByReferenceAPIView(APIView):
    def post(self, request, reference):
        # Поиск объекта по reference
        obj = get_object_or_404(Sensor, reference=reference)
        # Установка состояния блокировки в True
        obj.is_lock = True
        obj.save()
        serializer = SensorSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UnlockByReferenceAPIView(APIView):
    def post(self, request, reference):
        # Поиск объекта по reference
        obj = get_object_or_404(Sensor, reference=reference)
        # Снятие блокировки: is_lock = False
        obj.is_lock = False
        obj.save()
        serializer = SensorSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def sensor_list(request):
    sensors = Sensor.objects.all()
    serializer = SensorSerializer(sensors, many=True)
    return Response(serializer.data)