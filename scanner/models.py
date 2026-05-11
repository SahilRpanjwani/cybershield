from django.db import models
from engagements.models import Engagement

class ScanResult(models.Model):
    SEVERITY_CHOICES = [
        ("info", "Info"), ("low", "Low"), ("medium", "Medium"),
        ("high", "High"), ("critical", "Critical"),
    ]
    engagement = models.ForeignKey(
        Engagement, on_delete=models.CASCADE, related_name="scan_results"
    )
    module = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES)
    evidence = models.TextField()
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.module} — {self.engagement}"


class NOVAAnalysis(models.Model):
    engagement = models.OneToOneField(
        Engagement, on_delete=models.CASCADE, related_name="nova_analysis"
    )
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NOVA Analysis — {self.engagement}"