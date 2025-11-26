from django.urls import path
from . import views
from .views import (
    HomeScreenView,
    AutomaticIrrigationView,
    ManualIrrigationView,
    PlantViewSet,
    SelectPlantView,
    FlowerpotViewSet,
    IrrigationEventViewSet,
    UserProfileView,
)
from rest_framework.routers import DefaultRouter
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

app_name = "arduino"

router = DefaultRouter()
router.register(r"plants", PlantViewSet, basename="plants")
router.register(r"flowerpots", FlowerpotViewSet, basename="flowerpots")
router.register(r"irrigation/events", IrrigationEventViewSet, basename="irrigation-events")

urlpatterns = [
    # Admin UI
    path("home-admin/", views.home_admin_view, name="home-admin"),
    path("plants/<int:pk>/edit/", views.edit_plant_view, name="edit-plant"),
    path("plants/<int:pk>/delete/", views.delete_plant_view, name="delete-plant"),
    # Auth (local login for admin UI)
    path(
        "login/",
        LoginView.as_view(template_name="arduino/login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),

    # Category management for admin UI
    path("categories/create/", views.create_category_view, name="create-category"),
    path("categories/<int:pk>/delete/", views.delete_category_view, name="delete-category"),

    # API endpoints (DRF)
    path("home/", HomeScreenView.as_view(), name="home-screen"),
    path("irrigation/automatic/", AutomaticIrrigationView.as_view(), name="automatic-irrigation"),
    path("irrigation/manual/", ManualIrrigationView.as_view(), name="manual-irrigation"),
    path("flowerpot/select-plant/", SelectPlantView.as_view(), name="select-plant"),
    path('user/me/', UserProfileView.as_view(), name='user_profile'),
] + router.urls
