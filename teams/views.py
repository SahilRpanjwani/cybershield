from django.shortcuts import render

# Create your views here.
# staff_dashboard/views.py

from engagements.models import PentestRequest
from django.shortcuts import render

def request_list(request):
    requests = PentestRequest.objects.all()
    return render(request, 'staff_dashboard/request_list.html', {
        'requests': requests
    })

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from engagements.models import PentestRequest, Engagement
from teams.models import Team
from datetime import date, timedelta


@login_required
def approve_request(request, pk):

    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    # Prevent re-approval
    if pentest_request.status != 'pending':
        return redirect('request_list')

    # Change status
    pentest_request.status = 'approved'
    pentest_request.save()

    # Create Engagement automatically
    Engagement.objects.create(
        request=pentest_request,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
    )

    return redirect('request_list')

# teams/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from teams.models import Team, TeamMember
from engagements.models import Task, Engagement
from teams.permissions import user_teams, is_team_lead
from django.contrib.auth.models import User

@login_required(login_url="/login/")
def team_dashboard(request):
    """Show all teams the user belongs to, with tasks and member lists."""
    user = request.user
    teams = user_teams(user).prefetch_related('members__user', 'members__user__profile')

    teams_data = []
    for team in teams:
        engagements = team.engagements.all()
        # Filter tasks: show only tasks from active engagements if any exist
        active_engagements = engagements.filter(status='active')
        if active_engagements.exists():
            tasks = Task.objects.filter(
                engagement__in=active_engagements
            ).select_related('engagement', 'assigned_to')
        else:
            # No active engagement – show all tasks (old/completed ones)
            tasks = Task.objects.filter(
                engagement__in=engagements
            ).select_related('engagement', 'assigned_to')

        user_is_lead = is_team_lead(user, team)
        members = team.members.select_related('user', 'user__profile').all()

        teams_data.append({
            'team': team,
            'tasks': tasks,
            'members': members,
            'is_lead': user_is_lead,
            'engagements': engagements,
        })

    context = {
        'teams_data': teams_data,
    }

    # Choose template based on user role
    if user.profile.role == 'client':
        template = 'teams/client_team_dashboard.html'
    else:
        template = 'teams/team_dashboard.html'

    return render(request, template, context)
@login_required(login_url="/login/")
def team_task_create(request, team_id):
    """Create a new task for a team (lead only)."""
    team = get_object_or_404(Team, id=team_id)
    if not is_team_lead(request.user, team):
        messages.error(request, "Only team leads can create tasks.")
        return redirect('teams:team_dashboard')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        engagement_id = request.POST.get('engagement')
        assigned_to_id = request.POST.get('assigned_to')
        status = request.POST.get('status', 'todo')

        if not title or not engagement_id:
            messages.error(request, "Title and engagement are required.")
            return redirect('teams:team_dashboard')

        engagement = get_object_or_404(Engagement, id=engagement_id, assigned_team=team)
        assigned_to = None
        if assigned_to_id:
            assigned_to = get_object_or_404(User, id=assigned_to_id)

        Task.objects.create(
            engagement=engagement,
            title=title,
            description=description,
            assigned_to=assigned_to,
            status=status
        )
        messages.success(request, f"Task '{title}' created successfully.")
        return redirect('teams:team_dashboard')

    return redirect('teams:team_dashboard')
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from engagements.models import Task
from teams.permissions import is_team_lead


@login_required(login_url="/login/")
def assign_task(request, task_id):
    """Assign a task to a team member (team lead only)."""
    task = get_object_or_404(Task, id=task_id)
    team = task.engagement.assigned_team  # assuming Engagement has assigned_team FK to Team

    if not team:
        messages.error(request, "This task's engagement has no team assigned.")
        return redirect('teams:team_dashboard')

    if not is_team_lead(request.user, team):
        messages.error(request, "Only team leads can assign tasks.")
        return redirect('teams:team_dashboard')

    if request.method == 'POST':
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            assigned_to = get_object_or_404(User, id=assigned_to_id)
            # Optional: validate that assigned_to is a member of the team
            if not team.members.filter(user=assigned_to).exists():
                messages.error(request, "Selected user is not a member of this team.")
                return redirect('teams:team_dashboard')
            task.assigned_to = assigned_to
        else:
            task.assigned_to = None  # allow unassign

        task.save()
        messages.success(request, f"Task '{task.title}' assigned successfully.")

    return redirect('teams:team_dashboard')


@login_required(login_url="/login/")
def delete_task(request, task_id):
    """Delete a task (team lead only)."""
    task = get_object_or_404(Task, id=task_id)
    team = task.engagement.assigned_team

    if not team:
        messages.error(request, "This task's engagement has no team assigned.")
        return redirect('teams:team_dashboard')

    if not is_team_lead(request.user, team):
        messages.error(request, "Only team leads can delete tasks.")
        return redirect('teams:team_dashboard')

    if request.method == 'POST':
        task_title = task.title
        task.delete()
        messages.success(request, f"Task '{task_title}' deleted.")

    return redirect('teams:team_dashboard')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from engagements.models import Task
from teams.permissions import user_teams  # or check membership directly

@login_required(login_url="/login/")
def task_detail(request, task_id):
    task = get_object_or_404(Task.objects.select_related(
        'engagement__request', 'engagement__assigned_team', 'assigned_to'
    ), id=task_id)

    team = task.engagement.assigned_team
    if not team:
        messages.error(request, "This task is not associated with a team.")
        return redirect('teams:team_dashboard')

    # Check if user is a member of the team
    if not team.members.filter(user=request.user).exists():
        messages.error(request, "You do not have permission to view this task.")
        return redirect('teams:team_dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        comment = request.POST.get('comment', '').strip()

        if new_status in dict(Task.STATUS_CHOICES):
            task.status = new_status
            task.save()
            # If you want to log comment, you'd need a TaskComment model
            messages.success(request, f"Task status updated to {task.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")

        return redirect('teams:task_detail', task_id=task.id)

    context = {
        'task': task,
        'team': team,
        'is_lead': team.team_lead == request.user,
    }
    return render(request, 'teams/task_detail.html', context)