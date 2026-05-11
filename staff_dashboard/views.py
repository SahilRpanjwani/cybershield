from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from users.models import UserProfile, Role
from teams.models import Team, TeamMember
from engagements.models import PentestRequest

# -------------------
# Helper function to check if user is admin
def is_admin(user):
    """Check if user has admin role"""
    try:
        return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'
    except:
        return False


# -------------------
# Helper decorator to ensure only admins access these pages
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not is_admin(request.user):
            messages.error(request, "You don't have permission to access this page.")
            return redirect("/")  # Redirect to home page
        return view_func(request, *args, **kwargs)
    return wrapper


# -------------------
# Admin Login
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email").lower()
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user:
            if is_admin(user):
                login(request, user)
                return redirect("staff_dashboard")
            else:
                return render(request, "staff_dashboard/login.html", {"error": "Not an admin"})
        return render(request, "staff_dashboard/login.html", {"error": "Invalid credentials"})
    return render(request, "staff_dashboard/login.html")


# Admin Logout
@login_required(login_url="staff_login")
def logout_view(request):
    logout(request)
    return redirect("staff_login")   # changed from "login"


# -------------------
# Dashboard
@login_required(login_url="staff_login")
@admin_required
def dashboard(request):
    """Main admin dashboard with statistics"""
    # Get statistics
    total_users = User.objects.count()
    total_teams = Team.objects.filter(is_active=True).count()

    # Calculate analyst count (network_analyst + soc_analyst)
    analyst_count = UserProfile.objects.filter(
        role__in=[Role.NETWORK_ANALYST, Role.SOC_ANALYST]
    ).count()

    # Calculate pentester count (web_pentester + mobile_pentester)
    pentester_count = UserProfile.objects.filter(
        role__in=[Role.WEB_PENTESTER, Role.MOBILE_PENTESTER]
    ).count()

    # Users by role
    role_stats = UserProfile.objects.values('role').annotate(count=Count('role')).order_by('role')

    # Recent teams
    recent_teams = Team.objects.filter(is_active=True).order_by('-created_at')[:5]

    # Recent users
    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:5]

    context = {
        'total_users': total_users,
        'total_teams': total_teams,
        'analyst_count': analyst_count,
        'pentester_count': pentester_count,
        'role_stats': role_stats,
        'recent_teams': recent_teams,
        'recent_users': recent_users,
        'recent_requests': PentestRequest.objects.order_by('-created_at')[:5],
    }

    return render(request, 'staff_dashboard/dashboard.html', context)

# -------------------
# Team Management
@login_required(login_url="staff_login")
@admin_required
def team_list(request):
    """List all teams"""
    teams = Team.objects.annotate(
        member_count=Count('members')
    ).select_related('team_lead').order_by('-created_at')

    context = {
        'teams': teams,
    }

    return render(request, 'staff_dashboard/team_list.html', context)


