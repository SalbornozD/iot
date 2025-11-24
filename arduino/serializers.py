from rest_framework import serializers
from arduino.models import Plants, Flowerpot, SensorReading


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plants
        fields = [
            "id",
            "name",
            "humidity_min",
            "humidity_max",
            "created_at",
        ]


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = [
            "id",
            "humidity",
            "created_at",
        ]


class FlowerpotSerializer(serializers.ModelSerializer):
    plant = PlantSerializer()

    class Meta:
        model = Flowerpot
        fields = [
            "id",
            "plant",
            "manual_irrigation",
            "automatic_irrigation",
            "last_servo_state",
            "last_updated_at",
            "created_at",
        ]


class HomeScreenSerializer(serializers.Serializer):
    """
    Estructura específica para la pantalla Home.
    """
    flowerpot = FlowerpotSerializer()
    last_reading = SensorReadingSerializer(allow_null=True)


class AutomaticIrrigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flowerpot
        fields = ["automatic_irrigation"]


class ManualIrrigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flowerpot
        fields = ["manual_irrigation"]


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plants
        fields = ["id", "name", "humidity_min", "humidity_max", "created_at"]
        read_only_fields = ["id", "created_at"]


class SelectPlantSerializer(serializers.Serializer):
    plant_id = serializers.PrimaryKeyRelatedField(
        queryset=Plants.objects.all(),
        source="plant",
        help_text="ID de la planta a asociar al macetero",
    )

    def update(self, instance: Flowerpot, validated_data):
        # validated_data["plant"] viene desde source="plant"
        instance.plant = validated_data["plant"]
        instance.save(update_fields=["plant", "last_updated_at"])
        return instance

    def create(self, validated_data):
        # No lo usaremos (solo update), pero DRF lo exige
        raise NotImplementedError("Solo se usa para actualizar un Flowerpot existente.")