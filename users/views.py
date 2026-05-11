from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import random
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserEditForm

# ================= HOME =================
def home(request):
    return render(request, "home_pages/home.html")

# ================= STATIC PAGES =================
def privacy(request):
    return render(request, "home_pages/privacy.html")

def security(request):
    return render(request, "home_pages/security.html")

def blog(request):
    return render(request, "home_pages/blog.html")

def contact(request):
    return render(request, "home_pages/contact.html")


# ================= AUTH =================
def register(request):
    return render(request, "login/register.html")


@csrf_exempt
def send_otp(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"})

    data = json.loads(request.body)
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        return JsonResponse({"success": False, "error": "Invalid email"})

    if User.objects.filter(email=email).exists():
        return JsonResponse({"success": False, "error": "Email already registered"})

    if cache.get(f"otp_rate_{email}"):
        return JsonResponse({"success": False, "error": "Wait before retrying"})

    otp = random.randint(100000, 999999)
    cache.set(f"otp_{email}", str(otp), timeout=600)
    cache.set(f"otp_rate_{email}", True, timeout=60)

    send_mail(
        "Your CyberShield OTP",
        f"Your OTP is {otp}",
        "noreply@cybershield.com",
        [email],
        fail_silently=False,
    )

    return JsonResponse({"success": True})


def verify_otp(request):
    if request.method != "POST":
        return redirect("/register/")

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    otp = request.POST.get("otp", "").strip()
    password = request.POST.get("password", "")
    confirm = request.POST.get("confirm_password", "")

    if not all([first_name, last_name, email, otp, password, confirm]):
        return render(request, "login/register.html", {"error": "All fields required"})

    if password != confirm:
        return render(request, "login/register.html", {"error": "Passwords do not match"})

    try:
        validate_password(password)
    except ValidationError as e:
        return render(request, "login/register.html", {"error": " ".join(e.messages)})

    stored_otp = cache.get(f"otp_{email}")
    if stored_otp != otp:
        return render(request, "login/register.html", {"error": "Invalid or expired OTP"})

    if User.objects.filter(email=email).exists():
        return render(request, "login/register.html", {"error": "Email already registered. Please login."})

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    user.profile.role = "client"
    user.profile.save()
    cache.delete(f"otp_{email}")

    messages.success(request, "✅ Account created successfully! Please login.")
    return redirect("/login/")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email").lower()
        password = request.POST.get("password")

        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            username = email

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            role = user.profile.role
            if role == 'admin':
                return redirect('/staff/')
            elif role in ['web_pentester', 'mobile_pentester', 'network_analyst', 'soc_analyst']:
                return redirect('/pentester/dashboard/')
            else:
                return redirect('/userdashboard/')
        return render(request, "login/login.html", {"error": "Invalid credentials"})

    return render(request, "login/login.html")


def logout_view(request):
    logout(request)
    return redirect("/login/")


# ================= USER =================
from engagements.models import Engagement, Task
from .models import Report


@login_required(login_url="/login/")
def user_dashboard(request):
    user = request.user
    requests_qs = user.pentest_requests.all().order_by('-created_at')

    # Separate active vs completed engagements
    engagements = Engagement.objects.filter(request__client=user)
    active_engagements = engagements.filter(status='active')
    completed_engagements = engagements.filter(status='completed')

    recent_requests = requests_qs[:5]
    pending_requests = requests_qs.filter(status='pending').count()

    reports_qs = Report.objects.filter(
        engagement__request__client=user
    ).select_related('engagement', 'engagement__request').order_by('-created_at')
    reports_received = reports_qs.count()
    recent_reports = reports_qs[:5]

    has_team = user.team_memberships.exists()

    context = {
        'total_requests': requests_qs.count(),
        'active_projects': active_engagements.count(),
        'completed_projects': completed_engagements.count(),  # ← new
        'recent_requests': recent_requests,
        'pending_requests': pending_requests,
        'reports_received': reports_received,
        'recent_reports': recent_reports,
        'has_team': has_team,
    }
    return render(request, "user/userdashboard.html", context)
@login_required(login_url="/login/")
def user_profile(request):
    profile = request.user.profile  # assuming UserProfile exists
    role = profile.role

    if role in ['web_pentester', 'mobile_pentester', 'network_analyst', 'soc_analyst']:
        template = 'user/operator_profile.html'
    else:
        template = 'user/profile.html'

    context = {'profile': profile}  # add any extra stats if needed
    return render(request, template, context)

from engagements.forms import PentestRequestForm


from django.core.mail import send_mail
from django.conf import settings as django_settings

def _email_request_submitted(pentest_request):
    client = pentest_request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = pentest_request.company_name
    req_type = pentest_request.get_request_type_display()
    req_id = pentest_request.id

    subject = f"[CyberShield] Pentest Request Received – {company}"

    body = f"""Hi {client_name},

Thank you for submitting a pentest request to CyberShield.

We have received your application and it is now pending review by our team.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID : {req_id}
Company    : {company}
Type       : {req_type}
Status     : Pending Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Our security analysts will evaluate your scope and respond within 24–48 hours.
If we need additional information, we’ll reach out to you directly.

You can track the status of your request at any time by logging into the CyberShield portal.

Thank you for choosing CyberShield.

—  
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

def _email_request_submitted(pentest_request):
    client = pentest_request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = pentest_request.company_name
    req_type = pentest_request.get_request_type_display()
    req_id = pentest_request.id

    subject = f"[CyberShield] Pentest Request Received – {company}"

    body = f"""Hi {client_name},

Thank you for submitting a pentest request to CyberShield.

We have received your application and it is now pending review by our team.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID : {req_id}
Company    : {company}
Type       : {req_type}
Status     : Pending Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Our security analysts will evaluate your scope and respond within 24–48 hours.
If we need additional information, we’ll reach out to you directly.

You can track the status of your request at any time by logging into the CyberShield portal.

Thank you for choosing CyberShield.

—  
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )

