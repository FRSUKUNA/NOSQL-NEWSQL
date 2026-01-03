from django.urls import path
from .views import api_status, api_list, api_get_versions

urlpatterns = [
    path("api/", api_status),
    path("api/technologies/", api_list),
    path("api/technologies/<str:tech>/versions/", api_get_versions),
]