@login_required(login_url="staff_login")
@admin_required
def team_create(request):
    """Create a new team"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        team_lead_id = request.POST.get('team_lead')

        if not name:
            messages.error(request, "Team name is required.")
            return redirect('team_create')

        team_lead = None
        if team_lead_id:
            team_lead = get_object_or_404(User, id=team_lead_id)

        team = Team.objects.create(
            name=name,
            description=description,
            team_lead=team_lead
        )

        messages.success(request, f"Team '{team.name}' created successfully!")
        return redirect('team_detail', team_id=team.id)

    # Get potential team leads (analysts and pentesters)
    potential_leads = User.objects.filter(
        profile__role__in=[
            Role.NETWORK_ANALYST,
            Role.WEB_PENTESTER,
            Role.MOBILE_PENTESTER,
            Role.SOC_ANALYST
        ]
    ).select_related('profile')

    context = {
        'potential_leads': potential_leads,
    }

    return render(request, 'staff_dashboard/team_form.html', context)


@login_required(login_url="staff_login")
@admin_required
def team_edit(request, team_id):
    """Edit an existing team"""
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        team.name = request.POST.get('name', team.name)
        team.description = request.POST.get('description', team.description)

        team_lead_id = request.POST.get('team_lead')
        if team_lead_id:
            team.team_lead = get_object_or_404(User, id=team_lead_id)
        else:
            team.team_lead = None

        team.is_active = request.POST.get('is_active') == 'on'
        team.save()

        messages.success(request, f"Team '{team.name}' updated successfully!")
        return redirect('team_detail', team_id=team.id)

    potential_leads = User.objects.filter(
        profile__role__in=[
            Role.NETWORK_ANALYST,
            Role.WEB_PENTESTER,
            Role.MOBILE_PENTESTER,
            Role.SOC_ANALYST
        ]
    ).select_related('profile')

    context = {
        'team': team,
        'potential_leads': potential_leads,
        'is_edit': True,
    }

    return render(request, 'staff_dashboard/team_form.html', context)

from engagements.models import Task
from users.models import Report
from scanner.models import ScanResult

@login_required(login_url="staff_login")
@admin_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    members = TeamMember.objects.filter(team=team).select_related('user', 'user__profile')
    current_member_ids = members.values_list('user_id', flat=True)

    pentester_roles = [
        Role.WEB_PENTESTER,
        Role.MOBILE_PENTESTER,
        Role.NETWORK_ANALYST,
        Role.SOC_ANALYST
    ]
    pentesters = User.objects.filter(
        profile__role__in=pentester_roles
    ).exclude(id__in=current_member_ids)

    engagements = team.engagements.all()
    client_ids = engagements.values_list('request__client_id', flat=True).distinct()
    clients = User.objects.filter(
        id__in=client_ids
    ).exclude(id__in=current_member_ids)

    available_users = (pentesters | clients).distinct().order_by('username')

    all_tasks = Task.objects.filter(
        engagement__assigned_team=team
    ).select_related('engagement', 'engagement__request', 'assigned_to').order_by('-created_at')

    active_tasks = all_tasks.exclude(status='done')
    completed_tasks = all_tasks.filter(status='done')

    # Fetch reports and scan results for this team's engagements
    reports = Report.objects.filter(
        engagement__assigned_team=team
    ).select_related('engagement', 'engagement__request', 'author').order_by('-created_at')

    scan_results = ScanResult.objects.filter(
        engagement__assigned_team=team
    ).select_related('engagement', 'engagement__request').order_by('-created_at')

    context = {
        'team': team,
        'members': members,
        'available_users': available_users,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'reports': reports,
        'scan_results': scan_results,
    }

    return render(request, 'staff_dashboard/team_detail.html', context)
@login_required(login_url="staff_login")
@admin_required
def team_add_member(request, team_id):
    """Add a member to a team"""
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)

        # Check if already a member
        if TeamMember.objects.filter(team=team, user=user).exists():
            messages.warning(request, f"{user.username} is already a member of {team.name}.")
        else:
            TeamMember.objects.create(team=team, user=user)
            messages.success(request, f"{user.username} added to {team.name} successfully!")

    return redirect('team_detail', team_id=team_id)


@login_required(login_url="staff_login")
@admin_required
def team_remove_member(request, team_id, member_id):
    """Remove a member from a team"""
    team = get_object_or_404(Team, id=team_id)
    member = get_object_or_404(TeamMember, id=member_id, team=team)

    username = member.user.username
    member.delete()
    messages.success(request, f"{username} removed from {team.name}.")

    return redirect('team_detail', team_id=team_id)


@login_required(login_url="staff_login")
@admin_required
def team_delete(request, team_id):
    """Delete a team"""
    team = get_object_or_404(Team, id=team_id)

    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f"Team '{team_name}' deleted successfully!")
        return redirect('team_list')

    context = {
        'team': team,
    }

    return render(request, 'staff_dashboard/team_confirm_delete.html', context)


# -------------------
# User Management
@login_required(login_url="staff_login")
@admin_required
def user_list(request):
    """List all users with filtering options"""
    # Get filter parameters
    role_filter = request.GET.get('role', '')
    search_query = request.GET.get('search', '')

    users = User.objects.select_related('profile').all()

    # Apply filters
    if role_filter:
        users = users.filter(profile__role=role_filter)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    users = users.order_by('-date_joined')

    context = {
        'users': users,
        'role_choices': Role.choices,
        'current_role_filter': role_filter,
        'search_query': search_query,
    }

    return render(request, 'staff_dashboard/user_list.html', context)


from users.models import Role   # ensure this is at the top of the file

@login_required(login_url="staff_login")
@admin_required
def user_detail(request, user_id):
    """View user details including teams"""
    user = get_object_or_404(User, id=user_id)
    teams = TeamMember.objects.filter(user=user).select_related('team')

    context = {
        'viewed_user': user,
        'teams': teams,
        'role_choices': Role.choices,   # <-- add this line
    }

    return render(request, 'staff_dashboard/user_detail.html', context)

@login_required(login_url="staff_login")
@admin_required
def user_update_role(request, user_id):
    """Update a user's role"""
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(Role.choices):
            user.profile.role = new_role
            user.profile.save()
            messages.success(request, f"Role updated for {user.username}.")
        else:
            messages.error(request, "Invalid role selected.")

    return redirect('user_detail', user_id=user_id)


