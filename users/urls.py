from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("send-otp/", views.send_otp, name="send_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("userdashboard/", views.user_dashboard, name="user_dashboard"),
    path("profile/", views.user_profile, name="profile"),
    path('request/new/', views.create_request, name='create_request'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('pentester/dashboard/', views.pentester_dashboard, name='pentester_dashboard'),
    path('pentester/reports/new/', views.report_create, name='report_create'),
    path('pentester/reports/', views.report_list, name='report_list'),
    path('pentester/reports/<int:pk>/edit/', views.report_edit, name='report_edit'),
    path('pentester/reports/<int:pk>/delete/', views.report_delete, name='report_delete'),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Static Pages
    path("privacy/", views.privacy, name="privacy"),
    path("security/", views.security, name="security"),
    path("blog/", views.blog, name="blog"),
    path("contact/", views.contact, name="contact"),
]

from django.conf import settings
from django.conf.urls.static import static

# at the very bottom, after urlpatterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
