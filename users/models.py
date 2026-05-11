from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.TextChoices):
    CLIENT = 'client', 'Client'
    NETWORK_ANALYST = 'network_analyst', 'Network Analyst'
    WEB_PENTESTER = 'web_pentester', 'Web Pentester'
    MOBILE_PENTESTER = 'mobile_pentester', 'Mobile Pentester'
    SOC_ANALYST = 'soc_analyst', 'SOC Analyst'
    ADMIN = 'admin', 'Administrator'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.CLIENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} | {self.role}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


from engagements.models import Engagement


class Report(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('informational', 'Informational'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    engagement = models.ForeignKey(
        Engagement,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    title = models.CharField(max_length=300)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    summary = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    attachments = models.FileField(upload_to='report_attachments/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # NOVA AI analysis generated when pentester submits
    nova_analysis = models.TextField(blank=True, help_text='AI-generated analysis by NOVA')

    # Admin review fields
    admin_notes = models.TextField(blank=True, help_text='Admin notes added during review')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} | {self.author.username} | {self.status}"