# -------------------
# Add Pentester (NEW)
@login_required(login_url="staff_login")
@admin_required
def add_pentester(request):
    """Create a new pentester account"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email').lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        phone = request.POST.get('phone', '')
        bio = request.POST.get('bio', '')

        # Validation
        if not username or not email or not password or not role:
            messages.error(request, "Username, email, password, and role are required.")
            return redirect('add_pentester')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('add_pentester')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('add_pentester')

        # ⬇️ Allow all pentester‑type roles
        allowed_pentester_roles = [
            Role.WEB_PENTESTER,
            Role.MOBILE_PENTESTER,
            Role.NETWORK_ANALYST,
            Role.SOC_ANALYST,
        ]
        if role not in allowed_pentester_roles:
            messages.error(request, "Invalid pentester role selected.")
            return redirect('add_pentester')

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('add_pentester')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return redirect('add_pentester')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Update profile
            user.profile.role = role
            user.profile.phone_number = phone
            user.profile.bio = bio
            user.profile.save()

            messages.success(request, f"Pentester '{username}' created successfully!")
            return redirect('user_detail', user_id=user.id)

        except Exception as e:
            messages.error(request, f"Error creating pentester: {str(e)}")
            return redirect('add_pentester')

    return render(request, 'staff_dashboard/add_pentester.html')

from engagements.models import PentestRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def request_list(request):
    requests = PentestRequest.objects.all()
    return render(request, "staff_dashboard/request_list.html", {
        "requests": requests
    })
from engagements.models import PentestRequest
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required(login_url="staff_login")
@admin_required
def approve_request(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    # Only send email if the request was NOT already approved
    was_already_approved = (pentest_request.status == 'approved')

    pentest_request.status = 'approved'
    pentest_request.save()

    if not was_already_approved:
        _email_request_approved(pentest_request)

    messages.success(request, f"Request #{pk} has been approved. The client has been notified.")
    return redirect('request_list')


@login_required(login_url="staff_login")
@admin_required
def request_detail(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    # Engagement flags
    engagement = getattr(pentest_request, 'engagement', None)
    engagement_is_active = engagement.status == 'active' if engagement else False
    has_approved_reports = engagement.reports.filter(status='approved').exists() if engagement else False

    context = {
        'request_obj': pentest_request,
        'engagement_is_active': engagement_is_active,
        'has_approved_reports': has_approved_reports,
    }
    return render(request, 'staff_dashboard/request_detail.html', context)

@login_required(login_url="staff_login")
@admin_required
def reject_request(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    was_already_rejected = (pentest_request.status == 'rejected')

    pentest_request.status = 'rejected'
    pentest_request.save()

    if not was_already_rejected:
        _email_request_rejected(pentest_request)

    messages.success(request, f"Request #{pk} has been rejected. The client has been notified.")
    return redirect('request_list')

from engagements.models import PentestRequest, Engagement
from engagements.forms import EngagementForm


@login_required(login_url="staff_login")
@admin_required
def assign_team(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    # Prevent duplicate engagement
    if hasattr(pentest_request, 'engagement'):
        messages.warning(request, "A team is already assigned to this request.")
        return redirect('request_detail', pk=pk)

    if request.method == 'POST':
        form = EngagementForm(request.POST)
        if form.is_valid():
            engagement = form.save(commit=False)
            engagement.request = pentest_request
            engagement.save()

            # Create default tasks for the team
            default_tasks = [
                {"title": "Reconnaissance", "description": "Gather information about the target environment"},
                {"title": "Vulnerability Scanning",
                 "description": "Perform automated and manual vulnerability assessment"},
                {"title": "Exploitation", "description": "Attempt to exploit discovered vulnerabilities"},
                {"title": "Reporting", "description": "Document findings and prepare final report"},
            ]
            for task_data in default_tasks:
                Task.objects.create(
                    engagement=engagement,
                    title=task_data["title"],
                    description=task_data["description"],
                    status='todo'
                )

            # Notify the client that a team has been assigned
            _email_team_assigned(engagement)

            messages.success(request, "Team assigned and default tasks created successfully! The client has been notified.")
            return redirect('request_detail', pk=pk)
    else:
        form = EngagementForm()

    return render(request, 'staff_dashboard/assign_team.html', {
        'form': form,
        'pentest_request': pentest_request
    })

@login_required(login_url="staff_login")
@admin_required
def request_delete(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)

    if request.method == 'POST':
        # Optionally delete related engagement if exists
        try:
            if hasattr(pentest_request, 'engagement'):
                # If you want to delete the engagement as well uncomment next line:
                # pentest_request.engagement.delete()
                pass
        except Exception:
            # ignore if no engagement or deletion issues - request will be deleted anyway
            pass

        pentest_request.delete()
        messages.success(request, f"Request #{pk} has been deleted.")
        return redirect('request_list')

    # If GET, render a simple confirmation page (optional). To keep flow simple, redirect.
    messages.info(request, "Delete must be performed via the delete button on the request page.")
    return redirect('request_detail', pk=pk)

from django.db.models.deletion import ProtectedError

@login_required(login_url="staff_login")
@admin_required
def user_delete(request, user_id):
    """Delete a user – only for staff, cannot delete self."""
    user_to_delete = get_object_or_404(User, id=user_id)

    # Prevent deleting yourself
    if request.user == user_to_delete:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_detail', user_id=user_to_delete.id)

    if request.method == 'POST':
        username = user_to_delete.username
        try:
            user_to_delete.delete()
            messages.success(request, f"User '{username}' has been deleted.")
            return redirect('user_list')
        except ProtectedError as e:
            # This happens if a protected foreign key prevents deletion
            messages.error(
                request,
                f"Cannot delete user '{username}' because they have related data that is protected. "
                "Please reassign or delete those objects first."
            )
            # Optionally log the error for debugging
            # import logging; logging.error(f"ProtectedError: {e}")
            return redirect('user_detail', user_id=user_to_delete.id)

    # If GET request, redirect to user detail (button should only be POST)
    return redirect('user_detail', user_id=user_to_delete.id)

# ─── APPEND THIS ENTIRE BLOCK TO THE BOTTOM OF staff_dashboard/views.py ──────

from users.models import Report
from django.core.mail import send_mail
from django.conf import settings as django_settings


@login_required(login_url="staff_login")
@admin_required
def report_list_admin(request):
    """Admin view: all submitted/approved/rejected reports."""
    status_filter = request.GET.get('status', '')
    reports = Report.objects.select_related(
        'author', 'engagement', 'engagement__request'
    ).exclude(status='draft').order_by('-created_at')

    if status_filter:
        reports = reports.filter(status=status_filter)

    context = {
        'reports': reports,
        'status_filter': status_filter,
        'status_choices': [('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
    }
    return render(request, 'staff_dashboard/report_list.html', context)


@login_required(login_url="staff_login")
@admin_required
def report_review(request, pk):
    """Admin view: review a single report, add notes, approve or reject."""
    report = get_object_or_404(
        Report.objects.select_related('author', 'engagement', 'engagement__request'),
        pk=pk
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '').strip()
        report.admin_notes = admin_notes

        if action == 'approve':
            report.status = 'approved'
            report.save()

            # Mark all tasks in this engagement as done
            engagement = report.engagement
            Task.objects.filter(engagement=engagement).update(status='done')

            _email_report_to_client(report, request)
            messages.success(request,
                             f'Report approved and emailed to {report.engagement.request.client.email}. All tasks marked done.')

        elif action == 'reject':
            report.status = 'rejected'
            report.save()
            messages.warning(request, 'Report rejected.')

        else:
            # Just saving notes without changing status
            report.save()
            messages.success(request, 'Notes saved.')

        return redirect('report_review', pk=pk)

    context = {'report': report}
    return render(request, 'staff_dashboard/report_review.html', context)

import io
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings as django_settings
from weasyprint import HTML


def _email_report_to_client(report, request):
    """Generate a PDF report and email it to the client."""
    client = report.engagement.request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = report.engagement.request.company_name

    # 1. Render HTML from template
    html_string = render_to_string('emails/report_pdf.html', {'report': report})

    # 2. Generate PDF in memory
    pdf_buffer = io.BytesIO()
    HTML(string=html_string).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    # 3. Build email with attachment
    subject = f"[CyberShield] Security Assessment Report — {company}"
    body = f"""Dear {client_name},

