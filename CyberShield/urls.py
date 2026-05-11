# CyberShield/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("users.urls", "users"), namespace="users")),
    path("staff/", include("staff_dashboard.urls")),
    path("scanner/", include("scanner.urls")),
path('teams/', include('teams.urls', namespace='teams')),
]