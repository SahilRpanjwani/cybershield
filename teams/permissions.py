# teams/permissions.py
from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import models as django_models
from teams.models import Team, TeamMember

def is_team_lead(user, team):
    """Return True if user is the team_lead of the given team."""
    return team.team_lead == user

def is_team_member(user, team):
    """Return True if user is a member of the given team."""
    return TeamMember.objects.filter(team=team, user=user).exists()

def user_teams(user):
    """Return QuerySet of teams the user belongs to (as member or lead)."""
    return Team.objects.filter(
        django_models.Q(team_lead=user) | django_models.Q(members__user=user)
    ).distinct()

def team_member_required(view_func):
    """Decorator: user must be a team member or lead to access."""
    @wraps(view_func)
    def _wrapped_view(request, team_id, *args, **kwargs):
        team = get_object_or_404(Team, id=team_id)
        if not (is_team_member(request.user, team) or is_team_lead(request.user, team)):
            messages.error(request, "You are not a member of this team.")
            return redirect('pentester_dashboard')
        return view_func(request, team_id, *args, **kwargs)
    return _wrapped_view

def team_lead_required(view_func):
    """Decorator: user must be the team lead."""
    @wraps(view_func)
    def _wrapped_view(request, team_id, *args, **kwargs):
        team = get_object_or_404(Team, id=team_id)
        if not is_team_lead(request.user, team):
            messages.error(request, "Only the team lead can perform this action.")
            return redirect('team_member_detail', team_id=team_id)
        return view_func(request, team_id, *args, **kwargs)
    return _wrapped_view