@login_required
def create_request(request):
    if request.user.profile.role != 'client':
        return redirect('home')

    if request.method == 'POST':
        form = PentestRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.client = request.user
            obj.save()
            _email_request_submitted(obj)   # ← send email
            messages.success(request, "Your request has been submitted. A confirmation email will arrive shortly.")
            return redirect('users:my_requests')
    else:
        form = PentestRequestForm()

    return render(request, 'user/create_request.html', {'form': form})

@login_required
def my_requests(request):
    if request.user.profile.role != 'client':
        return redirect('home')

    requests = request.user.pentest_requests.select_related('engagement').all()
    return render(request, 'user/my_requests.html', {'requests': requests})

from teams.models import Team, TeamMember


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from teams.permissions import user_teams
from engagements.models import Engagement, Task
from users.models import Report
from scanner.models import ScanResult
from teams.models import Team, TeamMember

@login_required(login_url="/login/")
def pentester_dashboard(request):
    user = request.user
    role = user.profile.role

    if role not in ['web_pentester', 'mobile_pentester', 'network_analyst', 'soc_analyst']:
        return redirect('/userdashboard/')

    # Teams the user belongs to (as member or lead)
    teams = user_teams(user)

    # Engagements for those teams
    engagements = Engagement.objects.filter(
        assigned_team__in=teams
    ).select_related('request', 'assigned_team').order_by('-start_date')

    # Tasks from those engagements
    tasks = Task.objects.filter(
        engagement__assigned_team__in=teams
    ).select_related('engagement', 'engagement__request', 'assigned_to').order_by('-created_at')

    # Reports from those engagements (team‑wide)
    reports = Report.objects.filter(
        engagement__assigned_team__in=teams
    ).select_related('engagement', 'engagement__request', 'author').order_by('-created_at')

    # Scan results from those engagements
    scan_results = ScanResult.objects.filter(
        engagement__assigned_team__in=teams
    ).select_related('engagement', 'engagement__request').order_by('-created_at')

    # For team lead specific info (optional, can keep if needed)
    led_teams = Team.objects.filter(team_lead=user, is_active=True)
    is_lead = led_teams.exists()

    # Report counts for the user (personal stats) – optional, can keep or remove
    report_counts = {
        'total': reports.filter(author=user).count(),
        'drafts': reports.filter(author=user, status='draft').count(),
        'submitted': reports.filter(author=user, status='submitted').count(),
        'approved': reports.filter(author=user, status='approved').count(),
    }

    context = {
        'teams': teams,
        'engagements': engagements,
        'tasks': tasks,
        'reports': reports,
        'scan_results': scan_results,
        'led_teams': led_teams,
        'is_lead': is_lead,
        'report_counts': report_counts,
    }
    return render(request, 'user/pentester_dashboard.html', context)

    context = {
        'memberships': memberships,
        'tasks': tasks,
        'is_lead': is_lead,
        'led_teams': led_teams,
        'client_details': client_details,
        'report_counts': report_counts,
    }

    return render(request, 'user/pentester_dashboard.html', context)


