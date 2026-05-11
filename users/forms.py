from django import forms
from .models import Report
from engagements.models import Engagement

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title', 'engagement', 'severity', 'summary', 'findings', 'attachments']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Web Application Pentest Report – Client Name (Date)'
            }),
            'engagement': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'summary': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Brief overview of the assessment and key findings...'
            }),
            'findings': forms.HiddenInput(),  # Quill handles this
            'attachments': forms.ClearableFileInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Only show engagements where this pentester is on the assigned team
            from teams.models import TeamMember
            user_teams = TeamMember.objects.filter(user=user).values_list('team', flat=True)
            self.fields['engagement'].queryset = Engagement.objects.filter(
                assigned_team__in=user_teams,
                status='active'
            ).select_related('request')
            self.fields['engagement'].label_from_instance = lambda obj: f"{obj.request.company_name} ({obj.request.request_type})"


from django import forms
from django.contrib.auth.models import User

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']