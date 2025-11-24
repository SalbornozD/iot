from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework import viewsets

from arduino.models import Flowerpot, Plants
from .serializers import (
    HomeScreenSerializer,
    AutomaticIrrigationSerializer,
    FlowerpotSerializer,
    ManualIrrigationSerializer,
    PlantSerializer,
    SelectPlantSerializer,    
)



class HomeScreenView(APIView):
    """
    Devuelve la información necesaria para la pantalla Home:
    - Maceta (estados de riego, planta, etc.)
    - Última lectura de humedad
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        # Por ahora asumimos una sola maceta. Luego se puede filtrar por ID o usuario.
        flowerpot = (
            Flowerpot.objects
            .select_related("plant")
            .prefetch_related("sensor_readings")
            .first()
        )

        if flowerpot is None:
            return Response(
                {"detail": "No hay macetas configuradas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Gracias al ordering en SensorReading, la primera es la última lectura
        last_reading = flowerpot.sensor_readings.first()

        payload = {
            "flowerpot": flowerpot,
            "last_reading": last_reading,
        }

        serializer = HomeScreenSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AutomaticIrrigationView(APIView):
    """
    Activa / desactiva el riego automático de la maceta.

    Request (JSON):
    {
        "automatic_irrigation": true | false
    }

    Respuesta:
    - La maceta actualizada (FlowerpotSerializer).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        # Por ahora asumimos una sola maceta
        flowerpot = Flowerpot.objects.select_related("plant").first()

        if flowerpot is None:
            return Response(
                {"detail": "No hay macetas configuradas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AutomaticIrrigationSerializer(
            instance=flowerpot,
            data=request.data,
            partial=True,  # por si en el futuro mandas más campos
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Solo guardamos el nuevo valor del flag automatic_irrigation
        serializer.save()

        # Devolvemos la maceta completa para que el frontend se actualice
        flowerpot.refresh_from_db()
        response_serializer = FlowerpotSerializer(flowerpot)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ManualIrrigationView(APIView):
    """
    Activa / desactiva el riego manual ("Regar ahora").

    Request (JSON):
    {
        "manual_irrigation": true | false
    }

    Lógica:
    - Solo actualiza el flag manual_irrigation en la maceta.
    - La lógica de riego real (servo, comandos por serial, etc.)
      la hace el proceso/comando que lee periódicamente este valor.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        # Por ahora asumimos una sola maceta
        flowerpot = Flowerpot.objects.select_related("plant").first()

        if flowerpot is None:
            return Response(
                {"detail": "No hay macetas configuradas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ManualIrrigationSerializer(
            instance=flowerpot,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Solo guardamos el nuevo valor del flag
        serializer.save()

        # Devolvemos la maceta completa para que el frontend se actualice
        flowerpot.refresh_from_db()
        response_serializer = FlowerpotSerializer(flowerpot)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PlantViewSet(viewsets.ModelViewSet):
    """
    CRUD de plantas para la sección "Mis plantas".

    Endpoints generados:
    - GET    /api/plants/        -> listar plantas
    - POST   /api/plants/        -> crear planta
    - GET    /api/plants/{id}/   -> detalle planta
    - PUT    /api/plants/{id}/   -> actualizar planta (completo)
    - PATCH  /api/plants/{id}/   -> actualizar planta (parcial)
    - DELETE /api/plants/{id}/   -> borrar planta
    """
    queryset = Plants.objects.all().order_by("-created_at")
    serializer_class = PlantSerializer
    permission_classes = [IsAuthenticated]


class SelectPlantView(APIView):
    """
    Endpoint para seleccionar la planta del macetero.

    POST /api/flowerpot/select-plant/

    Body JSON:
    {
        "plant_id": 1
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        # Caso simple: usar el primer (y único) macetero
        flowerpot = Flowerpot.objects.select_related("plant").first()

        if flowerpot is None:
            return Response(
                {"detail": "No hay macetas configuradas."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SelectPlantSerializer(instance=flowerpot, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Opcional: devolver el flowerpot actualizado
        flowerpot_data = FlowerpotSerializer(flowerpot).data

        return Response(
            {
                "detail": "Planta seleccionada correctamente.",
                "flowerpot": flowerpot_data,
            },
            status=status.HTTP_200_OK,
        )