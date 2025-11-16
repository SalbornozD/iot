from django.contrib import admin
from .models import SensorZone, SensorReading, IrrigationEvent

# Register your models here.
admin.site.register(SensorZone)
admin.site.register(SensorReading)
admin.site.register(IrrigationEvent)