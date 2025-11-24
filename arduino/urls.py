from django.urls import path
from .views import HomeScreenView, AutomaticIrrigationView, ManualIrrigationView, PlantViewSet, SelectPlantView
from rest_framework.routers import DefaultRouter
from .views import UserProfileView


router = DefaultRouter()
router.register(r"plants", PlantViewSet, basename="plants")

urlpatterns = [
    path("home/", HomeScreenView.as_view(), name="home-screen"),
    path("irrigation/automatic/", AutomaticIrrigationView.as_view(), name="automatic-irrigation"),
    path("irrigation/manual/", ManualIrrigationView.as_view(), name="manual-irrigation"),
    path("flowerpot/select-plant/", SelectPlantView.as_view(), name="select-plant"),
    path('user/me/', UserProfileView.as_view(), name='user_profile'),
] + router.urls
