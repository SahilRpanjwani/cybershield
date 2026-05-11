from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from .models import PentestRequest, Engagement, Task

class PentestRequestForm(forms.ModelForm):
    class Meta:
        model = PentestRequest
        fields = ['company_name', 'request_type', 'scope_description', 'website_url']
        widgets = {
            'website_url': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
        }

class EngagementForm(forms.ModelForm):
    class Meta:
        model = Engagement
        fields = ['assigned_team', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date:
            min_allowed = date.today() + timedelta(days=2)
            if start_date < min_allowed:
                raise ValidationError("Start date must be at least 2 days from today.")
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date:
            if end_date <= start_date:
                self.add_error('end_date', "End date must be after the start date.")
        return cleaned_data