Your penetration testing engagement for {company} has been completed.

Please find the detailed security assessment report attached as a PDF.

If you have any questions, contact your assigned team lead or reply to this email.

Regards,
CyberShield Security Team
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        to=[client_email],
    )
    email.attach(
        f'{company}_Security_Report.pdf',
        pdf_buffer.getvalue(),
        'application/pdf'
    )
    email.send(fail_silently=False)


from engagements.models import PentestRequest, Engagement

@login_required(login_url="staff_login")
@admin_required
def complete_engagement(request, pk):
    pentest_request = get_object_or_404(PentestRequest, pk=pk)
    engagement = getattr(pentest_request, 'engagement', None)

    if not engagement:
        messages.error(request, "No engagement associated with this request.")
        return redirect('request_detail', pk=pk)

    if engagement.status != 'active':
        messages.warning(request, "Engagement is already completed or on hold.")
        return redirect('request_detail', pk=pk)

    if not engagement.reports.filter(status='approved').exists():
        messages.error(request, "Cannot complete engagement until a report is approved.")
        return redirect('request_detail', pk=pk)

    was_already_completed = (engagement.status == 'completed')

    engagement.status = 'completed'
    engagement.save()

    if not was_already_completed:
        _email_engagement_complete(engagement)

    messages.success(request, f"Engagement for {pentest_request.company_name} marked as complete. The client has been notified.")
    return redirect('request_detail', pk=pk)