from .forms import ReportForm
from django.shortcuts import get_object_or_404


@login_required(login_url="/login/")
def report_create(request):
    user = request.user
    if user.profile.role not in ['web_pentester', 'mobile_pentester', 'network_analyst', 'soc_analyst']:
        return redirect('/userdashboard/')

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            report = form.save(commit=False)
            report.author = user
            action = request.POST.get('action', 'draft')
            report.status = 'submitted' if action == 'submit' else 'draft'

            # Run NOVA analysis on submit
            if report.status == 'submitted':
                from scanner.nova import generate_report_analysis
                report.save()  # need PK before analysis (engagement FK needed)
                report.nova_analysis = generate_report_analysis(report)

            report.save()
            messages.success(
                request,
                '✅ Report submitted — NOVA analysis generated.' if report.status == 'submitted' else '💾 Draft saved.'
            )
            return redirect('users:pentester_dashboard')
    else:
        form = ReportForm(user=user)

    return render(request, 'user/reports.html', {'form': form})


# users/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from teams.permissions import user_teams
from users.models import Report


# users/views.py
@login_required(login_url="/login/")
def report_list(request):
    user = request.user
    # Only allow pentesters/analysts
    if user.profile.role not in ['web_pentester', 'mobile_pentester', 'network_analyst', 'soc_analyst']:
        return redirect('/userdashboard/')

    teams = user_teams(user)
    reports = Report.objects.filter(
        engagement__assigned_team__in=teams
    ).select_related('engagement', 'engagement__request', 'author', 'engagement__assigned_team').order_by('-created_at')

    # Add permission flag for each report
    for report in reports:
        report.can_view = (
            report.author == user
            or getattr(report.engagement.assigned_team, 'team_lead', None) == user
        )

    return render(request, 'user/report_list.html', {'reports': reports})
@login_required(login_url="/login/")
def report_edit(request, pk):
    user = request.user
    report = get_object_or_404(Report, pk=pk, author=user)
    if report.status != 'draft':
        messages.error(request, 'Submitted reports cannot be edited.')
        return redirect('users:report_list')

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, instance=report, user=user)
        if form.is_valid():
            report = form.save(commit=False)
            action = request.POST.get('action', 'draft')
            report.status = 'submitted' if action == 'submit' else 'draft'

            # Run NOVA analysis on submit
            if report.status == 'submitted':
                from scanner.nova import generate_report_analysis
                report.save()
                report.nova_analysis = generate_report_analysis(report)

            report.save()
            messages.success(
                request,
                '✅ Report submitted — NOVA analysis generated.' if report.status == 'submitted' else '💾 Draft updated.'
            )
            return redirect('users:report_list')
    else:
        form = ReportForm(instance=report, user=user)

    return render(request, 'user/reports.html', {'form': form, 'editing': True})


