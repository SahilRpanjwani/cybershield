from django.urls import path
from . import views

# app_name = "staff_dashboard"  # Comment this out or remove it

urlpatterns = [
    # Authentication
    path("login/", views.login_view, name="staff_login"),
    path("logout/", views.logout_view, name="staff_logout"),

    # Dashboard - CHANGE name from 'dashboard' to 'staff_dashboard'
    path("", views.dashboard, name="staff_dashboard"),

    # Team Management
    path("teams/", views.team_list, name="team_list"),
    path("teams/create/", views.team_create, name="team_create"),
    path("teams/<int:team_id>/", views.team_detail, name="team_detail"),
    path("teams/<int:team_id>/edit/", views.team_edit, name="team_edit"),
    path("teams/<int:team_id>/delete/", views   .team_delete, name="team_delete"),
    path("teams/<int:team_id>/add-member/", views.team_add_member, name="team_add_member"),
    path("teams/<int:team_id>/remove-member/<int:member_id>/", views.team_remove_member, name="team_remove_member"),

    # User Management
    path("users/", views.user_list, name="user_list"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("users/<int:user_id>/update-role/", views.user_update_role, name="user_update_role"),
    path("users/add-pentester/", views.add_pentester, name="add_pentester"),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    # Pentest Requests
    path('requests/', views.request_list, name='request_list'),
    path('requests/<int:pk>/approve/', views.approve_request, name='approve_request'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('requests/<int:pk>/assign-team/', views.assign_team, name='assign_team'),
    path('requests/<int:pk>/delete/', views.request_delete, name='request_delete'),  # fixed
    path('request/<int:pk>/complete/', views.complete_engagement, name='complete_engagement'),

    path('reports/', views.report_list_admin, name='report_list_admin'),
    path('reports/<int:pk>/review/', views.report_review, name='report_review'),

]