def _email_engagement_complete(engagement):
    """Notify the client that their engagement has been completed."""
    client = engagement.request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = engagement.request.company_name

    subject = f"[CyberShield] Engagement Completed — {company}"

    body = f"""Dear {client_name},

We are pleased to inform you that the security assessment engagement for **{company}** has been successfully completed.

All findings have been reviewed, and the final report has been delivered to your email.  
Your dedicated security team has ensured that the identified vulnerabilities are thoroughly documented, along with clear remediation guidance.

If you have any further questions or require additional clarification regarding the report or the assessment, please do not hesitate to contact your assigned team lead or reply to this email.

Thank you for trusting **CyberShield** with your security needs.

Sincerely,  
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )

from django.core.mail import send_mail
from django.conf import settings as django_settings



def _email_request_approved(request_obj):
    client = request_obj.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = request_obj.company_name
    req_id = request_obj.id

    subject = f"[CyberShield] Pentest Request Approved – {company}"

    body = f"""Dear {client_name},

We are pleased to inform you that your pentest request for **{company}** has been approved.

Our security team will now be assigned to your engagement.  
You will receive further updates as the assessment progresses, including the final report upon completion.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID : {req_id}
Company    : {company}
Status     : Approved
━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you have any questions in the meantime, feel free to contact us.

Regards,  
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )

def _email_request_rejected(request_obj):
    client = request_obj.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = request_obj.company_name
    req_id = request_obj.id

    subject = f"[CyberShield] Pentest Request Update – {company}"

    body = f"""Dear {client_name},

Thank you for your interest in CyberShield’s security services.

After careful review, we regret to inform you that your pentest request for **{company}** could not be approved at this time.  
This decision may be due to an incomplete scope, conflict of interest, or other operational reasons.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID : {req_id}
Status     : Not Approved
━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you believe this decision was made in error, or if you would like to resubmit a revised request, please contact us and we’ll work with you to find the best path forward.

We appreciate your understanding.

Regards,  
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )

def _email_team_assigned(engagement):
    client = engagement.request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = engagement.request.company_name
    team = engagement.assigned_team
    lead = team.team_lead
    lead_name = lead.get_full_name() or lead.username
    lead_email = lead.email

    subject = f"[CyberShield] Security Team Assigned – {company}"

    body = f"""Dear {client_name},

Your pentest engagement for **{company}** has been assigned a dedicated security team.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEAM DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Team Name     : {team.name}
Team Lead     : {lead_name}
Lead Email    : {lead_email}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

The team will now begin the assessment.  
You will receive regular updates and the final report upon completion.

If you need to reach the team lead directly, you can contact them via the email above.

Regards,
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )