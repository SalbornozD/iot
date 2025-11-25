from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import HttpResponseRedirect

from .models import Plants, PlantCategory
from django.views.decorators.http import require_POST


def index_redirect(request):
    """Redirect root URL to login or admin home depending on auth state."""
    if request.user.is_authenticated:
        return redirect(reverse("arduino:home-admin"))
    return redirect(reverse("arduino:login"))


@login_required
def home_admin_view(request):
    """
    Vista simple para administrar plantas:
    - Listar plantas existentes
    - Crear nuevas plantas (nombre, image_url, categorías separadas por coma)
    """
    # Crear planta (POST)
    if request.method == "POST":
        name = request.POST.get("name") or ""
        image_url = request.POST.get("image_url") or ""
        humidity_min = request.POST.get("humidity_min")
        humidity_max = request.POST.get("humidity_max")
        category_id = request.POST.get("category_id") or ""
        category_location = request.POST.get("category_location") or "BOTH"

        if name.strip():
            plant = Plants.objects.create(
                name=name.strip(),
                image_url=image_url.strip() or None,
            )

            # Handle numeric fields if provided
            try:
                if humidity_min is not None and humidity_min != "":
                    plant.humidity_min = float(humidity_min)
                if humidity_max is not None and humidity_max != "":
                    plant.humidity_max = float(humidity_max)
                plant.save()
            except ValueError:
                # Ignore invalid numeric input and keep defaults
                pass

            # Associate selected single category (if provided)
            if category_id:
                try:
                    cid = int(category_id)
                    category = PlantCategory.objects.filter(pk=cid).first()
                    if category:
                        plant.categories.add(category)
                except (ValueError, TypeError):
                    pass

            return redirect(reverse("arduino:home-admin"))

    # GET: listar todas las plantas
    plants = Plants.objects.prefetch_related("categories").order_by("-created_at")

    context = {
        "plants": plants,
        "categories": PlantCategory.objects.order_by("name"),
    }
    return render(request, "arduino/home_admin.html", context)


@require_POST
@login_required
def create_category_view(request):
    """Create a PlantCategory from the admin UI."""
    name = request.POST.get("category_name") or ""
    location = request.POST.get("category_location") or "BOTH"
    if name.strip():
        PlantCategory.objects.get_or_create(name=name.strip(), defaults={"location": location})
    return redirect(reverse("arduino:home-admin"))


@require_POST
@login_required
def delete_category_view(request, pk):
    cat = get_object_or_404(PlantCategory, pk=pk)
    cat.delete()
    return redirect(reverse("arduino:home-admin"))


@login_required
def edit_plant_view(request, pk):
    plant = get_object_or_404(Plants, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name") or plant.name
        image_url = request.POST.get("image_url") or ""
        humidity_min = request.POST.get("humidity_min")
        humidity_max = request.POST.get("humidity_max")
        category_id = request.POST.get("category_id") or ""
        category_location = request.POST.get("category_location") or "BOTH"

        plant.name = name.strip()
        plant.image_url = image_url.strip() or None
        try:
            if humidity_min is not None and humidity_min != "":
                plant.humidity_min = float(humidity_min)
            if humidity_max is not None and humidity_max != "":
                plant.humidity_max = float(humidity_max)
        except ValueError:
            pass

        plant.save()

        # Replace categories with the single selected category (or none)
        plant.categories.clear()
        if category_id:
            try:
                cid = int(category_id)
                category = PlantCategory.objects.filter(pk=cid).first()
                if category:
                    # Optionally update the category's location based on the form
                    try:
                        if category_location in ("INDOOR", "OUTDOOR", "BOTH"):
                            category.location = category_location
                            category.save()
                    except Exception:
                        # Keep existing location if update fails for any reason
                        pass
                    plant.categories.add(category)
            except (ValueError, TypeError):
                pass

        return redirect(reverse("arduino:home-admin"))

    categories_str = ", ".join(list(plant.categories.values_list("name", flat=True)))
    context = {
        "plant": plant,
        "categories_str": categories_str,
        "categories": PlantCategory.objects.order_by("name"),
    }
    return render(request, "arduino/edit_plant.html", context)


@login_required
def delete_plant_view(request, pk):
    plant = get_object_or_404(Plants, pk=pk)
    if request.method == "POST":
        plant.delete()
        return redirect(reverse("arduino:home-admin"))
    return redirect(reverse("arduino:home-admin"))


def logout_view(request):
    """Log out the current user and redirect to the login page."""
    logout(request)
    return HttpResponseRedirect(reverse("arduino:login"))
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