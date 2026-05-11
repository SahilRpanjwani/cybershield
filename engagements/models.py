from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class PentestRequest(models.Model):

    REQUEST_TYPE_CHOICES = [
        ('web', 'Web Application'),
        ('network', 'Network Infrastructure'),
        ('mobile', 'Mobile Application'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pentest_requests'
    )
    website_url = models.URLField(
        max_length=500,
        blank=True,         # makes it optional in forms
        null=True,          # allows null in database
        help_text="Official website URL of the target organization"
    )

    company_name = models.CharField(max_length=200)
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES)
    scope_description = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.request_type}"

from teams.models import Team


class Engagement(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]

    request = models.OneToOneField(
        PentestRequest,
        on_delete=models.CASCADE,
        related_name='engagement'
    )

    assigned_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='engagements'
    )

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Engagement for {self.request.company_name}"

class Task(models.Model):

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]   

    engagement = models.ForeignKey(
        Engagement,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
