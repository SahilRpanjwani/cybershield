from django.urls import path
from . import views

urlpatterns = [
    path("scan/<int:engagement_id>/", views.run_scan, name="run_scan"),
    path("results/<int:engagement_id>/", views.scan_results, name="scan_results"),
    path("nova/chat/<int:engagement_id>/", views.nova_chat, name="nova_chat"),
]