@login_required(login_url="/login/")
def report_delete(request, pk):
    user = request.user
    report = get_object_or_404(Report, pk=pk, author=user)
    if report.status != 'draft':
        messages.error(request, 'Only drafts can be deleted.')
        return redirect('users:report_list')
    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Draft deleted.')
    return redirect('users:report_list')

# ================= PASSWORD RESET =================
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import render, redirect

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "login/password_reset.html")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists
            messages.success(request, "If that email is registered, you'll receive a reset OTP shortly.")
            return redirect("users:login")

        # Rate limiting
        if cache.get(f"pwd_reset_rate_{email}"):
            messages.error(request, "Please wait before requesting another OTP.")
            return render(request, "login/password_reset.html")

        otp = random.randint(100000, 999999)
        cache.set(f"pwd_reset_otp_{email}", str(otp), timeout=600)
        cache.set(f"pwd_reset_rate_{email}", True, timeout=60)

        send_mail(
            "CyberShield Password Reset OTP",
            f"Your OTP to reset your password is {otp}. It expires in 10 minutes.",
            "noreply@cybershield.com",
            [email],
            fail_silently=False,
        )

        # Store email in session for the verify step
        request.session["reset_email"] = email
        messages.success(request, "OTP sent! Please check your email.")
        return redirect("users:password_reset_verify")

    return render(request, "login/password_reset.html")


def password_reset_verify(request):
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Please request a password reset first.")
        return redirect("users:password_reset")

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if not all([otp, password, confirm]):
            messages.error(request, "All fields are required.")
            return render(request, "login/password_reset_confirm.html")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "login/password_reset_confirm.html")

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
            return render(request, "login/password_reset_confirm.html")

        stored_otp = cache.get(f"pwd_reset_otp_{email}")
        if stored_otp != otp:
            messages.error(request, "Invalid or expired OTP.")
            return render(request, "login/password_reset_confirm.html")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("users:password_reset")

        user.set_password(password)
        user.save()
        cache.delete(f"pwd_reset_otp_{email}")
        del request.session["reset_email"]

        messages.success(request, "Password reset successful! Please login with your new password.")
        return redirect("users:login")

    return render(request, "login/password_reset_confirm.html")


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teams.permissions import user_teams
from users.models import Report


# users/views.py

@login_required(login_url="/login/")
def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related('engagement', 'engagement__request', 'author'),
        pk=pk
    )
    user = request.user

    # 1. Author can always see their own report
    if user == report.author:
        return render(request, 'user/report_detail.html', {'report': report})

    # 2. Team lead of the engagement’s team can also see it
    engagement = report.engagement
    team = getattr(engagement, 'assigned_team', None)   # adjust if field name differs
    if team and team.team_lead == user:
        return render(request, 'user/report_detail.html', {'report': report})

    # 3. Everyone else is denied
    messages.error(request, "You don't have permission to view this report.")
    return redirect('users:report_list')

@login_required(login_url="/login/")
def profile_edit(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('users:profile')
    else:
        form = UserEditForm(instance=request.user)

    return render(request, 'user/profile_edit.html', {'form': form})

from django.core.mail import send_mail
from django.conf import settings as django_settings

def _email_request_submitted(pentest_request):
    client = pentest_request.client
    client_email = client.email
    client_name = client.get_full_name() or client.username
    company = pentest_request.company_name
    req_type = pentest_request.get_request_type_display()
    req_id = pentest_request.id

    subject = f"[CyberShield] Pentest Request Received – {company}"

    body = f"""Hi {client_name},

Thank you for submitting a pentest request to CyberShield.

We have received your application and it is now pending review by our team.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID : {req_id}
Company    : {company}
Type       : {req_type}
Status     : Pending Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Our security analysts will evaluate your scope and respond within 24–48 hours.  
If we need additional information, we’ll reach out to you directly.

You can track the status of your request at any time by logging into the CyberShield portal.

Thank you for choosing CyberShield.

—  
CyberShield Security Team
"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cybershield.com'),
        recipient_list=[client_email],
        fail_silently=False,
    )
