from .models import Flowerpot, Plants, SensorReading, IrrigationEvent
from django.contrib import admin

admin.site.register(Flowerpot)
admin.site.register(Plants)
admin.site.register(SensorReading)
admin.site.register(IrrigationEvent)

